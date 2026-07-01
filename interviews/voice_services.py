from io import BytesIO

from django.conf import settings
from openai import OpenAI


def transcribe_audio_file(uploaded_file) -> str:
    """Convert an uploaded audio answer into text using OpenAI Whisper."""
    if not settings.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is missing. Add it to your .env file.")

    uploaded_file.seek(0)
    audio_buffer = BytesIO(uploaded_file.read())
    audio_buffer.name = uploaded_file.name

    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    transcript = client.audio.transcriptions.create(
        model="whisper-1",
        file=audio_buffer,
    )
    return transcript.text.strip()
