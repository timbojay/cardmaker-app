"""
Backgrounds router — list, generate, and delete card background overlays.
Prompts and colors are persisted in assets/backgrounds/prompts.json.
Works like the icons system but generates card-sized border overlays.
"""

import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from PIL import Image

from services import comfyui, compositor

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
BG_DIR = PROJECT_ROOT / "assets" / "backgrounds"
PROMPTS_FILE = BG_DIR / "prompts.json"


def _load_prompts() -> dict:
    if PROMPTS_FILE.exists():
        with open(PROMPTS_FILE) as f:
            return json.load(f)
    return {}


def _save_prompts(prompts: dict):
    BG_DIR.mkdir(parents=True, exist_ok=True)
    with open(PROMPTS_FILE, "w") as f:
        json.dump(prompts, f, indent=2)


class BackgroundCreate(BaseModel):
    id: str
    prompt: str
    border_color: list[int] = [150, 150, 150]
    border_accent: list[int] = [200, 200, 200]


class BackgroundResponse(BaseModel):
    id: str
    prompt: str
    border_color: list[int]
    border_accent: list[int]
    has_image: bool


router = APIRouter(prefix="/backgrounds", tags=["backgrounds"])


@router.get("/", response_model=list[BackgroundResponse])
def list_backgrounds():
    """Return all available backgrounds with their prompts."""
    if not BG_DIR.exists():
        return []
    prompts = _load_prompts()
    backgrounds = []
    for p in sorted(BG_DIR.glob("*.png")):
        bg_id = p.stem.replace("_border", "")
        meta = prompts.get(bg_id, {})
        if isinstance(meta, str):
            meta = {"prompt": meta, "border_color": [150, 150, 150], "border_accent": [200, 200, 200]}
        backgrounds.append(BackgroundResponse(
            id=bg_id,
            prompt=meta.get("prompt", ""),
            border_color=meta.get("border_color", [150, 150, 150]),
            border_accent=meta.get("border_accent", [200, 200, 200]),
            has_image=True,
        ))
    return backgrounds


@router.post("/generate", response_model=BackgroundResponse)
def generate_background(data: BackgroundCreate):
    """Generate a card background overlay via ComfyUI."""
    bg_id = data.id.strip().lower().replace(" ", "_").replace("-", "_")
    if not bg_id:
        raise HTTPException(status_code=400, detail="Background ID is required")

    # Check ComfyUI
    status = comfyui.get_status()
    if status["status"] != "connected":
        raise HTTPException(status_code=503, detail="ComfyUI is not running")

    # Generate raw border art
    seed = hash(bg_id) % (2**32)
    prompt = comfyui.build_border_prompt(
        data.prompt, compositor.CARD_W, compositor.CARD_H, seed
    )
    prompt_id = comfyui.queue_prompt(prompt)
    history = comfyui.wait_for_completion(prompt_id)
    raw_image = comfyui.get_generated_image(history)

    # Create border overlay
    border = compositor.create_border_overlay(
        raw_image,
        border_color=tuple(data.border_color),
        border_accent=tuple(data.border_accent),
    )

    # Save
    BG_DIR.mkdir(parents=True, exist_ok=True)
    out_path = BG_DIR / f"{bg_id}_border.png"
    border.save(str(out_path), dpi=(300, 300))

    # Save prompt + colors
    prompts = _load_prompts()
    prompts[bg_id] = {
        "prompt": data.prompt,
        "border_color": data.border_color,
        "border_accent": data.border_accent,
    }
    _save_prompts(prompts)

    return BackgroundResponse(
        id=bg_id,
        prompt=data.prompt,
        border_color=data.border_color,
        border_accent=data.border_accent,
        has_image=True,
    )


@router.delete("/{bg_id}", status_code=204)
def delete_background(bg_id: str):
    """Delete a background file and its saved prompt."""
    bg_path = BG_DIR / f"{bg_id}_border.png"
    if not bg_path.exists():
        raise HTTPException(status_code=404, detail="Background not found")
    bg_path.unlink()

    prompts = _load_prompts()
    prompts.pop(bg_id, None)
    _save_prompts(prompts)
