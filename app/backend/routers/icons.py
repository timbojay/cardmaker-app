"""
Icons router — list, create, generate, and delete icons.
Prompts and metadata are persisted in assets/icons/prompts.json.
Icons support three sizes: small (96px), medium (128px), large (160px) on the card.
"""

import json
import random
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import numpy as np
from PIL import Image

from services import comfyui, compositor

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
ICONS_DIR = PROJECT_ROOT / "assets" / "icons"


def _remove_white_background(img: Image.Image, threshold: int = 230) -> Image.Image:
    """Replace white / near-white pixels with transparency.

    Uses a smooth falloff so edges anti-alias nicely instead of getting
    harsh jagged outlines.
    """
    rgba = img.convert("RGBA")
    data = np.array(rgba, dtype=np.float32)
    r, g, b, a = data[:, :, 0], data[:, :, 1], data[:, :, 2], data[:, :, 3]

    # How "white" each pixel is (0 = not white, 1 = pure white)
    brightness = np.minimum(np.minimum(r, g), b)
    # Smooth ramp: fully transparent above threshold, fully opaque below (threshold - 40)
    ramp_low = float(threshold - 40)
    ramp_high = float(threshold)
    alpha_factor = np.clip((ramp_high - brightness) / (ramp_high - ramp_low), 0.0, 1.0)

    data[:, :, 3] = a * alpha_factor
    return Image.fromarray(data.astype(np.uint8), "RGBA")
PROMPTS_FILE = ICONS_DIR / "prompts.json"

# Size name -> pixel size on the printed card
ICON_SIZES = {
    "small": 96,
    "medium": 128,
    "large": 160,
}


def _load_prompts() -> dict:
    if PROMPTS_FILE.exists():
        with open(PROMPTS_FILE) as f:
            data = json.load(f)
        # Migrate old string-only format to dict format
        migrated = {}
        for k, v in data.items():
            if isinstance(v, str):
                migrated[k] = {"prompt": v, "size": "small"}
            else:
                migrated[k] = v
        return migrated
    return {}


def _save_prompts(prompts: dict):
    ICONS_DIR.mkdir(parents=True, exist_ok=True)
    with open(PROMPTS_FILE, "w") as f:
        json.dump(prompts, f, indent=2)


class IconCreate(BaseModel):
    id: str
    prompt: str
    size: str = "small"


class IconResponse(BaseModel):
    id: str
    prompt: str
    size: str
    size_px: int
    has_image: bool


router = APIRouter(prefix="/icons", tags=["icons"])


@router.get("/", response_model=list[IconResponse])
def list_icons():
    """Return all available icons with their prompts and sizes."""
    if not ICONS_DIR.exists():
        return []
    prompts = _load_prompts()
    icons = []
    for p in sorted(ICONS_DIR.glob("*.png")):
        meta = prompts.get(p.stem, {})
        if isinstance(meta, str):
            meta = {"prompt": meta, "size": "small"}
        size_name = meta.get("size", "small")
        icons.append(IconResponse(
            id=p.stem,
            prompt=meta.get("prompt", ""),
            size=size_name,
            size_px=ICON_SIZES.get(size_name, 96),
            has_image=True,
        ))
    return icons


@router.get("/sizes")
def get_icon_sizes():
    """Return available icon size options."""
    return [
        {"name": "small", "px": 96, "label": "Small (96px)"},
        {"name": "medium", "px": 128, "label": "Medium (128px)"},
        {"name": "large", "px": 160, "label": "Large (160px)"},
    ]


@router.post("/generate", response_model=IconResponse)
def generate_icon(data: IconCreate):
    """Generate a new icon via ComfyUI and save it."""
    icon_id = data.id.strip().lower().replace(" ", "_").replace("-", "_")
    if not icon_id:
        raise HTTPException(status_code=400, detail="Icon ID is required")

    size_name = data.size if data.size in ICON_SIZES else "small"

    # Check ComfyUI
    status = comfyui.get_status()
    if status["status"] != "connected":
        raise HTTPException(status_code=503, detail="ComfyUI is not running")

    # Generate at 512x512 then resize to storage size (256px for quality)
    seed = random.randint(0, 2**32 - 1)
    art_image = comfyui.generate_image(data.prompt, 512, 512, seed)

    # Save at 256px - big enough for all display sizes
    ICONS_DIR.mkdir(parents=True, exist_ok=True)
    icon = art_image.resize((256, 256), Image.LANCZOS)
    icon = _remove_white_background(icon)
    out_path = ICONS_DIR / f"{icon_id}.png"
    icon.save(str(out_path))

    # Save prompt + size
    prompts = _load_prompts()
    prompts[icon_id] = {"prompt": data.prompt, "size": size_name}
    _save_prompts(prompts)

    # Clear compositor cache so new size takes effect
    compositor.clear_icon_cache()

    return IconResponse(
        id=icon_id,
        prompt=data.prompt,
        size=size_name,
        size_px=ICON_SIZES[size_name],
        has_image=True,
    )


class IconUpdate(BaseModel):
    prompt: Optional[str] = None
    size: Optional[str] = None


@router.put("/{icon_id}", response_model=IconResponse)
def update_icon(icon_id: str, data: IconUpdate):
    """Update icon metadata (prompt, size) without regenerating the image."""
    icon_path = ICONS_DIR / f"{icon_id}.png"
    if not icon_path.exists():
        raise HTTPException(status_code=404, detail="Icon not found")

    prompts = _load_prompts()
    meta = prompts.get(icon_id, {})
    if isinstance(meta, str):
        meta = {"prompt": meta, "size": "small"}

    if data.prompt is not None:
        meta["prompt"] = data.prompt
    if data.size is not None and data.size in ICON_SIZES:
        meta["size"] = data.size

    prompts[icon_id] = meta
    _save_prompts(prompts)
    compositor.clear_icon_cache()

    size_name = meta.get("size", "small")
    return IconResponse(
        id=icon_id,
        prompt=meta.get("prompt", ""),
        size=size_name,
        size_px=ICON_SIZES.get(size_name, 96),
        has_image=True,
    )


@router.delete("/{icon_id}", status_code=204)
def delete_icon(icon_id: str):
    """Delete an icon file and its saved prompt."""
    icon_path = ICONS_DIR / f"{icon_id}.png"
    if not icon_path.exists():
        raise HTTPException(status_code=404, detail="Icon not found")
    icon_path.unlink()

    prompts = _load_prompts()
    prompts.pop(icon_id, None)
    _save_prompts(prompts)


@router.post("/fix-transparency", status_code=200)
def fix_all_icon_transparency():
    """Remove white backgrounds from all existing icon PNGs."""
    fixed = []
    for png in ICONS_DIR.glob("*.png"):
        img = Image.open(str(png))
        if img.mode != "RGBA" or _is_fully_opaque(img):
            img = _remove_white_background(img)
            img.save(str(png))
            fixed.append(png.stem)
    compositor.clear_icon_cache()
    return {"fixed": fixed, "count": len(fixed)}


def _is_fully_opaque(img: Image.Image) -> bool:
    """Check if an RGBA image has any transparency at all."""
    if img.mode != "RGBA":
        return True
    alpha = np.array(img)[:, :, 3]
    return bool(np.all(alpha == 255))
