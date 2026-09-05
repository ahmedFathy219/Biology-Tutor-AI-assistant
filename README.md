# 🧠 ECHO — AI-Powered Voice-Driven Biology Study Assistant

> **Learn. Practice. Improve.**

ECHO is an AI-powered voice-driven biology study assistant designed to make studying more interactive, personalized, and engaging.

It combines **voice interaction, Retrieval-Augmented Generation (RAG), AI-powered quizzes, flashcards, weakness tracking, attention monitoring, and Raspberry Pi hardware** into one integrated study companion.

Instead of simply answering questions, ECHO helps students **learn, practice, review, and improve** through natural voice interaction.

---

## ✨ Features

- 🎙️ **Voice Interaction** — Talk naturally with ECHO without typing.
- 🔊 **Wake Word Detection** — Activate ECHO using the custom **"Hey ECHO"** wake word.
- 📚 **Biology Q&A** — Get answers grounded in the provided biology study materials.
- 🧠 **RAG** — Retrieves relevant course content before generating responses.
- ❓ **Quiz Mode** — Test your knowledge and receive feedback.
- 🗂️ **Flashcard Mode** — Review concepts using AI-generated flashcards.
- 📊 **Weakness Tracking** — Gives more practice to topics where the student struggles.
- 👀 **Attention Monitoring** — Detects prolonged distraction or absence using computer vision.
- 🖥️ **TFT Display** — Provides visual feedback throughout the interaction.
- 🔔 **Attention Alert** — Uses a buzzer to alert the student when prolonged distraction is detected.
- 🍓 **Raspberry Pi 5** — Integrated with physical hardware.
- 💻 **Cross-Platform** — Supports Windows and Raspberry Pi 5.

---

# 🏗️ How ECHO Works

ECHO follows a simple voice-based interaction pipeline:

```text
User
  │
  ▼
"Hey ECHO"
  │
  ▼
Wake Word Detection
  │
  ▼
Speech-to-Text
  │
  ▼
Command Processing
  │
  ├──────────────┬───────────────┐
  ▼              ▼               ▼
Study          Quiz          Flashcards
Mode           Mode             Mode
  │              │               │
  └──────────────┴───────────────┘
                 │
                 ▼
              RAG + LLM
                 │
                 ▼
          Generated Response
                 │
          ┌──────┴──────┐
          ▼             ▼
         TTS       TFT Display
          │
          ▼
       Speaker
```

---

# 🤖 AI & Technologies

## Artificial Intelligence

- **Llama 3.2:3b** — Local Large Language Model
- **Nomic Embed Text** — Text embeddings
- **ChromaDB** — Vector database
- **LangChain** — RAG and LLM orchestration

## Voice

- **Faster-Whisper** — Speech-to-Text
- **OpenWakeWord** — Wake-word detection
- **Piper** — Local Text-to-Speech on Raspberry Pi
- **Pocket-TTS** — Local Text-to-Speech on Windows/non-Pi systems

## Computer Vision

- **OpenCV**
- **MediaPipe**

Used for head-pose estimation and attention monitoring.

## Hardware

- Raspberry Pi 5
- ST7735 TFT Display
- Camera
- Microphone
- Speaker
- Buzzer

---

# 🎯 ECHO Modes

## 📚 Study Mode

Ask ECHO questions about the biology course material using natural voice interaction.

ECHO retrieves relevant information from the biology knowledge base and generates a grounded response using the LLM.

---

## ❓ Quiz Mode

ECHO generates biology questions based on the selected topic.

After answering, ECHO evaluates the response and provides feedback.

Quiz performance is also used to improve future topic selection.

---

## 🗂️ Flashcard Mode

ECHO generates flashcards to help students review biology concepts.

Students can rate each card as:

- Easy
- Medium
- Hard

The difficulty rating affects when the card will appear again and contributes to topic-level weakness tracking.

---

## 📊 Weakness-Based Practice

ECHO tracks performance across different biology topics.

Topics where the student performs poorly are identified as weaker areas and prioritized in later revision.

---

# 👀 Attention Monitoring

ECHO uses the camera with **MediaPipe and OpenCV** to estimate head orientation and monitor prolonged distraction.

The system identifies three states:

- 🟢 **Focused**
- 🟠 **Distracted**
- 🔴 **No Face**

Attention monitoring uses temporal thresholds rather than classifying distraction from a single frame.

When prolonged distraction or face absence is detected, ECHO provides visual feedback through the TFT display and activates the buzzer on Raspberry Pi.

### 📸 Attention Detection

**ADD ATTENTION SCREENSHOT HERE**

---

# 🖥️ TFT Display

The TFT display provides visual feedback throughout the ECHO experience.

It changes according to the current state of the system, including:

- 🏠 Welcome
- 🎙️ Listening
- 🧠 Thinking
- 💬 Answer
- ❓ Quiz Question
- ✅ Quiz Result
- 🗂️ Flashcard Question
- 💡 Flashcard Answer
- 📊 Flashcard Difficulty
- 👀 Attention Warning

### 📸 TFT Display States

**ADD ONE COLLAGE IMAGE HERE**

> The collage should contain the different TFT states instead of adding a separate screenshot for every state.

---

# 🍓 Raspberry Pi 5

ECHO is integrated with a **Raspberry Pi 5** to provide a physical study companion.

### Hardware Components

- Raspberry Pi 5
- Microphone
- Speaker
- ST7735 TFT Display
- Camera
- Buzzer

The Raspberry Pi implementation uses a physical SPI TFT display, USB audio devices, a camera, a GPIO-controlled buzzer, and Piper for local Text-to-Speech.

### 📸 Complete Hardware Setup

**ADD HARDWARE PHOTO HERE**

---

# ⚙️ Installation

## 1. Clone the Repository

```bash
git clone https://github.com/ahmedFathy219/Biology-Tutor-AI-assistant.git
cd Biology-Tutor-AI-assistant
```

## 2. Create a Virtual Environment

### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

### Raspberry Pi / Linux

```bash
python3 -m venv venv
source venv/bin/activate
```

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

## 4. Install Ollama Models

ECHO uses Ollama to run the local AI models.

```bash
ollama pull llama3.2:3b
ollama pull nomic-embed-text
```

Make sure Ollama is running before starting ECHO.

---

# 🔊 Pocket-TTS Setup

On Windows/non-Raspberry Pi systems, ECHO uses **Pocket-TTS** for local Text-to-Speech.

Before running ECHO, start the required local services in separate terminals.

### Terminal 1 — Pocket-TTS Server

Open a PowerShell terminal and run:

```powershell
pocket-tts serve --host 127.0.0.1 --port 8000
```

Keep this terminal running.

### Terminal 2 — Voice File Server

Open a second PowerShell terminal in the project directory and run:

```powershell
python -m http.server 8001 --bind 127.0.0.1
```

Keep this terminal running.

### Terminal 3 — Start ECHO

Open a third terminal in the project directory and run:

```powershell
python src/main.py
```

The communication flow is:

```text
ECHO
  │
  ▼
Pocket-TTS Server
127.0.0.1:8000
  │
  ▼
Generated Voice
  │
  ▼
Voice File Server
127.0.0.1:8001
  │
  ▼
ECHO → Speaker
```

> **Note:** The Pocket-TTS and voice file server terminals must remain open while ECHO is running.

### Raspberry Pi

The Raspberry Pi implementation uses **Piper** for local Text-to-Speech and does not require the Pocket-TTS setup above.

---

# ▶️ Usage

Once ECHO is running, interact with it using your voice.

### 1. Activate ECHO

Say:

```text
Hey ECHO
```

ECHO enters the listening state and waits for your request.

### 2. Study

Ask a biology question naturally:

```text
What is the function of mitochondria?
```

ECHO retrieves relevant biology content and provides an AI-generated explanation through the speaker and display.

### 3. Quiz

Say:

```text
Start a quiz
```

Choose or provide a biology topic and answer the generated question verbally.

ECHO evaluates the answer, provides feedback, and updates your performance.

### 4. Flashcards

Say:

```text
Start flashcards
```

ECHO presents a question for active recall.

After attempting the question, request the answer and rate the card:

```text
Easy
Medium
Hard
```

The rating affects when the card will appear again.

### 5. Follow-Up Questions

ECHO supports follow-up questions without requiring the wake word again.

For example:

```text
Hey ECHO
What is DNA?

What about RNA?
```

### 6. Interrupting ECHO

If ECHO is speaking, saying:

```text
Hey ECHO
```

can interrupt the current response and return the system to the listening state.

---

# 📂 Project Structure

```text
Biology-Tutor-AI-assistant/
│
├── data/
│   ├── chat_histories/
│   └── chromadb/
│
├── models/
│   ├── Hey_Echo.onnx
│   ├── attenborough-ref.wav
│   └── attenborough-voice.safetensors
│
├── scripts/
│
├── src/
│   ├── alerts/
│   ├── attention/
│   ├── display/
│   ├── rag/
│   ├── stt/
│   ├── tts/
│   ├── utils/
│   ├── wake_word/
│   └── main.py
│
├── requirements.txt
└── README.md
```

---

# 📸 ECHO in Action

## 🎙️ Voice Interaction

**ADD ONE SCREENSHOT HERE**

## 📚 Learning with ECHO

**ADD ONE SCREENSHOT HERE**

## 🍓 Complete ECHO Setup

**ADD HARDWARE PHOTO HERE**

---

# 🚀 Future Improvements

The future development of ECHO focuses on improving personalization, interaction, and accessibility:

- 📄 **User-Uploaded Documents** — Allow students to upload their own study materials and use them as additional sources for the RAG knowledge base.
- 👁️ **Gaze-Based Attention Monitoring** — Extend attention detection beyond head pose by incorporating gaze information with adjustable alert thresholds.
- 🎙️ **Improved Interruption Handling** — Further improve the ability to interrupt and resume ECHO's speech naturally during interactions.
- 🖥️ **Full Graphical User Interface** — Develop a complete GUI to provide a richer visual interface for interacting with ECHO and viewing learning progress.
- 🔔 **Windows Audio Alert** — Add an optional Windows audio alert that matches the physical buzzer behavior available on the Raspberry Pi.

---

# 🛠️ Project Stack

**Python • Llama 3.2 • RAG • ChromaDB • Nomic Embeddings • LangChain • Faster-Whisper • OpenWakeWord • Pocket-TTS • Piper • MediaPipe • OpenCV • Raspberry Pi 5**

---

# 📬 Contact

**GitHub:**  
https://github.com/ahmedFathy219/Biology-Tutor-AI-assistant

**Email:**  
mohamedkh8806@gmail.com

**LinkedIn:**  
www.linkedin.com/in/mohamed-khaled-142872345</sub>

---

# ⭐ ECHO

> **Learn. Practice. Improve.**

ECHO brings together **AI, voice interaction, adaptive learning, computer vision, and embedded hardware** to create an interactive biology study companion.

Instead of functioning only as a question-answering chatbot, ECHO is designed as a complete study assistant that can **explain concepts, test knowledge, identify weaker topics, support revision, monitor attention, and provide visual and physical feedback** during study sessions.
