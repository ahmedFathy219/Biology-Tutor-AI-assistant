# 🧠 ECHO — AI-Powered Voice-Driven Biology Study Assistant

> **Learn. Practice. Improve.**

ECHO is an AI-powered voice-driven biology study assistant designed to make studying more interactive, personalized, and engaging.

ECHO combines **voice interaction, Retrieval-Augmented Generation (RAG), AI-powered quizzes, flashcards, weakness tracking, attention monitoring, and Raspberry Pi hardware** into one integrated study companion.

Instead of simply answering questions, ECHO helps students **learn, practice, review, and improve** through natural voice interaction.

---

## ✨ Features

- 🎙️ **Voice Interaction** — Talk naturally with ECHO without typing.
- 🔊 **Wake Word Detection** — Activate ECHO using the custom **"Hey ECHO"** wake word.
- 📚 **Biology Q&A** — Get answers grounded in the provided biology study materials.
- 🧠 **RAG** — Retrieves relevant course content before generating responses.
- ❓ **Quiz Mode** — Test your knowledge and receive feedback.
- 🗂️ **Flashcard Mode** — Review concepts using AI-generated flashcards.
- 📊 **Weakness Tracking** — Focuses practice on topics where the student performs poorly.
- 👀 **Attention Monitoring** — Detects prolonged distraction or absence using computer vision.
- 🖥️ **TFT Display** — Provides visual feedback throughout the interaction.
- 🔔 **Attention Alert** — Uses a buzzer to alert the student when prolonged distraction is detected.
- 🍓 **Raspberry Pi 5** — Fully integrated with physical hardware.
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
🤖 AI & Technologies
Artificial Intelligence
Llama 3.2:3b — Local Large Language Model
Nomic Embed Text — Text embeddings
ChromaDB — Vector database
LangChain — RAG and LLM orchestration
Voice
Faster-Whisper — Speech-to-Text
OpenWakeWord — Wake-word detection
Piper — Local Text-to-Speech on Raspberry Pi
Pocket-TTS — Text-to-Speech on non-Pi systems
Computer Vision
OpenCV
MediaPipe

Used for head-pose estimation and attention monitoring.

Hardware
Raspberry Pi 5
ST7735 TFT Display
Camera
Microphone
Speaker
Buzzer
🎯 ECHO Modes
📚 Study Mode

Ask ECHO questions about the biology course material using natural voice interaction.

ECHO retrieves relevant information from the biology knowledge base and generates a grounded response using the LLM.

📸 Study Mode

ADD SCREENSHOT HERE

❓ Quiz Mode

ECHO generates biology questions based on the selected topic.

After answering, ECHO evaluates the response and provides feedback.

Quiz performance is also used to improve future topic selection.

📸 Quiz Mode

ADD SCREENSHOT HERE

🗂️ Flashcard Mode

ECHO generates flashcards to help students review biology concepts.

Students can rate each card as:

Easy
Medium
Hard

The system uses the difficulty rating to schedule future reviews.

📸 Flashcard Mode

ADD SCREENSHOT HERE

📊 Weakness-Based Practice

ECHO tracks performance across different biology topics.

Topics where the student performs poorly receive more practice, allowing revision to become more personalized.

📸 Weakness Tracking

ADD SCREENSHOT HERE

👀 Attention Monitoring

ECHO uses the camera with MediaPipe and OpenCV to estimate head orientation and monitor prolonged distraction.

The system identifies three states:

🟢 Focused
🟠 Distracted
🔴 No Face

When prolonged distraction or absence is detected, ECHO provides visual feedback through the TFT display and can activate the buzzer.

📸 Attention Warning

ADD SCREENSHOT HERE

🖥️ TFT Display

The TFT display provides visual feedback throughout the ECHO experience.

The display changes according to the current state of the system.

🏠 Welcome

ADD SCREENSHOT HERE

🎙️ Listening

ADD SCREENSHOT HERE

🧠 Thinking

ADD SCREENSHOT HERE

💬 Answer

ADD SCREENSHOT HERE

❓ Quiz Question

ADD SCREENSHOT HERE

✅ Quiz Result

ADD SCREENSHOT HERE

🗂️ Flashcard Question

ADD SCREENSHOT HERE

💡 Flashcard Answer

ADD SCREENSHOT HERE

📊 Flashcard Difficulty

ADD SCREENSHOT HERE

👀 Attention Warning

ADD SCREENSHOT HERE

🍓 Raspberry Pi 5

ECHO is integrated with a Raspberry Pi 5 to provide a physical study companion.

Hardware Components
Raspberry Pi 5
Microphone
Speaker
ST7735 TFT Display
Camera
Buzzer

The Raspberry Pi version uses hardware-specific implementations for the TFT display, GPIO-controlled buzzer, and local Text-to-Speech.

📸 Complete Hardware Setup

ADD HARDWARE PHOTO HERE

⚙️ Installation
1. Clone the Repository
git clone https://github.com/ahmedFathy219/Biology-Tutor-AI-assistant.git
cd Biology-Tutor-AI-assistant
2. Create a Virtual Environment
Windows
python -m venv venv
venv\Scripts\activate
Raspberry Pi / Linux
python3 -m venv venv
source venv/bin/activate
3. Install Dependencies
pip install -r requirements.txt
4. Install Ollama Models

ECHO uses Ollama to run the local AI models.

ollama pull llama3.2:3b
ollama pull nomic-embed-text

Make sure Ollama is running before starting ECHO.

5. Run ECHO
python src/main.py
📂 Project Structure
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
🔄 System Overview

ECHO brings together several technologies into one integrated learning experience:

Voice Input → Speech Recognition → AI Processing → Learning Mode → Voice & Visual Feedback

The system can operate in:

📚 Study Mode
❓ Quiz Mode
🗂️ Flashcard Mode

while attention monitoring operates alongside the main interaction.

📸 ECHO in Action
🎙️ Voice Interaction

ADD SCREENSHOT HERE

📚 Studying with ECHO

ADD SCREENSHOT HERE

❓ Taking a Quiz

ADD SCREENSHOT HERE

🗂️ Reviewing Flashcards

ADD SCREENSHOT HERE

👀 Attention Detection

ADD SCREENSHOT HERE

🍓 Complete ECHO Setup

ADD HARDWARE PHOTO HERE

🚀 Future Improvements
🌍 Support for additional subjects
🧠 More advanced personalized learning
📈 Detailed learning analytics
🎤 Improved speech recognition in noisy environments
⚡ Reduced response latency
👤 Multiple student profiles
📱 Companion mobile application
🔊 Additional TTS voices
🔄 Improved spaced-repetition algorithms
👥 Project
ECHO — AI-Powered Voice-Driven Biology Study Assistant

Built using:

Python • Llama 3.2 • RAG • ChromaDB • Faster-Whisper • OpenWakeWord • MediaPipe • OpenCV • Raspberry Pi 5

📬 Contact

GitHub:
https://github.com/ahmedFathy219/Biology-Tutor-AI-assistant

Email:
ADD YOUR EMAIL HERE

LinkedIn:
ADD YOUR LINKEDIN HERE

⭐ ECHO

Learn. Practice. Improve.

ECHO brings together AI, voice interaction, adaptive learning, computer vision, and embedded hardware to create an interactive biology study companion.

Instead of functioning only as a question-answering chatbot, ECHO is designed as a complete study assistant that can explain concepts, test knowledge, identify weaker topics, support revision, monitor attention, and provide visual and physical feedback during study sessions.
