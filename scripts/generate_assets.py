#!/usr/bin/env python3
"""
Generate deck backs and card type borders for Space Junk.

Generates:
  - Deck back images (one per deck)
  - Card border overlay images (one per card type)
"""

import io
import json
import sys
import time
import uuid
from pathlib import Path

import requests
from PIL import Image, ImageDraw

PROJECT_ROOT = Path(__file__).parent.parent
DECKS_DATA = PROJECT_ROOT / "card-data" / "decks.json"
BACKS_DIR = PROJECT_ROOT / "assets" / "backs"
BORDERS_DIR = PROJECT_ROOT / "assets" / "borders"

COMFYUI_URL = "http://127.0.0.1:8188"

CARD_W = 825
CARD_H = 1125


def load_decks_data():
    with open(DECKS_DATA) as f:
        return json.load(f)


def build_prompt(art_prompt, width, height, seed=42):
    """Build a ComfyUI API prompt."""
    return {
        "3": {
            "class_type": "KSampler",
            "inputs": {
                "seed": seed,
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
                "width": width,
                "height": height,
                "batch_size": 1,
            },
        },
        "6": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": art_prompt,
                "clip": ["8", 0],
            },
        },
        "7": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": "text, words, letters, watermark, logo, blurry, low quality, ugly",
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
                "filename_prefix": "asset",
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
            filename = img_info["filename"]
            subfolder = img_info.get("subfolder", "")
            resp = requests.get(
                f"{COMFYUI_URL}/view",
                params={"filename": filename, "subfolder": subfolder, "type": "output"},
                stream=True,
            )
            resp.raise_for_status()
            image_data = io.BytesIO(resp.content)
            image_data.seek(0)
            return Image.open(image_data)
    raise ValueError("No image found in ComfyUI output")


def generate_image(art_prompt, width, height, seed=42):
    """Generate a single image via ComfyUI."""
    prompt = build_prompt(art_prompt, width, height, seed)
    prompt_id = queue_prompt(prompt)
    print(f"  Queued (prompt_id: {prompt_id}), waiting...")
    history = wait_for_completion(prompt_id)
    return get_generated_image(history)


def create_border_overlay(base_image, border_color, border_accent, border_width=55):
    """
    Create a border overlay from a generated border image.
    Cuts out the center to create a frame effect.
    """
    from PIL import ImageChops

    img = base_image.resize((CARD_W, CARD_H), Image.LANCZOS).convert("RGBA")

    # Create a mask that makes the center transparent
    mask = Image.new("L", (CARD_W, CARD_H), 255)
    mask_draw = ImageDraw.Draw(mask)

    # Cut out center rectangle (leaving border visible)
    inner_x = border_width + 5
    inner_y = border_width + 5
    mask_draw.rounded_rectangle(
        [inner_x, inner_y, CARD_W - inner_x, CARD_H - inner_y],
        radius=15,
        fill=0,
    )

    # Round the outer corners
    outer_mask = Image.new("L", (CARD_W, CARD_H), 0)
    outer_draw = ImageDraw.Draw(outer_mask)
    outer_draw.rounded_rectangle(
        [0, 0, CARD_W, CARD_H],
        radius=25,
        fill=255,
    )

    # Combine masks: border frame = outer AND NOT inner
    final_mask = ImageChops.darker(mask, outer_mask)
    img.putalpha(final_mask)

    # Add a thin inner edge glow
    overlay = Image.new("RGBA", (CARD_W, CARD_H), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rounded_rectangle(
        [inner_x - 2, inner_y - 2, CARD_W - inner_x + 2, CARD_H - inner_y + 2],
        radius=15,
        outline=(*border_accent, 180),
        width=2,
    )

    img = Image.alpha_composite(img, overlay)
    return img


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Generate deck backs and card borders")
    parser.add_argument("--backs-only", action="store_true", help="Only generate deck backs")
    parser.add_argument("--borders-only", action="store_true", help="Only generate borders")
    parser.add_argument("--force", action="store_true", help="Regenerate existing assets")
    args = parser.parse_args()

    data = load_decks_data()

    # Check ComfyUI
    try:
        requests.get(f"{COMFYUI_URL}/system_stats", timeout=5)
    except requests.ConnectionError:
        print("ERROR: ComfyUI is not running.")
        sys.exit(1)

    BACKS_DIR.mkdir(parents=True, exist_ok=True)
    BORDERS_DIR.mkdir(parents=True, exist_ok=True)

    do_backs = not args.borders_only
    do_borders = not args.backs_only

    # Generate deck backs
    if do_backs:
        print("=== Generating Deck Backs ===\n")
        for deck in data["decks"]:
            out_path = BACKS_DIR / f"{deck['id']}_back.png"
            if out_path.exists() and not args.force:
                print(f"Skipping: {deck['name']} back — already exists")
                continue

            print(f"Generating: {deck['name']} back...")
            img = generate_image(deck["back_prompt"], CARD_W, CARD_H, seed=hash(deck["id"]) % (2**32))
            img = img.resize((CARD_W, CARD_H), Image.LANCZOS)

            # Add rounded corners
            rounded = img.convert("RGBA")
            mask = Image.new("L", (CARD_W, CARD_H), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.rounded_rectangle([0, 0, CARD_W, CARD_H], radius=25, fill=255)
            rounded.putalpha(mask)

            rounded.save(str(out_path), dpi=(300, 300))
            print(f"  Saved: {out_path}")

    # Generate card type borders
    if do_borders:
        print("\n=== Generating Card Type Borders ===\n")
        for ctype in data["card_types"]:
            out_path = BORDERS_DIR / f"{ctype['id']}_border.png"
            if out_path.exists() and not args.force:
                print(f"Skipping: {ctype['name']} border — already exists")
                continue

            print(f"Generating: {ctype['name']} border...")
            img = generate_image(ctype["border_prompt"], CARD_W, CARD_H, seed=hash(ctype["id"]) % (2**32))

            border = create_border_overlay(
                img,
                border_color=tuple(ctype["border_color"]),
                border_accent=tuple(ctype["border_accent"]),
            )
            border.save(str(out_path), dpi=(300, 300))
            print(f"  Saved: {out_path}")

    print("\nDone!")


if __name__ == "__main__":
    main()
