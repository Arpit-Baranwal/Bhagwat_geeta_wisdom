"""Input/output guardrails: rate limiting, crisis safety, off-topic filtering,
and output moderation.
"""
import re
import time
from collections import deque, defaultdict
from typing import Deque, Dict, Optional

from fastapi import Request

from config import logger


# --- Input validation & abuse limits ---
MIN_SITUATION_LEN = 3
MAX_SITUATION_LEN = 1000  # hard cap on free-text input to bound cost/abuse
MAX_TTS_LEN = 4000        # cap TTS payload so a caller can't drive huge synthesis jobs


# --- Rate limiting ---
# Simple in-memory per-client sliding-window limiter. This is per-process
# (fine for a single-worker deployment); swap for Redis if you scale horizontally.
RATE_LIMIT_MAX = 20        # requests allowed per window per client
RATE_LIMIT_WINDOW = 60.0   # seconds
_rate_buckets: Dict[str, Deque[float]] = defaultdict(deque)


def client_key(request: Request) -> str:
    """Best-effort client identity for rate limiting (honours proxy headers)."""
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def check_rate_limit(key: str) -> bool:
    """Return True if the client is under the limit, recording this request."""
    now = time.monotonic()
    bucket = _rate_buckets[key]
    while bucket and now - bucket[0] > RATE_LIMIT_WINDOW:
        bucket.popleft()
    if len(bucket) >= RATE_LIMIT_MAX:
        return False
    bucket.append(now)
    return True


# --- Crisis / self-harm safety ---
# If a situation matches these, we short-circuit BEFORE the LLM and surface
# real support resources instead of a spiritual reflection alone.
_CRISIS_PATTERNS = [
    r"\bkill(?:ing)?\s+myself\b",
    r"\bkill\s+me\b",
    r"\bsuicid(?:e|al)\b",
    r"\bend(?:ing)?\s+(?:my|it)\s+(?:life|all)\b",
    r"\btake\s+my\s+(?:own\s+)?life\b",
    r"\b(?:want|wanna|wanting)\s+(?:to\s+)?die\b",
    r"\bwant\s+to\s+end\s+it\b",
    r"\bno\s+(?:reason|point)\s+(?:to|in)\s+(?:live|living)\b",
    r"\b(?:don'?t|do\s+not|can'?t)\s+want\s+to\s+(?:live|be\s+alive)\b",
    r"\bbetter\s+off\s+dead\b",
    r"\bself[\s-]?harm\b",
    r"\bcut(?:ting)?\s+myself\b",
    r"\bhang\s+myself\b",
    r"\boverdose\b",
]
_CRISIS_RE = re.compile("|".join(_CRISIS_PATTERNS), re.IGNORECASE)

CRISIS_MESSAGE = (
    "It sounds like you may be going through intense pain right now, and I'm really "
    "glad you reached out. Please talk to someone who can support you immediately — "
    "you deserve that help:\n\n"
    "• India (KIRAN, 24x7): 1800-599-0019\n"
    "• India (AASRA): +91-98204 66726\n"
    "• If you are in immediate danger, call your local emergency number.\n"
    "• Find international helplines at https://findahelpline.com\n\n"
    "The Gita teaches that even in the darkest moment the steady Self within you "
    "endures — but please reach out to a person who can walk with you through this now."
)


def is_crisis(text: str) -> bool:
    return bool(_CRISIS_RE.search(text or ""))


# --- Output moderation ---
MAX_GUIDANCE_LEN = 1200
# Markers that suggest the model leaked instructions, roleplay, or links into the
# guidance (e.g. via a prompt-injection attempt). If present, we drop the guidance
# and fall back to a safe, generic reflection instead of serving it.
_OUTPUT_BLOCKLIST = (
    "http://", "https://", "www.", "<script", "</", "system prompt",
    "ignore previous", "ignore the above", "as an ai", "i am an ai",
    "language model", "chosen_index", "selection_reason",
)


def moderate_guidance(text: str) -> str:
    """Return vetted guidance text, or '' to trigger the safe fallback."""
    if not text:
        return ""
    text = text.strip()
    lowered = text.lower()
    if any(marker in lowered for marker in _OUTPUT_BLOCKLIST):
        logger.warning("Guidance failed output moderation; using fallback")
        return ""
    if len(text) > MAX_GUIDANCE_LEN:
        text = text[:MAX_GUIDANCE_LEN].rsplit(" ", 1)[0].rstrip() + "…"
    return text


# --- Off-topic / gibberish pre-filter ---
# A cheap, high-confidence heuristic that rejects obvious non-situations BEFORE
# spending any retrieval/LLM compute. Nuanced off-topic cases (personal commands,
# trivia phrased naturally) are left to the LLM "applicable" gate downstream.
TOPIC_REJECT_MESSAGE = (
    "Please share a real-life situation or feeling you'd like guidance on — "
    "not a calculation, a factual question, or random text."
)

# Word-like tokens: 2+ letters, Latin or Devanagari (so Hindi/Sanskrit counts).
_WORD_RE = re.compile(r"[A-Za-zऀ-ॿ]{2,}")
# A pure arithmetic expression, e.g. "2+2", "12 / 4", "(3*5)-1".
_ARITHMETIC_RE = re.compile(r"^[\s\d.,()+\-*/^%×÷=xX]+$")
# A calculation phrased as a command, e.g. "calculate 5*3", "what is 12 + 4".
_MATH_LEAD_RE = re.compile(r"^(?:calculate|compute|solve|evaluate|what\s+is)\b", re.IGNORECASE)
_MATH_OPS = set("+-*/^%×÷=")


def looks_like_math(text: str) -> bool:
    t = text.strip()
    has_digit = any(c.isdigit() for c in t)
    has_op = any(c in _MATH_OPS for c in t)
    if has_digit and has_op:
        return bool(_ARITHMETIC_RE.match(t) or _MATH_LEAD_RE.match(t))
    return False


def looks_like_gibberish(text: str) -> bool:
    t = text.strip()
    non_space = [c for c in t if not c.isspace()]
    if not non_space:
        return True
    letters = [c for c in non_space if c.isalpha()]
    # Mostly symbols/numbers (e.g. "!!!", "12345", "@#$%") — not written prose.
    if len(letters) / len(non_space) < 0.45:
        return True
    # No real word tokens at all.
    if not _WORD_RE.search(t):
        return True
    return False


def off_topic_reason(text: str) -> Optional[str]:
    """Return a rejection message for obvious non-situations, else None."""
    if looks_like_math(text) or looks_like_gibberish(text):
        return TOPIC_REJECT_MESSAGE
    return None
