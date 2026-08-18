"""
Card compositor — renders full card images from data + art.

Extracted from scripts/generate_cards.py and scripts/generate_assets.py.
Preserves the exact same rendering logic.
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent

ICONS_DIR = PROJECT_ROOT / "assets" / "icons"
BORDERS_DIR = PROJECT_ROOT / "assets" / "borders"
BACKGROUNDS_DIR = PROJECT_ROOT / "assets" / "backgrounds"

CARD_W = 825
CARD_H = 1125


# ---------- Fonts ----------

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


# ---------- Icons ----------

import json as _json

_icon_cache = {}
_icon_sizes_cache = None

ICON_SIZE_MAP = {"small": 96, "medium": 128, "large": 160}
DEFAULT_ICON_SIZE = 96

TEXT_SIZE_MAP = {"small": 0.75, "medium": 1.0, "large": 1.35}
DEFAULT_TITLE_SIZE = 38
DEFAULT_DESC_SIZE = 26


def _load_icon_sizes() -> dict[str, int]:
    """Load per-icon sizes from prompts.json."""
    global _icon_sizes_cache
    prompts_file = ICONS_DIR / "prompts.json"
    if prompts_file.exists():
        with open(prompts_file) as f:
            data = _json.load(f)
        sizes = {}
        for k, v in data.items():
            if isinstance(v, dict):
                size_name = v.get("size", "small")
            else:
                size_name = "small"
            sizes[k] = ICON_SIZE_MAP.get(size_name, DEFAULT_ICON_SIZE)
        _icon_sizes_cache = sizes
        return sizes
    return {}


def clear_icon_cache():
    """Clear cached icons so size changes take effect."""
    global _icon_cache, _icon_sizes_cache
    _icon_cache = {}
    _icon_sizes_cache = None


def get_icon_size(name: str) -> int:
    """Get the configured display size for an icon."""
    global _icon_sizes_cache
    if _icon_sizes_cache is None:
        _icon_sizes_cache = _load_icon_sizes()
    return _icon_sizes_cache.get(name, DEFAULT_ICON_SIZE)


def load_icon(name, size=None):
    if size is None:
        size = get_icon_size(name)
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
                "payload": (160, 100, 50),
                "capacity": (200, 60, 60),
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


def draw_icon_row(canvas, icons_dict, x_start, y, area_width, icon_size):
    """Draw a row of icons that auto-compresses to fit the available width.

    Strategy:
    - Build a flat list of "slots" to place, each with a name & size.
    - Lay them out left-to-right with a gap between different icon types
      and a (possibly compressed) step between same-type duplicates.
    - If the row is too wide, shrink same-type gaps first (gentle overlap),
      then shrink cross-type gaps, ensuring everything fits.
    """
    items = [(k, v) for k, v in icons_dict.items() if v > 0]
    if not items:
        return 0

    TYPE_GAP = 20       # ideal gap between different icon types
    SAME_GAP = 4        # ideal gap between same-type icons
    MIN_SAME_STEP = 0.35  # minimum step as fraction of icon size (overlap)
    MIN_TYPE_GAP = 6     # minimum gap between different types

    # Build groups: [{name, count, size}]
    groups = []
    for name, count in items:
        s = get_icon_size(name)
        groups.append({"name": name, "count": count, "size": s})

    # --- Calculate ideal total width ---
    def calc_total(grps, type_gap, same_steps):
        """Total width given per-group same-icon steps and a type gap."""
        w = 0
        for i, g in enumerate(grps):
            step = same_steps[i]
            # Group width = first icon full size + remaining icons at step
            w += g["size"] + max(0, g["count"] - 1) * step
            if i < len(grps) - 1:
                w += type_gap
        return w

    # Start with ideal steps (full icon + gap)
    same_steps = [g["size"] + SAME_GAP for g in groups]
    type_gap = TYPE_GAP

    ideal_w = calc_total(groups, type_gap, same_steps)

    if ideal_w > area_width:
        overflow = ideal_w - area_width

        # Phase 1: compress same-type spacing proportionally (not to minimum)
        # Calculate how much slack we can get from same-type compression
        total_slack = 0
        group_slack = []
        for i, g in enumerate(groups):
            if g["count"] > 1:
                min_step = max(int(g["size"] * MIN_SAME_STEP), 20)
                extras = g["count"] - 1
                slack = extras * (same_steps[i] - min_step)
                group_slack.append((i, extras, min_step, slack))
                total_slack += slack
            else:
                group_slack.append((i, 0, same_steps[i], 0))

        if total_slack > 0:
            ratio = min(1.0, overflow / total_slack)
            for i, extras, min_step, slack in group_slack:
                if extras > 0:
                    reduction = slack * ratio
                    same_steps[i] = max(min_step, int(same_steps[i] - reduction / extras))

        compressed_w = calc_total(groups, type_gap, same_steps)

        if compressed_w > area_width and len(groups) > 1:
            # Phase 2: also shrink the type gap
            overflow2 = compressed_w - area_width
            gap_slots = len(groups) - 1
            reduction_per = min(type_gap - MIN_TYPE_GAP, overflow2 // gap_slots)
            type_gap = type_gap - reduction_per

        # Phase 3: if still too wide (many single-count groups), spread evenly
        final_check = calc_total(groups, type_gap, same_steps)
        if final_check > area_width:
            # Distribute the remaining overflow across all steps
            total_icons = sum(g["count"] for g in groups)
            total_gaps = total_icons - 1
            if total_gaps > 0:
                excess = final_check - area_width
                per_gap_reduction = excess / total_gaps
                for i, g in enumerate(groups):
                    same_steps[i] = max(
                        max(int(g["size"] * MIN_SAME_STEP), 20),
                        int(same_steps[i] - per_gap_reduction)
                    )
                type_gap = max(MIN_TYPE_GAP, int(type_gap - per_gap_reduction))

    # --- Draw ---
    final_w = calc_total(groups, type_gap, same_steps)
    # Center if there's room, but never start before x_start
    spare = area_width - final_w
    x = x_start + max(0, spare // 2)
    if x < x_start:
        x = x_start
    max_h = 0

    for i, g in enumerate(groups):
        s = g["size"]
        step = same_steps[i]
        max_h = max(max_h, s)

        for j in range(g["count"]):
            icon = load_icon(g["name"], s)
            icon_y = y + (icon_size - s) // 2 if s < icon_size else y
            draw_x = int(x + j * step)
            canvas.paste(icon, (draw_x, icon_y), icon)

        # Advance past this group (first icon full + rest at step)
        x += s + max(0, g["count"] - 1) * step

        if i < len(groups) - 1:
            x += type_gap

    return max_h


# ---------- Text ----------

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


# ---------- Drawing helpers ----------

def draw_plus_minus_circle(draw, x, y, size, is_plus=True):
    """Draw a green + or red - circle with a white outline ring."""
    outline_w = max(size // 8, 4)
    # White outline ring (drawn first, slightly larger)
    draw.ellipse(
        [x - outline_w, y - outline_w, x + size + outline_w, y + size + outline_w],
        fill=(255, 255, 255, 245),
    )
    if is_plus:
        color = (40, 180, 60)
        draw.ellipse([x, y, x + size, y + size], fill=color)
        # Plus sign
        bar_w = size // 5
        cx, cy = x + size // 2, y + size // 2
        half = size // 3
        draw.rounded_rectangle([cx - half, cy - bar_w // 2, cx + half, cy + bar_w // 2], radius=2, fill="white")
        draw.rounded_rectangle([cx - bar_w // 2, cy - half, cx + bar_w // 2, cy + half], radius=2, fill="white")
    else:
        color = (210, 50, 50)
        draw.ellipse([x, y, x + size, y + size], fill=color)
        # Minus sign
        bar_w = size // 5
        cx, cy = x + size // 2, y + size // 2
        half = size // 3
        draw.rounded_rectangle([cx - half, cy - bar_w // 2, cx + half, cy + bar_w // 2], radius=2, fill="white")


# ---------- Card compositing ----------

def _max_icon_size_for_row(icons_dict):
    """Calculate the tallest icon size in a row of icons."""
    if not icons_dict:
        return DEFAULT_ICON_SIZE
    max_s = 0
    for name, count in icons_dict.items():
        if count > 0:
            max_s = max(max_s, get_icon_size(name))
    return max_s if max_s > 0 else DEFAULT_ICON_SIZE


def composite_card(art_image, card, layout):
    """Build the full card with all zones."""
    margin = layout["inner_margin"]
    inner_left = margin
    inner_right = CARD_W - margin
    inner_width = inner_right - inner_left

    benefits = card.get("benefits", {})
    costs = card.get("costs", {})

    # Calculate actual icon row heights based on the icons used
    benefit_row_h = _max_icon_size_for_row(benefits)
    cost_row_h = _max_icon_size_for_row(costs)

    # Plus/minus circles scale to match the tallest icon in their row
    benefit_pm_size = max(benefit_row_h - 10, 44)
    cost_pm_size = max(cost_row_h - 10, 44)

    # Start with a dark background
    canvas = Image.new("RGBA", (CARD_W, CARD_H), (30, 30, 40, 255))
    draw = ImageDraw.Draw(canvas)

    # --- Per-card text sizes (small/medium/large) with layout as base ---
    title_scale = TEXT_SIZE_MAP.get(card.get("title_size", "medium") or "medium", 1.0)
    desc_scale = TEXT_SIZE_MAP.get(card.get("desc_size", "medium") or "medium", 1.0)
    title_font_px = int(layout["title_font_size"] * title_scale)
    desc_font_px = int(layout["desc_font_size"] * desc_scale)

    # --- HEADER (title + green plus + benefits — dynamically sized) ---
    hdr_y = layout["header"]["y"]
    font_title = get_font(title_font_px)
    bbox = draw.textbbox((0, 0), card["title"], font=font_title)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]

    # Header height = title + separator + icon row + padding
    hdr_h = 8 + th + 6 + 8 + benefit_row_h + 10
    draw.rounded_rectangle(
        [inner_left, hdr_y, inner_right, hdr_y + hdr_h],
        radius=12, fill=(255, 255, 255, 245),
    )

    # Title text
    tx = inner_left + (inner_width - tw) // 2
    ty = hdr_y + 8
    draw.text((tx, ty), card["title"], fill=(30, 30, 40), font=font_title)

    # Thin separator
    sep_y = ty + th + 6
    draw.line([inner_left + 20, sep_y, inner_right - 20, sep_y], fill=(200, 200, 210), width=1)

    # Benefit icons (+ circle drawn later, after border)
    show_plus = card.get("show_plus", True)
    icon_row_y = sep_y + 8
    pm_circles = []
    if show_plus:
        pm_y = icon_row_y + (benefit_row_h - benefit_pm_size) // 2
        outline_w = max(benefit_pm_size // 8, 4)
        # Position circle on the box edge, but clamp so it doesn't spill off the card
        pm_x = max(4, inner_left - benefit_pm_size // 2)
        pm_circles.append((pm_x, pm_y, benefit_pm_size, True))
        # Icons start after the +/- circle + outline
        icons_x_start = pm_x + benefit_pm_size + outline_w + 8
    else:
        icons_x_start = inner_left + 14
    icons_area_w = inner_right - icons_x_start - 10
    draw_icon_row(canvas, benefits, icons_x_start, icon_row_y, icons_area_w, benefit_row_h)

    # --- INFO AREA (calculate first so art can fill the gap) ---
    font_desc = get_font_regular(desc_font_px)
    desc_text = card.get("description", "")
    lines = word_wrap(draw, desc_text, font_desc, inner_width - 40)

    text_block_h = sum(
        draw.textbbox((0, 0), line, font=font_desc)[3] - draw.textbbox((0, 0), line, font=font_desc)[1] + 4
        for line in lines
    )

    # Info area: text + separator + cost icons row (dynamically sized)
    info_padding = 15
    sep_height = 25
    info_h = info_padding + text_block_h + sep_height + cost_row_h + 10 + info_padding

    bottom_margin = layout.get("info_area_bottom_margin", 65)
    info_y = CARD_H - bottom_margin - info_h

    # --- CARD ART (fills all space between header and info area) ---
    art_y = hdr_y + hdr_h + 5
    art_bottom = info_y - 5
    art_h = art_bottom - art_y
    art_crop = art_image.resize((inner_width, art_h), Image.LANCZOS)
    canvas.paste(art_crop.convert("RGBA"), (inner_left, art_y))

    draw.rounded_rectangle(
        [inner_left, info_y, inner_right, info_y + info_h],
        radius=12, fill=(255, 255, 255, 245),
    )

    # Description text
    line_y = info_y + info_padding
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font_desc)
        lw = bbox[2] - bbox[0]
        lh = bbox[3] - bbox[1]
        lx = inner_left + (inner_width - lw) // 2
        draw.text((lx, line_y), line, fill=(40, 40, 50), font=font_desc)
        line_y += lh + 4

    # Thin separator
    sep_cost_y = line_y + 8
    draw.line([inner_left + 20, sep_cost_y, inner_right - 20, sep_cost_y], fill=(210, 210, 215), width=1)

    # Cost icons (- circle drawn later, after border)
    show_minus = card.get("show_minus", True)
    cost_icon_y = sep_cost_y + 10
    if show_minus:
        cost_pm_y = cost_icon_y + (cost_row_h - cost_pm_size) // 2
        outline_w = max(cost_pm_size // 8, 4)
        pm_x = max(4, inner_left - cost_pm_size // 2)
        pm_circles.append((pm_x, cost_pm_y, cost_pm_size, False))
        cost_icons_x = pm_x + cost_pm_size + outline_w + 8
    else:
        cost_icons_x = inner_left + 14
    cost_icons_w = inner_right - cost_icons_x - 10
    draw_icon_row(canvas, costs, cost_icons_x, cost_icon_y, cost_icons_w, cost_row_h)

    # Attach circle positions so they can be drawn after the border
    canvas._pm_circles = pm_circles

    return canvas


def draw_pm_overlay(canvas):
    """Draw +/- circles on top of the final card (after border has been applied)."""
    circles = getattr(canvas, '_pm_circles', [])
    if not circles:
        return canvas
    draw = ImageDraw.Draw(canvas)
    for (x, y, size, is_plus) in circles:
        draw_plus_minus_circle(draw, x, y, size, is_plus)
    return canvas


# ---------- Border overlay (from generate_assets.py) ----------

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


def apply_border(card_image, background_id):
    """Apply a background border overlay if it exists. Returns the composited image."""
    # Preserve pm_circles through the composite
    circles = getattr(card_image, '_pm_circles', [])
    # Check backgrounds folder first, then legacy borders folder
    border_path = BACKGROUNDS_DIR / f"{background_id}_border.png"
    if not border_path.exists():
        border_path = BORDERS_DIR / f"{background_id}_border.png"
    if border_path.exists():
        border = Image.open(str(border_path)).convert("RGBA")
        border = border.resize((CARD_W, CARD_H), Image.LANCZOS)
        result = Image.alpha_composite(card_image.convert("RGBA"), border)
        result._pm_circles = circles
        return result
    card_image._pm_circles = circles
    return card_image


def create_placeholder_art(width, height):
    """Create a grey placeholder image for preview compositing without ComfyUI."""
    img = Image.new("RGBA", (width, height), (80, 80, 100, 255))
    draw = ImageDraw.Draw(img)
    font = get_font(36)
    text = "Art Placeholder"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    draw.text(((width - tw) // 2, (height - th) // 2), text, fill=(160, 160, 180), font=font)
    return img
