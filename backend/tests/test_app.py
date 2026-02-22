from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.auth import pwd_context
from app.main import create_app


def test_health_ok(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("SQLITE_PATH", str(db_path))
    monkeypatch.setenv("SESSION_SECRET", "test-secret")

    app = create_app()
    with TestClient(app) as client:
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


def test_notes_persist_in_sqlite(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "persist.db"
    monkeypatch.setenv("SQLITE_PATH", str(db_path))
    monkeypatch.setenv("SESSION_SECRET", "test-secret")
    monkeypatch.setenv("ADMIN_USER", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD_HASH", pwd_context.hash("pw"))

    app = create_app()
    with TestClient(app) as client:
        login = client.post("/api/login", json={"username": "admin", "password": "pw"})
        assert login.status_code == 200

        r = client.post("/api/notes", json={"content": "hello"})
        assert r.status_code == 200

    # New app instance reading same DB file should see the note
    app2 = create_app()
    with TestClient(app2) as client2:
        login2 = client2.post("/api/login", json={"username": "admin", "password": "pw"})
        assert login2.status_code == 200

        r2 = client2.get("/api/notes")
        assert r2.status_code == 200
        notes = r2.json()
        assert len(notes) == 1
        assert notes[0]["content"] == "hello"
