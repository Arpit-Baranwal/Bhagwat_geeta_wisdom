"""Verse retrieval for the RAG pipeline.

Loads the verified Bhagavad Gita corpus and its precomputed embedding matrix
once at import time (module-level singletons), then ranks verses against a
user's situation by cosine similarity. The corpus is the source of truth for
all verse text — the LLM only selects among retrieved candidates and writes
guidance, it never authors Sanskrit or translations.
"""
import json
from pathlib import Path
from typing import List, Tuple

import numpy as np
from sentence_transformers import SentenceTransformer

DATA = Path(__file__).parent / "data"
MODEL_NAME = "all-MiniLM-L6-v2"  # must match build_embeddings.py

# Loaded once at import — kept resident for the process lifetime.
CORPUS: List[dict] = json.loads((DATA / "gita_corpus.json").read_text(encoding="utf-8"))
_EMBEDDINGS: np.ndarray = np.load(DATA / "gita_embeddings.npy")  # (N, dim), L2-normalized
_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    """Lazy-load the embedding model on first query to keep startup fast."""
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def retrieve_top_k(situation: str, k: int = 3) -> List[Tuple[dict, float]]:
    """Return the top-k most relevant verses for a situation.

    Each item is (verse_dict, cosine_similarity). Embeddings are L2-normalized,
    so cosine similarity is a single matrix-vector dot product (<1ms for 701 rows).
    """
    query = _get_model().encode(
        situation, normalize_embeddings=True, convert_to_numpy=True
    ).astype(np.float32)
    scores = _EMBEDDINGS @ query  # (N,)
    top_idx = np.argsort(-scores)[:k]
    return [(CORPUS[i], float(scores[i])) for i in top_idx]
