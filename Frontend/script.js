/* ===============================
   Merged JS for Unified Chat UI
   - Handles both text and voice input
   - Communicates with backend endpoints:
       /generate_audio_sdk  (POST JSON {text})       → Convert text to audio
       /tts/echo            (POST file)              → Echo back with audio
       /transcribe/file     (POST file)              → Get text transcription
       /llm/query           (POST JSON/FormData)     → LLM response + TTS
   =============================== */

/* =========================================================
   1. DOM ELEMENT REFERENCES
   ========================================================= */
const chatArea = document.getElementById("chatArea");

let sessionId = new URLSearchParams(window.location.search).get("session_id");
if (!sessionId) {
  sessionId = Math.random().toString(36).substring(2, 10);
  const url = new URL(window.location.href);
  url.searchParams.set("session_id", sessionId);
  window.history.replaceState({}, "", url);
}

const textInput = document.getElementById("textInput");
const sendBtn = document.getElementById("sendBtn");
const startBtn = document.getElementById("startBtn");
const stopBtn = document.getElementById("stopBtn");
const refreshBtn = document.getElementById("refreshBtn");

/* =========================================================
   2. HELPER FUNCTIONS
   ========================================================= */
function scrollToBottom() {
  chatArea.scrollTop = chatArea.scrollHeight;
}

function appendBotBubble(htmlOrText, allowHTML = false) {
  const div = document.createElement("div");
  div.className = "bot-message";
  if (allowHTML) div.innerHTML = htmlOrText;
  else div.innerText = htmlOrText;
  chatArea.appendChild(div);
  scrollToBottom();
  return div;
}

function appendUserBubble(text) {
  const div = document.createElement("div");
  div.className = "user-message";
  div.innerText = text;
  chatArea.appendChild(div);
  scrollToBottom();
  return div;
}

/* =========================================================
   3. TEXT MODE: User text → LLM → TTS
   ========================================================= */
async function generateAudio() {
  const inputText = textInput.value.trim();
  if (!inputText) return;

  appendUserBubble(inputText);
  textInput.value = "";

  const status = appendBotBubble("Thinking...");

  const form = new FormData();
  form.append("text", inputText);

  const res = await fetch(`/agent/chat/${sessionId}`, {
    method: "POST",
    body: form,
  });

  const data = await res.json();
  status.remove();

  appendBotBubble(data.llm_text);

  const botDiv = document.createElement("div");
  botDiv.className = "bot-message";
  const audio = document.createElement("audio");
  audio.controls = true;
  audio.autoplay = true;
  audio.src = data.audio_url;
  botDiv.appendChild(audio);
  chatArea.appendChild(botDiv);
  scrollToBottom();
}

sendBtn.addEventListener("click", generateAudio);
textInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") generateAudio();
});

/* =========================================================
   4. VOICE MODE: Record → Send → LLM + TTS + Transcription
   ========================================================= */
const recordBtn = document.getElementById("recordBtn");
let isRecording = false;
let mediaRecorder = null;
let audioChunks = [];

recordBtn.addEventListener("click", async () => {
  if (!isRecording) {
    // Start recording
    recordBtn.classList.add("recording");
    isRecording = true;

    const recIndicator = appendBotBubble("Recording...");

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorder = new MediaRecorder(stream);
      audioChunks = [];

      mediaRecorder.ondataavailable = (ev) => {
        if (ev.data && ev.data.size > 0) audioChunks.push(ev.data);
      };

      mediaRecorder.onstop = async () => {
        recIndicator.remove();
        recordBtn.classList.remove("recording");
        isRecording = false;

        const blob = new Blob(audioChunks, { type: "audio/webm" });
        const status = appendBotBubble("Processing your voice with LLM...");

        try {
          const form = new FormData();
          form.append("file", blob, "recording.webm");

          const res = await fetch(`/agent/chat/${sessionId}`, {
            method: "POST",
            body: form,
          });

          if (!res.ok) throw new Error("LLM query failed");
          const data = await res.json();

          status.remove();
          appendUserBubble(data.transcription);
          appendBotBubble(data.llm_text);

          const botDiv = document.createElement("div");
          botDiv.className = "bot-message";
          const audio = document.createElement("audio");
          audio.controls = true;
          audio.autoplay = true;
          audio.src = data.audio_url;
          botDiv.appendChild(audio);
          chatArea.appendChild(botDiv);
          scrollToBottom();
        } catch (err) {
          console.error(err);
          status.remove();
          appendBotBubble("❌ There was a problem processing your voice.");
        }
      };

      mediaRecorder.start();
    } catch (err) {
      console.error("Microphone error:", err);
      appendBotBubble("❌ Microphone access denied or error.");
      recordBtn.classList.remove("recording");
      isRecording = false;
    }
  } else {
    // Stop recording
    if (mediaRecorder && mediaRecorder.state === "recording") {
      mediaRecorder.stop();
    }
  }
});

/* =========================================================
   5. TRANSCRIPTION UPLOAD
   ========================================================= */
async function uploadAndTranscribeAudio(blob) {
  const status = appendBotBubble("Transcribing...");
  const form = new FormData();
  form.append("file", blob, "recording.webm");

  const res = await fetch("/transcribe/file", { method: "POST", body: form });
  const data = await res.json();

  status.remove();
  appendBotBubble(data.text || "(no text returned)");
}

/* =========================================================
   6. PAGE REFRESH
   ========================================================= */
refreshBtn.addEventListener("click", () => {
  window.location.reload();
});
