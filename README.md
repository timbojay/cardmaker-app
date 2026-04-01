# CardMaker App

AI-powered playing card generator for the **Space Junk** card game. Runs entirely on local hardware (24GB M4 MacBook Pro) using ComfyUI + FLUX.1-schnell.

## Architecture

```
ComfyUI (image generation)
    └── FLUX.1-schnell model (quantized, ~12GB)
    └── Custom workflow: generates full card art at print resolution
    └── Post-processing: composites text/number boxes at fixed positions

Scripts (card pipeline)
    └── card-data/*.json — card definitions (name, stats, flavor text)
    └── templates/ — card layout templates (box positions, fonts)
    └── output/print-ready/ — final 825x1125px 300DPI PNGs
```

## Card Specs (Poker Size)

- **Card size:** 2.5" x 3.5" (63.5mm x 88.9mm)
- **With bleed:** 2.75" x 3.75" (825 x 1125 px @ 300 DPI)
- **Safe area:** 2.25" x 3.25" (675 x 975 px @ 300 DPI)
- **Color space:** CMYK for print, RGB for preview
- **Format:** PNG (print-ready), JPEG (previews)

## Setup

### 1. Install ComfyUI

```bash
cd /Users/timothyjordan/Git
git clone https://github.com/comfyanonymous/ComfyUI.git
cd ComfyUI
pip install -r requirements.txt
```

### 2. Download FLUX.1-schnell (quantized)

```bash
# Using Hugging Face CLI
pip install huggingface_hub
huggingface-cli download black-forest-labs/FLUX.1-schnell \
    --local-dir ComfyUI/models/unet/
```

Or download the Q8 GGUF quantized version (~12GB) for better VRAM fit:
```bash
huggingface-cli download city96/FLUX.1-schnell-gguf \
    flux1-schnell-Q8_0.gguf \
    --local-dir ComfyUI/models/unet/
```

### 3. Download required supporting models

```bash
# CLIP text encoders (needed for FLUX)
huggingface-cli download comfyanonymous/flux_text_encoders \
    clip_l.safetensors t5xxl_fp16.safetensors \
    --local-dir ComfyUI/models/clip/

# VAE
huggingface-cli download black-forest-labs/FLUX.1-schnell \
    ae.safetensors \
    --local-dir ComfyUI/models/vae/
```

### 4. Install CardMaker dependencies

```bash
cd /Users/timothyjordan/Git/cardmaker-app
pip install -r requirements.txt
```

### 5. Run

```bash
# Start ComfyUI
cd /Users/timothyjordan/Git/ComfyUI
python main.py

# In another terminal, generate cards
cd /Users/timothyjordan/Git/cardmaker-app
python scripts/generate_cards.py
```

## Directory Structure

```
cardmaker-app/
├── card-data/          # Card definitions (JSON)
├── templates/          # Card layout templates
├── workflows/          # ComfyUI workflow files (.json)
├── scripts/            # Generation and post-processing scripts
├── assets/
│   ├── borders/        # Card border/frame images
│   └── icons/          # Game icons (suits, symbols)
├── output/
│   ├── print-ready/    # Final 300DPI print files
│   └── previews/       # Low-res preview images
└── requirements.txt
```

## License

Private project.
