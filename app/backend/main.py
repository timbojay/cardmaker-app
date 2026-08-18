"""
CardMaker FastAPI backend.

Run with: cd app/backend && uvicorn main:app --reload
"""

import json
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from database import init_db, _migrate_db, is_db_empty, import_from_json
from routers import cards, decks, card_types, icons as icons_router, backgrounds, export
from services import comfyui

PROJECT_ROOT = Path(__file__).parent.parent.parent
ASSETS_DIR = PROJECT_ROOT / "assets"
OUTPUT_DIR = PROJECT_ROOT / "output"
CARDS_JSON = PROJECT_ROOT / "card-data" / "space_junk_cards.json"
ICONS_DIR = ASSETS_DIR / "icons"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    _migrate_db()
    if is_db_empty():
        print("Database is empty — importing from JSON files...")
        import_from_json()
        print("Import complete.")
    yield
    # Shutdown (nothing to clean up)


app = FastAPI(title="CardMaker API", version="0.1.0", lifespan=lifespan)

# CORS for Vite dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static file mounts
ASSETS_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static/assets", StaticFiles(directory=str(ASSETS_DIR)), name="assets")
app.mount("/static/output", StaticFiles(directory=str(OUTPUT_DIR)), name="output")

# Routers
app.include_router(cards.router, prefix="/api")
app.include_router(decks.router, prefix="/api")
app.include_router(card_types.router, prefix="/api")
app.include_router(icons_router.router, prefix="/api")
app.include_router(backgrounds.router, prefix="/api")
app.include_router(export.router, prefix="/api")


@app.get("/api/comfyui/status")
def comfyui_status():
    """Check ComfyUI connection status."""
    return comfyui.get_status()


@app.get("/api/layout")
def get_layout():
    """Return the layout config from the cards JSON."""
    with open(CARDS_JSON) as f:
        data = json.load(f)
    return {
        "card_specs": data["card_specs"],
        "layout": data["layout"],
    }


@app.get("/api/icon-names")
def list_icon_names():
    """Return simple list of available icon names (for dropdowns)."""
    if not ICONS_DIR.exists():
        return []
    return sorted(p.stem for p in ICONS_DIR.glob("*.png"))
