# Geeta Wisdom

Describe a life situation and get a relevant Bhagavad Gita shloka — Sanskrit, transliteration,
Hindi & English translation, and practical guidance — with optional Sanskrit audio narration.

- **Frontend:** React 19 + CRACO + Tailwind + framer-motion
- **Backend:** FastAPI + Motor (MongoDB)
- **Retrieval (RAG):** a verified 701-verse Bhagavad Gita corpus (`backend/data/gita_corpus.json`) with
  precomputed `sentence-transformers` embeddings (`all-MiniLM-L6-v2`).
- **LLM:** Claude Haiku 4.5 via the Anthropic API (verse selection + guidance only)
- **TTS:** ElevenLabs (`eleven_multilingual_v2`)

## How it works

The pipeline is designed so that **scripture can never be hallucinated** — the guarantee is
enforced by code, not by prompting.

```
situation → semantic search (top-3 verses) → LLM picks an index + writes guidance
          → server looks up that verse's text from the corpus → combine → respond
```

1. **Retrieve.** The user's situation is embedded and compared (cosine similarity) against the
   precomputed corpus embeddings; the top-3 verses are selected. See
   [`backend/retrieval.py`](backend/retrieval.py).
2. **Select — the LLM chooses, it does not author.** The 3 candidate verses are handed to Claude,
   which returns **only** a `chosen_index` (0–2) plus a short `practical_guidance` paragraph
   ([`backend/prompts.py`](backend/prompts.py)). It is never asked to reproduce Sanskrit or translations.
3. **Assemble from the source of truth.** The server takes the index, validates its range, and
   serves the verse text (Sanskrit, transliteration, Hindi/English translations, reference)
   **verbatim from the corpus** — never from the model's output ([`backend/server.py`](backend/server.py)).

So the model's generative text reaches the user only as the *guidance paragraph*. The **verse
itself is always a corpus lookup**, so no shloka can be fabricated even if the model misbehaves.
This is an authenticity guarantee (the scripture is real), not a relevance guarantee (the model
can still pick a less-fitting verse) — retrieval falls back to the top-similarity verse on any
LLM/parse failure, and refuses to answer when no verse clears a minimum similarity threshold.

**Guardrails** ([`backend/guardrails.py`](backend/guardrails.py)) wrap the endpoint: per-client
rate limiting, input length/abuse checks, an off-topic/gibberish pre-filter, a crisis/self-harm
short-circuit that surfaces support resources instead of a verse, a relevance gate, and moderation
of the LLM-authored guidance before it is trusted.

To rebuild embeddings after editing the corpus: `cd backend && python build_embeddings.py`.

> **Deployment note:** the backend runs a `sentence-transformers` model (`all-MiniLM-L6-v2`, ~90MB).
> It is **baked into the Docker image at build time** (see [`backend/Dockerfile`](backend/Dockerfile)),
> so the first request is instant and doesn't depend on a runtime download. Budget ~1GB RAM for
> `torch` + the model; CPU-only `torch` is installed to keep the image small enough for a free CPU Space.

## Prerequisites
- Node 18+ and Yarn (Classic) for the frontend
- Python 3.11+ for the backend
- A MongoDB instance (local, or free [MongoDB Atlas](https://www.mongodb.com/atlas))
- An [Anthropic API key](https://console.anthropic.com/) (required)
- An [ElevenLabs API key](https://elevenlabs.io/) (optional — needed only for audio narration)

## Local development

### Backend
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then fill in the values
uvicorn server:app --reload   # serves on http://localhost:8000
```

`.env` keys: `MONGO_URL`, `DB_NAME`, `ANTHROPIC_API_KEY`, `ELEVENLABS_API_KEY`, `CORS_ORIGINS`.

### Frontend
```bash
cd frontend
yarn install
cp .env.example .env          # set REACT_APP_BACKEND_URL=http://localhost:8000
yarn start                    # serves on http://localhost:3000
```

## Deployment

### Backend → Hugging Face Spaces (Docker)
- Create a new **Docker** Space and push the contents of `backend/` to it (the
  [`backend/Dockerfile`](backend/Dockerfile) builds the image and bakes in the embedding model).
- The container listens on **port 7860**, which HF Spaces expects.
- Add `MONGO_URL`, `ANTHROPIC_API_KEY`, `ELEVENLABS_API_KEY`, and `CORS_ORIGINS` as **Space secrets**
  (Settings → Variables and secrets). `CORS_ORIGINS` must be your Vercel frontend origin.
- Use a Space with ≥1GB RAM for `torch` + the model.

### Frontend → Vercel
- Import the repo, set the project **root directory** to `frontend/`.
- [`frontend/vercel.json`](frontend/vercel.json) configures the build and SPA routing.
- Set the `REACT_APP_BACKEND_URL` env var to your deployed backend URL.

### Database → MongoDB Atlas
Create a free cluster and use its connection string as `MONGO_URL` on the backend.

## API
- `POST /api/shloka/generate` — `{ "situation": "..." }` → structured shloka JSON
- `POST /api/tts/narrate` — `{ "text": "..." }` → base64 mp3
- `GET /api/history` — recent generated shlokas
- `GET /api/` — health check
