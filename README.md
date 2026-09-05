# Biology-Tutor-AI-assistant
# 🧠 ECHO — AI-Powered Voice-Driven Biology Study Assistant

> **Learn. Practice. Improve.**

ECHO is an **AI-powered, voice-driven biology study assistant** designed to provide students with an interactive and personalized learning experience.

Unlike a traditional chatbot, ECHO combines **voice interaction, Retrieval-Augmented Generation (RAG), active recall, adaptive practice, attention monitoring, and Raspberry Pi hardware** into a single study companion.

ECHO allows students to ask biology questions naturally, practice through quizzes, review concepts using flashcards, receive targeted practice based on their weaknesses, and receive visual and physical feedback while studying.

---

## 📸 Project Overview

**ADD SCREENSHOT HERE**

<!-- Add your main ECHO project photo here -->

---

## ✨ Features

### 🎙️ Voice-Based Interaction

Interact naturally with ECHO using your voice instead of typing.

### 🔊 Wake-Word Detection

Activate ECHO hands-free using the custom **"Hey ECHO"** wake word.

### 📚 Biology-Grounded Question Answering

Ask biology questions and receive answers grounded in the provided biology course materials.

### 🧠 Retrieval-Augmented Generation (RAG)

ECHO retrieves relevant information from the biology knowledge base before generating an answer, helping keep responses grounded in the supplied course material.

### ❓ Quiz Mode

ECHO can generate biology questions based on the selected topic and evaluate the student's answers.

### 🗂️ Flashcard Mode

ECHO generates and reviews flashcards to support active recall and spaced revision.

### 📊 Weakness Tracking

ECHO tracks performance across different biology topics and increases the probability of selecting topics where the student performs poorly.

### 👀 Attention Monitoring

ECHO uses computer vision and head-pose estimation to detect prolonged distraction or absence.

### 🖥️ TFT Display

A TFT display provides visual feedback for system states, questions, answers, quiz results, flashcards, and attention warnings.

### 🔔 Attention Alert

When prolonged distraction or absence is detected, ECHO can provide physical feedback through a buzzer.

### 💻 Cross-Platform Support

ECHO supports both **Windows** development/simulation and **Raspberry Pi 5** hardware deployment.

---

# 🏗️ System Architecture

ECHO is built as a modular system where voice input is converted into text, processed through the AI and RAG pipeline, and converted back into speech.

```text
                         ┌─────────────────────┐
                         │        USER         │
                         │   Voice Interaction │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │     Wake Word       │
                         │    OpenWakeWord     │
                         │     "Hey ECHO"      │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │    Speech-to-Text   │
                         │    Faster-Whisper   │
                         └──────────┬──────────┘
                                    │
                                    ▼
                  ┌──────────────────────────────────┐
                  │            ECHO CORE             │
                  │                                  │
                  │       Command Processing         │
                  │                                  │
                  │     ┌────────┬──────────┐        │
                  │     │        │          │        │
                  │     ▼        ▼          ▼        │
                  │   Study     Quiz     Flashcards  │
                  │    Mode     Mode        Mode     │
                  └──────────────┬───────────────────┘
                                 │
                                 ▼
                       ┌─────────────────────┐
                       │        RAG          │
                       │                     │
                       │ Query Embedding     │
                       │        ↓            │
                       │ ChromaDB Retrieval  │
                       │        ↓            │
                       │ Relevant Context    │
                       └──────────┬──────────┘
                                  │
                                  ▼
                       ┌─────────────────────┐
                       │     Llama 3.2:3b    │
                       │       Ollama         │
                       └──────────┬──────────┘
                                  │
                                  ▼
                       ┌─────────────────────┐
                       │   Generated Answer  │
                       └──────────┬──────────┘
                                  │
                     ┌────────────┴────────────┐
                     ▼                         ▼
              ┌─────────────┐          ┌─────────────┐
              │     TTS     │          │ TFT Display │
              │ Piper /     │          │   ST7735    │
              │ Pocket-TTS  │          └─────────────┘
              └──────┬──────┘
                     │
                     ▼
                  🔊 Speaker
```

---

# 👀 Attention Monitoring Architecture

Attention monitoring operates alongside the main interaction pipeline.

```text
                     Camera
                        │
                        ▼
                     OpenCV
                        │
                        ▼
                MediaPipe FaceMesh
                        │
                        ▼
               Head Pose Estimation
                  Yaw / Pitch / Roll
                        │
                        ▼
                 Attention Tracker
                        │
          ┌─────────────┼─────────────┐
          ▼             ▼             ▼
       Focused      Distracted      No Face
                        │             │
                        └──────┬──────┘
                               ▼
                    ┌───────────────────┐
                    │ Attention Warning │
                    │   TFT + Buzzer    │
                    └───────────────────┘
```

---

# 📚 RAG Knowledge Pipeline

ECHO uses **Retrieval-Augmented Generation** to ground its answers in the provided biology learning materials.

```text
                Biology PDF Materials
                         │
                         ▼
                PDF Text Extraction
                         │
                         ▼
                    OCR Images
                         │
                         ▼
                  Text Chunking
                         │
                         ▼
                 Topic Classification
                         │
                         ▼
                 Nomic Embeddings
                         │
                         ▼
                     ChromaDB
                         │
                         │
                 ───── RUNTIME ─────
                         │
                         ▼
                    User Question
                         │
                         ▼
                  Query Embedding
                         │
                         ▼
              Relevant Chunks Retrieved
                         │
                         ▼
                   Context + Prompt
                         │
                         ▼
                  Llama 3.2:3b
                         │
                         ▼
                  Grounded Answer
```

The knowledge base is created by processing biology PDF materials, extracting text and images, applying OCR when necessary, splitting the content into smaller chunks, generating embeddings, classifying content by topic, and storing the resulting information in **ChromaDB**.

At runtime, ECHO retrieves the most relevant chunks and provides them to the LLM as context before generating the response.

---

# 🤖 Artificial Intelligence

## Llama 3.2:3b

ECHO uses **Llama 3.2:3b** as its main local large language model.

The model is used for:

* Biology question answering
* Quiz question generation
* Student answer evaluation
* Flashcard generation
* Explanations
* Study interactions

The model runs locally through **Ollama**.

---

## 🔎 Nomic Embed Text

**Nomic Embed Text** is used to convert text into vector embeddings.

These embeddings allow ECHO to compare the user's question with stored biology content and retrieve semantically relevant information from ChromaDB.

---

## 🎙️ Faster-Whisper

ECHO uses **Faster-Whisper** for Speech-to-Text.

The user's voice is captured through the microphone, processed, and converted into text before being passed to ECHO's processing pipeline.

---

## 🔊 OpenWakeWord

ECHO uses **OpenWakeWord** together with a custom:

```text
Hey_Echo.onnx
```

wake-word model.

The system continuously listens for the wake word and activates the main interaction pipeline when the wake word is detected.

---

## 🗣️ Text-to-Speech

ECHO supports two local Text-to-Speech implementations.

### Raspberry Pi 5

**Piper**

Piper runs locally on the Raspberry Pi and generates speech using a local voice model.

### Windows / Non-Pi

**Pocket-TTS**

Pocket-TTS runs as a local service. ECHO sends the text to the local TTS server through HTTP and receives generated audio for playback.

---

# 🛠️ Technologies Used

| Technology       | Purpose                                  |
| ---------------- | ---------------------------------------- |
| Python           | Core application and system logic        |
| Llama 3.2:3b     | Local Large Language Model               |
| Ollama           | Local LLM and embedding runtime          |
| LangChain        | RAG pipeline and LLM orchestration       |
| ChromaDB         | Vector database                          |
| Nomic Embed Text | Text embeddings                          |
| Faster-Whisper   | Speech-to-Text                           |
| OpenWakeWord     | Wake-word detection                      |
| Piper            | Local TTS on Raspberry Pi                |
| Pocket-TTS       | Local TTS service on Windows             |
| OpenCV           | Computer vision and camera processing    |
| MediaPipe        | Facial landmark detection                |
| PyAudio          | Microphone and audio capture             |
| Pygame           | Audio playback                           |
| Pillow           | Image processing and TFT rendering       |
| PyMuPDF          | PDF processing                           |
| pytesseract      | OCR                                      |
| NumPy            | Numerical and audio processing           |
| SciPy            | Audio resampling                         |
| scikit-learn     | Cosine similarity / topic classification |
| Pydantic         | Structured LLM outputs                   |
| spidev           | SPI communication with TFT               |
| gpiozero         | Raspberry Pi GPIO control                |
| lgpio            | Raspberry Pi GPIO interface              |
| Tkinter          | Windows display simulation               |
| Git / GitHub     | Version control                          |

---

# 🖥️ Hardware

ECHO is designed to run on a **Raspberry Pi 5** with the following hardware components:

* Raspberry Pi 5
* Microphone
* Speaker
* ST7735 TFT Display
* Camera
* Buzzer

The Raspberry Pi version uses:

* **SPI** for TFT communication
* **GPIO** for hardware control
* **Piper** for local Text-to-Speech
* **OpenCV + MediaPipe** for attention monitoring

---

# 📸 Hardware Setup

**ADD HARDWARE PHOTO HERE**

<!-- Add a photo of your Raspberry Pi 5 setup here -->

---

# 🖥️ TFT Display

ECHO uses an **ST7735 TFT display** to provide visual feedback to the user.

The display can show:

* Wake-word instructions
* Listening state
* Thinking state
* Answering state
* Quiz topics
* Quiz questions
* Quiz results
* Flashcard questions
* Flashcard answers
* Flashcard difficulty
* Attention warnings

### 📸 TFT Display

**ADD TFT SCREENSHOT / PHOTO HERE**

---

# ❓ Quiz Mode

Quiz Mode allows the user to practice biology topics through automatically generated questions.

The process is:

```text
Select Topic
     │
     ▼
Retrieve Biology Content
     │
     ▼
Generate Question
     │
     ▼
Student Answers
     │
     ▼
Evaluate Answer
     │
     ▼
Feedback
     │
     ▼
Update Weakness Tracking
```

The system can also select weaker topics to provide more targeted practice.

### 📸 Quiz Mode

**ADD QUIZ SCREENSHOT HERE**

---

# 🗂️ Flashcard Mode

Flashcard Mode provides another way to revise biology concepts.

ECHO:

1. Selects a topic.
2. Retrieves relevant biology content.
3. Generates a flashcard.
4. Displays and speaks the question.
5. Reveals the answer.
6. Asks the student to rate the difficulty.
7. Schedules the card for future review.

Difficulty levels:

* 🟢 Easy
* 🟡 Medium
* 🔴 Hard

### 📸 Flashcard Mode

**ADD FLASHCARD SCREENSHOT HERE**

---

# 📊 Weakness Tracking

ECHO maintains a weakness score for different biology topics.

The score changes based on quiz performance:

```text
Correct Answer
      │
      ▼
Weakness Score Decreases
```

```text
Incorrect Answer
      │
      ▼
Weakness Score Increases
```

Topics with higher weakness scores have a greater probability of being selected for future practice.

This allows ECHO to provide more targeted revision instead of treating every topic equally.

---

# 👀 Attention Monitoring

ECHO uses the camera to estimate the student's head orientation.

The system tracks:

* **Yaw**
* **Pitch**
* **Roll**

The attention system classifies the student's state as:

* **Focused**
* **Distracted**
* **No Face**

If prolonged distraction or absence is detected, ECHO can:

1. Display an attention warning on the TFT.
2. Activate the buzzer.
3. Resume normal operation once the student returns to a focused state.

### 📸 Attention Monitoring

**ADD ATTENTION MONITORING SCREENSHOT HERE**

---

# 🎙️ Voice Interaction Flow

The complete voice interaction process is:

```text
"Hey ECHO"
     │
     ▼
Wake Word Detection
     │
     ▼
Speech Capture
     │
     ▼
Faster-Whisper
     │
     ▼
Text Command
     │
     ▼
Command Processing
     │
     ▼
RAG / Quiz / Flashcards
     │
     ▼
LLM Processing
     │
     ▼
Generated Response
     │
     ▼
Text-to-Speech
     │
     ▼
Speaker
```

---

# 🔄 Speech Interruption

ECHO also supports interruptible speech.

While ECHO is speaking, the wake-word detector can continue listening.

If the user says:

```text
Hey ECHO
```

ECHO can interrupt the current speech and return control to the user.

This is implemented using concurrent threads and event-based control between the wake-word detector and the TTS engine.

---

# 📁 Project Structure

```text
Biology-Tutor-AI-assistant/
│
├── 📁 data/
│   ├── 📁 chat_histories/
│   └── 📁 chromadb/
│
├── 📁 models/
│   ├── Hey_Echo.onnx
│   ├── attenborough-ref.wav
│   └── attenborough-voice.safetensors
│
├── 📁 scripts/
│   ├── EchoModetests.py
│   ├── WakeWordSetup.py
│   ├── checkMic.py
│   ├── listInputDevices.py
│   ├── stream_test.py
│   ├── testAttention.py
│   ├── testBuzzer.py
│   ├── testDisplay.py
│   ├── testEchoDisplay.py
│   ├── testFlashcardDisplay.py
│   ├── testPocketTTS.py
│   ├── testQuizDisplay.py
│   ├── test_st7735.py
│   └── test_tts.py
│
├── 📁 src/
│   ├── 📁 alerts/
│   │   └── buzzer.py
│   │
│   ├── 📁 attention/
│   │   ├── attention_config.py
│   │   ├── attention_monitor.py
│   │   ├── attention_tracker.py
│   │   └── head_pose.py
│   │
│   ├── 📁 display/
│   │   ├── st7735_display.py
│   │   ├── textPagination.py
│   │   └── tftDisplay.py
│   │
│   ├── 📁 rag/
│   │   ├── chat.py
│   │   ├── flashcard_session.py
│   │   ├── initRag.py
│   │   ├── quizz_session.py
│   │   └── weakness_tracker.py
│   │
│   ├── 📁 stt/
│   │   └── fasterWhisperSTT.py
│   │
│   ├── 📁 tts/
│   │   ├── local_tts_engine.py
│   │   └── tts_engine.py
│   │
│   ├── 📁 utils/
│   │   ├── available_topics.json
│   │   ├── config.json
│   │   └── config_loader.py
│   │
│   ├── 📁 wake_word/
│   │   └── openWakeWordDetector.py
│   │
│   └── main.py
│
├── 📄 requirements.txt
├── 📄 .env
└── 📄 README.md
```

---

# ⚙️ Installation

## 1. Clone the Repository

```bash
git clone https://github.com/ahmedFathy219/Biology-Tutor-AI-assistant.git
cd Biology-Tutor-AI-assistant
```

---

## 2. Create a Virtual Environment

### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

### Linux / Raspberry Pi

```bash
python3 -m venv venv
source venv/bin/activate
```

---

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 4. Install Ollama

ECHO uses Ollama to run the local LLM and embedding model.

Install Ollama and then download the required models:

```bash
ollama pull llama3.2:3b
ollama pull nomic-embed-text
```

Make sure Ollama is running before starting ECHO.

---

## 5. Configure Environment Variables

Create a `.env` file in the project root.

Example:

```env
LLM_MODEL=llama3.2:3b
EMBEDDING_MODEL=nomic-embed-text
OLLAMA_HOST=http://localhost:11434

STT_MODEL=base.en
STT_DEVICE=cpu
STT_COMPUTE_TYPE=int8
STT_SPEECH_THRESHOLD=400
STT_SILENCE_SECONDS=3
STT_WAIT_FOR_SPEECH_SECONDS=5
STT_MAX_RECORDING_SECONDS=7
STT_BEAM_SIZE=3
```

Additional configuration can be used for wake-word detection, microphone selection, attention monitoring, and buzzer settings.

---

# ▶️ Running ECHO

Run the main application using:

```bash
python src/main.py
```

On Raspberry Pi 5, ECHO automatically selects the hardware-specific implementations for:

* TFT display
* GPIO
* Buzzer
* Piper TTS

On non-Raspberry Pi systems, ECHO can use the software display simulation and Pocket-TTS implementation.

---

# 📖 Usage

## 🎙️ Activate ECHO

Say:

```text
Hey ECHO
```

ECHO will activate and listen for your command.

---

## 📚 Ask a Biology Question

Example:

```text
What is the function of mitochondria?
```

ECHO retrieves relevant biology content and generates a grounded response.

---

## ❓ Start a Quiz

Say:

```text
Quiz me
```

or:

```text
Quiz me on Cell Biology
```

ECHO generates a question and evaluates your answer.

---

## 🗂️ Start Flashcards

Say:

```text
Flashcards
```

ECHO generates or retrieves flashcards for revision.

---

## 🧠 Practice Weak Topics

You can ask ECHO to quiz you on your weakest topic.

The weakness tracker uses previous quiz performance to determine which topics should receive more practice.

---

# 📸 Screenshots

## 🏠 Main Interface

**ADD SCREENSHOT HERE**

---

## 🎙️ Voice Interaction

**ADD SCREENSHOT HERE**

---

## 🧠 RAG Question Answering

**ADD SCREENSHOT HERE**

---

## ❓ Quiz Mode

**ADD SCREENSHOT HERE**

---

## 🗂️ Flashcard Mode

**ADD SCREENSHOT HERE**

---

## 👀 Attention Monitoring

**ADD SCREENSHOT HERE**

---

## 🖥️ Raspberry Pi Hardware

**ADD HARDWARE PHOTO HERE**

---

## 📺 TFT Display

**ADD TFT PHOTO HERE**

---

# 📈 Testing

ECHO was tested across its major components and integrated functionality.

| Component                | Result                          |
| ------------------------ | ------------------------------- |
| Wake Word Detection      | 20/20 successful detections     |
| Speech-to-Text           | 18/20 successful transcriptions |
| RAG Question Answering   | Functional                      |
| Quiz Mode                | Functional                      |
| Flashcard Mode           | Functional                      |
| Weakness Tracking        | Functional                      |
| Attention Monitoring     | Successfully tested             |
| TFT Display              | Functional                      |
| Buzzer Alert             | Functional                      |
| Raspberry Pi Integration | Functional                      |

The system was tested both at the individual component level and as an integrated study assistant.

---

# 🧪 Component Testing

The repository includes dedicated testing scripts for individual components.

Examples include:

```text
testAttention.py
testBuzzer.py
testDisplay.py
testEchoDisplay.py
testFlashcardDisplay.py
testQuizDisplay.py
test_st7735.py
test_tts.py
testPocketTTS.py
checkMic.py
listInputDevices.py
```

These scripts were used to test individual hardware and software components before integrating them into the main system.

---

# 🚀 Future Improvements

Potential future improvements include:

* 🌍 Supporting additional subjects beyond biology
* 🎤 Improving speech recognition in noisy environments
* ⚡ Reducing end-to-end response latency
* 🧠 Improving personalized learning strategies
* 📈 Adding detailed learning analytics
* 👤 Supporting multiple student profiles
* 📱 Developing a companion mobile application
* 🔊 Adding more local TTS voices
* 🔄 Improving spaced-repetition algorithms
* ☁️ Optional cloud synchronization
* 🎯 More advanced adaptive quiz generation

---

# 🤝 Contributing

Contributions, suggestions, and improvements are welcome.

To contribute:

```bash
git checkout -b feature/new-feature
```

Make your changes and commit them:

```bash
git add .
git commit -m "Add new feature"
```

Push your branch:

```bash
git push origin feature/new-feature
```

Then open a Pull Request.

---

# ⚠️ Notes

ECHO is an academic project developed as an AI-powered biology study assistant.

The system is designed to provide educational support and should not be treated as a replacement for qualified educational or professional advice.

---

# 👥 Project

**ECHO — AI-Powered Voice-Driven Biology Study Assistant**

Built with:

**Python • Llama 3.2 • RAG • ChromaDB • Faster-Whisper • OpenWakeWord • MediaPipe • OpenCV • Raspberry Pi 5**

---

# 📬 Contact

For questions, collaboration, or project discussions:

**GitHub:**
https://github.com/ahmedFathy219/Biology-Tutor-AI-assistant

**Email:**
ADD YOUR EMAIL HERE

**LinkedIn:**
ADD YOUR LINKEDIN HERE

---

# ⭐ ECHO

> **Learn. Practice. Improve.**

ECHO brings together **voice interaction, grounded AI, adaptive learning, computer vision, and embedded hardware** to create an interactive biology study companion.

Instead of functioning only as a question-answering chatbot, ECHO is designed as a complete study assistant that can **explain concepts, test knowledge, identify weaker topics, support revision, monitor attention, and provide visual and physical feedback** during study sessions.
