# Geeta Wisdom

Describe a life situation and get a relevant Bhagavad Gita shloka — Sanskrit, transliteration,
Hindi & English translation, and practical guidance — with optional Sanskrit audio narration.

- **Frontend:** React 19 + CRACO + Tailwind + framer-motion
- **Backend:** FastAPI + Motor (MongoDB)
- **Retrieval (RAG):** a verified 701-verse Bhagavad Gita corpus (`backend/data/gita_corpus.json`) with
  precomputed `sentence-transformers` embeddings (`all-MiniLM-L6-v2`). The endpoint retrieves the top-3
  most relevant verses, then Claude selects the best fit and writes the guidance — verse text is always
  served verbatim from the corpus, never generated, so no shloka can be hallucinated.
- **LLM:** Claude Haiku 4.5 via the Anthropic API (selection + guidance only)
- **TTS:** ElevenLabs (`eleven_multilingual_v2`)

To rebuild embeddings after editing the corpus: `cd backend && python build_embeddings.py`.

> **Deployment note:** the backend loads a `sentence-transformers` model (~90MB, downloaded from
> Hugging Face on first request and cached). Budget ~1GB RAM for `torch` + model — Render/Railway's
> smallest free tiers may be too small; use a paid instance or an instance with ≥1GB. The corpus and
> embeddings are committed, so only the model itself is fetched at runtime.

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

### Backend → Render (or Railway)
- **Render:** push to GitHub and create a new **Blueprint** from [`render.yaml`](render.yaml).
  Set the `MONGO_URL`, `ANTHROPIC_API_KEY`, `ELEVENLABS_API_KEY`, and `CORS_ORIGINS`
  secrets in the dashboard. `CORS_ORIGINS` must be your Vercel frontend origin.
- **Railway:** point a service at the `backend/` directory; it uses [`backend/Procfile`](backend/Procfile).
  Add the same environment variables.

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
