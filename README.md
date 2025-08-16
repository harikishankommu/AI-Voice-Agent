# 30 Days of AI Voice Agents

A fully functional AI-powered voice agent that can interact with users via text or voice. The agent uses **STT (Speech-to-Text)**, **LLM (Large Language Model)**, and **TTS (Text-to-Speech)** to provide responses in a natural voice.

---

## Table of Contents

- [Project Overview] 
- [Features]  
- [Technologies Used / Tech Stack]  
- [Architecture]  
- [Installation & Setup]  
- [Usage] 
- [API Endpoints]   
- [Contributing] 
- [License]

---

## Project Overview

This project was built as part of the **30 Days of AI Voice Agents** challenge. It demonstrates the creation of a conversational AI that can:

1. Record user voice input.
2. Transcribe voice to text using a transcription service.
3. Send text to an LLM to generate responses.
4. Convert responses into a natural voice using TTS.
5. Maintain session-based chat history.

---

## Features

- **Text Input**: Type a message and get a spoken response.
- **Voice Input**: Record your voice and get a spoken response.
- **Echo Bot**: Record and immediately playback your voice (Day 4–7).
- **Conversational Bot**: Full conversational AI with chat history support.
- **Dynamic Session Management**: Tracks chat history per session.
- **Error Handling**: Provides fallback messages if APIs fail.

---

## Technologies Used / Tech Stack

The 30 Days of AI Voice Agents project uses a combination of frontend, backend, APIs, and supporting tools to create a fully functional voice agent:

**Frontend:**  
- **HTML5 & CSS3** – Structure and styling of the web interface, including responsive design and dark-glass card layout.  
- **JavaScript (Vanilla)** – Handles UI interactions, fetch requests to backend endpoints, audio playback, and dynamic updates.  
- **MediaRecorder API** – Captures microphone input for recording user voice.  

**Backend:**  
- **Python 3.x** – Main server-side programming language.  
- **FastAPI** – Web framework used to create API endpoints for TTS, STT, LLM, and chat session management.  
- **Uvicorn** – ASGI server to run the FastAPI application.  

**APIs & Services:**  
- **AssemblyAI** – Speech-to-Text (STT) service for transcribing recorded audio.  
- **Murf AI** – Text-to-Speech (TTS) service to generate natural-sounding audio from text.  
- **Google Gemini API** – Large Language Model (LLM) to generate AI responses for the conversational agent.  

**Other Tools / Libraries:**  
- **Fetch API** – Used in the frontend to send HTTP requests to the server.  
- **Session Storage / Global In-Memory Storage** – Maintains per-session chat history.  
- **Environment Variables (.env)** – Securely store API keys without exposing them in code.  

---

## Architecture

The project follows a **client-server architecture** with clearly defined responsibilities:

### Frontend (Client)
- User interacts via text input or voice recording.
- Sends requests to backend endpoints.
- Plays back generated audio in the `<audio>` element.

### Backend (Server)
- FastAPI endpoints handle text and audio requests.
- Audio input is transcribed using AssemblyAI.
- Transcription is sent to an LLM (Google Gemini) to generate responses.
- Response text is converted into audio using Murf AI TTS.
- Returns the audio URL to the frontend for playback.

### Session Management
- Chat history is stored per session to maintain context.
- Session ID is passed as a query parameter for tracking conversations.

---

## Endpoints

Here are the main API endpoints used in the project:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/transcribe/file` | POST | Accepts audio file, transcribes using AssemblyAI, returns text. |
| `/llm/query` | POST | Accepts text input (or transcribed audio), sends it to Google Gemini, returns LLM response. |
| `/tts/echo` | POST | Accepts text (or transcribed audio), generates Murf AI voice audio, returns audio URL. |
| `/agent/chat/{session_id}` | POST | Maintains session-based chat history, handles full conversational flow (STT → LLM → TTS). |

---


