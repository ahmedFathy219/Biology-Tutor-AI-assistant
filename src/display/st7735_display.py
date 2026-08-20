"""
ST7735 TFT Display Driver for Raspberry Pi 5
Landscape mode with auto-scrolling topics and paginated text
"""

import spidev
import lgpio
from PIL import Image, ImageDraw, ImageFont
import time
import textwrap
import threading

# ST7735 Commands
ST7735_SWRESET = 0x01
ST7735_SLPOUT = 0x11
ST7735_NORON = 0x13
ST7735_INVOFF = 0x20
ST7735_INVON = 0x21
ST7735_DISPON = 0x29
ST7735_CASET = 0x2A
ST7735_RASET = 0x2B
ST7735_RAMWR = 0x2C
ST7735_MADCTL = 0x36
ST7735_COLMOD = 0x3A

# Display dimensions (LANDSCAPE MODE)
TFT_WIDTH = 160   # Was 128
TFT_HEIGHT = 128  # Was 160

class ST7735Hardware:
    """Low-level ST7735 SPI driver for Raspberry Pi 5"""
    
    def __init__(self, dc_pin=24, reset_pin=25, 
                 spi_bus=0, spi_device=0, spi_speed=40000000):
        
        self._saved_image = None          # copy of the screen
        self._saved_scroll_mode = None    # 'topics' or 'pages' or None
        self._saved_scroll_data = {}      # store topics/pages and current indices

        # Open GPIO chip (Pi 5 uses gpiochip4)
        self.gpio_chip = lgpio.gpiochip_open(4)
        
        self.dc_pin = dc_pin
        self.reset_pin = reset_pin
        
        # Claim only DC and RESET pins (CS handled by SPI)
        lgpio.gpio_claim_output(self.gpio_chip, dc_pin, 0)
        lgpio.gpio_claim_output(self.gpio_chip, reset_pin, 1)
        
        # SPI setup (CS is handled automatically by spidev)
        self.spi = spidev.SpiDev()
        self.spi.open(spi_bus, spi_device)
        self.spi.max_speed_hz = spi_speed
        self.spi.mode = 0b00
        
        # Initialize display
        self.reset()
        self.init_display()
    
    def reset(self):
        """Hardware reset the display"""
        lgpio.gpio_write(self.gpio_chip, self.reset_pin, 1)
        time.sleep(0.1)
        lgpio.gpio_write(self.gpio_chip, self.reset_pin, 0)
        time.sleep(0.1)
        lgpio.gpio_write(self.gpio_chip, self.reset_pin, 1)
        time.sleep(0.1)
    
    def write_cmd(self, cmd):
        """Send command to display"""
        lgpio.gpio_write(self.gpio_chip, self.dc_pin, 0)
        self.spi.xfer2([cmd])
    
    def write_data(self, data):
        """Send data to display"""
        lgpio.gpio_write(self.gpio_chip, self.dc_pin, 1)
        
        if isinstance(data, int):
            self.spi.xfer2([data])
        elif isinstance(data, list):
            chunk_size = 4096
            for i in range(0, len(data), chunk_size):
                self.spi.xfer2(data[i:i + chunk_size])
        elif isinstance(data, bytes):
            self.spi.xfer2(list(data))
    
    def init_display(self):
        """Initialize display with landscape orientation"""
        self.write_cmd(ST7735_SWRESET)
        time.sleep(0.15)
        self.write_cmd(ST7735_SLPOUT)
        time.sleep(0.5)
        
        # Color mode: 16-bit
        self.write_cmd(ST7735_COLMOD)
        self.write_data(0x05)
        time.sleep(0.01)
        
        # Memory access control for landscape mode
        # MADCTL: MX=1, MY=0, MV=1 for landscape orientation
        self.write_cmd(ST7735_MADCTL)
        self.write_data(0xA0)  # Landscape mode (adjust if your display is upside down)
        time.sleep(0.01)
        
        # Display on
        self.write_cmd(ST7735_NORON)
        time.sleep(0.01)
        self.write_cmd(ST7735_DISPON)
        time.sleep(0.5)
    
    def set_addr_window(self, x0, y0, x1, y1):
        """Set the address window for pixel drawing"""
        self.write_cmd(ST7735_CASET)
        self.write_data([0x00, x0, 0x00, x1])
        
        self.write_cmd(ST7735_RASET)
        self.write_data([0x00, y0, 0x00, y1])
        
        self.write_cmd(ST7735_RAMWR)
    
    def display_image(self, image):
        """Display a PIL Image on the TFT"""
        if image.size != (TFT_WIDTH, TFT_HEIGHT):
            image = image.resize((TFT_WIDTH, TFT_HEIGHT))
        
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        self.set_addr_window(0, 0, TFT_WIDTH - 1, TFT_HEIGHT - 1)
        
        pixel_data = []
        pixels = image.load()
        
        for y in range(TFT_HEIGHT):
            for x in range(TFT_WIDTH):
                r, g, b = pixels[x, y]
                rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
                pixel_data.append((rgb565 >> 8) & 0xFF)
                pixel_data.append(rgb565 & 0xFF)
        
        chunk_size = 4096
        for i in range(0, len(pixel_data), chunk_size):
            self.write_data(pixel_data[i:i + chunk_size])
    
    def cleanup(self):
        """Clean up GPIO and SPI"""
        self.spi.close()
        lgpio.gpiochip_close(self.gpio_chip)


class TftDisplay:
    """
    ST7735 TFT Display Controller for Raspberry Pi 5
    Landscape mode with auto-scrolling and pagination
    """
    
    def __init__(self, dc_pin=24, reset_pin=25, 
                 scroll_rate=1.0, page_rate=3.0):
        self.display = None
        self.dc_pin = dc_pin
        self.reset_pin = reset_pin
        
        # Configuration
        self.scroll_rate = scroll_rate  # Seconds between topic scroll
        self.page_rate = page_rate      # Seconds between page turns
        
        # Threading for auto-scroll and pagination
        self.scroll_thread = None
        self.page_thread = None
        self.stop_scroll = threading.Event()
        self.stop_page = threading.Event()
        
        # Create image buffer
        self.image = Image.new('RGB', (TFT_WIDTH, TFT_HEIGHT), 'black')
        self.draw = ImageDraw.Draw(self.image)
        
        # Load fonts (smaller for landscape)
        try:
            self.font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
            self.font_medium = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
            self.font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11)
            self.font_tiny = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 9)
        except:
            self.font_large = ImageFont.load_default()
            self.font_medium = ImageFont.load_default()
            self.font_small = ImageFont.load_default()
            self.font_tiny = ImageFont.load_default()
        
        # Colors (RGB tuples)
        self.colors = {
            'black': (0, 0, 0),
            'white': (255, 255, 255),
            'red': (255, 0, 0),
            'green': (0, 255, 0),
            'blue': (0, 0, 255),
            'cyan': (0, 255, 255),
            'yellow': (255, 255, 0),
            'orange': (255, 165, 0),
            'accent': (127, 219, 255),
            'secondary': (169, 180, 199),
            'background': (11, 16, 32),
        }
        
        # Current state for scrolling/pagination
        self.current_topics = []
        self.current_topic_index = 0
        self.current_pages = []
        self.current_page_index = 0
    
    def start(self):
        """Initialize the physical display"""
        try:
            self.display = ST7735Hardware(
                dc_pin=self.dc_pin,
                reset_pin=self.reset_pin
            )
            self.clear()
            return True
        except Exception as e:
            print(f"Failed to initialize TFT display: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def clear(self):
        """Clear the display buffer"""
        self.draw.rectangle((0, 0, TFT_WIDTH, TFT_HEIGHT), 
                           fill=self.colors['background'])
        self._update_display()
    
    def _update_display(self):
        """Send the current buffer to the display"""
        if self.display:
            self.display.display_image(self.image)
    
    def _draw_text(self, text, x, y, font, fill='white', align='center'):
        """Draw text with alignment support"""
        if align == 'center':
            bbox = self.draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            x = x - text_width // 2
            y = y - text_height // 2
        elif align == 'right':
            bbox = self.draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            x = x - text_width
        
        self.draw.text((x, y), text, fill=self.colors.get(fill, fill), font=font)
    
    def _draw_microphone(self, center_x, center_y, scale=0.7):
        """Draw simplified microphone icon"""
        # Scale for landscape mode
        s = scale
        
        # Microphone body
        self.draw.rectangle((center_x - 8*s, center_y - 15*s, 
                            center_x + 8*s, center_y + 5*s),
                           outline=self.colors['accent'], width=2)
        
        # Microphone top (arc)
        self.draw.arc((center_x - 8*s, center_y - 20*s, 
                      center_x + 8*s, center_y - 10*s),
                      start=0, end=180, fill=self.colors['accent'], width=2)
        
        # Stand
        self.draw.line((center_x, center_y + 15*s, center_x, center_y + 22*s),
                      fill=self.colors['accent'], width=2)
        self.draw.line((center_x - 8*s, center_y + 22*s, center_x + 8*s, center_y + 22*s),
                      fill=self.colors['accent'], width=2)
    
    def _stop_threads(self):
        """Stop all background threads"""
        self.stop_scroll.set()
        self.stop_page.set()
        
        if self.scroll_thread and self.scroll_thread.is_alive():
            self.scroll_thread.join(timeout=1)
        
        if self.page_thread and self.page_thread.is_alive():
            self.page_thread.join(timeout=1)
        
        self.stop_scroll.clear()
        self.stop_page.clear()
    
    def _start_topic_scroll(self, topics, start_index=0):
        """Start auto-scrolling through topics"""
        self._stop_threads()
        self.current_topics = list(topics)
        self.current_topic_index = start_index % len(self.current_topics)
        
        def scroll_topics():
            while not self.stop_scroll.is_set():
                time.sleep(self.scroll_rate)
                if not self.stop_scroll.is_set():
                    self.current_topic_index = (self.current_topic_index + 1) % len(self.current_topics)
                    self._render_topics_page()
        
        self.scroll_thread = threading.Thread(target=scroll_topics, daemon=True)
        self.scroll_thread.start()
    
    def _start_page_turn(self, pages, start_index=0):
        """Start auto-pagination through pages"""
        self._stop_threads()
        self.current_pages = pages
        self.current_page_index = start_index % len(self.current_pages)
        
        def turn_pages():
            while not self.stop_page.is_set():
                time.sleep(self.page_rate)
                if not self.stop_page.is_set():
                    self.current_page_index = (self.current_page_index + 1) % len(self.current_pages)
                    self._render_page()
        
        self.page_thread = threading.Thread(target=turn_pages, daemon=True)
        self.page_thread.start()
    
    def _render_topics_page(self):
        """Render current topics page with scroll indicator"""
        self.draw.rectangle((0, 0, TFT_WIDTH, TFT_HEIGHT), 
                           fill=self.colors['background'])
        
        # Header
        self._draw_text("Choose a Topic", TFT_WIDTH//2, 10, self.font_small, 'accent')
        self._draw_text("Say the topic you want", TFT_WIDTH//2, 25, self.font_tiny, 'secondary')
        
        # Show 6 topics at a time (vertical list)
        topics_to_show = 6
        start_idx = self.current_topic_index
        visible_topics = []
        
        for i in range(topics_to_show):
            idx = (start_idx + i) % len(self.current_topics)
            visible_topics.append(self.current_topics[idx])
        
        y = 40
        for i, topic in enumerate(visible_topics):
            # Highlight current topic
            if i == 0:
                color = 'accent'
            else:
                color = 'white'
            
            self._draw_text(f"• {topic}", 10, y, self.font_tiny, color, align='left')
            y += 15
        
        # Scroll indicator
        total_topics = len(self.current_topics)
        if total_topics > topics_to_show:
            self._draw_text(f"↓ Scrolling... ({self.current_topic_index + 1}-{self.current_topic_index + topics_to_show} of {total_topics})", 
                          TFT_WIDTH//2, TFT_HEIGHT-10, self.font_tiny, 'secondary')
        
        self._update_display()
    
    def _render_page(self):
        """Render current page with page indicator"""
        if not self.current_pages:
            return
        
        self.draw.rectangle((0, 0, TFT_WIDTH, TFT_HEIGHT), 
                           fill=self.colors['background'])
        
        # Draw page content
        page_text = self.current_pages[self.current_page_index]
        lines = page_text.split('\n')
        
        y = 10
        for line in lines:
            self._draw_text(line, TFT_WIDTH//2, y, self.font_small, 'white')
            y += 20
        
        # Page indicator
        total_pages = len(self.current_pages)
        if total_pages > 1:
            self._draw_text(f"Page {self.current_page_index + 1}/{total_pages}", 
                          TFT_WIDTH//2, TFT_HEIGHT-10, self.font_tiny, 'secondary')
        
        self._update_display()
    
    def _paginate_text(self, text, chars_per_line=28, lines_per_page=5):
        """Split text into pages for display"""
        wrapped_lines = []
        
        for paragraph in text.splitlines():
            paragraph = paragraph.strip()
            if not paragraph:
                wrapped_lines.append("")
                continue
            
            lines = textwrap.wrap(paragraph, width=chars_per_line, 
                                 break_long_words=True, break_on_hyphens=False)
            wrapped_lines.extend(lines)
        
        if not wrapped_lines:
            wrapped_lines = [""]
        
        pages = []
        for i in range(0, len(wrapped_lines), lines_per_page):
            page_lines = wrapped_lines[i:i + lines_per_page]
            pages.append("\n".join(page_lines))
        
        return pages
    
    # Display methods (landscape optimized)
    def showWakeGuide(self):
        """Display wake guide screen"""
        self._stop_threads()
        self.draw.rectangle((0, 0, TFT_WIDTH, TFT_HEIGHT), 
                           fill=self.colors['background'])
        
        self._draw_text("ECHO", TFT_WIDTH//2 - 30, 40, self.font_medium, 'white')
        self._draw_microphone(TFT_WIDTH//2 - 30, 60, 0.6)
        self._draw_text('Say "Hey Echo"', TFT_WIDTH//2 + 30, 50, self.font_small, 'white')
        self._draw_text("Waiting for you...", TFT_WIDTH//2 + 30, 70, self.font_tiny, 'secondary')
        
        self._update_display()
    
    def showListening(self):
        """Display listening screen"""
        self._stop_threads()
        self.draw.rectangle((0, 0, TFT_WIDTH, TFT_HEIGHT), 
                           fill=self.colors['background'])
        
        self._draw_text("ECHO", TFT_WIDTH//2 - 30, 40, self.font_medium, 'white')
        self._draw_microphone(TFT_WIDTH//2 - 30, 60, 0.6)
        self._draw_text("Listening...", TFT_WIDTH//2 + 30, 50, self.font_small, 'white')
        self._draw_text("Ask me a question.", TFT_WIDTH//2 + 30, 70, self.font_tiny, 'secondary')
        
        self._update_display()
    
    def showThinking(self):
        """Display thinking screen"""
        self._stop_threads()
        self.draw.rectangle((0, 0, TFT_WIDTH, TFT_HEIGHT), 
                           fill=self.colors['background'])
        
        self._draw_text("ECHO", TFT_WIDTH//2, 30, self.font_medium, 'white')
        
        # Thinking dots
        for i in range(3):
            x = TFT_WIDTH//2 - 15 + i * 15
            self.draw.ellipse((x, 55, x + 8, 63), 
                             fill=self.colors['accent'])
        
        self._draw_text("Thinking...", TFT_WIDTH//2, 80, self.font_small, 'white')
        self._draw_text("Finding the best answer...", TFT_WIDTH//2, 100, self.font_tiny, 'secondary')
        
        self._update_display()
    
    def showAnswering(self, answerText="", pageNumber=1, totalPages=1):
        """Display answering screen"""
        self._stop_threads()
        self.draw.rectangle((0, 0, TFT_WIDTH, TFT_HEIGHT), 
                           fill=self.colors['background'])
        
        self._draw_text("ECHO", TFT_WIDTH//2, 40, self.font_medium, 'white')
        self._draw_text("Answering...", TFT_WIDTH//2, 75, self.font_small, 'accent')
        
        self._update_display()
    
    def showQuizTime(self, topic=None):
        """Display quiz time screen"""
        self._stop_threads()
        self.draw.rectangle((0, 0, TFT_WIDTH, TFT_HEIGHT), 
                           fill=self.colors['background'])
        
        self._draw_text("QUIZ TIME", TFT_WIDTH//2, 30, self.font_large, 'accent')
        
        if topic:
            self._draw_text(f"Topic: {topic}", TFT_WIDTH//2, 70, self.font_small, 'white')
        
        self._draw_text("Let's see what you know!", TFT_WIDTH//2, 100, self.font_tiny, 'secondary')
        
        self._update_display()
    
    def showQuizTopics(self, topics):
        """Display quiz topics with auto-scroll"""
        self._stop_threads()
        self.current_topics = list(topics)
        self.current_topic_index = 0
        self._render_topics_page()
        self._start_topic_scroll(topics)
    
    def showQuizQuestion(self, questionNumber, topic, question):
        """Display quiz question with pagination if needed"""
        self._stop_threads()
        
        # Header
        self.draw.rectangle((0, 0, TFT_WIDTH, TFT_HEIGHT), 
                           fill=self.colors['background'])
        
        self._draw_text("QUIZ TIME", 5, 10, self.font_tiny, 'accent', align='left')
        self._draw_text(f"Q{questionNumber}", TFT_WIDTH-5, 10, self.font_tiny, 'secondary', align='right')
        self._draw_text(f"Topic: {topic}", 5, 22, self.font_tiny, 'secondary', align='left')
        self.draw.line((5, 35, TFT_WIDTH-5, 35), fill=self.colors['secondary'])
        
        # Paginate question if needed
        pages = self._paginate_text(question, chars_per_line=28, lines_per_page=4)
        
        if len(pages) > 1:
            # Show first page and start pagination
            self.current_pages = pages
            self.current_page_index = 0
            self._render_page()
            self._start_page_turn(pages)
        else:
            # Single page - display directly
            lines = textwrap.wrap(question, width=28)
            y = 55
            for line in lines[:4]:
                self._draw_text(line, TFT_WIDTH//2, y, self.font_small, 'white')
                y += 18
            
            self._draw_text("Your Answer...", TFT_WIDTH//2, TFT_HEIGHT-15, self.font_small, 'accent')
            self._update_display()
    
    def showQuizResult(self, isCorrect, streakValue, message):
        """Display quiz result"""
        self._stop_threads()
        self.draw.rectangle((0, 0, TFT_WIDTH, TFT_HEIGHT), 
                           fill=self.colors['background'])
        
        result_text = "CORRECT!" if isCorrect else "NOT QUITE"
        result_color = 'green' if isCorrect else 'red'
        
        self._draw_text(result_text, TFT_WIDTH//2, 20, self.font_medium, result_color)
        self._draw_text(f"Streak: {streakValue}", TFT_WIDTH//2, 40, self.font_small, 'accent')
        
        # Paginate message
        pages = self._paginate_text(message, chars_per_line=28, lines_per_page=3)
        if len(pages) > 1:
            self.current_pages = pages
            self.current_page_index = 0
            self._render_page()
            self._start_page_turn(pages)
        else:
            lines = textwrap.wrap(message, width=28)
            y = 65
            for line in lines[:3]:
                self._draw_text(line, TFT_WIDTH//2, y, self.font_tiny, 'white')
                y += 15
            self._update_display()
    
    def showQuizMessage(self, message, streakValue=0):
        """Display quiz message with pagination"""
        self._stop_threads()
        self.draw.rectangle((0, 0, TFT_WIDTH, TFT_HEIGHT), 
                           fill=self.colors['background'])
        
        self._draw_text("QUIZ TIME", TFT_WIDTH//2, 15, self.font_small, 'accent')
        self._draw_text("Echo says:", TFT_WIDTH//2, 30, self.font_tiny, 'secondary')
        
        # Paginate message
        pages = self._paginate_text(message, chars_per_line=28, lines_per_page=4)
        if len(pages) > 1:
            self.current_pages = pages
            self.current_page_index = 0
            self._render_page()
            self._start_page_turn(pages)
        else:
            lines = textwrap.wrap(message, width=28)
            y = 50
            for line in lines[:4]:
                self._draw_text(line, TFT_WIDTH//2, y, self.font_small, 'white')
                y += 18
            
            if streakValue > 0:
                self._draw_text(f"Streak: {streakValue}", TFT_WIDTH//2, TFT_HEIGHT-15, 
                               self.font_tiny, 'accent')
            self._update_display()
    
    def showFlashcardMode(self, topic=None):
        """Display flashcard mode screen"""
        self._stop_threads()
        self.draw.rectangle((0, 0, TFT_WIDTH, TFT_HEIGHT), 
                           fill=self.colors['background'])
        
        self._draw_text("FLASHCARD MODE", TFT_WIDTH//2, 30, self.font_large, 'accent')
        
        if topic:
            self._draw_text(f"Topic: {topic}", TFT_WIDTH//2, 65, self.font_small, 'white')
        
        self._draw_text("Study at your own pace", TFT_WIDTH//2, 95, self.font_tiny, 'secondary')
        
        self._update_display()
    
    def showFlashcardTopics(self, topics):
        """Display flashcard topics with auto-scroll"""
        self._stop_threads()
        self.current_topics = list(topics)
        self.current_topic_index = 0
        
        # Add "WEAKEST" option at the top
        self.current_topics.insert(0, "WEAKEST")
        
        self._render_topics_page()
        self._start_topic_scroll(self.current_topics)
    
    def showFlashcardQuestion(self, topic, question):
        """Display flashcard question with pagination"""
        self._stop_threads()
        
        # Header
        self.draw.rectangle((0, 0, TFT_WIDTH, TFT_HEIGHT), 
                           fill=self.colors['background'])
        
        self._draw_text("FLASHCARD", 5, 10, self.font_tiny, 'accent', align='left')
        self._draw_text(str(topic), TFT_WIDTH-5, 10, self.font_tiny, 'secondary', align='right')
        self.draw.line((5, 22, TFT_WIDTH-5, 22), fill=self.colors['secondary'])
        self._draw_text("QUESTION", TFT_WIDTH//2, 30, self.font_tiny, 'secondary')
        
        # Paginate question
        pages = self._paginate_text(question, chars_per_line=28, lines_per_page=4)
        if len(pages) > 1:
            self.current_pages = pages
            self.current_page_index = 0
            self._render_page()
            self._start_page_turn(pages)
        else:
            lines = textwrap.wrap(question, width=28)
            y = 50
            for line in lines[:4]:
                self._draw_text(line, TFT_WIDTH//2, y, self.font_small, 'white')
                y += 18
            
            self._draw_text("Say 'reveal' for answer", TFT_WIDTH//2, TFT_HEIGHT-15, 
                           self.font_tiny, 'accent')
            self._update_display()
    
    def showFlashcardAnswer(self, topic, answer):
        """Display flashcard answer with pagination"""
        self._stop_threads()
        
        # Header
        self.draw.rectangle((0, 0, TFT_WIDTH, TFT_HEIGHT), 
                           fill=self.colors['background'])
        
        self._draw_text("FLASHCARD", 5, 10, self.font_tiny, 'accent', align='left')
        self._draw_text(str(topic), TFT_WIDTH-5, 10, self.font_tiny, 'secondary', align='right')
        self.draw.line((5, 22, TFT_WIDTH-5, 22), fill=self.colors['secondary'])
        self._draw_text("ANSWER", TFT_WIDTH//2, 30, self.font_small, 'accent')
        
        # Paginate answer
        pages = self._paginate_text(answer, chars_per_line=28, lines_per_page=4)
        if len(pages) > 1:
            self.current_pages = pages
            self.current_page_index = 0
            self._render_page()
            self._start_page_turn(pages)
        else:
            lines = textwrap.wrap(answer, width=28)
            y = 50
            for line in lines[:4]:
                self._draw_text(line, TFT_WIDTH//2, y, self.font_small, 'white')
                y += 18
            
            self._draw_text("Rate the difficulty", TFT_WIDTH//2, TFT_HEIGHT-15, 
                           self.font_tiny, 'secondary')
            self._update_display()
    
    def showFlashcardDifficulty(self, topic=None):
        """Display difficulty rating screen"""
        self._stop_threads()
        self.draw.rectangle((0, 0, TFT_WIDTH, TFT_HEIGHT), 
                           fill=self.colors['background'])
        
        self._draw_text("FLASHCARD MODE", TFT_WIDTH//2, 15, self.font_small, 'accent')
        
        if topic:
            self._draw_text(f"Topic: {topic}", TFT_WIDTH//2, 30, self.font_tiny, 'secondary')
        
        self._draw_text("How difficult?", TFT_WIDTH//2, 50, self.font_small, 'white')
        
        # Horizontal difficulty options (better for landscape)
        difficulties = [
            ("EASY", 25, 'green'),
            ("MEDIUM", 80, 'yellow'),
            ("HARD", 135, 'red'),
        ]
        
        for label, x, color in difficulties:
            self.draw.rectangle((x-15, 75, x+15, 100), 
                               outline=self.colors[color], width=2)
            self._draw_text(label, x, 87, self.font_tiny, color)
        
        self._update_display()
    
    def showFlashcardMessage(self, message, topic=None):
        """Display flashcard message with pagination"""
        self._stop_threads()
        self.draw.rectangle((0, 0, TFT_WIDTH, TFT_HEIGHT), 
                           fill=self.colors['background'])
        
        self._draw_text("FLASHCARD MODE", TFT_WIDTH//2, 15, self.font_small, 'accent')
        
        if topic:
            self._draw_text(f"Topic: {topic}", TFT_WIDTH//2, 30, self.font_tiny, 'secondary')
        
        self._draw_text("Echo says:", TFT_WIDTH//2, 45, self.font_tiny, 'secondary')
        
        # Paginate message
        pages = self._paginate_text(message, chars_per_line=28, lines_per_page=4)
        if len(pages) > 1:
            self.current_pages = pages
            self.current_page_index = 0
            self._render_page()
            self._start_page_turn(pages)
        else:
            lines = textwrap.wrap(message, width=28)
            y = 65
            for line in lines[:4]:
                self._draw_text(line, TFT_WIDTH//2, y, self.font_small, 'white')
                y += 18
            self._update_display()
    
    def showAttentionWarning(self):
        # 1. Save the current screen
        self._saved_image = self.image.copy()

        # 2. Remember what auto‑mode was active
        if self.scroll_thread and self.scroll_thread.is_alive():
            self._saved_scroll_mode = 'topics'
            self._saved_scroll_data = {
                'topics': self.current_topics[:],
                'index': self.current_topic_index
            }
        elif self.page_thread and self.page_thread.is_alive():
            self._saved_scroll_mode = 'pages'
            self._saved_scroll_data = {
                'pages': self.current_pages[:],
                'index': self.current_page_index
            }
        else:
            self._saved_scroll_mode = None

        # 3. Stop threads
        self._stop_threads()

        # 4. Draw the warning (your existing code)
        self.draw.rectangle((0, 0, TFT_WIDTH, TFT_HEIGHT), fill=self.colors['background'])
        self._draw_text("!", TFT_WIDTH//2, 25, self.font_large, 'accent')
        self._draw_text("Please Pay Attention", TFT_WIDTH//2, 55, self.font_small, 'white')
        self._draw_text("Echo is paused", TFT_WIDTH//2, 75, self.font_tiny, 'secondary')
        self._draw_text("Continue when ready", TFT_WIDTH//2, 95, self.font_tiny, 'secondary')
        self._update_display()
        
    def clearAttentionWarning(self):
        if self._saved_image is None:
            return

        # 1. Restore the image
        self.image = self._saved_image.copy()
        self._update_display()

        # 2. Resume the previous auto‑mode if it existed
        if self._saved_scroll_mode == 'topics':
            data = self._saved_scroll_data
            self._start_topic_scroll(data['topics'], start_index=data['index'])
        elif self._saved_scroll_mode == 'pages':
            data = self._saved_scroll_data
            self._start_page_turn(data['pages'], start_index=data['index'])

        # 3. Clear saved state
        self._saved_image = None
        self._saved_scroll_mode = None
        self._saved_scroll_data = {}   
    def close(self):
        """Clean up and close display, reset to black."""
        self._stop_threads()
        if self.display:
            # Clear the screen to black
            self.draw.rectangle((0, 0, TFT_WIDTH, TFT_HEIGHT), fill=(0, 0, 0))
            self._update_display()
            # Then clean up hardware
            self.display.cleanup()