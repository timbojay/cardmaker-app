# CardMaker CLI Scripts

These Python scripts are batch/utility generators that run outside the FastAPI backend. They are useful for bulk generation and one-off asset creation.

## Requirements

All scripts use the project root Python environment:

```bash
cd "/Users/timothyjordan/projects/Programming Projects/cardmaker-app"
pip install -r requirements.txt
```

## Scripts

### `generate_cards.py`

Batch-generates print-ready Space Junk cards using ComfyUI.

```bash
python scripts/generate_cards.py
```

- Reads `card-data/space_junk_cards.json`
- Generates AI art via ComfyUI + FLUX.1-schnell
- Composites title, benefits, costs, description, border, and +/- indicators
- Writes:
  - `output/print-ready/{id}_print.png`
  - `output/previews/{id}_preview.jpg`
  - `output/raw-art/{id}_art.png`

> ComfyUI must be running on `http://127.0.0.1:8188`.

### `generate_assets.py`

Generates card borders and deck backs from the prompts in `card-data/decks.json`.

```bash
python scripts/generate_assets.py
```

- Generates border overlays for each card type into `assets/borders/`
- Generates deck backs into `assets/backs/`
- Uses `services/compositor.py` and `services/comfyui.py`

### `generate_icons.py`

Generates individual game icons (benefits, costs, stats).

```bash
python scripts/generate_icons.py
```

- Reads/writes icon prompts and PNGs in `assets/icons/`
- Outputs transparent PNG icons at 256x256 px
- Saves metadata to `assets/icons/prompts.json`

## Notes

- The FastAPI backend does not depend on these scripts; it has equivalent functionality built in.
- These scripts duplicate some backend logic for standalone batch operation.
- When the backend regenerates assets or icons, it clears the compositor cache automatically.
