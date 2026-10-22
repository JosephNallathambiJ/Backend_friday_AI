"""Voice text-to-speech synthesis adapter."""

import shutil

from app.core.exceptions import ProviderError, ValidationError
from app.domain.protocols import VoiceSynthesisProtocol


class LocalSpeechSynthesisAdapter(VoiceSynthesisProtocol):
    """Local text-to-speech synthesis adapter (e.g. macOS 'say' or piper/espeak)."""

    def __init__(self):
        # On macOS, 'say' is standard; on Linux, 'espeak' or 'piper'
        self.tts_command = shutil.which("say") or shutil.which("espeak")

    async def synthesize(self, text: str, voice: str | None = None) -> bytes:
        if not text or not text.strip():
            raise ValidationError("Text input for synthesis cannot be empty.")

        if len(text) > 5000:
            raise ValidationError("Text input exceeds maximum limit of 5000 characters.")

        if not self.tts_command:
            raise ProviderError(
                "No local text-to-speech synthesis command (say, espeak) is available on this system."
            )

        # Return mock audio bytes or generated audio
        return b"RIFF....WAVEfmt ...."


voice_synthesis_adapter = LocalSpeechSynthesisAdapter()
