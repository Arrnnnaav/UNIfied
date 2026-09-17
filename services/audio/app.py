"""Optional audio worker: CPU speech-to-text (faster-whisper) and text-to-speech (pocket-tts) behind a tiny
HTTP surface so the slim API image never carries torch. The API proxies /api/audio/* here when
SPATIAL_AUDIO_URL is set. Run: uvicorn services.audio.app:app --port 8790 (from the repo root)."""
from __future__ import annotations

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.core.spatial.audio import audio_status, synthesize, transcribe

app = FastAPI(title="StudyOS audio worker", version="0.1.0")


class Speak(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    voice: str | None = None


@app.get("/health")
def health():
    return {"status": "ok", "audio": audio_status()}


@app.post("/stt")
async def stt(audio: UploadFile = File(...), language: str | None = Form(default=None)):
    data = await audio.read()
    if not data:
        raise HTTPException(400, {"code": "EMPTY_AUDIO", "message": "empty audio"})
    result = transcribe(data, language)
    if result["status"] != "ok":
        raise HTTPException(503, {"code": "STT_UNAVAILABLE", "message": result.get("error", "unavailable")})
    return result


@app.post("/tts")
def tts(payload: Speak):
    wav, meta = synthesize(payload.text, payload.voice)
    if wav is None:
        raise HTTPException(503, {"code": "TTS_UNAVAILABLE", "message": meta.get("error", meta.get("status", "unavailable"))})
    return Response(content=wav, media_type="audio/wav", headers={"X-TTS-Seconds": str(meta["seconds"]), "X-TTS-Voice": meta["voice"]})
