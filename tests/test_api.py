"""API-level tests for the CardMaker FastAPI backend."""

import json


def test_comfyui_status(client):
    resp = client.get("/api/comfyui/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data


def test_list_decks(client):
    resp = client.get("/api/decks/")
    assert resp.status_code == 200
    decks = resp.json()
    assert isinstance(decks, list)
    assert len(decks) == 3  # junk, hazard, mission


def test_list_cards(client):
    resp = client.get("/api/cards/")
    assert resp.status_code == 200
    cards = resp.json()
    assert isinstance(cards, list)
    assert len(cards) == 3  # sj-005, sj-006, sj-007


def test_card_crud(client):
    # Create
    payload = {
        "id": "sj-test-001",
        "title": "Test Card",
        "deck_id": "junk",
        "background_id": "junk",
        "benefits": {"navigation": 2, "fame": 1},
        "costs": {"bajillion": 1},
        "description": "A test card.",
        "art_prompt": "Test art prompt",
    }
    resp = client.post("/api/cards/", json=payload)
    assert resp.status_code == 201
    card = resp.json()
    assert card["id"] == "sj-test-001"
    assert card["title"] == "Test Card"

    # Read
    resp = client.get("/api/cards/sj-test-001")
    assert resp.status_code == 200
    assert resp.json()["id"] == "sj-test-001"

    # Update
    resp = client.put("/api/cards/sj-test-001", json={"title": "Updated Test Card"})
    assert resp.status_code == 200
    assert resp.json()["title"] == "Updated Test Card"

    # Delete
    resp = client.delete("/api/cards/sj-test-001")
    assert resp.status_code == 204

    resp = client.get("/api/cards/sj-test-001")
    assert resp.status_code == 404


def test_preview_placeholder(client):
    """Preview endpoint should return a placeholder PNG for any card."""
    resp = client.get("/api/cards/sj-005/preview")
    assert resp.status_code == 200
    assert resp.headers["content-type"] in ("image/png", "image/jpeg")


def test_export_cards_document(client):
    resp = client.get("/api/export/cards-doc")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
