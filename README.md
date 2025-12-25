
# AI Interview Assistant

An **AI-powered Interview Assistant** designed to help students and job seekers prepare effectively for technical and HR interviews.  
The system combines **domain-specific knowledge retrieval**, **LLM-based reasoning**, and **speech-enabled mock interviews** to simulate a real interview environment.

---

## Hardware & Performance

This project is **optimized for GPU-based laptops** and AI workstations:

- ✅ Supports GPU acceleration for faster inference
- Suitable for laptops with **CUDA-enabled GPUs**
- Efficient execution for **real-time mock interviews** and LLM responses

---

## Features

### Company & Role-Specific Interview Assistance (RAG-based)

- Select **company name**, **job role**, and **preparation requirements**
- Custom-maintained interview knowledge base
- Uses **Retrieval-Augmented Generation (RAG)** for accurate and grounded responses

---

### Directory

### LLM-Powered Chatbot

- Powered by **Mistral 7B**
- Handles:
  - Role-specific interview questions
  - Company-specific preparation
  - Conceptual doubts
  - General interview guidance
- Produces context-aware, relevant answers

---

### 🎙️ Mock Interview (Speech-to-Speech)

- AI asks interview questions using voice
- User responds via speech
- System evaluates answers and provides:
  - Strengths
  - Weaknesses
  - Improvement suggestions
  - Communication feedback

---

## System Architecture

User Query / Voice Input
↓
Speech-to-Text (Whisper)
↓
Retriever (ChromaDB + RAG)
↓
LLM (Mistral 2B)
↓
Answer / Feedback Generation
↓
Text-to-Speech (Silero)

---

## Tech Stack

| Component       | Technology                           |
| --------------- | ------------------------------------ |
| LLM             | Mistral 7B                           |
| Speech-to-Text  | Whisper                              |
| Text-to-Speech  | Silero                               |
| Vector Database | ChromaDB                             |
| Retrieval       | RAG (Retrieval-Augmented Generation) |
| Backend         | Python                               |

---

## Project Structure

```
├── interview_content/
│
├── outputs/
│ ├── ai_output/
│ ├── stt/
│ ├── tts/
│
├── models/
│ ├──mistral-7b-instruct-v0.2.Q4_K_M.gguf
│
├── static/
│ ├──css/styles.css
│ ├──js/main.js
│
├──templates/
│ ├──aboutus.html
│ ├──features.html
│ ├──hire-ready-ai.html
│ ├──index.html
│ ├──mock-interview.html
│
├── app.py
├── interview_chatbot.py
├── main.py
├── talkingsim_blueprint.py
├── requirements.txt
└── README.md
```

---

### Installation & Setup

### Clone the Repository

```bash
git clone https://github.com/NjadG99/ai-interview-assistant.git
cd ai-interview-assistant
```

**Install Dependencies**

```bash
pip install -r requirements.txt
```

---

### Use Cases

-Campus placement preparation

-Freshers targeting specific companies and roles

-Interview practice on AI laptops without GPUs

-Improving answer clarity and confidence

---
