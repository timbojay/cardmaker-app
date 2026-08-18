"""Unit tests for the card compositor service."""

from app.backend.services import compositor


def test_create_placeholder_art_size():
    img = compositor.create_placeholder_art(825, 1125)
    assert img.size == (825, 1125)
    assert img.mode == "RGBA"


def test_composite_card_structure():
    card = {
        "id": "sj-test",
        "title": "Test Card",
        "benefits": {"navigation": 2, "fame": 1},
        "costs": {"bajillion": 1, "payload": 2},
        "description": "A short description for the test card.",
        "art_prompt": "",
        "title_size": "medium",
        "desc_size": "medium",
        "show_plus": True,
        "show_minus": True,
    }
    layout = {
        "border_width": 55,
        "header": {"y": 60, "height": 160},
        "art_area": {"y": 200, "height": 500},
        "info_area_bottom_margin": 65,
        "inner_margin": 70,
        "icon_size": 96,
        "plus_minus_size": 60,
        "title_font_size": 38,
        "desc_font_size": 26,
    }
    art = compositor.create_placeholder_art(825, 1125)
    final = compositor.composite_card(art, card, layout)
    final = compositor.apply_border(final, "junk")
    final = compositor.draw_pm_overlay(final)
    assert final.size == (825, 1125)
