from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.auth import pwd_context
from app.main import create_app


def test_low_stock_endpoint_and_flag(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "low.db"
    monkeypatch.setenv("SQLITE_PATH", str(db_path))
    monkeypatch.setenv("SESSION_SECRET", "test-secret")
    monkeypatch.setenv("ADMIN_USER", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD_HASH", pwd_context.hash("pw"))

    app = create_app()
    with TestClient(app) as client:
        login = client.post("/api/login", json={"username": "admin", "password": "pw"})
        assert login.status_code == 200

        # product OK
        r1 = client.post(
            "/api/products",
            json={
                "name": "Arroz",
                "sku": "SKU-1",
                "category": "Alimentos",
                "supplier": "A",
                "quantity": 10,
                "min_stock": 2,
                "cost": "1.00",
                "price": "2.00",
            },
        )
        assert r1.status_code == 200
        assert r1.json()["low_stock"] is False

        # low stock (<=)
        r2 = client.post(
            "/api/products",
            json={
                "name": "Feijao",
                "sku": "SKU-2",
                "category": "Alimentos",
                "supplier": "B",
                "quantity": 1,
                "min_stock": 1,
                "cost": "1.00",
                "price": "2.00",
            },
        )
        assert r2.status_code == 200
        assert r2.json()["low_stock"] is True

        low = client.get("/api/low-stock")
        assert low.status_code == 200
        data = low.json()
        assert len(data) == 1
        assert data[0]["sku"] == "SKU-2"
        assert data[0]["low_stock"] is True
