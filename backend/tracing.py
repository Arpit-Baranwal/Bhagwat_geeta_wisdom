"""Optional Phoenix (Arize) tracing for local debugging.

Set PHOENIX_TRACING=1 to trace every request in the Phoenix UI at
http://localhost:6006 — the retrieval step (candidates + similarity scores)
and the Anthropic LLM call (exact prompt, raw response, token usage, latency).

Phoenix runs as a SEPARATE process, not inside the API server: launching it
in-process breaks under uvicorn --reload, because each reloaded worker tries
to re-bind Phoenix's ports (6006/4317) while the old worker still holds them.
init_tracing() spawns `phoenix serve` detached if it isn't already running,
then only registers a span exporter pointing at it, which reloads can safely
repeat. The Phoenix process outlives the API server; stop it with:
    pkill -f "phoenix.server.main"

Requires dev dependencies (requirements-dev.txt):
    pip install arize-phoenix openinference-instrumentation-anthropic

When the flag is off (production), this module is a no-op and none of the
tracing packages are imported.
"""
import os
import subprocess
import sys
import time
import urllib.request
from contextlib import nullcontext

from config import logger

PHOENIX_TRACING = os.environ.get("PHOENIX_TRACING", "").lower() in ("1", "true", "yes")
PHOENIX_URL = "http://localhost:6006"


def _phoenix_running() -> bool:
    try:
        urllib.request.urlopen(PHOENIX_URL, timeout=2)
        return True
    except Exception:
        return False


def _spawn_phoenix() -> bool:
    """Start `phoenix serve` as a detached background process and wait for it."""
    logger.info("Starting Phoenix server (first launch can take ~30s)...")
    subprocess.Popen(
        [sys.executable, "-m", "phoenix.server.main", "serve"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,  # survives API server restarts/reloads
    )
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        if _phoenix_running():
            return True
        time.sleep(1)
    return False


def init_tracing() -> None:
    """Ensure Phoenix is up, then instrument the Anthropic SDK to export to it."""
    if not PHOENIX_TRACING:
        return
    try:
        from phoenix.otel import register
        from openinference.instrumentation.anthropic import AnthropicInstrumentor

        if not _phoenix_running() and not _spawn_phoenix():
            logger.warning("Phoenix did not come up on %s; tracing disabled", PHOENIX_URL)
            return
        tracer_provider = register(project_name="gita-wisdom", set_global_tracer_provider=True)
        AnthropicInstrumentor().instrument(tracer_provider=tracer_provider)
        logger.info("Phoenix tracing enabled — UI at %s", PHOENIX_URL)
    except Exception:
        logger.exception("Failed to initialize Phoenix tracing; continuing without it")


def retrieval_span():
    """Context manager yielding a span for the retrieval step (None when off)."""
    if not PHOENIX_TRACING:
        return nullcontext(None)
    from opentelemetry import trace

    return trace.get_tracer("gita").start_as_current_span("retrieve_verses")


def record_candidates(span, situation: str, candidates) -> None:
    """Attach the query and scored candidates to the retrieval span using
    OpenInference retriever conventions so Phoenix renders them as documents."""
    if span is None:
        return
    span.set_attribute("openinference.span.kind", "RETRIEVER")
    span.set_attribute("input.value", situation)
    for i, (verse, score) in enumerate(candidates):
        prefix = f"retrieval.documents.{i}.document"
        span.set_attribute(f"{prefix}.id", verse["reference"])
        span.set_attribute(f"{prefix}.content", verse["english_translation"])
        span.set_attribute(f"{prefix}.score", float(score))
