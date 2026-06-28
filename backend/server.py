from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import json
import base64
import uuid
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, timezone

from emergentintegrations.llm.chat import LlmChat, UserMessage
from elevenlabs.client import ElevenLabs
from elevenlabs import VoiceSettings


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
mongo_client = AsyncIOMotorClient(mongo_url)
db = mongo_client[os.environ['DB_NAME']]

# Integrations
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY')
ELEVENLABS_API_KEY = os.environ.get('ELEVENLABS_API_KEY')

eleven_client = ElevenLabs(api_key=ELEVENLABS_API_KEY) if ELEVENLABS_API_KEY else None

# Default ElevenLabs voice (multilingual capable - "Rachel" multilingual)
# Using a voice ID that works well with Sanskrit/Hindi via eleven_multilingual_v2
DEFAULT_VOICE_ID = "pNInz6obpgDQGcFmaJgB"  # Adam - good multilingual male voice

app = FastAPI()
api_router = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# ============== MODELS ==============

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


class TTSRequest(BaseModel):
    text: str
    voice_id: Optional[str] = None


class TTSResponse(BaseModel):
    audio_base64: str
    mime_type: str = "audio/mpeg"


# ============== HELPERS ==============

SYSTEM_PROMPT = """You are a wise spiritual guide deeply versed in the Bhagavad Gita.
Given a user's life situation or emotional state, you select ONE most relevant authentic shloka (verse) from the Bhagavad Gita that offers wisdom for their situation.

You MUST respond ONLY with a valid JSON object (no markdown, no code fences, no explanations outside JSON) with the following exact fields:
{
  "sanskrit": "the original Sanskrit shloka in Devanagari script, with proper line breaks using \\n",
  "transliteration": "IAST romanized transliteration of the shloka",
  "hindi_translation": "clear, accurate Hindi translation in Devanagari",
  "english_translation": "clear, accurate English translation",
  "practical_guidance": "2-4 sentences explaining how this verse applies to the user's specific situation and what action or perspective they should adopt. Be warm, compassionate, and practical.",
  "chapter": chapter_number_as_integer,
  "verse": verse_number_as_integer,
  "reference": "Bhagavad Gita Chapter.Verse (e.g. Bhagavad Gita 2.47)"
}

Choose authentic, well-known verses. Be accurate with Sanskrit. Respond ONLY with the JSON object."""


def parse_llm_json(text: str) -> dict:
    """Extract JSON from LLM response, stripping any markdown fences."""
    text = text.strip()
    if text.startswith("```"):
        # Strip code fences
        text = text.split("```", 2)
        if len(text) >= 2:
            inner = text[1]
            if inner.startswith("json"):
                inner = inner[4:]
            text = inner.strip()
        else:
            text = "".join(text)
    # Find JSON object boundaries
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        text = text[start:end + 1]
    return json.loads(text)


# ============== ROUTES ==============

@api_router.get("/")
async def root():
    return {"message": "Geeta Wisdom API", "status": "ok"}


@api_router.post("/shloka/generate", response_model=ShlokaResponse)
async def generate_shloka(req: ShlokaRequest):
    if not EMERGENT_LLM_KEY:
        raise HTTPException(status_code=500, detail="LLM key not configured")
    if not req.situation or len(req.situation.strip()) < 3:
        raise HTTPException(status_code=400, detail="Please describe your situation in more detail")

    session_id = req.session_id or str(uuid.uuid4())

    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=session_id,
            system_message=SYSTEM_PROMPT,
        ).with_model("anthropic", "claude-sonnet-4-5-20250929")

        user_msg = UserMessage(text=f"My situation: {req.situation}\n\nProvide the most relevant Bhagavad Gita shloka with all required fields as JSON.")
        response_text = await chat.send_message(user_msg)

        data = parse_llm_json(response_text)

        shloka_id = str(uuid.uuid4())
        now_iso = datetime.now(timezone.utc).isoformat()

        result = ShlokaResponse(
            id=shloka_id,
            situation=req.situation,
            sanskrit=data.get("sanskrit", ""),
            transliteration=data.get("transliteration", ""),
            hindi_translation=data.get("hindi_translation", ""),
            english_translation=data.get("english_translation", ""),
            practical_guidance=data.get("practical_guidance", ""),
            reference=data.get("reference", ""),
            chapter=int(data.get("chapter", 0)),
            verse=int(data.get("verse", 0)),
            created_at=now_iso,
        )

        # Save to history collection
        await db.shloka_history.insert_one(result.model_dump())

        return result
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {e}; raw={response_text[:500] if 'response_text' in dir() else 'N/A'}")
        raise HTTPException(status_code=500, detail="Could not parse wisdom. Please try again.")
    except Exception as e:
        logger.exception("Error generating shloka")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@api_router.post("/tts/narrate", response_model=TTSResponse)
async def narrate_text(req: TTSRequest):
    if not eleven_client:
        raise HTTPException(status_code=500, detail="ElevenLabs not configured")
    if not req.text or len(req.text.strip()) == 0:
        raise HTTPException(status_code=400, detail="Text is required")

    voice_id = req.voice_id or DEFAULT_VOICE_ID

    try:
        voice_settings = VoiceSettings(
            stability=0.6,
            similarity_boost=0.75,
            style=0.3,
            use_speaker_boost=True,
        )
        audio_iter = eleven_client.text_to_speech.convert(
            text=req.text,
            voice_id=voice_id,
            model_id="eleven_multilingual_v2",
            voice_settings=voice_settings,
            output_format="mp3_44100_128",
        )
        audio_bytes = b""
        for chunk in audio_iter:
            if chunk:
                audio_bytes += chunk

        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
        return TTSResponse(audio_base64=audio_b64, mime_type="audio/mpeg")
    except Exception as e:
        logger.exception("Error generating TTS")
        raise HTTPException(status_code=500, detail=f"TTS error: {str(e)}")


@api_router.get("/history", response_model=List[ShlokaResponse])
async def list_history(limit: int = 20):
    """Get recent shloka history (server-side, public)."""
    docs = await db.shloka_history.find({}, {"_id": 0}).sort("created_at", -1).to_list(limit)
    return docs


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("shutdown")
async def shutdown_db_client():
    mongo_client.close()
