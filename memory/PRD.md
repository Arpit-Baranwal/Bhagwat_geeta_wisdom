# Geeta Wisdom — PRD

## Original Problem Statement
> "i want to create a web app where i can get motivation from bhagwat geeta on the basis of situation i am in. then in 2nd phase i want to add a speaker to it which can narrate the sanskrit sholkah for us"

## User Choices (locked in Day 1)
- LLM: Claude Sonnet 4.5 (via Emergent Universal LLM key)
- TTS: ElevenLabs (multilingual v2, voice Adam – `pNInz6obpgDQGcFmaJgB`)
- Output: Sanskrit + Hindi + English + Practical guidance + Chapter:Verse reference
- Auth: Open access (no login)
- History & Favorites: browser localStorage (private to device)

## Architecture
- Backend: FastAPI + Motor (MongoDB) + emergentintegrations.LlmChat + elevenlabs SDK
  - `POST /api/shloka/generate` — Claude returns structured JSON shloka, persisted to `shloka_history`
  - `POST /api/tts/narrate` — ElevenLabs returns base64 mp3
  - `GET /api/history` — global recent shlokas (server-side)
  - `GET /api/` — health
- Frontend: React 19 + react-router + framer-motion + sonner + Tailwind
  - Theme: Organic & Earthy — Cormorant Garamond / Outfit / Noto Serif Devanagari, moss/sand palette
  - Pages: `/` (Home), `/favorites`, `/history`
  - localStorage keys: `geeta_favorites`, `geeta_history`

## What's Implemented (2026-02)
- [x] Day 1 MVP: situation → Claude Sonnet 4.5 → structured Sanskrit shloka
- [x] Day 1 Phase 2 (combined): ElevenLabs TTS Sanskrit narration with cached playback
- [x] Save to favorites (heart), Share (Web Share / clipboard fallback)
- [x] Local history of every query with re-open
- [x] Editorial UI: Sanskrit-first typography, staggered reveal animation, breathing loader

## Backlog
### P1 (next session)
- Add a select for ElevenLabs voice (male/female, language)
- Display chapter context / surrounding verses
- "Why this verse?" deeper explanation toggle
- Hindi UI toggle (translate UI strings to Hindi)

### P2
- Daily verse push (PWA + notification)
- Audio download (.mp3)
- Public share link with OG image
- Sign-in (Emergent Google) to sync favorites across devices

## Test Credentials
None — app is fully open access. No accounts.
