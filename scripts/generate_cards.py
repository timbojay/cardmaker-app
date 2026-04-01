#!/usr/bin/env python3
"""
CardMaker — Space Junk card generator.

Sends prompts to ComfyUI API, then composites text/stat boxes
onto the generated art to produce print-ready card images.
"""

import json
import os
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
WORKFLOW_DIR = PROJECT_ROOT / "workflows"

COMFYUI_URL = "http://127.0.0.1:8188"


def load_card_data():
    with open(CARD_DATA) as f:
        return json.load(f)


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
            "class_type": "UNETLoader",
            "inputs": {
                "unet_name": "flux1-schnell-Q8_0.gguf",
                "weight_dtype": "default",
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
    """Send a prompt to ComfyUI and return the prompt ID."""
    payload = {"prompt": prompt, "client_id": str(uuid.uuid4())}
    resp = requests.post(f"{COMFYUI_URL}/prompt", json=payload)
    resp.raise_for_status()
    return resp.json()["prompt_id"]


def wait_for_completion(prompt_id, timeout=300):
    """Poll ComfyUI until the prompt finishes."""
    start = time.time()
    while time.time() - start < timeout:
        resp = requests.get(f"{COMFYUI_URL}/history/{prompt_id}")
        data = resp.json()
        if prompt_id in data:
            return data[prompt_id]
        time.sleep(2)
    raise TimeoutError(f"Prompt {prompt_id} did not complete within {timeout}s")


def get_generated_image(history):
    """Extract the image filename from ComfyUI history and download it."""
    outputs = history["outputs"]
    for node_id, output in outputs.items():
        if "images" in output:
            img_info = output["images"][0]
            filename = img_info["filename"]
            subfolder = img_info.get("subfolder", "")
            resp = requests.get(
                f"{COMFYUI_URL}/view",
                params={"filename": filename, "subfolder": subfolder, "type": "output"},
            )
            resp.raise_for_status()
            return Image.open(resp.raw if hasattr(resp, "raw") else __import__("io").BytesIO(resp.content))
    raise ValueError("No image found in ComfyUI output")


def composite_card(base_image, card, text_boxes):
    """Overlay text and stat boxes onto the generated art."""
    img = base_image.copy()
    draw = ImageDraw.Draw(img)

    # Try to use a good system font, fall back to default
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

    # Draw semi-transparent boxes behind text
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)

    # Title bar
    tb = text_boxes["title"]
    overlay_draw.rounded_rectangle(
        [tb["x"] - 10, tb["y"] - 5, tb["x"] + tb["width"] + 10, tb["y"] + tb["height"] + 5],
        radius=8, fill=(0, 0, 0, 160),
    )

    # Stat circles
    for key in ["stats_top_left", "stats_top_right"]:
        sb = text_boxes[key]
        cx, cy = sb["x"] + sb["width"] // 2, sb["y"] + sb["height"] // 2
        r = 35
        overlay_draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(0, 0, 0, 180))

    # Flavor text bar
    fb = text_boxes["flavor_text"]
    overlay_draw.rounded_rectangle(
        [fb["x"] - 10, fb["y"] - 5, fb["x"] + fb["width"] + 10, fb["y"] + fb["height"] + 15],
        radius=8, fill=(0, 0, 0, 160),
    )

    img = Image.alpha_composite(img.convert("RGBA"), overlay)
    draw = ImageDraw.Draw(img)

    # Title
    font_title = get_font(tb["font_size"])
    bbox = draw.textbbox((0, 0), card["title"], font=font_title)
    tw = bbox[2] - bbox[0]
    tx = tb["x"] + (tb["width"] - tw) // 2
    draw.text((tx, tb["y"] + 10), card["title"], fill=tb["color"], font=font_title)

    # Stats
    for key, stat_key in [("stats_top_left", "top_left"), ("stats_top_right", "top_right")]:
        sb = text_boxes[key]
        font_stat = get_font(sb["font_size"])
        val = card["stats"][stat_key]
        bbox = draw.textbbox((0, 0), val, font=font_stat)
        sw, sh = bbox[2] - bbox[0], bbox[3] - bbox[1]
        sx = sb["x"] + (sb["width"] - sw) // 2
        sy = sb["y"] + (sb["height"] - sh) // 2
        draw.text((sx, sy), val, fill=sb["color"], font=font_stat)

    # Flavor text
    font_flavor = get_font(fb["font_size"])
    # Simple word wrap
    words = card["flavor_text"].split()
    lines, current = [], ""
    for w in words:
        test = f"{current} {w}".strip()
        bbox = draw.textbbox((0, 0), test, font=font_flavor)
        if bbox[2] - bbox[0] <= fb["width"]:
            current = test
        else:
            lines.append(current)
            current = w
    lines.append(current)

    y_offset = fb["y"] + 10
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font_flavor)
        lw = bbox[2] - bbox[0]
        lx = fb["x"] + (fb["width"] - lw) // 2
        draw.text((lx, y_offset), line, fill=fb["color"], font=font_flavor)
        y_offset += bbox[3] - bbox[1] + 4

    return img


def main():
    data = load_card_data()
    specs = data["card_specs"]
    text_boxes = data["text_boxes"]
    cards = data["cards"]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)

    # Check ComfyUI is running
    try:
        requests.get(f"{COMFYUI_URL}/system_stats", timeout=5)
    except requests.ConnectionError:
        print("ERROR: ComfyUI is not running. Start it with:")
        print("  cd /Users/timothyjordan/Git/ComfyUI && python main.py")
        sys.exit(1)

    for card in cards:
        print(f"Generating: {card['title']} ({card['id']})...")

        # Build and queue the prompt
        prompt = build_prompt(card, specs)
        prompt_id = queue_prompt(prompt)
        print(f"  Queued (prompt_id: {prompt_id}), waiting...")

        # Wait and download
        history = wait_for_completion(prompt_id)
        base_image = get_generated_image(history)
        base_image = base_image.resize((specs["width_px"], specs["height_px"]), Image.LANCZOS)

        # Composite text overlays
        final = composite_card(base_image, card, text_boxes)

        # Save print-ready (PNG)
        print_path = OUTPUT_DIR / f"{card['id']}_print.png"
        final_rgb = final.convert("RGB")
        final_rgb.save(str(print_path), dpi=(300, 300))
        print(f"  Saved: {print_path}")

        # Save preview (smaller JPEG)
        preview = final_rgb.resize((413, 563), Image.LANCZOS)
        preview_path = PREVIEW_DIR / f"{card['id']}_preview.jpg"
        preview.save(str(preview_path), quality=85)
        print(f"  Preview: {preview_path}")

    print(f"\nDone! Generated {len(cards)} cards.")


if __name__ == "__main__":
    main()
