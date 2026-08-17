import multiprocessing as mp
import time
from queue import Empty


SHOW_WAKE_GUIDE = "SHOW_WAKE_GUIDE"
SHOW_LISTENING = "SHOW_LISTENING"
SHOW_THINKING = "SHOW_THINKING"
SHOW_ANSWERING = "SHOW_ANSWERING"

SHOW_ATTENTION_WARNING = "SHOW_ATTENTION_WARNING"
CLEAR_ATTENTION_WARNING = "CLEAR_ATTENTION_WARNING"

CLOSE_DISPLAY = "CLOSE_DISPLAY"


# ============================================================
# Physical TFT process
# ============================================================

def _runDisplay(commandQueue):
    """
    Runs the physical ST7735S TFT display.
    """

    import board
    import digitalio

    from PIL import (
        Image,
        ImageDraw,
        ImageFont,
    )

    from adafruit_rgb_display import st7735
    from adafruit_rgb_display.rgb import DummyPin


    print("[Display] Initializing physical TFT...")

    spi = board.SPI()

    cs = digitalio.DigitalInOut(board.D5)
    dc = digitalio.DigitalInOut(board.D25)
    reset = digitalio.DigitalInOut(board.D24)
    backlight = DummyPin()

    # Optional TE pin (V-Sync) if connected to D22
    try:
        te = digitalio.DigitalInOut(board.D22)
        te.direction = digitalio.Direction.INPUT
    except Exception:
        te = None


    # ========================================================
    # ST7735S initialization
    # ========================================================

    display = st7735.ST7735S(
        spi,
        dc=dc,
        cs=cs,
        bl=backlight,
        rst=reset,
        width=160,
        height=128,
        x_offset=2,
        y_offset=1,
        rotation=0,
        baudrate=32000000,  # Boost SPI to 32 MHz for sub-10ms transfers
    )

    WINDOW_WIDTH = display.width
    WINDOW_HEIGHT = display.height

    print(f"[Display] TFT initialized: {WINDOW_WIDTH}x{WINDOW_HEIGHT}")


    # ========================================================
    # Colors
    # ========================================================

    backgroundColor = (11, 16, 32)
    mainTextColor = (255, 255, 255)
    secondaryTextColor = (169, 180, 199)
    accentColor = (127, 219, 255)
    warningColor = (255, 204, 0)


    # ========================================================
    # Fonts
    # ========================================================

    def loadFont(size, bold=False):
        try:
            path = (
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
                if bold
                else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
            )
            return ImageFont.truetype(path, size)
        except Exception:
            return ImageFont.load_default()


    titleFont = loadFont(16, bold=True)
    headingFont = loadFont(13, bold=True)
    bodyFont = loadFont(10)
    smallFont = loadFont(8)


    # ========================================================
    # Display state
    # ========================================================

    attentionOverride = False
    baseCommand = SHOW_WAKE_GUIDE

    pulseSize = 16
    pulseDirection = 1
    lastPulseUpdate = time.monotonic()


    # ========================================================
    # Drawing helpers
    # ========================================================

    def createFrame():
        image = Image.new("RGB", (WINDOW_WIDTH, WINDOW_HEIGHT), backgroundColor)
        draw = ImageDraw.Draw(image)
        return image, draw


    def sendFrame(image, bounding_box=None):
        """
        Sends the frame or cropped sub-region (bounding box) to hardware.
        """
        if te is not None:
            timeout = time.monotonic() + 0.03
            while not te.value and time.monotonic() < timeout:
                time.sleep(0.0005)

        if bounding_box:
            # Crop image to just the dirty region to drastically reduce SPI payload
            cropped = image.crop(bounding_box)
            x0, y0, x1, y1 = bounding_box
            display.image(cropped, rotation=0, x=x0, y=y0)
        else:
            display.image(image, rotation=0)


    def centerText(draw, y, text, font, fill):
        box = draw.textbbox((0, 0), text, font=font)
        textWidth = box[2] - box[0]
        x = (WINDOW_WIDTH - textWidth) // 2
        draw.text((x, y), text, font=font, fill=fill)


    def drawMicrophone(draw, centerX, centerY):
        draw.rounded_rectangle(
            (centerX - 7, centerY - 14, centerX + 7, centerY + 8),
            radius=5,
            outline=accentColor,
            width=2,
        )
        draw.arc(
            (centerX - 12, centerY - 5, centerX + 12, centerY + 14),
            start=0,
            end=180,
            fill=accentColor,
            width=2,
        )
        draw.line(
            (centerX, centerY + 13, centerX, centerY + 20),
            fill=accentColor,
            width=2,
        )
        draw.line(
            (centerX - 6, centerY + 20, centerX + 6, centerY + 20),
            fill=accentColor,
            width=2,
        )


    # ========================================================
    # Screen Renderers
    # ========================================================

    def showWakeGuide(is_animating=False):
        image, draw = createFrame()

        centerText(draw, 8, "ECHO", titleFont, mainTextColor)

        microphoneX = 64
        microphoneY = 65

        # Dynamic pulse radius
        draw.ellipse(
            (
                microphoneX - pulseSize,
                microphoneY - pulseSize,
                microphoneX + pulseSize,
                microphoneY + pulseSize,
            ),
            outline=accentColor,
            width=2,
        )

        drawMicrophone(draw, microphoneX, microphoneY)

        centerText(draw, 105, 'Say "Hey Echo"', headingFont, mainTextColor)
        centerText(draw, 132, "Waiting for you...", smallFont, secondaryTextColor)

        if is_animating:
            # Only update dirty region around mic (48x48 box instead of 160x128)
            dirty_box = (
                microphoneX - 24,
                microphoneY - 24,
                microphoneX + 24,
                microphoneY + 24,
            )
            sendFrame(image, bounding_box=dirty_box)
        else:
            sendFrame(image)


    def showListening(is_animating=False):
        image, draw = createFrame()

        centerText(draw, 8, "ECHO", titleFont, mainTextColor)

        microphoneX = 64
        microphoneY = 65

        draw.ellipse(
            (
                microphoneX - pulseSize,
                microphoneY - pulseSize,
                microphoneX + pulseSize,
                microphoneY + pulseSize,
            ),
            outline=accentColor,
            width=2,
        )

        drawMicrophone(draw, microphoneX, microphoneY)

        centerText(draw, 105, "Listening...", headingFont, mainTextColor)
        centerText(draw, 132, "Ask me a question", smallFont, secondaryTextColor)

        if is_animating:
            dirty_box = (
                microphoneX - 24,
                microphoneY - 24,
                microphoneX + 24,
                microphoneY + 24,
            )
            sendFrame(image, bounding_box=dirty_box)
        else:
            sendFrame(image)


    def showThinking():
        image, draw = createFrame()

        centerText(draw, 10, "ECHO", titleFont, mainTextColor)

        centerX = 64
        for offset in (-18, 0, 18):
            x = centerX + offset
            draw.ellipse((x - 4, 58, x + 4, 66), fill=accentColor)

        centerText(draw, 92, "Thinking...", headingFont, mainTextColor)
        centerText(draw, 122, "Finding the answer", smallFont, secondaryTextColor)

        sendFrame(image)


    def showAnswering(answerText, pageNumber, totalPages):
        image, draw = createFrame()

        centerText(draw, 3, "ECHO", headingFont, mainTextColor)
        centerText(draw, 20, "Answering...", bodyFont, accentColor)
        draw.line((5, 35, 123, 35), fill=secondaryTextColor)

        draw.multiline_text(
            (5, 42),
            answerText,
            font=smallFont,
            fill=mainTextColor,
            spacing=2,
        )

        if totalPages > 1:
            pageText = f"{pageNumber}/{totalPages}"
            draw.text((100, 147), pageText, font=smallFont, fill=secondaryTextColor)

        sendFrame(image)


    def showAttentionWarningScreen():
        image, draw = createFrame()

        centerText(draw, 15, "!", titleFont, warningColor)
        centerText(draw, 52, "PAY ATTENTION", headingFont, warningColor)
        centerText(draw, 88, "Echo is paused", bodyFont, mainTextColor)
        centerText(draw, 118, "Look back when ready", smallFont, secondaryTextColor)

        sendFrame(image)


    # ========================================================
    # Render dispatcher
    # ========================================================

    def renderBaseCommand(command, is_animating=False):
        commandType = command[0] if isinstance(command, tuple) else command

        if commandType == SHOW_WAKE_GUIDE:
            showWakeGuide(is_animating=is_animating)
        elif commandType == SHOW_LISTENING:
            showListening(is_animating=is_animating)
        elif commandType == SHOW_THINKING:
            showThinking()
        elif commandType == SHOW_ANSWERING:
            showAnswering(command[1], command[2], command[3])


    # Render initial screen
    renderBaseCommand(baseCommand, is_animating=False)

    running = True


    # ========================================================
    # Main Display Loop
    # ========================================================

    try:
        while running:
            try:
                while True:
                    command = commandQueue.get_nowait()
                    commandType = command[0] if isinstance(command, tuple) else command

                    if commandType == SHOW_ATTENTION_WARNING:
                        attentionOverride = True
                        showAttentionWarningScreen()

                    elif commandType == CLEAR_ATTENTION_WARNING:
                        attentionOverride = False
                        renderBaseCommand(baseCommand, is_animating=False)

                    elif commandType == CLOSE_DISPLAY:
                        running = False
                        break

                    else:
                        baseCommand = command
                        if not attentionOverride:
                            renderBaseCommand(baseCommand, is_animating=False)

            except Empty:
                pass


            # ------------------------------------------------
            # Animation Loop (Partial Dirty-Box Updates)
            # ------------------------------------------------

            now = time.monotonic()

            if not attentionOverride and (now - lastPulseUpdate >= 0.10):
                baseType = baseCommand[0] if isinstance(baseCommand, tuple) else baseCommand

                if baseType in {SHOW_WAKE_GUIDE, SHOW_LISTENING}:
                    pulseSize += pulseDirection

                    if pulseSize >= 21:
                        pulseDirection = -1
                    elif pulseSize <= 16:
                        pulseDirection = 1

                    # Trigger partial update (sends only 48x48 pixel area)
                    renderBaseCommand(baseCommand, is_animating=True)

                lastPulseUpdate = now

            time.sleep(0.01)

    finally:
        print("[Display] Shutting down TFT.")
        try:
            blank = Image.new("RGB", (WINDOW_WIDTH, WINDOW_HEIGHT), backgroundColor)
            display.image(blank)
        except Exception:
            pass

        for pin in (cs, dc, reset):
            try:
                pin.deinit()
            except Exception:
                pass


# ============================================================
# Echo Display Controller
# ============================================================

class TftDisplay:
    """
    Controller used by Echo to communicate with the physical TFT process.
    """

    def __init__(self):
        self.context = mp.get_context("spawn")
        self.commandQueue = self.context.Queue()
        self.displayProcess = None

    def start(self):
        if self.displayProcess is not None and self.displayProcess.is_alive():
            return

        self.displayProcess = self.context.Process(
            target=_runDisplay,
            args=(self.commandQueue,),
            daemon=True,
        )
        self.displayProcess.start()

    def showWakeGuide(self):
        self.commandQueue.put(SHOW_WAKE_GUIDE)

    def showListening(self):
        self.commandQueue.put(SHOW_LISTENING)

    def showThinking(self):
        self.commandQueue.put(SHOW_THINKING)

    def showAnswering(self, answerText, pageNumber=1, totalPages=1):
        self.commandQueue.put((SHOW_ANSWERING, str(answerText), pageNumber, totalPages))

    def showAttentionWarning(self):
        self.commandQueue.put(SHOW_ATTENTION_WARNING)

    def clearAttentionWarning(self):
        self.commandQueue.put(CLEAR_ATTENTION_WARNING)

    def close(self):
        if self.displayProcess is None:
            return

        if self.displayProcess.is_alive():
            self.commandQueue.put(CLOSE_DISPLAY)
            self.displayProcess.join(timeout=2)

        if self.displayProcess.is_alive():
            self.displayProcess.terminate()
            self.displayProcess.join()