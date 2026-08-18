# CardMaker App

AI-powered playing card generator for the **Space Junk** board game. Runs entirely on local hardware (24GB M4 MacBook Pro) using ComfyUI + FLUX.1-schnell.

## Quick Start

```bash
cd "/Users/timothyjordan/projects/Programming Projects/cardmaker-app"

# Install Python dependencies (backend + scripts)
pip install -r requirements.txt

# Install frontend dependencies
cd app/frontend
npm install

# Start ComfyUI (in a separate terminal)
cd /Users/timothyjordan/Git/ComfyUI
python main.py

# Back in the project root, start the CardMaker app
bash app/run.sh
```

The app will open at `http://localhost:5173`. The backend runs on `http://localhost:8000`.

> **Note:** ComfyUI must be running for AI image generation. The card editor, gallery, and data management features work without it.

---

## Components

| Component | Tech | Location | Purpose |
|-----------|------|----------|---------|
| Backend | FastAPI + SQLite | `app/backend/` | REST API, card CRUD, image generation orchestration, export |
| Frontend | Vite + React + TypeScript | `app/frontend/` | Web UI for browsing, editing, and generating cards |
| Scripts | Python (PIL, requests) | `scripts/` | CLI batch generators for cards, borders, backs, and icons |
| Card data | JSON | `card-data/` | Card definitions, deck definitions, layout specs |
| Assets | PNG images | `assets/` | Borders, backs, icons, backgrounds |
| Output | PNG/JPEG | `output/` | Print-ready cards, previews, raw AI-generated art |

---

## Architecture

```
ComfyUI (image generation)
    └── FLUX.1-schnell model (quantized, ~12GB)
    └── Custom workflow: generates full card art at print resolution
    └── Post-processing: composes text/number boxes at fixed positions

Backend (FastAPI)
    └── REST API: /api/cards, /api/decks, /api/backgrounds, /api/icons, /api/export
    └── SQLite database for cards/decks/backgrounds
    └── Services: ComfyUI client + card compositor

Frontend (Vite/React/TypeScript)
    └── Gallery, card editor, deck editor, icon editor, background editor
    └── Proxies /api and /static to the backend dev server

Scripts (CLI)
    └── card-data/*.json — card definitions (name, stats, flavor text)
    └── templates/ — card layout templates (box positions, fonts)
    └── output/print-ready/ — final 825x1125px 300DPI PNGs
```

---

## Card Specs (Poker Size)

- **Card size:** 2.5" x 3.5" (63.5mm x 88.9mm)
- **With bleed:** 2.75" x 3.75" (825 x 1125 px @ 300 DPI)
- **Safe area:** 2.25" x 3.25" (675 x 975 px @ 300 DPI)
- **Color space:** CMYK for print, RGB for preview
- **Format:** PNG (print-ready), JPEG (previews)

---

## Setup

### 1. Install ComfyUI

```bash
cd /Users/timothyjordan/Git
git clone https://github.com/comfyanonymous/ComfyUI.git
cd ComfyUI
pip install -r requirements.txt
```

### 2. Download FLUX.1-schnell (quantized)

```bash
# Using Hugging Face CLI
pip install huggingface_hub
huggingface-cli download black-forest-labs/FLUX.1-schnell \
    --local-dir ComfyUI/models/unet/
```

Or download the Q8 GGUF quantized version (~12GB) for better VRAM fit:
```bash
huggingface-cli download city96/FLUX.1-schnell-gguf \
    flux1-schnell-Q8_0.gguf \
    --local-dir ComfyUI/models/unet/
```

### 3. Download required supporting models

```bash
# CLIP text encoders (needed for FLUX)
huggingface-cli download comfyanonymous/flux_text_encoders \
    clip_l.safetensors t5xxl_fp16.safetensors \
    --local-dir ComfyUI/models/clip/

# VAE
huggingface-cli download black-forest-labs/FLUX.1-schnell \
    ae.safetensors \
    --local-dir ComfyUI/models/vae/
```

### 4. Install CardMaker dependencies

```bash
cd "/Users/timothyjordan/projects/Programming Projects/cardmaker-app"
pip install -r requirements.txt
```

### 5. Run

```bash
# Start ComfyUI (in a separate terminal)
cd /Users/timothyjordan/Git/ComfyUI
python main.py

# Start CardMaker
bash app/run.sh
```

---

## Directory Structure

```
cardmaker-app/
├── AGENT_CONTEXT.md      # Agent handoff notes
├── README.md             # This file
├── requirements.txt      # Top-level Python dependencies
├── config.py             # Model configuration (FLUX, CLIP, VAE)
├── app/
│   ├── backend/          # FastAPI backend
│   │   ├── main.py
│   │   ├── database.py
│   │   ├── models.py
│   │   ├── requirements.txt
│   │   ├── routers/      # API endpoints
│   │   └── services/   # ComfyUI client + compositor
│   ├── frontend/         # Vite + React + TypeScript UI
│   │   ├── src/
│   │   └── package.json
│   └── run.sh            # One-command launcher
├── card-data/            # Card definitions (JSON)
│   ├── decks.json
│   └── space_junk_cards.json
├── scripts/              # CLI generation and utility scripts
│   ├── generate_cards.py
│   ├── generate_assets.py
│   └── generate_icons.py
├── assets/
│   ├── backgrounds/      # Card background/border overlays
│   ├── backs/            # Deck back images
│   ├── borders/          # Legacy border images
│   └── icons/            # Game icons (benefits, costs, stats)
├── output/
│   ├── print-ready/      # Final 300DPI print files
│   ├── previews/         # Low-res preview images
│   └── raw-art/          # Uncomposited AI-generated art
└── tests/                # Backend tests
```

---

## Useful Commands

```bash
# Run backend tests
pytest tests/ -q

# Type-check frontend
cd app/frontend && npx tsc --noEmit

# Run frontend lint
cd app/frontend && npm run lint

# Start backend only
cd app/backend && uvicorn main:app --reload --port 8000

# Start frontend only
cd app/frontend && npm run dev
```

---

## License

Private project.
