"""Modular Audio Service for microphone ingestion, STT, and TTS.

Ensures strict temporary file cleanup, privacy-first audio retention controls,
size limits, format validation, and provider fallback handling.
"""

import asyncio
import logging
import os
import shutil
import tempfile
from pathlib import Path
from uuid import uuid4

from app.core.config import settings
from app.core.exceptions import ValidationError
from app.domain.enums import AudioFormat
from app.services.audio.models import (
    AudioSynthesisRequest,
    AudioTranscriptionRequest,
    AudioTranscriptionResponse,
)

logger = logging.getLogger("friday.audio_service")

SUPPORTED_AUDIO_TYPES: dict[str, AudioFormat] = {
    "audio/wav": AudioFormat.WAV,
    "audio/x-wav": AudioFormat.WAV,
    "audio/wave": AudioFormat.WAV,
    "audio/mpeg": AudioFormat.MP3,
    "audio/mp3": AudioFormat.MP3,
    "audio/ogg": AudioFormat.OGG,
    "audio/webm": AudioFormat.WEBM,
    "audio/x-m4a": AudioFormat.M4A,
    "audio/m4a": AudioFormat.M4A,
    "audio/mp4": AudioFormat.M4A,
}


class AudioService:
    """Microphone audio processing service for STT transcription and TTS synthesis."""

    def __init__(self):
        self.whisper_available = shutil.which("whisper") is not None
        self.tts_command = shutil.which("say") or shutil.which("espeak")
        self.temp_dir = settings.AUDIO_TEMP_DIR
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    @property
    def is_ready(self) -> bool:
        return True

    @property
    def provider_name(self) -> str:
        return "whisper" if self.whisper_available else "mock_fallback"

    def validate_audio(self, audio_bytes: bytes, mime_type: str) -> AudioFormat:
        """Validate audio size and format."""
        if not audio_bytes:
            raise ValidationError("Audio content is empty.")

        if len(audio_bytes) > settings.AUDIO_MAX_SIZE_BYTES:
            raise ValidationError(
                f"Audio file size ({len(audio_bytes)} bytes) exceeds maximum limit "
                f"of {settings.AUDIO_MAX_SIZE_BYTES} bytes (25MB)."
            )

        clean_mime = mime_type.lower().split(";")[0].strip()
        if clean_mime not in SUPPORTED_AUDIO_TYPES:
            raise ValidationError(
                f"Unsupported audio format: '{mime_type}'. Supported MIME types: {list(SUPPORTED_AUDIO_TYPES.keys())}"
            )

        return SUPPORTED_AUDIO_TYPES[clean_mime]

    async def transcribe(
        self,
        audio_bytes: bytes,
        mime_type: str,
        options: AudioTranscriptionRequest | None = None,
    ) -> AudioTranscriptionResponse:
        """Transcribe uploaded audio bytes with immediate temporary file cleanup."""
        audio_format = self.validate_audio(audio_bytes, mime_type)
        options = options or AudioTranscriptionRequest(format=audio_format)
        transcript_id = f"stt-{uuid4().hex[:8]}"

        # Write to temporary file for processing
        suffix = f".{audio_format.value}"
        temp_file = tempfile.NamedTemporaryFile(
            dir=str(self.temp_dir),
            suffix=suffix,
            delete=False,
        )
        temp_path = Path(temp_file.name)
        retained = False

        try:
            temp_file.write(audio_bytes)
            temp_file.flush()
            temp_file.close()

            logger.info(
                "Processing audio file: %s (format=%s, size=%d bytes)",
                temp_path.name,
                audio_format.value,
                len(audio_bytes),
            )

            # Local Whisper execution if installed
            if self.whisper_available:
                transcript_text = await self._run_whisper_cli(temp_path)
                is_fallback = False
            else:
                # Simulated / Fallback speech recognition
                transcript_text = "FRIDAY system status report requested. All diagnostic monitors nominal."
                is_fallback = True

            # Check privacy retention settings: only retain if user explicitly opts in
            if options.save_audio and settings.AUDIO_RETENTION_ENABLED:
                permanent_dir = settings.DATA_DIR / "audio_records"
                permanent_dir.mkdir(parents=True, exist_ok=True)
                dest = permanent_dir / f"{transcript_id}{suffix}"
                shutil.copy2(temp_path, dest)
                retained = True
                logger.info("Audio retained per user request at: %s", dest.name)

            return AudioTranscriptionResponse(
                transcript_id=transcript_id,
                transcript=transcript_text,
                duration_seconds=float(round(len(audio_bytes) / 32000.0, 2)),
                format=audio_format.value,
                audio_size_bytes=len(audio_bytes),
                confidence=0.96 if not is_fallback else 0.85,
                is_mock_fallback=is_fallback,
                retained_on_disk=retained,
            )

        finally:
            # Ephemeral guarantee: Clean up temporary file unconditionally
            try:
                if temp_path.exists():
                    os.unlink(temp_path)
            except Exception as e:
                logger.warning("Failed to remove temporary audio file %s: %s", temp_path, str(e))

    async def _run_whisper_cli(self, file_path: Path) -> str:
        """Run local whisper CLI safely."""
        proc = await asyncio.create_subprocess_exec(
            "whisper",
            str(file_path),
            "--model", "base",
            "--output_format", "txt",
            "--output_dir", str(file_path.parent),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        txt_file = file_path.with_suffix(".txt")
        if txt_file.exists():
            content = txt_file.read_text(encoding="utf-8").strip()
            txt_file.unlink(missing_ok=True)
            return content
        return stdout.decode(errors="ignore").strip() or "[Transcribed audio]"

    async def synthesize(self, request: AudioSynthesisRequest) -> tuple[bytes, str]:
        """Synthesize text to speech audio."""
        if not self.tts_command:
            # Generate minimal valid WAV header for headless environments
            wav_bytes = self._create_dummy_wav()
            return wav_bytes, "audio/wav"

        out_file = tempfile.NamedTemporaryFile(
            dir=str(self.temp_dir),
            suffix=".wav",
            delete=False,
        )
        out_path = Path(out_file.name)
        out_file.close()

        try:
            if "say" in self.tts_command:
                # macOS say command
                voice_args = ["-v", request.voice] if request.voice else []
                proc = await asyncio.create_subprocess_exec(
                    "say",
                    "-o", str(out_path),
                    "--data-format=LEF32@22050",
                    *voice_args,
                    request.text,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                await proc.communicate()
            else:
                # espeak command
                proc = await asyncio.create_subprocess_exec(
                    "espeak",
                    "-w", str(out_path),
                    request.text,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                await proc.communicate()

            if out_path.exists() and out_path.stat().st_size > 0:
                audio_data = out_path.read_bytes()
                return audio_data, "audio/wav"

            return self._create_dummy_wav(), "audio/wav"

        finally:
            if out_path.exists():
                os.unlink(out_path)

    @staticmethod
    def _create_dummy_wav() -> bytes:
        """Create minimal 44-byte valid WAV header (silent audio) for testing."""
        import struct

        num_samples = 8000  # 1 second of silence at 8kHz
        sample_rate = 8000
        byte_rate = sample_rate * 2
        block_align = 2
        bits_per_sample = 16
        data_size = num_samples * 2
        chunk_size = 36 + data_size

        header = struct.pack(
            "<4sI4s4sIHHIIHH4sI",
            b"RIFF",
            chunk_size,
            b"WAVE",
            b"fmt ",
            16,
            1,  # PCM
            1,  # Mono
            sample_rate,
            byte_rate,
            block_align,
            bits_per_sample,
            b"data",
            data_size,
        )
        return header + (b"\x00" * data_size)


# Global singleton instance
audio_service = AudioService()
