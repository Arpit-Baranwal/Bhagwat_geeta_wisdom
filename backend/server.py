"""FastAPI application and route handlers for the Geeta Wisdom API."""
import os
import base64
import uuid
from datetime import datetime, timezone
from typing import List

from fastapi import FastAPI, APIRouter, HTTPException, Request
from starlette.middleware.cors import CORSMiddleware

import retrieval
from config import (
    db,
    logger,
    anthropic_client,
    eleven_client,
    mongo_client,
    LLM_MODEL,
    DEFAULT_VOICE_ID,
    TTS_MODEL_ID,
    TTS_OUTPUT_FORMAT,
    TTS_MIME_TYPE,
    TTS_VOICE_SETTINGS,
    MIN_SIMILARITY,
)
from models import ShlokaRequest, ShlokaResponse, TTSRequest, TTSResponse
from prompts import SYSTEM_PROMPT, parse_llm_json
from tts_cache import tts_cache_key, read_cached_audio, write_cached_audio
import guardrails as g


app = FastAPI()
api_router = APIRouter(prefix="/api")


# ============== ROUTES ==============

@api_router.get("/")
async def root():
    return {"message": "Geeta Wisdom API", "status": "ok"}


@api_router.post("/shloka/generate", response_model=ShlokaResponse)
async def generate_shloka(req: ShlokaRequest, request: Request):
    if not anthropic_client:
        raise HTTPException(status_code=500, detail="LLM key not configured")

    # Guardrail: per-client rate limiting.
    if not g.check_rate_limit(g.client_key(request)):
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please wait a moment before trying again.",
        )

    # Guardrail: input validation & abuse limits.
    situation = (req.situation or "").strip()
    if len(situation) < g.MIN_SITUATION_LEN:
        raise HTTPException(status_code=400, detail="Please describe your situation in more detail")
    if len(situation) > g.MAX_SITUATION_LEN:
        raise HTTPException(
            status_code=400,
            detail=f"Please keep your situation under {g.MAX_SITUATION_LEN} characters.",
        )

    # Guardrail: crisis / self-harm safety. Short-circuit BEFORE the LLM and
    # surface real support resources instead of a verse. No verse is attached so
    # the client can render this as a distinct crisis panel, not a shloka card.
    if g.is_crisis(situation):
        result = ShlokaResponse(
            id=str(uuid.uuid4()),
            situation=situation,
            sanskrit="",
            transliteration="",
            hindi_translation="",
            english_translation="",
            practical_guidance=g.CRISIS_MESSAGE,
            reference="Support Resources",
            chapter=0,
            verse=0,
            created_at=datetime.now(timezone.utc).isoformat(),
            crisis=True,
        )
        # Deliberately not persisted to history.
        return result

    # Guardrail: cheap off-topic/gibberish pre-filter. Reject obvious
    # non-situations (math, symbol/number-only, gibberish) before any compute.
    reason = g.off_topic_reason(situation)
    if reason:
        raise HTTPException(status_code=422, detail=reason)

    # 1. Retrieve verified candidate verses from the corpus.
    candidates = retrieval.retrieve_top_k(situation, k=3)
    top_score = candidates[0][1] if candidates else 0.0
    if not candidates or top_score < MIN_SIMILARITY:
        raise HTTPException(
            status_code=422,
            detail="Could not find a clearly relevant verse. Please describe your situation with a bit more detail.",
        )

    # Build the candidate block the LLM selects from (verified text only).
    candidate_text = "\n\n".join(
        f"[{i}] {v['reference']}\n"
        f"Sanskrit: {v['sanskrit']}\n"
        f"English: {v['english_translation']}"
        for i, (v, _) in enumerate(candidates)
    )
    user_content = (
        f"<situation>\n{situation}\n</situation>\n\n"
        f"Candidate verses:\n{candidate_text}\n\n"
        "Choose the best-fitting candidate by index and write the guidance as JSON."
    )

    try:
        message = await anthropic_client.messages.create(
            model=LLM_MODEL,
            max_tokens=512,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_content}],
        )
        response_text = message.content[0].text
        data = parse_llm_json(response_text)
        # Guardrail: relevance gate. If the model judges the input is not a genuine
        # life situation, reject rather than forcing an unrelated verse onto it.
        if data.get("applicable") is False:
            raise HTTPException(
                status_code=422,
                detail="Please share a real-life situation or feeling you'd like guidance on.",
            )
        # Guardrail: moderate the LLM-authored guidance before trusting it.
        guidance = g.moderate_guidance(str(data.get("practical_guidance", "")))
    except HTTPException:
        raise
    except Exception as e:
        # Retrieval already gave us a grounded verse; on any LLM/parse failure
        # fall back to the top-similarity verse with no fabricated guidance.
        logger.warning(f"LLM selection failed ({e}); falling back to top-1 retrieved verse")
        data, guidance = {}, ""

    # Resolve the chosen verse — default to the top-similarity candidate.
    try:
        chosen_index = int(data.get("chosen_index", 0))
    except (TypeError, ValueError):
        chosen_index = 0
    if not 0 <= chosen_index < len(candidates):
        chosen_index = 0
    verse, _ = candidates[chosen_index]

    if not guidance:
        guidance = (
            "Reflect on this verse in the context of your situation; let its "
            "teaching guide your next step with a calm and steady mind."
        )

    # 2. Serve VERIFIED fields from the corpus; only guidance comes from the LLM.
    result = ShlokaResponse(
        id=str(uuid.uuid4()),
        situation=situation,
        sanskrit=verse["sanskrit"],
        transliteration=verse["transliteration"],
        hindi_translation=verse["hindi_translation"],
        english_translation=verse["english_translation"],
        practical_guidance=guidance,
        reference=verse["reference"],
        chapter=int(verse["chapter"]),
        verse=int(verse["verse"]),
        created_at=datetime.now(timezone.utc).isoformat(),
    )

    try:
        await db.shloka_history.insert_one(result.model_dump())
    except Exception:
        logger.exception("Failed to persist shloka history")

    return result


@api_router.post("/tts/narrate", response_model=TTSResponse)
async def narrate_text(req: TTSRequest, request: Request):
    if not eleven_client:
        raise HTTPException(status_code=500, detail="ElevenLabs not configured")

    if not g.check_rate_limit(g.client_key(request)):
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please wait a moment before trying again.",
        )

    if not req.text or len(req.text.strip()) == 0:
        raise HTTPException(status_code=400, detail="Text is required")
    if len(req.text) > g.MAX_TTS_LEN:
        raise HTTPException(
            status_code=400,
            detail=f"Text is too long (max {g.MAX_TTS_LEN} characters).",
        )

    voice_id = req.voice_id or DEFAULT_VOICE_ID
    key = tts_cache_key(req.text, voice_id)

    # 1. Cache hit: serve stored audio, no ElevenLabs call.
    cached = await read_cached_audio(key)
    if cached:
        return TTSResponse(
            audio_base64=cached["audio_base64"],
            mime_type=cached.get("mime_type", TTS_MIME_TYPE),
        )

    # 2. Cache miss: synthesize via ElevenLabs.
    try:
        audio_iter = eleven_client.text_to_speech.convert(
            text=req.text,
            voice_id=voice_id,
            model_id=TTS_MODEL_ID,
            voice_settings=TTS_VOICE_SETTINGS,
            output_format=TTS_OUTPUT_FORMAT,
        )
        audio_bytes = b""
        for chunk in audio_iter:
            if chunk:
                audio_bytes += chunk

        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
    except Exception as e:
        logger.exception("Error generating TTS")
        raise HTTPException(status_code=500, detail=f"TTS error: {str(e)}")

    # 3. Lazy fill: store verse-sized results so future plays are free/instant.
    await write_cached_audio(key, req.text, voice_id, audio_b64)

    return TTSResponse(audio_base64=audio_b64, mime_type=TTS_MIME_TYPE)


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
