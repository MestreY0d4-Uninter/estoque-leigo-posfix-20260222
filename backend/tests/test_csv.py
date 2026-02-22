from __future__ import annotations

import io
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app


def _upload_file(client: TestClient, content: str, *, apply: bool, mode: str = "upsert"):
    f = io.BytesIO(content.encode("utf-8"))
    files = {"file": ("products.csv", f, "text/csv")}
    return client.post(
        f"/api/products/import?apply={'true' if apply else 'false'}&mode={mode}", files=files
    )


def test_export_and_import_preview_apply(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "db.db"))

    app = create_app()
    with TestClient(app) as client:
        # import preview
        csv_content = (
            "sku,name,category,supplier,quantity,cost,price,min_stock\n"
            "SKU-1,Item A,Cat,Sup,10,1.00,2.00,1\n"
            "SKU-2,Item B,Cat,Sup,0,0.50,1.50,0\n"
        )
        r = _upload_file(client, csv_content, apply=False)
        assert r.status_code == 200
        data = r.json()
        assert data["summary"]["create"] == 2

        # apply should create
        r2 = _upload_file(client, csv_content, apply=True)
        assert r2.status_code == 200
        data2 = r2.json()
        assert data2["summary"]["create"] == 2

        # export should include headers and created SKUs
        r3 = client.get("/api/products.csv")
        assert r3.status_code == 200
        text = r3.text
        assert "sku,name,category,supplier,quantity,cost,price,min_stock" in text
        assert "SKU-1" in text
        assert "SKU-2" in text


def test_import_invalid_row_rejected(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "db.db"))

    app = create_app()
    with TestClient(app) as client:
        csv_content = (
            "sku,name,category,supplier,quantity,cost,price,min_stock\n"
            ",NoSku,Cat,Sup,10,1.00,2.00,1\n"
            "SKU-OK,Ok,Cat,Sup,-1,1.00,2.00,1\n"
        )
        r = _upload_file(client, csv_content, apply=False)
        assert r.status_code == 200
        data = r.json()
        assert data["summary"]["invalid"] == 2
