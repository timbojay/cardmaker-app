"""
Decks router — CRUD + deck back generation via ComfyUI.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException
from PIL import Image, ImageDraw

from database import get_db
from models import DeckCreate, DeckUpdate, DeckResponse
from services import comfyui, compositor

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
BACKS_DIR = PROJECT_ROOT / "assets" / "backs"

router = APIRouter(prefix="/decks", tags=["decks"])


def _row_to_response(row) -> DeckResponse:
    return DeckResponse(
        id=row["id"],
        name=row["name"],
        back_prompt=row["back_prompt"],
        back_image_path=row["back_image_path"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.get("/", response_model=list[DeckResponse])
def list_decks():
    with get_db() as db:
        rows = db.execute("SELECT * FROM decks ORDER BY id").fetchall()
    return [_row_to_response(r) for r in rows]


@router.get("/{deck_id}", response_model=DeckResponse)
def get_deck(deck_id: str):
    with get_db() as db:
        row = db.execute("SELECT * FROM decks WHERE id = ?", (deck_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Deck not found")
    return _row_to_response(row)


@router.post("/", response_model=DeckResponse, status_code=201)
def create_deck(deck: DeckCreate):
    now = datetime.now(timezone.utc).isoformat()
    with get_db() as db:
        db.execute(
            "INSERT INTO decks (id, name, back_prompt, back_image_path, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (deck.id, deck.name, deck.back_prompt, None, now, now),
        )
        row = db.execute("SELECT * FROM decks WHERE id = ?", (deck.id,)).fetchone()
    return _row_to_response(row)


@router.put("/{deck_id}", response_model=DeckResponse)
def update_deck(deck_id: str, deck: DeckUpdate):
    now = datetime.now(timezone.utc).isoformat()
    with get_db() as db:
        existing = db.execute("SELECT * FROM decks WHERE id = ?", (deck_id,)).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Deck not found")

        updates = {}
        if deck.name is not None:
            updates["name"] = deck.name
        if deck.back_prompt is not None:
            updates["back_prompt"] = deck.back_prompt

        if updates:
            updates["updated_at"] = now
            set_clause = ", ".join(f"{k} = ?" for k in updates)
            values = list(updates.values()) + [deck_id]
            db.execute(f"UPDATE decks SET {set_clause} WHERE id = ?", values)

        row = db.execute("SELECT * FROM decks WHERE id = ?", (deck_id,)).fetchone()
    return _row_to_response(row)


@router.delete("/{deck_id}", status_code=204)
def delete_deck(deck_id: str):
    with get_db() as db:
        existing = db.execute("SELECT * FROM decks WHERE id = ?", (deck_id,)).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Deck not found")
        db.execute("DELETE FROM decks WHERE id = ?", (deck_id,))


@router.post("/{deck_id}/generate-back", response_model=DeckResponse)
def generate_deck_back(deck_id: str):
    """Generate a deck back image via ComfyUI."""
    with get_db() as db:
        row = db.execute("SELECT * FROM decks WHERE id = ?", (deck_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Deck not found")

    deck_data = dict(row)
    if not deck_data["back_prompt"]:
        raise HTTPException(status_code=400, detail="Deck has no back_prompt set")

    # Check ComfyUI
    status = comfyui.get_status()
    if status["status"] != "connected":
        raise HTTPException(status_code=503, detail="ComfyUI is not running")

    # Generate back image
    seed = hash(deck_data["id"]) % (2**32)
    art_image = comfyui.generate_image(
        deck_data["back_prompt"],
        compositor.CARD_W,
        compositor.CARD_H,
        seed,
    )

    # Add rounded corners
    img = art_image.resize((compositor.CARD_W, compositor.CARD_H), Image.LANCZOS).convert("RGBA")
    mask = Image.new("L", (compositor.CARD_W, compositor.CARD_H), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle([0, 0, compositor.CARD_W, compositor.CARD_H], radius=25, fill=255)
    img.putalpha(mask)

    # Save
    BACKS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = BACKS_DIR / f"{deck_data['id']}_back.png"
    img.save(str(out_path), dpi=(300, 300))

    # Update DB
    now = datetime.now(timezone.utc).isoformat()
    with get_db() as db:
        db.execute(
            "UPDATE decks SET back_image_path = ?, updated_at = ? WHERE id = ?",
            (str(out_path), now, deck_data["id"]),
        )
        row = db.execute("SELECT * FROM decks WHERE id = ?", (deck_data["id"],)).fetchone()

    return _row_to_response(row)
