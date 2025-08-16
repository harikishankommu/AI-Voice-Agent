"""
main.py - AI Voice Agent with Gemini LLM, Murf TTS, and AssemblyAI Transcription
"""

# ================================
# 1. Imports
# ================================
import os
from dotenv import load_dotenv
import google.generativeai as genai
import assemblyai as aai
import uuid

from fastapi import FastAPI, File, UploadFile, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles

from murf import Murf
from murf.core.api_error import ApiError


# ================================
# 2. Environment Variables
# ================================
load_dotenv()
chat_history_store = {}
# -- Gemini API Key --
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("Missing GEMINI_API_KEY. Please set it in .env file.")
genai.configure(api_key=GEMINI_API_KEY)

# -- AssemblyAI API Key --
ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")
if not ASSEMBLYAI_API_KEY:
    raise RuntimeError("Missing ASSEMBLYAI_API_KEY. Please set it in your .env file or environment.")
aai.settings.api_key = ASSEMBLYAI_API_KEY

# -- Murf API Key --
MURF_API_KEY = os.getenv("MURF_API_KEY")
if not MURF_API_KEY:
    raise RuntimeError("Missing MURF_API_KEY. Please set it in your .env file.")


# ================================
# 3. Model & Client Initialization
# ================================
# Gemini LLM Model
llm_model = genai.GenerativeModel("gemini-1.5-flash")

# Murf TTS Client
client = Murf(api_key=MURF_API_KEY)


# ================================
# 4. FastAPI App Setup
# ================================
app = FastAPI()

# Enable CORS for all origins (development use)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend files
app.mount("/Frontend", StaticFiles(directory="Frontend", html=True), name="frontend")


# ================================
# 5. Routes - General
# ================================
@app.get("/")
def serve_home():
    """Serve index.html at root"""
    return FileResponse(os.path.join("Frontend","index.html"))

@app.get("/ping")
def ping():
    """Health check endpoint"""
    return {"message": "server running successfully"}


# ================================
# 6. Routes - Murf TTS
# ================================
class TextInput(BaseModel):
    text: str

@app.post("/generate_audio_sdk")
async def generate_audio_sdk(input: TextInput):
    """Generate TTS audio from text using Murf API"""
    try:
        res = client.text_to_speech.generate(
            text=input.text,
            voice_id="en-US-natalie",
            format="MP3"
        )
        return {"audio_url": res.audio_file}
    except ApiError as e:
        return {"error": f"{e.status_code}", "detail": e.body}


# ================================
# 7. Routes - File Upload
# ================================
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post("/upload_audio")
async def upload_audio(file: UploadFile = File(...)):
    """Upload audio file and store it locally"""
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)
    return JSONResponse({
        "filename": file.filename,
        "content_type": file.content_type,
        "size_bytes": len(content)
    })


# ================================
# 8. Routes - AssemblyAI Transcription
# ================================
@app.post("/transcribe/file")
async def transcribe_file(file: UploadFile = File(...)):
    """Transcribe audio file to text using AssemblyAI"""
    audio_data = await file.read()
    transcriber = aai.Transcriber()
    transcript = transcriber.transcribe(audio_data)
    if transcript.status == aai.TranscriptStatus.error:
        return JSONResponse({"error": transcript.error}, status_code=500)
    return JSONResponse({"text": transcript.text})


# ================================
# 9. Routes - Echo Bot with TTS
# ================================
@app.post("/tts/echo")
async def tts_echo(file: UploadFile = File(...)):
    """Transcribe audio, then echo back as TTS"""
    # Save file locally
    temp_path = f"{UPLOAD_DIR}/{file.filename}"
    with open(temp_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # Transcribe
    transcriber = aai.Transcriber()
    transcript = transcriber.transcribe(temp_path)

    if transcript.status == aai.TranscriptStatus.error:
        return JSONResponse({"error": transcript.error}, status_code=500)

    text = transcript.text

    # Generate TTS
    try:
        res = client.text_to_speech.generate(
            text=text,
            voice_id="en-US-natalie",
            format="MP3"
        )
        return JSONResponse({"audio_url": res.audio_file})
    except ApiError as e:
        return JSONResponse({"error": e.body}, status_code=e.status_code)



# ================================
# Chat History Store (in-memory)
# ================================
# Stores conversations as: { session_id: [ {"role": "...", "content": "..."} ] }



from fastapi import Body, Form

@app.post("/agent/chat/{session_id}")
async def agent_chat(
    session_id: str,
    file: UploadFile = File(None),   # For audio from FormData
    text: str = Form(None)           # Accepts text from FormData too
):
    try:
        # -------------------------
        # Handle voice input
        # -------------------------
        if file:
            temp_path = os.path.join(UPLOAD_DIR, file.filename)
            with open(temp_path, "wb") as f:
                f.write(await file.read())

            transcriber = aai.Transcriber()
            transcript = transcriber.transcribe(temp_path)
            if transcript.status == aai.TranscriptStatus.error:
                return JSONResponse({"error": transcript.error}, status_code=500)
            user_text = transcript.text

        # -------------------------
        # Handle text input
        # -------------------------
        elif text:
            user_text = text.strip()

        else:
            return JSONResponse({"error": "No file or text provided"}, status_code=400)

        # Get previous chat history
        history = chat_history_store.get(session_id, [])
        history.append({"role": "user", "content": user_text})

        # Prepare conversation text
        conversation_text = "\n".join([f"{m['role']}: {m['content']}" for m in history])

        # Generate LLM reply
        llm_response = llm_model.generate_content(conversation_text)
        bot_text = llm_response.text

        # Save bot reply
        history.append({"role": "assistant", "content": bot_text})
        chat_history_store[session_id] = history

        # Generate speech from bot text
        res = client.text_to_speech.generate(
            text=bot_text,
            voice_id="en-US-natalie",
            format="MP3"
        )

        return {
            "transcription": user_text,
            "llm_text": bot_text,
            "audio_url": res.audio_file
        }

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)




# ================================
# Chat History Store (in-memory)
# ================================
chat_history_store = {}

FALLBACK_MESSAGE = "I'm having trouble connecting right now."
FALLBACK_AUDIO_PATH = os.path.join(UPLOAD_DIR, "/Frontend/fallback.mp3") # Put fallback.mp3 in your 'static' folder


# Generate fallback audio once at startup if not already present
def generate_fallback_audio():
    if not os.path.exists(FALLBACK_AUDIO_PATH):
        try:
            res = client.text_to_speech.generate(
                text=FALLBACK_MESSAGE,
                voice_id="en-US-natalie",
                format="MP3"
            )
            with open(FALLBACK_AUDIO_PATH, "wb") as f:
                f.write(res.audio_file.read())
        except Exception as e:
            print("❌ Failed to pre-generate fallback audio:", e)

generate_fallback_audio()


@app.post("/agent/chat/{session_id}")
async def agent_chat(session_id: str, file: UploadFile = File(...)):
    try:
        # 1. Save audio locally
        temp_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(temp_path, "wb") as f:
            f.write(await file.read())

        # 2. Transcribe with AssemblyAI (STT)
        try:
            transcriber = aai.Transcriber()
            transcript = transcriber.transcribe(temp_path)
            if transcript.status == aai.TranscriptStatus.error:
                raise Exception(transcript.error)
            user_text = transcript.text
        except Exception as e:
            print("❌ STT failed:", e)
            return {
                "transcription": "(STT failed)",
                "llm_text": FALLBACK_MESSAGE,
                "audio_url": f"/uploads/{os.path.basename(FALLBACK_AUDIO_PATH)}"
            }

        # 3. Get previous messages
        history = chat_history_store.get(session_id, [])
        history.append({"role": "user", "content": user_text})

        # 4. Prepare prompt for LLM
        conversation_text = "\n".join([f"{m['role']}: {m['content']}" for m in history])

        # 5. LLM response
        try:
            llm_response = llm_model.generate_content(conversation_text)
            bot_text = llm_response.text
        except Exception as e:
            print("❌ LLM failed:", e)
            bot_text = FALLBACK_MESSAGE

        # 6. Append bot reply to history
        history.append({"role": "assistant", "content": bot_text})
        chat_history_store[session_id] = history

        # 7. TTS generation
        try:
            res = client.text_to_speech.generate(
                text=bot_text,
                voice_id="en-US-natalie",
                format="MP3"
            )
            audio_filename = f"{uuid.uuid4()}.mp3"
            audio_path = os.path.join(UPLOAD_DIR, audio_filename)
            with open(audio_path, "wb") as f:
                f.write(res.audio_file.read())
            audio_url = f"/uploads/{audio_filename}"
        except Exception as e:
            print("❌ TTS failed:", e)
            audio_url = f"/uploads/{os.path.basename(FALLBACK_AUDIO_PATH)}"

        return {
            "transcription": user_text,
            "llm_text": bot_text,
            "audio_url": audio_url
        }

    except Exception as e:
         # ==== This block handles ALL errors ====
        print("Error in pipeline:", e)
        return JSONResponse(
            {
                "transcription": user_text or "",
                "llm_text": FALLBACK_MESSAGE,
                "audio_url": FALLBACK_AUDIO_PATH
            },
            status_code=500
        )
