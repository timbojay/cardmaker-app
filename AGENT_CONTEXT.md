# CardMaker — Agent Handoff Notes

## What this project is

CardMaker is a local full-stack tool for generating print-ready playing cards for the Space Junk board game. It has a FastAPI backend, a Vite/React/TypeScript frontend, and uses ComfyUI + FLUX.1-schnell for AI-generated card art.

## Where things live

- **Project root:** `/Users/timothyjordan/projects/Programming Projects/cardmaker-app`
- **Backend:** `app/backend/` — FastAPI app in `main.py`
- **Frontend:** `app/frontend/` — Vite + React + TS, entry `src/main.tsx`
- **Card data:** `card-data/space_junk_cards.json` + `card-data/decks.json`
- **Assets:** `assets/icons/`, `assets/borders/`, `assets/backgrounds/`, `assets/backs/`
- **Output:** `output/print-ready/`, `output/previews/`, `output/raw-art/` (ignored by git)
- **Config:** `config.py` — FLUX/CLIP/VAE model names
- **Launcher:** `app/run.sh`

## How to start

```bash
cd "/Users/timothyjordan/projects/Programming Projects/cardmaker-app"
bash app/run.sh
```

This starts the backend (`localhost:8000`) and frontend (`localhost:5173`) and opens the browser.

To check status:

```bash
bash app/run.sh status
```

To stop:

```bash
bash app/run.sh stop
```

## Important quirks

- **ComfyUI must be running separately** for AI generation (`http://localhost:8188`). The editor and database work without it.
- **Python interpreter:** `app/run.sh` detects `/opt/anaconda3/bin/python` first, then falls back to `python3`. The Anaconda env has all required packages.
- **Database:** SQLite at `app/backend/cardmaker.db` (ignored by git). It auto-seeds from `card-data/*.json` on first run.
- **Migrations:** `database.py` has `_migrate_db()` that adds missing columns (e.g., `title_size`, `show_plus`).
- **Static assets:** Backend mounts `/static/assets` and `/static/output` from the project `assets/` and `output/` folders.
- **Frontend proxy:** Vite proxies `/api` and `/static` to `localhost:8000` during dev.
- **Card layout:** `card-data/space_junk_cards.json` defines card specs and layout. `services/compositor.py` renders the card.
- **Borders/backgrounds:** The app looks for border overlays in `assets/backgrounds/{id}_border.png` first, then the legacy `assets/borders/{id}_border.png`.

## Common commands

```bash
# Backend tests
pytest tests/ -q

# Frontend type-check
cd app/frontend && npx tsc --noEmit

# Frontend lint
cd app/frontend && npm run lint

# Backend only
cd app/backend && uvicorn main:app --reload --port 8000

# Frontend only
cd app/frontend && npm run dev
```

## Known technical debt / TODOs

- Only three sample cards exist (`sj-005`, `sj-006`, `sj-007`). Expand the deck.
- `scripts/generate_cards.py` duplicates backend compositor logic; kept as CLI batch tool.
- Frontend has no automated tests yet.
- No formal print-to-PDF pipeline; output is per-card PNGs.

## When picking this up

1. Read the latest `README.md`.
2. Check `git status` and `git log --oneline -5`.
3. Run `pytest tests/ -q` and frontend `npx tsc --noEmit` to confirm health.
4. Run `bash app/run.sh status` to see if services are already up.
