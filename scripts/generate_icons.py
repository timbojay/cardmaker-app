#!/usr/bin/env python3
"""
Generate card icons for Space Junk: compass, oscar, gold bar.
Uses ComfyUI to generate, then crops/cleans each icon.
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
ICONS_DIR = PROJECT_ROOT / "assets" / "icons"
COMFYUI_URL = "http://127.0.0.1:8188"

# Model config — single source of truth in config.py at the project root
sys.path.insert(0, str(PROJECT_ROOT))
from config import CLIP_L, CLIP_T5, FLUX_MODEL_NAME, VAE  # noqa: E402

ICONS = [
    {
        "id": "navigation",
        "prompt": "Single cartoon compass icon on a solid white background, bright blue and gold nautical compass with a spinning needle, fun cartoon game icon style, clean simple bold design, centered, no text, bright vivid colors, game UI icon, white background",
    },
    {
        "id": "fame",
        "prompt": "Single cartoon golden Oscar trophy statue icon on a solid white background, shiny gold award trophy with a star on top, fun cartoon game icon style, clean simple bold design, centered, no text, bright gold color, game UI icon, white background",
    },
    {
        "id": "bajillion",
        "prompt": "Single cartoon gold bar ingot icon on a solid white background, shiny golden brick with a dollar sign stamped on it, fun cartoon game icon style, clean simple bold design, centered, no text, bright gold color, game UI icon, white background",
    },
    {
        "id": "payload",
        "prompt": "Single cartoon wooden cargo crate box icon on a solid white background, brown shipping crate with a small rocket sticker on it, fun cartoon game icon style, clean simple bold design, centered, no text, bright colors, game UI icon, white background",
    },
    {
        "id": "capacity",
        "prompt": "Single cartoon muscular arm flexing bicep icon on a solid white background, strong buff arm with bulging muscles, fun cartoon game icon style, clean simple bold design, centered, no text, bright colors, game UI icon, white background",
    },
]


def build_prompt(art_prompt, seed=42):
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
            "inputs": {"unet_name": FLUX_MODEL_NAME},
        },
        "5": {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": 512, "height": 512, "batch_size": 1},
        },
        "6": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": art_prompt, "clip": ["8", 0]},
        },
        "7": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": "text, words, letters, multiple objects, busy background, watermark",
                "clip": ["8", 0],
            },
        },
        "8": {
            "class_type": "DualCLIPLoader",
            "inputs": {
                "clip_name1": CLIP_L,
                "clip_name2": CLIP_T5,
                "type": "flux",
            },
        },
        "9": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["3", 0], "vae": ["10", 0]},
        },
        "10": {
            "class_type": "VAELoader",
            "inputs": {"vae_name": VAE},
        },
        "11": {
            "class_type": "SaveImage",
            "inputs": {"filename_prefix": "icon", "images": ["9", 0]},
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
    raise TimeoutError(f"Timeout waiting for {prompt_id}")


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
    raise ValueError("No image found")


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    try:
        requests.get(f"{COMFYUI_URL}/system_stats", timeout=5)
    except requests.ConnectionError:
        print("ERROR: ComfyUI not running.")
        sys.exit(1)

    ICONS_DIR.mkdir(parents=True, exist_ok=True)

    for icon in ICONS:
        out_path = ICONS_DIR / f"{icon['id']}.png"
        if out_path.exists() and not args.force:
            print(f"Skipping: {icon['id']} — already exists")
            continue

        print(f"Generating: {icon['id']} icon...")
        prompt = build_prompt(icon["prompt"], seed=hash(icon["id"]) % (2**32))
        prompt_id = queue_prompt(prompt)
        print(f"  Queued ({prompt_id}), waiting...")
        history = wait_for_completion(prompt_id)
        img = get_generated_image(history)

        # Resize to usable icon size
        img = img.resize((128, 128), Image.LANCZOS)
        img.save(str(out_path))
        print(f"  Saved: {out_path}")

    print("\nDone!")


if __name__ == "__main__":
    main()
