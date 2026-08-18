"""
Pydantic models for CardMaker API request/response schemas.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


# ---------- Deck ----------

class DeckCreate(BaseModel):
    id: str
    name: str
    back_prompt: Optional[str] = ""


class DeckUpdate(BaseModel):
    name: Optional[str] = None
    back_prompt: Optional[str] = None


class DeckResponse(BaseModel):
    id: str
    name: str
    back_prompt: Optional[str]
    back_image_path: Optional[str]
    created_at: str
    updated_at: str


# ---------- Card Type ----------

class CardTypeCreate(BaseModel):
    id: str
    name: str
    deck_id: str
    border_color: list[int] = []
    border_accent: list[int] = []
    border_prompt: Optional[str] = ""


class CardTypeUpdate(BaseModel):
    name: Optional[str] = None
    deck_id: Optional[str] = None
    border_color: Optional[list[int]] = None
    border_accent: Optional[list[int]] = None
    border_prompt: Optional[str] = None


class CardTypeResponse(BaseModel):
    id: str
    name: str
    deck_id: str
    border_color: list[int]
    border_accent: list[int]
    border_prompt: Optional[str]
    border_image_path: Optional[str]
    created_at: str
    updated_at: str


# ---------- Card ----------

class CardCreate(BaseModel):
    id: str
    title: str
    deck_id: str
    background_id: Optional[str] = ""
    benefits: dict[str, int] = {}
    costs: dict[str, int] = {}
    description: Optional[str] = ""
    art_prompt: Optional[str] = ""
    title_size: Optional[str] = "medium"
    desc_size: Optional[str] = "medium"
    show_plus: Optional[bool] = True
    show_minus: Optional[bool] = True


class CardUpdate(BaseModel):
    title: Optional[str] = None
    deck_id: Optional[str] = None
    background_id: Optional[str] = None
    benefits: Optional[dict[str, int]] = None
    costs: Optional[dict[str, int]] = None
    description: Optional[str] = None
    art_prompt: Optional[str] = None
    title_size: Optional[str] = None
    desc_size: Optional[str] = None
    show_plus: Optional[bool] = None
    show_minus: Optional[bool] = None


class CardResponse(BaseModel):
    id: str
    title: str
    deck_id: str
    background_id: Optional[str]
    benefits: dict[str, int]
    costs: dict[str, int]
    description: Optional[str]
    art_prompt: Optional[str]
    title_size: Optional[str]
    desc_size: Optional[str]
    show_plus: Optional[bool]
    show_minus: Optional[bool]
    art_image_path: Optional[str]
    print_image_path: Optional[str]
    preview_image_path: Optional[str]
    created_at: str
    updated_at: str
