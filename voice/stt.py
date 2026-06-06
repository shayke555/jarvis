import io
import wave
from groq import AsyncGroq
from config.settings import settings

_client: AsyncGroq | None = None


def _get_client() -> AsyncGroq:
    global _client
    if _client is None:
        _client = AsyncGroq(api_key=settings.groq_api_key)
    return _client


async def transcribe(audio_bytes: bytes, sample_rate: int = 16000) -> str:
    wav_buffer = io.BytesIO()
    with wave.open(wav_buffer, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio_bytes)
    wav_buffer.seek(0)

    client = _get_client()
    transcription = await client.audio.transcriptions.create(
        file=("audio.wav", wav_buffer, "audio/wav"),
        model="whisper-large-v3-turbo",
        language="he",
        response_format="text",
    )
    return transcription.strip()


async def transcribe_ogg(ogg_bytes: bytes) -> str:
    """Transcribe Telegram voice messages (OGG/Opus format) directly."""
    client = _get_client()
    transcription = await client.audio.transcriptions.create(
        file=("voice.ogg", io.BytesIO(ogg_bytes), "audio/ogg"),
        model="whisper-large-v3-turbo",
        response_format="text",
    )
    return transcription.strip()
