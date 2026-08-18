"""
Card Types router — CRUD + border generation via ComfyUI.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException

from database import get_db
from models import CardTypeCreate, CardTypeUpdate, CardTypeResponse
from services import comfyui, compositor

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
BORDERS_DIR = PROJECT_ROOT / "assets" / "borders"

router = APIRouter(prefix="/card-types", tags=["card_types"])


def _row_to_response(row) -> CardTypeResponse:
    return CardTypeResponse(
        id=row["id"],
        name=row["name"],
        deck_id=row["deck_id"],
        border_color=json.loads(row["border_color"]) if row["border_color"] else [],
        border_accent=json.loads(row["border_accent"]) if row["border_accent"] else [],
        border_prompt=row["border_prompt"],
        border_image_path=row["border_image_path"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.get("/", response_model=list[CardTypeResponse])
def list_card_types(deck_id: str | None = None):
    with get_db() as db:
        if deck_id:
            rows = db.execute("SELECT * FROM card_types WHERE deck_id = ? ORDER BY id", (deck_id,)).fetchall()
        else:
            rows = db.execute("SELECT * FROM card_types ORDER BY id").fetchall()
    return [_row_to_response(r) for r in rows]


@router.get("/{type_id}", response_model=CardTypeResponse)
def get_card_type(type_id: str):
    with get_db() as db:
        row = db.execute("SELECT * FROM card_types WHERE id = ?", (type_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Card type not found")
    return _row_to_response(row)


@router.post("/", response_model=CardTypeResponse, status_code=201)
def create_card_type(ct: CardTypeCreate):
    now = datetime.now(timezone.utc).isoformat()
    with get_db() as db:
        db.execute(
            """INSERT INTO card_types (id, name, deck_id, border_color, border_accent, border_prompt,
               border_image_path, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                ct.id, ct.name, ct.deck_id,
                json.dumps(ct.border_color), json.dumps(ct.border_accent),
                ct.border_prompt, None, now, now,
            ),
        )
        row = db.execute("SELECT * FROM card_types WHERE id = ?", (ct.id,)).fetchone()
    return _row_to_response(row)


@router.put("/{type_id}", response_model=CardTypeResponse)
def update_card_type(type_id: str, ct: CardTypeUpdate):
    now = datetime.now(timezone.utc).isoformat()
    with get_db() as db:
        existing = db.execute("SELECT * FROM card_types WHERE id = ?", (type_id,)).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Card type not found")

        updates = {}
        if ct.name is not None:
            updates["name"] = ct.name
        if ct.deck_id is not None:
            updates["deck_id"] = ct.deck_id
        if ct.border_color is not None:
            updates["border_color"] = json.dumps(ct.border_color)
        if ct.border_accent is not None:
            updates["border_accent"] = json.dumps(ct.border_accent)
        if ct.border_prompt is not None:
            updates["border_prompt"] = ct.border_prompt

        if updates:
            updates["updated_at"] = now
            set_clause = ", ".join(f"{k} = ?" for k in updates)
            values = list(updates.values()) + [type_id]
            db.execute(f"UPDATE card_types SET {set_clause} WHERE id = ?", values)

        row = db.execute("SELECT * FROM card_types WHERE id = ?", (type_id,)).fetchone()
    return _row_to_response(row)


@router.delete("/{type_id}", status_code=204)
def delete_card_type(type_id: str):
    with get_db() as db:
        existing = db.execute("SELECT * FROM card_types WHERE id = ?", (type_id,)).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Card type not found")
        db.execute("DELETE FROM card_types WHERE id = ?", (type_id,))


@router.post("/{type_id}/generate-border", response_model=CardTypeResponse)
def generate_border(type_id: str):
    """Generate a border image for this card type via ComfyUI."""
    with get_db() as db:
        row = db.execute("SELECT * FROM card_types WHERE id = ?", (type_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Card type not found")

    ct_data = dict(row)
    border_color = json.loads(ct_data["border_color"]) if ct_data["border_color"] else [150, 150, 150]
    border_accent = json.loads(ct_data["border_accent"]) if ct_data["border_accent"] else [200, 200, 200]

    if not ct_data["border_prompt"]:
        raise HTTPException(status_code=400, detail="Card type has no border_prompt set")

    # Check ComfyUI
    status = comfyui.get_status()
    if status["status"] != "connected":
        raise HTTPException(status_code=503, detail="ComfyUI is not running")

    # Generate border art
    seed = hash(ct_data["id"]) % (2**32)
    prompt = comfyui.build_border_prompt(
        ct_data["border_prompt"],
        compositor.CARD_W,
        compositor.CARD_H,
        seed,
    )
    prompt_id = comfyui.queue_prompt(prompt)
    history = comfyui.wait_for_completion(prompt_id)
    raw_image = comfyui.get_generated_image(history)

    # Create border overlay
    border = compositor.create_border_overlay(
        raw_image,
        border_color=tuple(border_color),
        border_accent=tuple(border_accent),
    )

    # Save
    BORDERS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = BORDERS_DIR / f"{ct_data['id']}_border.png"
    border.save(str(out_path), dpi=(300, 300))

    # Update DB
    now = datetime.now(timezone.utc).isoformat()
    with get_db() as db:
        db.execute(
            "UPDATE card_types SET border_image_path = ?, updated_at = ? WHERE id = ?",
            (str(out_path), now, ct_data["id"]),
        )
        row = db.execute("SELECT * FROM card_types WHERE id = ?", (ct_data["id"],)).fetchone()

    return _row_to_response(row)
