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
