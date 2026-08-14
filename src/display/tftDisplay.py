import multiprocessing as mp
from queue import Empty
import tkinter as tk
import textwrap



WINDOW_WIDTH = 480
WINDOW_HEIGHT = 320

SHOW_WAKE_GUIDE = "SHOW_WAKE_GUIDE"
SHOW_LISTENING = "SHOW_LISTENING"
SHOW_THINKING = "SHOW_THINKING"
SHOW_ANSWERING = "SHOW_ANSWERING"
CLOSE_DISPLAY = "CLOSE_DISPLAY"
SHOW_ATTENTION_WARNING = "SHOW_ATTENTION_WARNING"
CLEAR_ATTENTION_WARNING = "CLEAR_ATTENTION_WARNING"


def _drawMicrophone(canvas, centerX, centerY):
    """
    Draw a simple microphone icon using shapes.

    We draw it ourselves instead of using an emoji so that
    the appearance does not depend on the computer's emoji font.
    """

    # Microphone body
    canvas.create_rectangle(
        centerX - 14,
        centerY - 30,
        centerX + 14,
        centerY + 10,
        outline="#7FDBFF",
        width=3,
    )

    # Rounded-looking microphone top
    canvas.create_arc(
        centerX - 14,
        centerY - 38,
        centerX + 14,
        centerY - 18,
        start=0,
        extent=180,
        outline="#7FDBFF",
        width=3,
        style="arc",
    )

    # Outer microphone holder
    canvas.create_arc(
        centerX - 25,
        centerY - 5,
        centerX + 25,
        centerY + 30,
        start=180,
        extent=180,
        outline="#7FDBFF",
        width=3,
        style="arc",
    )

    # Stand
    canvas.create_line(
        centerX,
        centerY + 28,
        centerX,
        centerY + 42,
        fill="#7FDBFF",
        width=3,
    )

    canvas.create_line(
        centerX - 15,
        centerY + 42,
        centerX + 15,
        centerY + 42,
        fill="#7FDBFF",
        width=3,
    )


def _paginateText(
    text,
    charactersPerLine=48,
    linesPerPage=8,
):
    """
    Split Echo's full answer into multiple pages
    that fit on the TFT display.
    """

    wrappedLines = []

    # ----------------------------------------------------
    # Process EVERY paragraph in the answer
    # ----------------------------------------------------

    for paragraph in text.splitlines():

        paragraph = paragraph.strip()

        # Preserve blank lines between paragraphs
        if not paragraph:

            wrappedLines.append("")

            continue

        # Wrap long paragraphs into TFT-sized lines
        lines = textwrap.wrap(
            paragraph,
            width=charactersPerLine,
            break_long_words=True,
            break_on_hyphens=False,
        )

        wrappedLines.extend(lines)

    # ----------------------------------------------------
    # Make sure there is something to display
    # ----------------------------------------------------

    if not wrappedLines:

        wrappedLines = [""]

    # ----------------------------------------------------
    # Divide all lines into pages
    # ----------------------------------------------------

    pages = []

    for index in range(
        0,
        len(wrappedLines),
        linesPerPage,
    ):

        pageLines = wrappedLines[
            index:index + linesPerPage
        ]

        pages.append(
            "\n".join(pageLines)
        )

    # IMPORTANT:
    # This must be OUTSIDE both loops.
    return pages

def _runDisplay(commandQueue):
    """
    Runs the laptop TFT simulator.

    This function runs in a separate process so the display
    will NOT block Echo's main program.
    """

    root = tk.Tk()

    root.title("Echo TFT Simulator")

    root.geometry(
        f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}"
    )

    root.resizable(False, False)

    backgroundColor = "#0B1020"
    mainTextColor = "#FFFFFF"
    secondaryTextColor = "#A9B4C7"
    accentColor = "#7FDBFF"

    canvas = tk.Canvas(
        root,
        width=WINDOW_WIDTH,
        height=WINDOW_HEIGHT,
        bg=backgroundColor,
        highlightthickness=0,
    )

    canvas.pack()

    pulseCircle = None
    pulseSize = 35
    pulseDirection = 1
    answerPageTimer = None
    attentionOverride = False
    baseCommand = SHOW_WAKE_GUIDE
    microphoneX = WINDOW_WIDTH // 2
    microphoneY = 145

    def stopAnswerPaging():
        """
        Stop any automatic page switching from
        a previous Answering screen.
        """

        nonlocal answerPageTimer

        if answerPageTimer is not None:

            try:

                root.after_cancel(
                    answerPageTimer
                )

            except tk.TclError:

                pass

            answerPageTimer = None


    def showWakeGuide():
        """
        Display the screen telling the student to say:
        Hey Echo
        """

        nonlocal pulseCircle
        
        stopAnswerPaging()

        canvas.delete("all")

        # Echo title
        canvas.create_text(
            WINDOW_WIDTH // 2,
            45,
            text="ECHO",
            fill=mainTextColor,
            font=("Arial", 28, "bold"),
        )

        # Pulsing circle behind microphone
        pulseCircle = canvas.create_oval(
            microphoneX - 35,
            microphoneY - 35,
            microphoneX + 35,
            microphoneY + 35,
            outline=accentColor,
            width=2,
        )

        # Microphone icon
        _drawMicrophone(
            canvas,
            microphoneX,
            microphoneY,
        )

        # Main instruction
        canvas.create_text(
            WINDOW_WIDTH // 2,
            225,
            text='Say "Hey Echo"',
            fill=mainTextColor,
            font=("Arial", 20, "bold"),
        )

        # Secondary instruction
        canvas.create_text(
            WINDOW_WIDTH // 2,
            265,
            text="Waiting for you...",
            fill=secondaryTextColor,
            font=("Arial", 12),
        )
    def showListening():
        nonlocal pulseCircle
        nonlocal pulseSize
        nonlocal pulseDirection
        stopAnswerPaging()

        canvas.delete("all")

        pulseSize = 35
        pulseDirection = 1

        canvas.create_text(
            WINDOW_WIDTH // 2,
            45,
            text="ECHO",
            fill=mainTextColor,
            font=("Arial", 28, "bold"),
        )

        pulseCircle = canvas.create_oval(
            microphoneX - pulseSize,
            microphoneY - pulseSize,
            microphoneX + pulseSize,
            microphoneY + pulseSize,
            outline=accentColor,
            width=2,
        )

        _drawMicrophone(
            canvas,
            microphoneX,
            microphoneY,
        )   

        canvas.create_text(
            WINDOW_WIDTH // 2,
            225,
            text="Listening...",
            fill=mainTextColor,
            font=("Arial", 20, "bold"),
        )

        canvas.create_text(
            WINDOW_WIDTH // 2,
            265,
            text="Ask me a question.",
            fill=secondaryTextColor,
            font=("Arial", 12),
        )

    def showThinking():
        nonlocal pulseCircle
        stopAnswerPaging()
        pulseCircle = None

        canvas.delete("all")

        canvas.create_text(
            WINDOW_WIDTH // 2,
            45,
            text="ECHO",
            fill=mainTextColor,
            font=("Arial", 28, "bold"),
        )

        canvas.create_oval(
            205,
            115,
            225,
            135,
            fill=accentColor,
            outline=accentColor,
        )

        canvas.create_oval(
            230,
            115,
            250,
            135,
            fill=accentColor,
            outline=accentColor,
        )

        canvas.create_oval(
            255,
            115,
            275,
            135,
            fill=accentColor,
            outline=accentColor,
        )  

        canvas.create_text(
            WINDOW_WIDTH // 2,
            195,
            text="Thinking...",
            fill=mainTextColor,
            font=("Arial", 20, "bold"),
        )

        canvas.create_text(
            WINDOW_WIDTH // 2,
            235,
            text="Finding the best answer...",
            fill=secondaryTextColor,
            font=("Arial", 12),
        )

    def showAnswering(
        answerText,
        pageNumber,
        totalPages,
    ):
        """
        Display one synchronized page of Echo's answer.
        """

        nonlocal pulseCircle

        pulseCircle = None

        canvas.delete("all")

        # ----------------------------------------------------
        # Header
        # ----------------------------------------------------

        canvas.create_text(
            WINDOW_WIDTH // 2,
            30,
            text="ECHO",
            fill=mainTextColor,
            font=("Arial", 22, "bold"),
        )

        canvas.create_text(
            WINDOW_WIDTH // 2,
            65,
            text="Answering...",
            fill=accentColor,
            font=("Arial", 16, "bold"),
        )

        canvas.create_line(
            30,
            90,
            WINDOW_WIDTH - 30,
            90,
            fill=secondaryTextColor,
        )

        # ----------------------------------------------------
        # Current page
        # ----------------------------------------------------

        canvas.create_text(
            30,
            110,
            text=answerText,
            fill=mainTextColor,
            font=("Arial", 13),
            width=WINDOW_WIDTH - 60,
            anchor="nw",
            justify="left",
        )

        # ----------------------------------------------------
        # Page number
        # ----------------------------------------------------

        if totalPages > 1:

            canvas.create_text(
                WINDOW_WIDTH - 30,
                WINDOW_HEIGHT - 20,
                text=f"{pageNumber}/{totalPages}",
                fill=secondaryTextColor,
                font=("Arial", 10),
                anchor="e",
            )

    def showAttentionWarningScreen():

        nonlocal pulseCircle

        pulseCircle = None

        canvas.delete("all")

        canvas.create_text(
            WINDOW_WIDTH // 2,
            70,
            text="!",
            fill=accentColor,
            font=("Arial", 48, "bold"),
        )

        canvas.create_text(
            WINDOW_WIDTH // 2,
            155,
            text="Please Pay Attention",
            fill=mainTextColor,
            font=("Arial", 22, "bold"),
        )

        canvas.create_text(
            WINDOW_WIDTH // 2,
            205,
            text="Echo is paused",
            fill=secondaryTextColor,
            font=("Arial", 14),
        )

        canvas.create_text(
            WINDOW_WIDTH // 2,
            245,
            text="We'll continue when you're ready",
            fill=secondaryTextColor,
            font=("Arial", 12),
        )



    def animatePulse():
        """
        Makes the circle around the microphone slowly
        expand and shrink.
        """

        nonlocal pulseSize
        nonlocal pulseDirection

        if pulseCircle is not None:

            pulseSize += pulseDirection

            if pulseSize >= 43:
                pulseDirection = -1

            elif pulseSize <= 35:
                pulseDirection = 1

            canvas.coords(
                pulseCircle,
                microphoneX - pulseSize,
                microphoneY - pulseSize,
                microphoneX + pulseSize,
                microphoneY + pulseSize,
            )

        root.after(
            45,
            animatePulse,
        )

    def renderBaseCommand(command):
        """
        Render one of Echo's normal screens.
        """

        if isinstance(command, tuple):
            commandType = command[0]
        else:
            commandType = command


        if commandType == SHOW_WAKE_GUIDE:

            showWakeGuide()


        elif commandType == SHOW_LISTENING:

            showListening()


        elif commandType == SHOW_THINKING:

            showThinking()


        elif commandType == SHOW_ANSWERING:

            answerText = command[1]
            pageNumber = command[2]
            totalPages = command[3]

            showAnswering(
                answerText,
                pageNumber,
                totalPages,
            )


    def checkCommands():

        nonlocal attentionOverride
        nonlocal baseCommand

        try:

            while True:

                command = commandQueue.get_nowait()

                if isinstance(command, tuple):
                    commandType = command[0]
                else:
                    commandType = command


                # ----------------------------------------
                # Student became distracted
                # ----------------------------------------

                if commandType == SHOW_ATTENTION_WARNING:

                    attentionOverride = True

                    showAttentionWarningScreen()


                # ----------------------------------------
                # Student is attentive again
                # ----------------------------------------

                elif commandType == CLEAR_ATTENTION_WARNING:

                    attentionOverride = False

                    # Restore whatever Echo was
                    # displaying before the warning.
                    renderBaseCommand(
                        baseCommand
                    )


                # ----------------------------------------
                # Close display
                # ----------------------------------------

                elif commandType == CLOSE_DISPLAY:

                    root.destroy()
                    return


                # ----------------------------------------
                # Normal Echo screen
                # ----------------------------------------

                else:

                    # Remember the most recent normal screen.
                    baseCommand = command

                    # Only draw it if the attention warning
                    # is not currently covering the TFT.
                    if not attentionOverride:

                        renderBaseCommand(
                            baseCommand
                        )


        except Empty:

            pass

        root.after(
            50,
            checkCommands,
        )


    # Show the wake guide immediately
    showWakeGuide()

    # Start animation
    animatePulse()

    # Start checking for commands
    checkCommands()

    # ESC can close the simulator
    root.bind(
        "<Escape>",
        lambda event: root.destroy(),
    )

    root.mainloop()


class TftDisplay:
    """
    Controller used by Echo to communicate with
    the laptop TFT simulator.
    """

    def __init__(self):

        self.context = mp.get_context("spawn")

        self.commandQueue = self.context.Queue()

        self.displayProcess = None


    def start(self):
        """
        Start the display window.
        """

        if (
            self.displayProcess is not None
            and self.displayProcess.is_alive()
        ):
            return

        self.displayProcess = self.context.Process(
            target=_runDisplay,
            args=(self.commandQueue,),
            daemon=True,
        )

        self.displayProcess.start()


    def showWakeGuide(self):
        """
        Tell the display to show the:
        Say "Hey Echo"
        screen.
        """

        self.commandQueue.put(
            SHOW_WAKE_GUIDE
        )

    def showListening(self):
        """
        Tell the display to show the:
        Listening...
        screen.
        """

        self.commandQueue.put(
            SHOW_LISTENING
        )

    def showThinking(self):
        """
        Tell the display to show the:
        Thinking...
        screen.
        """

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
    def showAttentionWarning(self):

        self.commandQueue.put(
            SHOW_ATTENTION_WARNING
        )


    def clearAttentionWarning(self):

        self.commandQueue.put(
            CLEAR_ATTENTION_WARNING
        )
    


    def close(self):
        """
        Close the display safely.
        """

        if self.displayProcess is None:
            return

        if self.displayProcess.is_alive():

            self.commandQueue.put(
                CLOSE_DISPLAY
            )

            self.displayProcess.join(
                timeout=1
            )

        if self.displayProcess.is_alive():

            self.displayProcess.terminate()

            self.displayProcess.join()