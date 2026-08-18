"""
Central model configuration for Cardmaker-App.

To switch models, change the values here — no need to touch any other files.
"""

# Image generation model (GGUF format, loaded via ComfyUI UnetLoaderGGUF)
FLUX_MODEL_NAME = "flux1-schnell-Q8_0.gguf"

# Text encoders (DualCLIPLoader)
CLIP_L = "clip_l.safetensors"
CLIP_T5 = "t5xxl_fp16.safetensors"

# Variational autoencoder
VAE = "ae.safetensors"
