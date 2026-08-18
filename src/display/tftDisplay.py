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

SHOW_QUIZ_TIME = "SHOW_QUIZ_TIME"
SHOW_QUIZ_TOPICS = "SHOW_QUIZ_TOPICS"
SHOW_QUIZ_QUESTION = "SHOW_QUIZ_QUESTION"
SHOW_QUIZ_RESULT = "SHOW_QUIZ_RESULT"
SHOW_QUIZ_MESSAGE = "SHOW_QUIZ_MESSAGE"

SHOW_FLASHCARD_MODE = "SHOW_FLASHCARD_MODE"
SHOW_FLASHCARD_TOPICS = "SHOW_FLASHCARD_TOPICS"
SHOW_FLASHCARD_QUESTION = "SHOW_FLASHCARD_QUESTION"
SHOW_FLASHCARD_ANSWER = "SHOW_FLASHCARD_ANSWER"
SHOW_FLASHCARD_DIFFICULTY = "SHOW_FLASHCARD_DIFFICULTY"
SHOW_FLASHCARD_MESSAGE = "SHOW_FLASHCARD_MESSAGE"


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
        Show only that Echo is answering.

        The actual answer is spoken through TTS
        and is not written on the display.
        """

        nonlocal pulseCircle

        pulseCircle = None

        canvas.delete("all")

        # ----------------------------------------------------
        # Echo title
        # ----------------------------------------------------

        canvas.create_text(
            WINDOW_WIDTH // 2,
            90,
            text="ECHO",
            fill=mainTextColor,
            font=("Arial", 28, "bold"),
        )

        # ----------------------------------------------------
        # Answering state
        # ----------------------------------------------------

        canvas.create_text(
            WINDOW_WIDTH // 2,
            170,
            text="Answering...",
            fill=accentColor,
            font=("Arial", 22, "bold"),
        )

    def showQuizTime(topic=None):

        nonlocal pulseCircle

        stopAnswerPaging()
        pulseCircle = None
        canvas.delete("all")

        # ----------------------------------------------------
        # ECHO
        # ----------------------------------------------------

        canvas.create_text(
            WINDOW_WIDTH // 2,
            45,
            text="ECHO",
            fill=mainTextColor,
            font=("Arial", 24, "bold"),
        )

        # ----------------------------------------------------
        # Quiz Time
        # ----------------------------------------------------

        canvas.create_text(
            WINDOW_WIDTH // 2,
            135,
            text="QUIZ TIME",
            fill=accentColor,
            font=("Arial", 34, "bold"),
        )

        # ----------------------------------------------------
        # Selected topic
        # ----------------------------------------------------

        if topic:

            canvas.create_text(
                WINDOW_WIDTH // 2,
                205,
                text=f"Topic: {topic}",
                fill=mainTextColor,
                font=("Arial", 16, "bold"),
            )

        canvas.create_text(
            WINDOW_WIDTH // 2,
            260,
            text="Let's see what you know!",
            fill=secondaryTextColor,
            font=("Arial", 13),
        )

    def showQuizTopics(topics):

        nonlocal pulseCircle

        stopAnswerPaging()
        pulseCircle = None
        canvas.delete("all")

        canvas.create_text(
            WINDOW_WIDTH // 2,
            35,
            text="Choose a Quiz Topic",
            fill=accentColor,
            font=("Arial", 24, "bold"),
        )

        canvas.create_text(
            WINDOW_WIDTH // 2,
            68,
            text="Say the topic you want",
            fill=secondaryTextColor,
            font=("Arial", 12),
        )

        # ----------------------------------------------------
        # Show maximum 10 topics in two columns.
        # ----------------------------------------------------

        visibleTopics = list(topics)[:10]

        leftX = 130
        rightX = 350

        startY = 110
        rowSpacing = 34

        for index, topic in enumerate(visibleTopics):

            column = index % 2
            row = index // 2

            x = (
                leftX
                if column == 0
                else rightX
            )

            y = (
                startY
                + row * rowSpacing
            )

            canvas.create_text(
                x,
                y,
                text=f"• {topic}",
                fill=mainTextColor,
                font=("Arial", 13),
                anchor="w",
            )

        # There are more topics than fit.
        if len(topics) > 10:

            canvas.create_text(
                WINDOW_WIDTH // 2,
                290,
                text=f"+ {len(topics) - 10} more topics",
                fill=secondaryTextColor,
                font=("Arial", 10),
            )
    
    def showQuizQuestion(
        questionNumber,
        topic,
        question,
    ):
        """Display the current quiz question."""

        nonlocal pulseCircle

        stopAnswerPaging()
        pulseCircle = None
        canvas.delete("all")

        # Header
        canvas.create_text(
            25,
            30,
            text="QUIZ TIME",
            fill=accentColor,
            font=("Arial", 18, "bold"),
            anchor="w",
        )

        canvas.create_text(
            WINDOW_WIDTH - 25,
            30,
            text=f"Question {questionNumber}",
            fill=secondaryTextColor,
            font=("Arial", 12, "bold"),
            anchor="e",
        )

        # Topic
        canvas.create_text(
            25,
            65,
            text=f"Topic: {topic}",
            fill=secondaryTextColor,
            font=("Arial", 11),
            anchor="w",
        )

        canvas.create_line(
            25,
            85,
            WINDOW_WIDTH - 25,
            85,
            fill=secondaryTextColor,
        )

        # Question
        canvas.create_text(
            WINDOW_WIDTH // 2,
            165,
            text=question,
            fill=mainTextColor,
            font=("Arial", 17, "bold"),
            width=410,
            justify="center",
        )

        # Waiting for student's answer
        canvas.create_text(
            WINDOW_WIDTH // 2,
            275,
            text="Your Answer...",
            fill=accentColor,
            font=("Arial", 16, "bold"),
        )


    def showQuizResult(
        isCorrect,
        streakValue,
        message,
    ):
        """Display whether the answer was correct plus streak and feedback."""

        nonlocal pulseCircle

        stopAnswerPaging()
        pulseCircle = None
        canvas.delete("all")

        if isCorrect:
            resultText = "CORRECT!"
            resultColor = "#66E0A3"
        else:
            resultText = "NOT QUITE"
            resultColor = "#FF6B6B"

        canvas.create_text(
            WINDOW_WIDTH // 2,
            55,
            text=resultText,
            fill=resultColor,
            font=("Arial", 30, "bold"),
        )

        canvas.create_text(
            WINDOW_WIDTH // 2,
            105,
            text=f"Streak: {streakValue}",
            fill=accentColor,
            font=("Arial", 18, "bold"),
        )

        canvas.create_text(
            WINDOW_WIDTH // 2,
            150,
            text="Echo says:",
            fill=secondaryTextColor,
            font=("Arial", 12, "bold"),
        )

        canvas.create_text(
            WINDOW_WIDTH // 2,
            215,
            text=message,
            fill=mainTextColor,
            font=("Arial", 14),
            width=410,
            justify="center",
        )


    def showQuizMessage(
        message,
        streakValue=0,
    ):
        """Display a spoken Echo message while quiz mode is active."""

        nonlocal pulseCircle

        stopAnswerPaging()
        pulseCircle = None
        canvas.delete("all")

        canvas.create_text(
            WINDOW_WIDTH // 2,
            45,
            text="QUIZ TIME",
            fill=accentColor,
            font=("Arial", 22, "bold"),
        )

        canvas.create_text(
            WINDOW_WIDTH // 2,
            100,
            text="Echo says:",
            fill=secondaryTextColor,
            font=("Arial", 13, "bold"),
        )

        canvas.create_text(
            WINDOW_WIDTH // 2,
            170,
            text=message,
            fill=mainTextColor,
            font=("Arial", 17),
            width=400,
            justify="center",
        )

        if streakValue > 0:
            canvas.create_text(
                WINDOW_WIDTH // 2,
                270,
                text=f"Current Streak: {streakValue}",
                fill=accentColor,
                font=("Arial", 14, "bold"),
            )


    def showFlashcardMode(topic=None):
        """Display the Flashcard Mode intro screen."""

        nonlocal pulseCircle

        stopAnswerPaging()
        pulseCircle = None
        canvas.delete("all")

        canvas.create_text(
            WINDOW_WIDTH // 2,
            45,
            text="ECHO",
            fill=mainTextColor,
            font=("Arial", 24, "bold"),
        )

        canvas.create_text(
            WINDOW_WIDTH // 2,
            135,
            text="FLASHCARD MODE",
            fill=accentColor,
            font=("Arial", 30, "bold"),
        )

        if topic:
            canvas.create_text(
                WINDOW_WIDTH // 2,
                205,
                text=f"Topic: {topic}",
                fill=mainTextColor,
                font=("Arial", 16, "bold"),
            )

        canvas.create_text(
            WINDOW_WIDTH // 2,
            260,
            text="Study at your own pace",
            fill=secondaryTextColor,
            font=("Arial", 13),
        )


    def showFlashcardTopics(topics):
        """Display available flashcard topics plus the Weakest option."""

        nonlocal pulseCircle

        stopAnswerPaging()
        pulseCircle = None
        canvas.delete("all")

        canvas.create_text(
            WINDOW_WIDTH // 2,
            30,
            text="Choose a Flashcard Topic",
            fill=accentColor,
            font=("Arial", 22, "bold"),
        )

        canvas.create_text(
            WINDOW_WIDTH // 2,
            60,
            text="Say a topic or say 'weakest'",
            fill=secondaryTextColor,
            font=("Arial", 11),
        )


        canvas.create_text(
            WINDOW_WIDTH // 2,
            97,
            text="WEAKEST",
            fill=mainTextColor,
            font=("Arial", 12),
        )

        visibleTopics = list(topics)[:8]

        leftX = 120
        rightX = 335
        startY = 145
        rowSpacing = 34

        for index, topic in enumerate(visibleTopics):
            column = index % 2
            row = index // 2

            x = leftX if column == 0 else rightX
            y = startY + row * rowSpacing

            canvas.create_text(
                x,
                y,
                text=f"• {topic}",
                fill=mainTextColor,
                font=("Arial", 12),
                anchor="w",
            )

        if len(topics) > 8:
            canvas.create_text(
                WINDOW_WIDTH // 2,
                292,
                text=f"+ {len(topics) - 8} more topics",
                fill=secondaryTextColor,
                font=("Arial", 10),
            )


    def showFlashcardQuestion(topic, question):
        """Display the flashcard question and reveal instruction."""

        nonlocal pulseCircle

        stopAnswerPaging()
        pulseCircle = None
        canvas.delete("all")

        canvas.create_text(
            25,
            28,
            text="FLASHCARD MODE",
            fill=accentColor,
            font=("Arial", 17, "bold"),
            anchor="w",
        )

        canvas.create_text(
            WINDOW_WIDTH - 25,
            28,
            text=str(topic),
            fill=secondaryTextColor,
            font=("Arial", 11, "bold"),
            anchor="e",
        )

        canvas.create_line(
            25,
            55,
            WINDOW_WIDTH - 25,
            55,
            fill=secondaryTextColor,
        )

        canvas.create_text(
            WINDOW_WIDTH // 2,
            90,
            text="QUESTION",
            fill=secondaryTextColor,
            font=("Arial", 11, "bold"),
        )

        canvas.create_text(
            WINDOW_WIDTH // 2,
            165,
            text=question,
            fill=mainTextColor,
            font=("Arial", 17, "bold"),
            width=410,
            justify="center",
        )

        canvas.create_text(
            WINDOW_WIDTH // 2,
            275,
            text="Say 'reveal' to show the answer",
            fill=accentColor,
            font=("Arial", 14, "bold"),
        )


    def showFlashcardAnswer(topic, answer):
        """Display the revealed answer."""

        nonlocal pulseCircle

        stopAnswerPaging()
        pulseCircle = None
        canvas.delete("all")

        canvas.create_text(
            25,
            28,
            text="FLASHCARD MODE",
            fill=accentColor,
            font=("Arial", 17, "bold"),
            anchor="w",
        )

        canvas.create_text(
            WINDOW_WIDTH - 25,
            28,
            text=str(topic),
            fill=secondaryTextColor,
            font=("Arial", 11, "bold"),
            anchor="e",
        )

        canvas.create_line(
            25,
            55,
            WINDOW_WIDTH - 25,
            55,
            fill=secondaryTextColor,
        )

        canvas.create_text(
            WINDOW_WIDTH // 2,
            95,
            text="ANSWER",
            fill=accentColor,
            font=("Arial", 20, "bold"),
        )

        canvas.create_text(
            WINDOW_WIDTH // 2,
            180,
            text=answer,
            fill=mainTextColor,
            font=("Arial", 16, "bold"),
            width=410,
            justify="center",
        )

        canvas.create_text(
            WINDOW_WIDTH // 2,
            275,
            text="Listen, then rate the difficulty",
            fill=secondaryTextColor,
            font=("Arial", 12),
        )


    def showFlashcardDifficulty(topic=None):
        """Display Easy / Medium / Hard rating choices."""

        nonlocal pulseCircle

        stopAnswerPaging()
        pulseCircle = None
        canvas.delete("all")

        canvas.create_text(
            WINDOW_WIDTH // 2,
            35,
            text="FLASHCARD MODE",
            fill=accentColor,
            font=("Arial", 21, "bold"),
        )

        if topic:
            canvas.create_text(
                WINDOW_WIDTH // 2,
                68,
                text=f"Topic: {topic}",
                fill=secondaryTextColor,
                font=("Arial", 11),
            )

        canvas.create_text(
            WINDOW_WIDTH // 2,
            105,
            text="How difficult was that?",
            fill=mainTextColor,
            font=("Arial", 18, "bold"),
        )

        choices = [
            ("EASY", 40, 140, "#66E0A3"),
            ("MEDIUM", 190, 290, "#FFD166"),
            ("HARD", 340, 440, "#FF6B6B"),
        ]

        for label, x1, x2, color in choices:
            canvas.create_rectangle(
                x1,
                145,
                x2,
                205,
                outline=color,
                width=3,
            )

            canvas.create_text(
                (x1 + x2) // 2,
                175,
                text=label,
                fill=color,
                font=("Arial", 14, "bold"),
            )

        canvas.create_text(
            WINDOW_WIDTH // 2,
            260,
            text="Say: Easy, Medium, or Hard",
            fill=secondaryTextColor,
            font=("Arial", 13, "bold"),
        )


    def showFlashcardMessage(message, topic=None):
        """Display something Echo says while flashcard mode is active."""

        nonlocal pulseCircle

        stopAnswerPaging()
        pulseCircle = None
        canvas.delete("all")

        canvas.create_text(
            WINDOW_WIDTH // 2,
            42,
            text="FLASHCARD MODE",
            fill=accentColor,
            font=("Arial", 22, "bold"),
        )

        if topic:
            canvas.create_text(
                WINDOW_WIDTH // 2,
                77,
                text=f"Topic: {topic}",
                fill=secondaryTextColor,
                font=("Arial", 11),
            )

        canvas.create_text(
            WINDOW_WIDTH // 2,
            120,
            text="Echo says:",
            fill=secondaryTextColor,
            font=("Arial", 13, "bold"),
        )

        canvas.create_text(
            WINDOW_WIDTH // 2,
            195,
            text=message,
            fill=mainTextColor,
            font=("Arial", 17),
            width=400,
            justify="center",
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


        elif commandType == SHOW_QUIZ_TIME:

            topic = command[1]

            showQuizTime(
                topic
            )


        elif commandType == SHOW_QUIZ_TOPICS:

            topics = command[1]

            showQuizTopics(
                topics
            )


        elif commandType == SHOW_QUIZ_QUESTION:

            questionNumber = command[1]
            topic = command[2]
            question = command[3]

            showQuizQuestion(
                questionNumber,
                topic,
                question,
            )


        elif commandType == SHOW_QUIZ_RESULT:

            isCorrect = command[1]
            streakValue = command[2]
            message = command[3]

            showQuizResult(
                isCorrect,
                streakValue,
                message,
            )


        elif commandType == SHOW_QUIZ_MESSAGE:

            message = command[1]
            streakValue = command[2]

            showQuizMessage(
                message,
                streakValue,
            )


        elif commandType == SHOW_FLASHCARD_MODE:

            topic = command[1]

            showFlashcardMode(
                topic
            )


        elif commandType == SHOW_FLASHCARD_TOPICS:

            topics = command[1]

            showFlashcardTopics(
                topics
            )


        elif commandType == SHOW_FLASHCARD_QUESTION:

            topic = command[1]
            question = command[2]

            showFlashcardQuestion(
                topic,
                question,
            )


        elif commandType == SHOW_FLASHCARD_ANSWER:

            topic = command[1]
            answer = command[2]

            showFlashcardAnswer(
                topic,
                answer,
            )


        elif commandType == SHOW_FLASHCARD_DIFFICULTY:

            topic = command[1]

            showFlashcardDifficulty(
                topic
            )


        elif commandType == SHOW_FLASHCARD_MESSAGE:

            message = command[1]
            topic = command[2]

            showFlashcardMessage(
                message,
                topic,
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
    def showQuizTime(
        self,
        topic=None,
    ):
        self.commandQueue.put(
            (
                SHOW_QUIZ_TIME,
                topic,
            )
        )


    def showQuizTopics(
        self,
        topics,
    ):
        self.commandQueue.put(
            (
                SHOW_QUIZ_TOPICS,
                list(topics),
            )
        )


    def showQuizQuestion(
        self,
        questionNumber,
        topic,
        question,
    ):
        self.commandQueue.put(
            (
                SHOW_QUIZ_QUESTION,
                int(questionNumber),
                str(topic),
                str(question),
            )
        )


    def showQuizResult(
        self,
        isCorrect,
        streakValue,
        message,
    ):
        self.commandQueue.put(
            (
                SHOW_QUIZ_RESULT,
                bool(isCorrect),
                int(streakValue),
                str(message),
            )
        )


    def showQuizMessage(
        self,
        message,
        streakValue=0,
    ):
        self.commandQueue.put(
            (
                SHOW_QUIZ_MESSAGE,
                str(message),
                int(streakValue),
            )
        )


    def showFlashcardMode(
        self,
        topic=None,
    ):
        self.commandQueue.put(
            (
                SHOW_FLASHCARD_MODE,
                topic,
            )
        )


    def showFlashcardTopics(
        self,
        topics,
    ):
        self.commandQueue.put(
            (
                SHOW_FLASHCARD_TOPICS,
                list(topics),
            )
        )


    def showFlashcardQuestion(
        self,
        topic,
        question,
    ):
        self.commandQueue.put(
            (
                SHOW_FLASHCARD_QUESTION,
                str(topic),
                str(question),
            )
        )


    def showFlashcardAnswer(
        self,
        topic,
        answer,
    ):
        self.commandQueue.put(
            (
                SHOW_FLASHCARD_ANSWER,
                str(topic),
                str(answer),
            )
        )


    def showFlashcardDifficulty(
        self,
        topic=None,
    ):
        self.commandQueue.put(
            (
                SHOW_FLASHCARD_DIFFICULTY,
                topic,
            )
        )


    def showFlashcardMessage(
        self,
        message,
        topic=None,
    ):
        self.commandQueue.put(
            (
                SHOW_FLASHCARD_MESSAGE,
                str(message),
                topic,
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