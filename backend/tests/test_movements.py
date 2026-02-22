from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app


def test_entry_exit_and_no_negative(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "movements.db"
    monkeypatch.setenv("SQLITE_PATH", str(db_path))

    app = create_app()
    with TestClient(app) as client:
        # create product with qty 0
        r = client.post(
            "/api/products",
            json={
                "name": "Arroz",
                "sku": "SKU-001",
                "category": "Alimentos",
                "supplier": "Fornecedor A",
                "quantity": 0,
                "min_stock": 0,
                "cost": "5.50",
                "price": "7.00",
            },
        )
        assert r.status_code == 200
        pid = r.json()["id"]

        # entry +10
        r2 = client.post(
            f"/api/products/{pid}/movements",
            json={"type": "entry", "quantity": 10, "note": "compra"},
        )
        assert r2.status_code == 200

        p = client.get(f"/api/products/{pid}").json()
        assert p["quantity"] == 10

        # exit -3
        r3 = client.post(
            f"/api/products/{pid}/movements",
            json={"type": "exit", "quantity": 3, "note": "venda"},
        )
        assert r3.status_code == 200

        p2 = client.get(f"/api/products/{pid}").json()
        assert p2["quantity"] == 7

        # exit -999 should fail
        r4 = client.post(
            f"/api/products/{pid}/movements",
            json={"type": "exit", "quantity": 999},
        )
        assert r4.status_code == 400

        p3 = client.get(f"/api/products/{pid}").json()
        assert p3["quantity"] == 7


def test_history_by_product(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "history.db"
    monkeypatch.setenv("SQLITE_PATH", str(db_path))

    app = create_app()
    with TestClient(app) as client:
        r = client.post(
            "/api/products",
            json={
                "name": "Feijao",
                "sku": "F-1",
                "category": "Alimentos",
                "supplier": "X",
                "quantity": 0,
                "min_stock": 0,
                "cost": "1.00",
                "price": "2.00",
            },
        )
        pid = r.json()["id"]

        client.post(f"/api/products/{pid}/movements", json={"type": "entry", "quantity": 2})
        client.post(f"/api/products/{pid}/movements", json={"type": "exit", "quantity": 1})

        hist = client.get(f"/api/products/{pid}/movements")
        assert hist.status_code == 200
        data = hist.json()
        assert len(data) == 2
        assert {m["type"] for m in data} == {"entry", "exit"}
        assert all(m["product_id"] == pid for m in data)
