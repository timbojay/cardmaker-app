import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent

# Ensure backend root is importable (main.py uses plain `import database`)
BACKEND_ROOT = PROJECT_ROOT / "app" / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

os.environ.setdefault("TESTING", "1")

import database as db_module  # noqa: E402
from main import app  # noqa: E402


@pytest.fixture(scope="function")
def client():
    """Create a FastAPI TestClient backed by a fresh temporary SQLite DB."""
    tmpdir = tempfile.mkdtemp(prefix="cardmaker_test_")
    db_path = Path(tmpdir) / "cardmaker.db"

    original_db_path = db_module.DB_PATH
    db_module.DB_PATH = db_path

    db_module.init_db()
    db_module._migrate_db()
    db_module.import_from_json()

    from fastapi.testclient import TestClient

    with TestClient(app) as c:
        yield c

    db_module.DB_PATH = original_db_path
    shutil.rmtree(tmpdir, ignore_errors=True)
