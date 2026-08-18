"""
Cards router — CRUD, generate art via ComfyUI, and preview with placeholder art.
"""

import io
import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from PIL import Image

from database import get_db
from models import CardCreate, CardUpdate, CardResponse
from services import comfyui, compositor

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output" / "print-ready"
PREVIEW_DIR = PROJECT_ROOT / "output" / "previews"
RAW_ART_DIR = PROJECT_ROOT / "output" / "raw-art"

router = APIRouter(prefix="/cards", tags=["cards"])


def _row_to_response(row) -> CardResponse:
    return CardResponse(
        id=row["id"],
        title=row["title"],
        deck_id=row["deck_id"],
        background_id=row["background_id"],
        benefits=json.loads(row["benefits"]) if row["benefits"] else {},
        costs=json.loads(row["costs"]) if row["costs"] else {},
        description=row["description"],
        art_prompt=row["art_prompt"],
        title_size=row["title_size"] if "title_size" in row.keys() else "medium",
        desc_size=row["desc_size"] if "desc_size" in row.keys() else "medium",
        show_plus=bool(row["show_plus"]) if "show_plus" in row.keys() else True,
        show_minus=bool(row["show_minus"]) if "show_minus" in row.keys() else True,
        art_image_path=row["art_image_path"],
        print_image_path=row["print_image_path"],
        preview_image_path=row["preview_image_path"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.get("/", response_model=list[CardResponse])
def list_cards(deck_id: str | None = None):
    with get_db() as db:
        query = "SELECT * FROM cards WHERE 1=1"
        params = []
        if deck_id:
            query += " AND deck_id = ?"
            params.append(deck_id)
        query += " ORDER BY id"
        rows = db.execute(query, params).fetchall()
    return [_row_to_response(r) for r in rows]


@router.get("/{card_id}", response_model=CardResponse)
def get_card(card_id: str):
    with get_db() as db:
        row = db.execute("SELECT * FROM cards WHERE id = ?", (card_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Card not found")
    return _row_to_response(row)


@router.post("/", response_model=CardResponse, status_code=201)
def create_card(card: CardCreate):
    now = datetime.now(timezone.utc).isoformat()
    with get_db() as db:
        db.execute(
            """INSERT INTO cards (id, title, deck_id, background_id, benefits, costs, description, art_prompt,
               title_size, desc_size, show_plus, show_minus,
               art_image_path, print_image_path, preview_image_path, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                card.id, card.title, card.deck_id, card.background_id,
                json.dumps(card.benefits), json.dumps(card.costs),
                card.description, card.art_prompt,
                card.title_size or "medium", card.desc_size or "medium",
                1 if card.show_plus else 0, 1 if card.show_minus else 0,
                None, None, None, now, now,
            ),
        )
        row = db.execute("SELECT * FROM cards WHERE id = ?", (card.id,)).fetchone()
    return _row_to_response(row)


@router.put("/{card_id}", response_model=CardResponse)
def update_card(card_id: str, card: CardUpdate):
    now = datetime.now(timezone.utc).isoformat()
    with get_db() as db:
        existing = db.execute("SELECT * FROM cards WHERE id = ?", (card_id,)).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Card not found")

        updates = {}
        if card.title is not None:
            updates["title"] = card.title
        if card.deck_id is not None:
            updates["deck_id"] = card.deck_id
        if card.background_id is not None:
            updates["background_id"] = card.background_id
        if card.benefits is not None:
            updates["benefits"] = json.dumps(card.benefits)
        if card.costs is not None:
            updates["costs"] = json.dumps(card.costs)
        if card.description is not None:
            updates["description"] = card.description
        if card.art_prompt is not None:
            updates["art_prompt"] = card.art_prompt
        if card.title_size is not None:
            updates["title_size"] = card.title_size
        if card.desc_size is not None:
            updates["desc_size"] = card.desc_size
        if card.show_plus is not None:
            updates["show_plus"] = 1 if card.show_plus else 0
        if card.show_minus is not None:
            updates["show_minus"] = 1 if card.show_minus else 0

        if updates:
            updates["updated_at"] = now
            set_clause = ", ".join(f"{k} = ?" for k in updates)
            values = list(updates.values()) + [card_id]
            db.execute(f"UPDATE cards SET {set_clause} WHERE id = ?", values)

        row = db.execute("SELECT * FROM cards WHERE id = ?", (card_id,)).fetchone()
    return _row_to_response(row)


@router.delete("/{card_id}", status_code=204)
def delete_card(card_id: str):
    with get_db() as db:
        existing = db.execute("SELECT * FROM cards WHERE id = ?", (card_id,)).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Card not found")
        db.execute("DELETE FROM cards WHERE id = ?", (card_id,))


@router.post("/{card_id}/generate", response_model=CardResponse)
def generate_card(card_id: str):
    """Generate card art via ComfyUI and composite the final print-ready card."""
    # Always reload icons fresh in case they've been regenerated
    compositor.clear_icon_cache()
    with get_db() as db:
        row = db.execute("SELECT * FROM cards WHERE id = ?", (card_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Card not found")

    card_data = dict(row)
    card_data["benefits"] = json.loads(card_data["benefits"]) if card_data["benefits"] else {}
    card_data["costs"] = json.loads(card_data["costs"]) if card_data["costs"] else {}

    # Check ComfyUI
    status = comfyui.get_status()
    if status["status"] != "connected":
        raise HTTPException(status_code=503, detail="ComfyUI is not running")

    # Load layout from JSON
    cards_json = PROJECT_ROOT / "card-data" / "space_junk_cards.json"
    with open(cards_json) as f:
        data = json.load(f)
    specs = data["card_specs"]
    layout = data["layout"]

    # Generate art
    seed = hash(card_data["id"]) % (2**32)
    art_image = comfyui.generate_image(
        card_data["art_prompt"], specs["width_px"], specs["height_px"], seed
    )

    # Save raw art for later recompositing
    RAW_ART_DIR.mkdir(parents=True, exist_ok=True)
    art_path = RAW_ART_DIR / f"{card_data['id']}_art.png"
    art_image.convert("RGB").save(str(art_path), dpi=(300, 300))

    # Composite
    final = compositor.composite_card(art_image, card_data, layout)
    final = compositor.apply_border(final, card_data.get("background_id", ""))
    final = compositor.draw_pm_overlay(final)

    # Save print-ready
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)

    print_path = OUTPUT_DIR / f"{card_data['id']}_print.png"
    final_rgb = final.convert("RGB")
    final_rgb.save(str(print_path), dpi=(300, 300))

    # Save preview
    preview = final_rgb.resize((413, 563), Image.LANCZOS)
    preview_path = PREVIEW_DIR / f"{card_data['id']}_preview.jpg"
    preview.save(str(preview_path), quality=85)

    # Update DB
    now = datetime.now(timezone.utc).isoformat()
    with get_db() as db:
        db.execute(
            "UPDATE cards SET art_image_path = ?, print_image_path = ?, preview_image_path = ?, updated_at = ? WHERE id = ?",
            (str(art_path), str(print_path), str(preview_path), now, card_data["id"]),
        )
        row = db.execute("SELECT * FROM cards WHERE id = ?", (card_data["id"],)).fetchone()

    return _row_to_response(row)


@router.post("/{card_id}/recomposite", response_model=CardResponse)
def recomposite_card(card_id: str):
    """Re-composite the card using saved raw art + current card data (no ComfyUI needed)."""
    # Always reload icons fresh in case they've been regenerated
    compositor.clear_icon_cache()
    with get_db() as db:
        row = db.execute("SELECT * FROM cards WHERE id = ?", (card_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Card not found")

    card_data = dict(row)
    card_data["benefits"] = json.loads(card_data["benefits"]) if card_data["benefits"] else {}
    card_data["costs"] = json.loads(card_data["costs"]) if card_data["costs"] else {}

    # Check raw art exists
    if not card_data["art_image_path"]:
        raise HTTPException(status_code=400, detail="No saved art found. Generate art first.")
    art_path = Path(card_data["art_image_path"])
    if not art_path.exists():
        raise HTTPException(status_code=400, detail="Saved art file not found. Generate art first.")

    art_image = Image.open(str(art_path)).convert("RGBA")

    # Load layout
    cards_json = PROJECT_ROOT / "card-data" / "space_junk_cards.json"
    with open(cards_json) as f:
        data = json.load(f)
    layout = data["layout"]

    # Composite with current card data
    final = compositor.composite_card(art_image, card_data, layout)
    final = compositor.apply_border(final, card_data.get("background_id", ""))
    final = compositor.draw_pm_overlay(final)

    # Save print-ready
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)

    print_path = OUTPUT_DIR / f"{card_data['id']}_print.png"
    final_rgb = final.convert("RGB")
    final_rgb.save(str(print_path), dpi=(300, 300))

    # Save preview
    preview = final_rgb.resize((413, 563), Image.LANCZOS)
    preview_path = PREVIEW_DIR / f"{card_data['id']}_preview.jpg"
    preview.save(str(preview_path), quality=85)

    # Update DB
    now = datetime.now(timezone.utc).isoformat()
    with get_db() as db:
        db.execute(
            "UPDATE cards SET print_image_path = ?, preview_image_path = ?, updated_at = ? WHERE id = ?",
            (str(print_path), str(preview_path), now, card_data["id"]),
        )
        row = db.execute("SELECT * FROM cards WHERE id = ?", (card_data["id"],)).fetchone()

    return _row_to_response(row)


@router.get("/{card_id}/preview")
def preview_card(card_id: str):
    """Return the generated preview if available, otherwise composite with placeholder art."""
    with get_db() as db:
        row = db.execute("SELECT * FROM cards WHERE id = ?", (card_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Card not found")

    # If a generated preview exists on disk, serve it directly
    if row["preview_image_path"]:
        preview_file = Path(row["preview_image_path"])
        if preview_file.exists():
            media = "image/jpeg" if preview_file.suffix == ".jpg" else "image/png"
            return StreamingResponse(open(preview_file, "rb"), media_type=media)

    card_data = dict(row)
    card_data["benefits"] = json.loads(card_data["benefits"]) if card_data["benefits"] else {}
    card_data["costs"] = json.loads(card_data["costs"]) if card_data["costs"] else {}

    # Load layout
    cards_json = PROJECT_ROOT / "card-data" / "space_junk_cards.json"
    with open(cards_json) as f:
        data = json.load(f)
    layout = data["layout"]
    specs = data["card_specs"]

    # Create placeholder art
    placeholder = compositor.create_placeholder_art(specs["width_px"], specs["height_px"])

    # Composite
    final = compositor.composite_card(placeholder, card_data, layout)
    final = compositor.apply_border(final, card_data.get("background_id", ""))
    final = compositor.draw_pm_overlay(final)

    # Return as PNG stream
    buf = io.BytesIO()
    final.convert("RGB").save(buf, format="PNG")
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")
