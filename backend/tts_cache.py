"""MongoDB-backed lazy cache for ElevenLabs TTS audio.

Verses are a fixed, finite set and synthesis is deterministic, so we store the
generated audio keyed by a hash of (text, voice, model, format) and serve it on
future plays instead of re-calling ElevenLabs. Cache failures never break
playback — reads degrade to a miss, writes are best-effort.
"""
import hashlib
from datetime import datetime, timezone
from typing import Optional

from config import db, logger, TTS_MODEL_ID, TTS_OUTPUT_FORMAT, TTS_MIME_TYPE


# Only short, verse-sized inputs are cached, and total cache size is capped, so
# arbitrary user text can't bloat the DB. The hash is the document _id.
TTS_CACHE_MAX_TEXT_LEN = 800   # cache only verse-length text, not long inputs
TTS_CACHE_MAX_DOCS = 2000      # hard ceiling on cached audio documents


def tts_cache_key(text: str, voice_id: str) -> str:
    """Deterministic key for a given text + synthesis configuration."""
    raw = "|".join([text, voice_id, TTS_MODEL_ID, TTS_OUTPUT_FORMAT])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


async def read_cached_audio(key: str) -> Optional[dict]:
    """Return the cached document for this key, or None on miss/error."""
    try:
        cached = await db.tts_cache.find_one({"_id": key})
    except Exception:
        logger.exception("TTS cache read failed; falling back to synthesis")
        return None
    if cached and cached.get("audio_base64"):
        return cached
    return None


async def write_cached_audio(key: str, text: str, voice_id: str, audio_b64: str) -> None:
    """Best-effort store of verse-sized audio. Guarded against bloat/abuse."""
    if len(text) > TTS_CACHE_MAX_TEXT_LEN:
        return
    try:
        if await db.tts_cache.estimated_document_count() < TTS_CACHE_MAX_DOCS:
            await db.tts_cache.update_one(
                {"_id": key},
                {"$setOnInsert": {
                    "audio_base64": audio_b64,
                    "mime_type": TTS_MIME_TYPE,
                    "text": text,
                    "voice_id": voice_id,
                    "model_id": TTS_MODEL_ID,
                    "output_format": TTS_OUTPUT_FORMAT,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }},
                upsert=True,
            )
    except Exception:
        logger.exception("TTS cache write failed (serving audio anyway)")
