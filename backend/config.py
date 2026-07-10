"""Central configuration: env, external clients, shared constants, logger.

This module imports nothing from the app's own modules, so everything else can
safely import from here without creating circular imports.
"""
import os
import logging
from pathlib import Path

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from anthropic import AsyncAnthropic
from elevenlabs.client import ElevenLabs
from elevenlabs import VoiceSettings


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger("gita")

# --- MongoDB ---
mongo_url = os.environ['MONGO_URL']
mongo_client = AsyncIOMotorClient(mongo_url)
db = mongo_client[os.environ['DB_NAME']]

# --- Integrations ---
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
ELEVENLABS_API_KEY = os.environ.get('ELEVENLABS_API_KEY')

anthropic_client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None
eleven_client = ElevenLabs(api_key=ELEVENLABS_API_KEY) if ELEVENLABS_API_KEY else None

# --- LLM ---
LLM_MODEL = "claude-haiku-4-5-20251001"

# --- ElevenLabs / TTS synthesis parameters ---
# Default multilingual-capable voice that works well with Sanskrit/Hindi.
DEFAULT_VOICE_ID = "pNInz6obpgDQGcFmaJgB"  # Adam
# These are part of the TTS cache key: identical text + these settings always
# yield the same audio, so a change here means new audio.
TTS_MODEL_ID = "eleven_multilingual_v2"
TTS_OUTPUT_FORMAT = "mp3_44100_128"
TTS_MIME_TYPE = "audio/mpeg"
TTS_VOICE_SETTINGS = VoiceSettings(
    stability=0.6,
    similarity_boost=0.75,
    style=0.3,
    use_speaker_boost=True,
)

# --- Retrieval ---
# Minimum cosine similarity for the top retrieved verse to be considered
# relevant. Below this, we ask the user to rephrase rather than force a match.
MIN_SIMILARITY = 0.15
