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

    The TFT runs in a separate process so display updates
    do not block Echo's main program.
    """

    # --------------------------------------------------------
    # Import Raspberry Pi hardware libraries only inside
    # the display process.
    # --------------------------------------------------------

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


    # ========================================================
    # GPIO / SPI configuration
    # ========================================================

    # TFT CS    -> GPIO8 / CE0 / physical pin 24
    # TFT A0    -> GPIO25      / physical pin 22
    # TFT RESET -> GPIO24      / physical pin 18
    #
    # TFT SDA   -> GPIO10 MOSI / physical pin 19
    # TFT SCK   -> GPIO11 SCLK / physical pin 23
    #
    # TFT LED is connected directly to 3.3V.

    spi = board.SPI()

    cs = digitalio.DigitalInOut(
        board.D5
    )

    dc = digitalio.DigitalInOut(
        board.D25
    )

    reset = digitalio.DigitalInOut(
        board.D24
    )
    backlight = DummyPin()


    # ========================================================
    # ST7735S initialization
    # ========================================================

    display = st7735.ST7735S(
        spi,
        dc=dc,
        cs=cs,
        bl=backlight,
        rst=reset,
        

        # Physical display is 128x160.
        # Rotate 90 degrees to use landscape orientation.
        rotation=90,

        baudrate=16000000,
    )


    WINDOW_WIDTH = display.width
    WINDOW_HEIGHT = display.height


    print(
        f"[Display] TFT initialized: "
        f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}"
    )


    # ========================================================
    # Colors
    # ========================================================

    backgroundColor = (
        11,
        16,
        32,
    )

    mainTextColor = (
        255,
        255,
        255,
    )

    secondaryTextColor = (
        169,
        180,
        199,
    )

    accentColor = (
        127,
        219,
        255,
    )

    warningColor = (
        255,
        204,
        0,
    )


    # ========================================================
    # Fonts
    # ========================================================

    def loadFont(
        size,
        bold=False,
    ):

        try:

            if bold:

                path = (
                    "/usr/share/fonts/truetype/"
                    "dejavu/DejaVuSans-Bold.ttf"
                )

            else:

                path = (
                    "/usr/share/fonts/truetype/"
                    "dejavu/DejaVuSans.ttf"
                )

            return ImageFont.truetype(
                path,
                size,
            )

        except Exception:

            return ImageFont.load_default()


    titleFont = loadFont(
        16,
        bold=True,
    )

    headingFont = loadFont(
        13,
        bold=True,
    )

    bodyFont = loadFont(
        10,
    )

    smallFont = loadFont(
        8,
    )


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
        """
        Create a new blank TFT image.
        """

        image = Image.new(
            "RGB",
            (
                WINDOW_WIDTH,
                WINDOW_HEIGHT,
            ),
            backgroundColor,
        )

        draw = ImageDraw.Draw(
            image
        )

        return image, draw


    def sendFrame(image):
        """
        Send the completed Pillow image to the TFT.
        """

        display.image(
            image
        )


    def centerText(
        draw,
        y,
        text,
        font,
        fill,
    ):
        """
        Draw horizontally centered text.
        """

        box = draw.textbbox(
            (0, 0),
            text,
            font=font,
        )

        textWidth = (
            box[2] - box[0]
        )

        x = (
            WINDOW_WIDTH - textWidth
        ) // 2

        draw.text(
            (
                x,
                y,
            ),
            text,
            font=font,
            fill=fill,
        )


    def drawMicrophone(
        draw,
        centerX,
        centerY,
    ):
        """
        Draw a small microphone icon.
        """

        # Microphone body
        draw.rounded_rectangle(
            (
                centerX - 7,
                centerY - 14,
                centerX + 7,
                centerY + 8,
            ),
            radius=5,
            outline=accentColor,
            width=2,
        )

        # Holder
        draw.arc(
            (
                centerX - 12,
                centerY - 5,
                centerX + 12,
                centerY + 14,
            ),
            start=0,
            end=180,
            fill=accentColor,
            width=2,
        )

        # Stand
        draw.line(
            (
                centerX,
                centerY + 13,
                centerX,
                centerY + 20,
            ),
            fill=accentColor,
            width=2,
        )

        draw.line(
            (
                centerX - 6,
                centerY + 20,
                centerX + 6,
                centerY + 20,
            ),
            fill=accentColor,
            width=2,
        )


    # ========================================================
    # Wake guide
    # ========================================================

    def showWakeGuide():

        image, draw = createFrame()

        centerText(
            draw,
            6,
            "ECHO",
            titleFont,
            mainTextColor,
        )


        microphoneX = (
            WINDOW_WIDTH // 2
        )

        microphoneY = 53


        # Pulsing circle
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


        drawMicrophone(
            draw,
            microphoneX,
            microphoneY,
        )


        centerText(
            draw,
            86,
            'Say "Hey Echo"',
            headingFont,
            mainTextColor,
        )


        centerText(
            draw,
            108,
            "Waiting for you...",
            smallFont,
            secondaryTextColor,
        )


        sendFrame(
            image
        )


    # ========================================================
    # Listening
    # ========================================================

    def showListening():

        image, draw = createFrame()


        centerText(
            draw,
            6,
            "ECHO",
            titleFont,
            mainTextColor,
        )


        microphoneX = (
            WINDOW_WIDTH // 2
        )

        microphoneY = 53


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


        drawMicrophone(
            draw,
            microphoneX,
            microphoneY,
        )


        centerText(
            draw,
            86,
            "Listening...",
            headingFont,
            mainTextColor,
        )


        centerText(
            draw,
            108,
            "Ask me a question",
            smallFont,
            secondaryTextColor,
        )


        sendFrame(
            image
        )


    # ========================================================
    # Thinking
    # ========================================================

    def showThinking():

        image, draw = createFrame()


        centerText(
            draw,
            7,
            "ECHO",
            titleFont,
            mainTextColor,
        )


        centerX = (
            WINDOW_WIDTH // 2
        )


        # Three thinking dots
        for offset in (
            -18,
            0,
            18,
        ):

            x = centerX + offset

            draw.ellipse(
                (
                    x - 4,
                    45,
                    x + 4,
                    53,
                ),
                fill=accentColor,
            )


        centerText(
            draw,
            72,
            "Thinking...",
            headingFont,
            mainTextColor,
        )


        centerText(
            draw,
            97,
            "Finding the best answer",
            smallFont,
            secondaryTextColor,
        )


        sendFrame(
            image
        )


    # ========================================================
    # Answering
    # ========================================================

    def showAnswering(
        answerText,
        pageNumber,
        totalPages,
    ):
        """
        Display one synchronized page of Echo's answer.
        """

        image, draw = createFrame()


        # Header
        centerText(
            draw,
            3,
            "ECHO",
            headingFont,
            mainTextColor,
        )


        centerText(
            draw,
            20,
            "Answering...",
            bodyFont,
            accentColor,
        )


        draw.line(
            (
                5,
                34,
                WINDOW_WIDTH - 5,
                34,
            ),
            fill=secondaryTextColor,
        )


        # Answer
        draw.multiline_text(
            (
                6,
                40,
            ),
            answerText,
            font=bodyFont,
            fill=mainTextColor,
            spacing=2,
        )


        # Page number
        if totalPages > 1:

            pageText = (
                f"{pageNumber}/{totalPages}"
            )

            box = draw.textbbox(
                (0, 0),
                pageText,
                font=smallFont,
            )

            textWidth = (
                box[2] - box[0]
            )

            draw.text(
                (
                    WINDOW_WIDTH
                    - textWidth
                    - 5,

                    WINDOW_HEIGHT
                    - 12,
                ),
                pageText,
                font=smallFont,
                fill=secondaryTextColor,
            )


        sendFrame(
            image
        )


    # ========================================================
    # Attention warning
    # ========================================================

    def showAttentionWarningScreen():

        image, draw = createFrame()


        centerText(
            draw,
            10,
            "!",
            titleFont,
            warningColor,
        )


        centerText(
            draw,
            40,
            "PAY ATTENTION",
            headingFont,
            warningColor,
        )


        centerText(
            draw,
            69,
            "Echo is paused",
            bodyFont,
            mainTextColor,
        )


        centerText(
            draw,
            92,
            "Look back when ready",
            smallFont,
            secondaryTextColor,
        )


        sendFrame(
            image
        )


    # ========================================================
    # Render normal Echo state
    # ========================================================

    def renderBaseCommand(
        command,
    ):

        if isinstance(
            command,
            tuple,
        ):

            commandType = command[0]

        else:

            commandType = command


        if (
            commandType
            == SHOW_WAKE_GUIDE
        ):

            showWakeGuide()


        elif (
            commandType
            == SHOW_LISTENING
        ):

            showListening()


        elif (
            commandType
            == SHOW_THINKING
        ):

            showThinking()


        elif (
            commandType
            == SHOW_ANSWERING
        ):

            answerText = command[1]
            pageNumber = command[2]
            totalPages = command[3]


            showAnswering(
                answerText,
                pageNumber,
                totalPages,
            )


    # ========================================================
    # Initial screen
    # ========================================================

    renderBaseCommand(
        baseCommand
    )


    running = True


    # ========================================================
    # Display loop
    # ========================================================

    try:

        while running:

            # ------------------------------------------------
            # Read all pending commands
            # ------------------------------------------------

            try:

                while True:

                    command = (
                        commandQueue.get_nowait()
                    )


                    if isinstance(
                        command,
                        tuple,
                    ):

                        commandType = (
                            command[0]
                        )

                    else:

                        commandType = command


                    # ----------------------------------------
                    # Attention warning
                    # ----------------------------------------

                    if (
                        commandType
                        == SHOW_ATTENTION_WARNING
                    ):

                        attentionOverride = True

                        showAttentionWarningScreen()


                    # ----------------------------------------
                    # Attention restored
                    # ----------------------------------------

                    elif (
                        commandType
                        == CLEAR_ATTENTION_WARNING
                    ):

                        attentionOverride = False

                        renderBaseCommand(
                            baseCommand
                        )


                    # ----------------------------------------
                    # Close TFT
                    # ----------------------------------------

                    elif (
                        commandType
                        == CLOSE_DISPLAY
                    ):

                        running = False
                        break


                    # ----------------------------------------
                    # Normal Echo state
                    # ----------------------------------------

                    else:

                        baseCommand = command

                        if not attentionOverride:

                            renderBaseCommand(
                                baseCommand
                            )


            except Empty:

                pass


            # ------------------------------------------------
            # Microphone pulse animation
            # ------------------------------------------------

            now = time.monotonic()


            if (
                not attentionOverride
                and now - lastPulseUpdate
                >= 0.12
            ):

                if isinstance(
                    baseCommand,
                    tuple,
                ):

                    baseType = (
                        baseCommand[0]
                    )

                else:

                    baseType = (
                        baseCommand
                    )


                if baseType in {
                    SHOW_WAKE_GUIDE,
                    SHOW_LISTENING,
                }:

                    pulseSize += (
                        pulseDirection
                    )


                    if pulseSize >= 20:

                        pulseDirection = -1


                    elif pulseSize <= 16:

                        pulseDirection = 1


                    renderBaseCommand(
                        baseCommand
                    )


                lastPulseUpdate = now


            time.sleep(
                0.02
            )


    finally:

        print(
            "[Display] Shutting down TFT."
        )


        # Clear screen
        try:

            blank = Image.new(
                "RGB",
                (
                    WINDOW_WIDTH,
                    WINDOW_HEIGHT,
                ),
                backgroundColor,
            )

            display.image(
                blank
            )

        except Exception:

            pass


        # Release GPIO resources
        try:
            cs.deinit()
        except Exception:
            pass

        try:
            dc.deinit()
        except Exception:
            pass

        try:
            reset.deinit()
        except Exception:
            pass


# ============================================================
# Echo display controller
# ============================================================

class TftDisplay:
    """
    Controller used by Echo to communicate with
    the physical Raspberry Pi TFT.
    """

    def __init__(
        self,
    ):

        self.context = (
            mp.get_context(
                "spawn"
            )
        )

        self.commandQueue = (
            self.context.Queue()
        )

        self.displayProcess = None


    def start(
        self,
    ):
        """
        Start the physical TFT process.
        """

        if (
            self.displayProcess
            is not None
            and
            self.displayProcess.is_alive()
        ):
            return


        self.displayProcess = (
            self.context.Process(
                target=_runDisplay,
                args=(
                    self.commandQueue,
                ),
                daemon=True,
            )
        )


        self.displayProcess.start()


    def showWakeGuide(
        self,
    ):

        self.commandQueue.put(
            SHOW_WAKE_GUIDE
        )


    def showListening(
        self,
    ):

        self.commandQueue.put(
            SHOW_LISTENING
        )


    def showThinking(
        self,
    ):

        self.commandQueue.put(
            SHOW_THINKING
        )


    def showAnswering(
        self,
        answerText,
        pageNumber=1,
        totalPages=1,
    ):

        self.commandQueue.put(
            (
                SHOW_ANSWERING,
                str(answerText),
                pageNumber,
                totalPages,
            )
        )


    def showAttentionWarning(
        self,
    ):

        self.commandQueue.put(
            SHOW_ATTENTION_WARNING
        )


    def clearAttentionWarning(
        self,
    ):

        self.commandQueue.put(
            CLEAR_ATTENTION_WARNING
        )


    def close(
        self,
    ):
        """
        Close the TFT safely.
        """

        if (
            self.displayProcess
            is None
        ):

            return


        if (
            self.displayProcess.is_alive()
        ):

            self.commandQueue.put(
                CLOSE_DISPLAY
            )


            self.displayProcess.join(
                timeout=2
            )


        if (
            self.displayProcess.is_alive()
        ):

            self.displayProcess.terminate()

            self.displayProcess.join()