"""Pydantic request/response schemas for the API."""
from typing import Optional

from pydantic import BaseModel


class ShlokaRequest(BaseModel):
    situation: str
    session_id: Optional[str] = None


class ShlokaResponse(BaseModel):
    id: str
    situation: str
    sanskrit: str
    transliteration: str
    hindi_translation: str
    english_translation: str
    practical_guidance: str
    reference: str  # e.g. "Bhagavad Gita 2.47"
    chapter: int
    verse: int
    created_at: str
    # True when the situation was flagged as an acute-distress / self-harm case.
    # The guidance then leads with crisis support resources rather than a verse.
    crisis: bool = False


class TTSRequest(BaseModel):
    text: str
    voice_id: Optional[str] = None


class TTSResponse(BaseModel):
    audio_base64: str
    mime_type: str = "audio/mpeg"
