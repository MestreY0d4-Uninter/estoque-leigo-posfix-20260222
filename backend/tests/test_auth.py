from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from passlib.context import CryptContext

from app.main import create_app


def _hash(pw: str) -> str:
    ctx = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
    return ctx.hash(pw)


def test_redirect_to_login_when_not_authenticated(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "db.db"))
    monkeypatch.setenv("SESSION_SECRET", "test-secret")
    monkeypatch.setenv("ADMIN_USER", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD_HASH", _hash("pw"))

    app = create_app()
    with TestClient(app, follow_redirects=False) as client:
        r = client.get("/")
        assert r.status_code in {301, 302, 307}
        assert r.headers["location"] == "/login"


def test_login_logout_flow(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "db.db"))
    monkeypatch.setenv("SESSION_SECRET", "test-secret")
    monkeypatch.setenv("ADMIN_USER", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD_HASH", _hash("pw"))

    app = create_app()
    with TestClient(app) as client:
        # wrong credentials
        r = client.post("/api/login", json={"username": "admin", "password": "wrong"})
        assert r.status_code == 401

        # correct login
        r2 = client.post("/api/login", json={"username": "admin", "password": "pw"})
        assert r2.status_code == 200
        assert r2.json() == {"ok": True}

        # now access protected route
        r3 = client.get("/api/products")
        assert r3.status_code == 200

        # logout
        r4 = client.post("/api/logout")
        assert r4.status_code == 200

        # should be blocked again
        r5 = client.get("/api/products")
        assert r5.status_code == 401
