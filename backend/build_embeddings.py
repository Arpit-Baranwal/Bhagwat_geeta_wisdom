"""One-time (re)build of the verse embedding matrix for RAG retrieval.

Run whenever data/gita_corpus.json changes:
    python build_embeddings.py

Produces data/gita_embeddings.npy — a float32 matrix aligned row-for-row with
the corpus, holding L2-normalized embeddings of each verse's English translation.
Retrieval at runtime (retrieval.py) embeds the user's situation with the same
model and ranks by cosine similarity (a dot product, since vectors are normalized).
"""
import json
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

DATA = Path(__file__).parent / "data"
MODEL_NAME = "all-MiniLM-L6-v2"


def main() -> None:
    corpus = json.loads((DATA / "gita_corpus.json").read_text(encoding="utf-8"))
    texts = [v["english_translation"] for v in corpus]

    model = SentenceTransformer(MODEL_NAME)
    embeddings = model.encode(
        texts,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=True,
    ).astype(np.float32)

    np.save(DATA / "gita_embeddings.npy", embeddings)
    print(f"Wrote {embeddings.shape} embeddings for {len(corpus)} verses "
          f"using {MODEL_NAME}")


if __name__ == "__main__":
    main()
