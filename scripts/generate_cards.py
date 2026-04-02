#!/usr/bin/env python3
"""
CardMaker — Space Junk card generator.

New layout:
  ┌───────────────────────────┐
  │ BORDER                    │
  │ ┌───────────────────────┐ │
  │ │ TITLE BAR (white)     │ │
  │ ├───────────────────────┤ │
  │ │ BENEFITS STRIP (white)│ │
  │ │ 🧭x2  🏆x3           │ │
  │ ├───────────────────────┤ │
  │ │                       │ │
  │ │   CARD ART (cartoon)  │ │
  │ │                       │ │
  │ ├───────────────────────┤ │
  │ │ DESCRIPTION TEXT      │ │
  │ ├───────────────────────┤ │
  │ │ COSTS STRIP           │ │
  │ │ 💰x2  -🏆x1          │ │
  │ └───────────────────────┘ │
  └───────────────────────────┘
"""

import io
import json
import sys
import time
import uuid
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
CARD_DATA = PROJECT_ROOT / "card-data" / "space_junk_cards.json"
OUTPUT_DIR = PROJECT_ROOT / "output" / "print-ready"
PREVIEW_DIR = PROJECT_ROOT / "output" / "previews"
BORDERS_DIR = PROJECT_ROOT / "assets" / "borders"
ICONS_DIR = PROJECT_ROOT / "assets" / "icons"

COMFYUI_URL = "http://127.0.0.1:8188"

CARD_W = 825
CARD_H = 1125


def load_card_data():
    with open(CARD_DATA) as f:
        return json.load(f)


def get_font(size):
    for font_name in [
        "/System/Library/Fonts/SFCompact-Bold.otf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    ]:
        try:
            return ImageFont.truetype(font_name, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


def get_font_regular(size):
    for font_name in [
        "/System/Library/Fonts/SFCompact.otf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
    ]:
        try:
            return ImageFont.truetype(font_name, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


# Load icons (cached)
_icon_cache = {}


def load_icon(name, size=48):
    key = (name, size)
    if key not in _icon_cache:
        path = ICONS_DIR / f"{name}.png"
        if path.exists():
            img = Image.open(str(path)).convert("RGBA")
            img = img.resize((size, size), Image.LANCZOS)
            _icon_cache[key] = img
        else:
            # Fallback: colored circle with letter
            img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            colors = {
                "navigation": (50, 120, 220),
                "fame": (220, 180, 30),
                "bajillion": (255, 200, 50),
                "fame_penalty": (200, 40, 40),
            }
            color = colors.get(name, (150, 150, 150))
            draw.ellipse([2, 2, size - 2, size - 2], fill=(*color, 230))
            font = get_font(size // 2)
            letter = name[0].upper()
            bbox = draw.textbbox((0, 0), letter, font=font)
            lw, lh = bbox[2] - bbox[0], bbox[3] - bbox[1]
            draw.text(((size - lw) // 2, (size - lh) // 2 - 2), letter, fill="white", font=font)
            _icon_cache[key] = img
    return _icon_cache[key]


def draw_icon_row(canvas, icons_dict, x_start, y, area_width, icon_size, label_font_size):
    """Draw a row of icons with multiplier labels. Returns nothing, draws in place."""
    draw = ImageDraw.Draw(canvas)
    font = get_font(label_font_size)

    # Calculate total width needed
    items = [(k, v) for k, v in icons_dict.items() if v > 0]
    if not items:
        return

    # Each item: icon + "x3" label + gap
    item_widths = []
    for name, count in items:
        label = f"x{count}"
        bbox = draw.textbbox((0, 0), label, font=font)
        label_w = bbox[2] - bbox[0]
        item_widths.append(icon_size + 4 + label_w)

    gap = 25
    total_w = sum(item_widths) + gap * (len(items) - 1)
    x = x_start + (area_width - total_w) // 2

    for i, (name, count) in enumerate(items):
        icon = load_icon(name, icon_size)
        canvas.paste(icon, (x, y + (icon_size - icon_size) // 2), icon)
        x += icon_size + 4

        label = f"x{count}"
        bbox = draw.textbbox((0, 0), label, font=font)
        label_h = bbox[3] - bbox[1]
        draw.text((x, y + (icon_size - label_h) // 2 - 2), label, fill=(50, 50, 50), font=font)
        x += bbox[2] - bbox[0] + gap


def word_wrap(draw, text, font, max_width):
    """Wrap text to fit within max_width."""
    words = text.split()
    lines, current = [], ""
    for w in words:
        test = f"{current} {w}".strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = w
    if current:
        lines.append(current)
    return lines


def composite_card(art_image, card, layout):
    """Build the full card with all zones."""
    margin = layout["inner_margin"]
    inner_left = margin
    inner_right = CARD_W - margin
    inner_width = inner_right - inner_left

    # Start with a dark background
    canvas = Image.new("RGBA", (CARD_W, CARD_H), (30, 30, 40, 255))
    draw = ImageDraw.Draw(canvas)

    icon_size = layout["icon_size"]
    cost_icon_size = layout.get("cost_icon_size", icon_size)

    # --- HEADER (title + benefits in one white block) ---
    hdr_y = layout["header"]["y"]
    hdr_h = layout["header"]["height"]
    draw.rounded_rectangle(
        [inner_left, hdr_y, inner_right, hdr_y + hdr_h],
        radius=12, fill=(255, 255, 255, 245),
    )

    # Title text — top portion of header
    font_title = get_font(layout["title_font_size"])
    bbox = draw.textbbox((0, 0), card["title"], font=font_title)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = inner_left + (inner_width - tw) // 2
    ty = hdr_y + 10
    draw.text((tx, ty), card["title"], fill=(30, 30, 40), font=font_title)

    # Thin separator line
    sep_y = hdr_y + 10 + th + 8
    draw.line([inner_left + 20, sep_y, inner_right - 20, sep_y], fill=(200, 200, 210), width=1)

    # Benefits icons — bottom portion of header
    benefits = card.get("benefits", {})
    icon_row_y = sep_y + 6
    draw_icon_row(canvas, benefits, inner_left, icon_row_y, inner_width, icon_size, layout["label_font_size"])

    # --- CARD ART ---
    art_y = layout["art_area"]["y"]
    art_h = layout["art_area"]["height"]
    art_crop = art_image.resize((inner_width, art_h), Image.LANCZOS)
    canvas.paste(art_crop.convert("RGBA"), (inner_left, art_y))

    # --- DESCRIPTION (white box, black text) ---
    desc_y = layout["description"]["y"]
    desc_h = layout["description"]["height"]
    draw.rounded_rectangle(
        [inner_left, desc_y, inner_right, desc_y + desc_h],
        radius=12, fill=(255, 255, 255, 240),
    )
    font_desc = get_font_regular(layout["desc_font_size"])
    desc_text = card.get("description", card.get("flavor_text", ""))
    lines = word_wrap(draw, desc_text, font_desc, inner_width - 30)

    # Vertically center the text block
    total_text_h = sum(
        draw.textbbox((0, 0), line, font=font_desc)[3] - draw.textbbox((0, 0), line, font=font_desc)[1] + 4
        for line in lines
    ) - 4
    line_y = desc_y + (desc_h - total_text_h) // 2
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font_desc)
        lw = bbox[2] - bbox[0]
        lh = bbox[3] - bbox[1]
        lx = inner_left + (inner_width - lw) // 2
        draw.text((lx, line_y), line, fill=(40, 40, 50), font=font_desc)
        line_y += lh + 4

    # --- COSTS STRIP (white, at very bottom) ---
    cost_y = layout["costs_strip"]["y"]
    cost_h = layout["costs_strip"]["height"]
    draw.rounded_rectangle(
        [inner_left, cost_y, inner_right, cost_y + cost_h],
        radius=12, fill=(255, 255, 255, 240),
    )

    # "COST" label on left
    font_cost_label = get_font(16)
    draw.text((inner_left + 12, cost_y + (cost_h - 16) // 2), "COST", fill=(160, 100, 100), font=font_cost_label)

    # Cost icons — centered, filling the strip height
    costs = card.get("costs", {})
    icon_pad = (cost_h - cost_icon_size) // 2
    draw_icon_row(canvas, costs, inner_left + 70, cost_y + icon_pad, inner_width - 70, cost_icon_size, layout["label_font_size"])

    return canvas


def build_prompt(card, specs):
    """Build a ComfyUI API prompt for a single card."""
    return {
        "3": {
            "class_type": "KSampler",
            "inputs": {
                "seed": hash(card["id"]) % (2**32),
                "steps": 4,
                "cfg": 1.0,
                "sampler_name": "euler",
                "scheduler": "simple",
                "denoise": 1.0,
                "model": ["4", 0],
                "positive": ["6", 0],
                "negative": ["7", 0],
                "latent_image": ["5", 0],
            },
        },
        "4": {
            "class_type": "UnetLoaderGGUF",
            "inputs": {
                "unet_name": "flux1-schnell-Q8_0.gguf",
            },
        },
        "5": {
            "class_type": "EmptyLatentImage",
            "inputs": {
                "width": specs["width_px"],
                "height": specs["height_px"],
                "batch_size": 1,
            },
        },
        "6": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": card["art_prompt"],
                "clip": ["8", 0],
            },
        },
        "7": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": "text, watermark, logo, blurry, low quality, border, frame",
                "clip": ["8", 0],
            },
        },
        "8": {
            "class_type": "DualCLIPLoader",
            "inputs": {
                "clip_name1": "clip_l.safetensors",
                "clip_name2": "t5xxl_fp16.safetensors",
                "type": "flux",
            },
        },
        "9": {
            "class_type": "VAEDecode",
            "inputs": {
                "samples": ["3", 0],
                "vae": ["10", 0],
            },
        },
        "10": {
            "class_type": "VAELoader",
            "inputs": {
                "vae_name": "ae.safetensors",
            },
        },
        "11": {
            "class_type": "SaveImage",
            "inputs": {
                "filename_prefix": card["id"],
                "images": ["9", 0],
            },
        },
    }


def queue_prompt(prompt):
    payload = {"prompt": prompt, "client_id": str(uuid.uuid4())}
    resp = requests.post(f"{COMFYUI_URL}/prompt", json=payload)
    if resp.status_code != 200:
        print(f"  ERROR {resp.status_code}: {resp.text}")
        resp.raise_for_status()
    return resp.json()["prompt_id"]


def wait_for_completion(prompt_id, timeout=300):
    start = time.time()
    while time.time() - start < timeout:
        resp = requests.get(f"{COMFYUI_URL}/history/{prompt_id}")
        data = resp.json()
        if prompt_id in data:
            return data[prompt_id]
        time.sleep(2)
    raise TimeoutError(f"Prompt {prompt_id} did not complete within {timeout}s")


def get_generated_image(history):
    outputs = history["outputs"]
    for node_id, output in outputs.items():
        if "images" in output:
            img_info = output["images"][0]
            resp = requests.get(
                f"{COMFYUI_URL}/view",
                params={
                    "filename": img_info["filename"],
                    "subfolder": img_info.get("subfolder", ""),
                    "type": "output",
                },
                stream=True,
            )
            resp.raise_for_status()
            image_data = io.BytesIO(resp.content)
            image_data.seek(0)
            return Image.open(image_data)
    raise ValueError("No image found in ComfyUI output")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Generate Space Junk cards")
    parser.add_argument("--force", action="store_true", help="Regenerate cards even if they already exist")
    parser.add_argument("--card", type=str, help="Generate a specific card by ID (e.g. sj-001)")
    args = parser.parse_args()

    data = load_card_data()
    specs = data["card_specs"]
    layout = data["layout"]
    cards = data["cards"]

    if args.card:
        cards = [c for c in cards if c["id"] == args.card]
        if not cards:
            print(f"ERROR: Card '{args.card}' not found.")
            sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)

    # Check ComfyUI is running
    try:
        requests.get(f"{COMFYUI_URL}/system_stats", timeout=5)
    except requests.ConnectionError:
        print("ERROR: ComfyUI is not running. Start it with:")
        print("  cd /Users/timothyjordan/Git/ComfyUI && python main.py")
        sys.exit(1)

    generated = 0
    skipped = 0
    for card in cards:
        print_path = OUTPUT_DIR / f"{card['id']}_print.png"

        if print_path.exists() and not args.force:
            print(f"Skipping: {card['title']} ({card['id']}) — already exists. Use --force to regenerate.")
            skipped += 1
            continue

        print(f"Generating: {card['title']} ({card['id']})...")

        # Build and queue the prompt
        prompt = build_prompt(card, specs)
        prompt_id = queue_prompt(prompt)
        print(f"  Queued (prompt_id: {prompt_id}), waiting...")

        # Wait and download
        history = wait_for_completion(prompt_id)
        art_image = get_generated_image(history)

        # Composite the full card layout
        final = composite_card(art_image, card, layout)

        # Apply card type border if it exists
        card_type = card.get("type", "")
        border_path = BORDERS_DIR / f"{card_type}_border.png"
        if border_path.exists():
            border = Image.open(str(border_path)).convert("RGBA")
            border = border.resize((CARD_W, CARD_H), Image.LANCZOS)
            final = Image.alpha_composite(final.convert("RGBA"), border)
            print(f"  Applied {card_type} border")

        # Save print-ready (PNG)
        final_rgb = final.convert("RGB")
        final_rgb.save(str(print_path), dpi=(300, 300))
        print(f"  Saved: {print_path}")

        # Save preview (smaller JPEG)
        preview = final_rgb.resize((413, 563), Image.LANCZOS)
        preview_path = PREVIEW_DIR / f"{card['id']}_preview.jpg"
        preview.save(str(preview_path), quality=85)
        print(f"  Preview: {preview_path}")
        generated += 1

    print(f"\nDone! Generated {generated}, skipped {skipped} (already exist).")


if __name__ == "__main__":
    main()
