"""
SQLite database for CardMaker.

Tables: decks, card_types, cards.
Includes init_db(), get_db() context manager, and import_from_json() seeder.
"""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
DB_PATH = PROJECT_ROOT / "app" / "backend" / "cardmaker.db"

CARDS_JSON = PROJECT_ROOT / "card-data" / "space_junk_cards.json"
DECKS_JSON = PROJECT_ROOT / "card-data" / "decks.json"


def _migrate_db():
    """Run any needed schema migrations."""
    with get_db() as db:
        cols = [row[1] for row in db.execute("PRAGMA table_info(cards)").fetchall()]
        if "art_image_path" not in cols:
            db.execute("ALTER TABLE cards ADD COLUMN art_image_path TEXT")
            print("Migration: added art_image_path column to cards table")
        if "background_id" not in cols:
            db.execute("ALTER TABLE cards ADD COLUMN background_id TEXT")
            # Migrate existing type_id values to background_id
            if "type_id" in cols:
                db.execute("UPDATE cards SET background_id = type_id WHERE background_id IS NULL")
            print("Migration: added background_id column to cards table")
        if "title_size" not in cols:
            db.execute("ALTER TABLE cards ADD COLUMN title_size TEXT DEFAULT 'medium'")
            print("Migration: added title_size column to cards table")
        if "desc_size" not in cols:
            db.execute("ALTER TABLE cards ADD COLUMN desc_size TEXT DEFAULT 'medium'")
            print("Migration: added desc_size column to cards table")
        if "show_plus" not in cols:
            db.execute("ALTER TABLE cards ADD COLUMN show_plus INTEGER DEFAULT 1")
            print("Migration: added show_plus column to cards table")
        if "show_minus" not in cols:
            db.execute("ALTER TABLE cards ADD COLUMN show_minus INTEGER DEFAULT 1")
            print("Migration: added show_minus column to cards table")


def init_db():
    """Create tables if they don't exist."""
    with get_db() as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS decks (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                back_prompt TEXT,
                back_image_path TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS card_types (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                deck_id TEXT NOT NULL,
                border_color TEXT,
                border_accent TEXT,
                border_prompt TEXT,
                border_image_path TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (deck_id) REFERENCES decks(id)
            );

            CREATE TABLE IF NOT EXISTS cards (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                deck_id TEXT NOT NULL,
                background_id TEXT,
                benefits TEXT,
                costs TEXT,
                description TEXT,
                art_prompt TEXT,
                art_image_path TEXT,
                print_image_path TEXT,
                preview_image_path TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (deck_id) REFERENCES decks(id)
            );
        """)


@contextmanager
def get_db():
    """Context manager that yields a sqlite3 connection with row factory."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _now():
    return datetime.now(timezone.utc).isoformat()


def is_db_empty():
    """Check if the database has any data."""
    with get_db() as db:
        row = db.execute("SELECT COUNT(*) FROM decks").fetchone()
        return row[0] == 0


def import_from_json():
    """Seed database from existing JSON files."""
    now = _now()

    # Load decks.json
    with open(DECKS_JSON) as f:
        decks_data = json.load(f)

    # Load space_junk_cards.json
    with open(CARDS_JSON) as f:
        cards_data = json.load(f)

    with get_db() as db:
        # Insert decks
        for deck in decks_data["decks"]:
            db.execute(
                """INSERT OR IGNORE INTO decks (id, name, back_prompt, back_image_path, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (deck["id"], deck["name"], deck.get("back_prompt", ""), None, now, now),
            )

        # Insert card types
        for ct in decks_data["card_types"]:
            # Check if border image already exists
            border_path = PROJECT_ROOT / "assets" / "borders" / f"{ct['id']}_border.png"
            border_image_path = str(border_path) if border_path.exists() else None

            db.execute(
                """INSERT OR IGNORE INTO card_types
                   (id, name, deck_id, border_color, border_accent, border_prompt, border_image_path, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    ct["id"],
                    ct["name"],
                    ct["deck"],
                    json.dumps(ct.get("border_color", [])),
                    json.dumps(ct.get("border_accent", [])),
                    ct.get("border_prompt", ""),
                    border_image_path,
                    now,
                    now,
                ),
            )

        # Insert cards
        for card in cards_data["cards"]:
            # Check if print/preview images already exist
            print_path = PROJECT_ROOT / "output" / "print-ready" / f"{card['id']}_print.png"
            preview_path = PROJECT_ROOT / "output" / "previews" / f"{card['id']}_preview.jpg"

            art_path = PROJECT_ROOT / "output" / "raw-art" / f"{card['id']}_art.png"

            db.execute(
                """INSERT OR IGNORE INTO cards
                   (id, title, deck_id, background_id, benefits, costs, description, art_prompt,
                    art_image_path, print_image_path, preview_image_path, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    card["id"],
                    card["title"],
                    card["deck"],
                    card.get("type", card.get("background", "")),
                    json.dumps(card.get("benefits", {})),
                    json.dumps(card.get("costs", {})),
                    card.get("description", ""),
                    card.get("art_prompt", ""),
                    str(art_path) if art_path.exists() else None,
                    str(print_path) if print_path.exists() else None,
                    str(preview_path) if preview_path.exists() else None,
                    now,
                    now,
                ),
            )
