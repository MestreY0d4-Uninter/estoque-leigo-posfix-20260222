from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app


def test_product_crud_and_unique_sku(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "products.db"
    monkeypatch.setenv("SQLITE_PATH", str(db_path))

    app = create_app()
    with TestClient(app) as client:
        # create
        r = client.post(
            "/api/products",
            json={
                "name": "Arroz",
                "sku": "SKU-001",
                "category": "Alimentos",
                "quantity": 10,
                "cost": "5.50",
                "price": "7.00",
                "supplier": "Fornecedor A",
                "min_stock": 2,
            },
        )
        assert r.status_code == 200
        pid = r.json()["id"]

        # unique SKU
        r2 = client.post(
            "/api/products",
            json={
                "name": "Arroz 2",
                "sku": "SKU-001",
                "category": "Alimentos",
                "quantity": 1,
                "cost": "1.00",
                "price": "2.00",
                "supplier": "Fornecedor A",
                "min_stock": 0,
            },
        )
        assert r2.status_code == 409

        # list + search
        r3 = client.get("/api/products", params={"search": "SKU-001"})
        assert r3.status_code == 200
        assert len(r3.json()) == 1

        # update
        r4 = client.put(
            f"/api/products/{pid}",
            json={"quantity": 99, "name": "Arroz Integral"},
        )
        assert r4.status_code == 200
        assert r4.json()["quantity"] == 99

        # delete
        r5 = client.delete(f"/api/products/{pid}")
        assert r5.status_code == 204

        r6 = client.get("/api/products")
        assert r6.status_code == 200
        assert r6.json() == []


def test_filters_and_ordering(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "filters.db"
    monkeypatch.setenv("SQLITE_PATH", str(db_path))

    app = create_app()
    with TestClient(app) as client:
        client.post(
            "/api/products",
            json={
                "name": "Banana",
                "sku": "B-1",
                "category": "Frutas",
                "supplier": "X",
                "quantity": 5,
                "cost": "1.00",
                "price": "2.00",
                "min_stock": 0,
            },
        )
        client.post(
            "/api/products",
            json={
                "name": "Abacate",
                "sku": "A-1",
                "category": "Frutas",
                "supplier": "Y",
                "quantity": 20,
                "cost": "3.00",
                "price": "5.00",
                "min_stock": 1,
            },
        )

        r = client.get(
            "/api/products",
            params={"category": "Frutas", "order_by": "quantity", "order_dir": "desc"},
        )
        assert r.status_code == 200
        data = r.json()
        assert [p["sku"] for p in data] == ["A-1", "B-1"]

        r2 = client.get("/api/products", params={"supplier": "X"})
        assert r2.status_code == 200
        assert len(r2.json()) == 1
        assert r2.json()[0]["sku"] == "B-1"
