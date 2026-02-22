from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app


def test_low_stock_filter(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "db.db"))

    app = create_app()
    with TestClient(app) as client:
        client.post(
            "/api/products",
            json={
                "name": "Produto OK",
                "sku": "OK",
                "category": "",
                "supplier": "",
                "quantity": 10,
                "cost": "1.00",
                "price": "2.00",
                "min_stock": 2,
            },
        )
        client.post(
            "/api/products",
            json={
                "name": "Produto Baixo",
                "sku": "LOW",
                "category": "",
                "supplier": "",
                "quantity": 2,
                "cost": "1.00",
                "price": "2.00",
                "min_stock": 2,
            },
        )

        all_r = client.get("/api/products")
        assert all_r.status_code == 200
        assert len(all_r.json()) == 2

        low_r = client.get("/api/products", params={"low_stock": "true"})
        assert low_r.status_code == 200
        data = low_r.json()
        assert len(data) == 1
        assert data[0]["sku"] == "LOW"
