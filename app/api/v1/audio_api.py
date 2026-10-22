"""Audio ingestion, streaming, and speech endpoints."""

import json

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Response,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)

from app.api.dependencies import verify_api_key
from app.domain.schemas import APIResponse
from app.services.audio import (
    AudioSynthesisRequest,
    AudioTranscriptionRequest,
    audio_service,
)

router = APIRouter(tags=["Audio & Speech Ingestion"])


@router.post("/api/v1/audio/transcriptions", response_model=APIResponse)
@router.post("/api/audio/transcriptions", response_model=APIResponse)
async def transcribe_audio_file(
    file: UploadFile = File(...),
    save_audio: bool = False,
    api_key_valid: bool = Depends(verify_api_key),
):
    """Upload an audio file (WAV, MP3, OGG, WEBM, M4A) for transcription."""
    try:
        content = await file.read()
        mime_type = file.content_type or "audio/wav"
        req = AudioTranscriptionRequest(save_audio=save_audio)
        result = await audio_service.transcribe(content, mime_type, req)
        return APIResponse(success=True, data=result.model_dump(), message="Audio transcribed successfully.")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/api/v1/audio/synthesize")
@router.post("/api/audio/synthesize")
@router.post("/api/v1/audio/speech")
@router.post("/api/audio/speech")
async def synthesize_speech(
    payload: AudioSynthesisRequest,
    api_key_valid: bool = Depends(verify_api_key),
):
    """Synthesize text into WAV speech audio."""
    try:
        audio_bytes, mime = await audio_service.synthesize(payload)
        return Response(content=audio_bytes, media_type=mime)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/api/v1/audio/status", response_model=APIResponse)
@router.get("/api/audio/status", response_model=APIResponse)
async def get_audio_status():
    """Return backend audio service, transcription readiness, and voice capture status."""
    return APIResponse(
        success=True,
        data={
            "transcription_provider": audio_service.provider_name,
            "transcription_ready": audio_service.is_ready,
            "speech_synthesis_ready": True,
            "voice_capture_status": "paused",
            "browser_mic_permission_required": True,
            "supported_formats": [
                "audio/wav",
                "audio/mp3",
                "audio/ogg",
                "audio/webm",
                "audio/m4a",
            ],
            "max_upload_size_mb": 25,
        },
    )


@router.websocket("/api/v1/audio/stream")
@router.websocket("/api/audio/stream")
async def websocket_audio_streaming(websocket: WebSocket):
    """WebSocket endpoint for real-time microphone audio streaming and chunk transcription.
    
    Frontend establishes connection, streams audio byte chunks, and receives transcription events.
    """
    await websocket.accept()
    buffer = bytearray()
    mime_type = "audio/wav"

    try:
        while True:
            message = await websocket.receive()
            if "bytes" in message and message["bytes"]:
                chunk = message["bytes"]
                buffer.extend(chunk)

                # Send chunk acknowledgment
                await websocket.send_json({
                    "event": "chunk_received",
                    "chunk_bytes": len(chunk),
                    "total_buffered": len(buffer),
                })

            elif "text" in message and message["text"]:
                try:
                    meta = json.loads(message["text"])
                    cmd = meta.get("action")
                    if cmd == "set_mime":
                        mime_type = meta.get("mime_type", "audio/wav")
                    elif cmd == "finalize":
                        # Process buffered audio
                        if buffer:
                            res = await audio_service.transcribe(bytes(buffer), mime_type)
                            await websocket.send_json({
                                "event": "final_transcript",
                                "transcript": res.transcript,
                                "duration": res.duration_seconds,
                            })
                            buffer.clear()
                    elif cmd == "cancel":
                        buffer.clear()
                        await websocket.send_json({"event": "cancelled"})
                except Exception as parse_err:
                    await websocket.send_json({"event": "error", "detail": str(parse_err)})

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        try:
            await websocket.send_json({"event": "error", "detail": str(exc)})
            await websocket.close()
        except Exception:
            pass
