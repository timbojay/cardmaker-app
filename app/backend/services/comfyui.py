"""
ComfyUI API client for image generation.

Extracted from scripts/generate_cards.py and scripts/generate_assets.py.
"""

import io
import sys
import time
import uuid
from pathlib import Path

import requests
from PIL import Image

# Add project root to path so config.py is importable
sys.path.insert(0, str(Path(__file__).parents[3]))
from config import CLIP_L, CLIP_T5, FLUX_MODEL_NAME, VAE

COMFYUI_URL = "http://127.0.0.1:8188"


def get_status() -> dict:
    """Check if ComfyUI is reachable and return system stats."""
    try:
        resp = requests.get(f"{COMFYUI_URL}/system_stats", timeout=5)
        resp.raise_for_status()
        return {"status": "connected", "details": resp.json()}
    except requests.ConnectionError:
        return {"status": "disconnected", "error": "ComfyUI is not running"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def build_card_art_prompt(art_prompt: str, width: int, height: int, seed: int) -> dict:
    """Build a ComfyUI API prompt for card art generation."""
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
                "unet_name": FLUX_MODEL_NAME,
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
                "text": "text, watermark, logo, blurry, low quality, border, frame",
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
            "inputs": {
                "samples": ["3", 0],
                "vae": ["10", 0],
            },
        },
        "10": {
            "class_type": "VAELoader",
            "inputs": {
                "vae_name": VAE,
            },
        },
        "11": {
            "class_type": "SaveImage",
            "inputs": {
                "filename_prefix": "cardmaker",
                "images": ["9", 0],
            },
        },
    }


def build_border_prompt(art_prompt: str, width: int, height: int, seed: int) -> dict:
    """Build a ComfyUI API prompt for border generation."""
    prompt = build_card_art_prompt(art_prompt, width, height, seed)
    # Use the border-specific negative prompt
    prompt["7"]["inputs"]["text"] = "text, words, letters, watermark, logo, blurry, low quality, ugly"
    return prompt


def queue_prompt(prompt: dict) -> str:
    """Submit a prompt to ComfyUI and return the prompt_id."""
    payload = {"prompt": prompt, "client_id": str(uuid.uuid4())}
    resp = requests.post(f"{COMFYUI_URL}/prompt", json=payload)
    if resp.status_code != 200:
        raise RuntimeError(f"ComfyUI error {resp.status_code}: {resp.text}")
    return resp.json()["prompt_id"]


def wait_for_completion(prompt_id: str, timeout: int = 300) -> dict:
    """Poll ComfyUI until the prompt completes or times out."""
    start = time.time()
    while time.time() - start < timeout:
        resp = requests.get(f"{COMFYUI_URL}/history/{prompt_id}")
        data = resp.json()
        if prompt_id in data:
            return data[prompt_id]
        time.sleep(2)
    raise TimeoutError(f"Prompt {prompt_id} did not complete within {timeout}s")


def get_generated_image(history: dict) -> Image.Image:
    """Download the generated image from ComfyUI output."""
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


def generate_image(art_prompt: str, width: int, height: int, seed: int = 42) -> Image.Image:
    """Full pipeline: build prompt, queue, wait, return PIL Image."""
    prompt = build_card_art_prompt(art_prompt, width, height, seed)
    prompt_id = queue_prompt(prompt)
    history = wait_for_completion(prompt_id)
    return get_generated_image(history)
