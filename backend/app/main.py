from __future__ import annotations

import csv
import io
from collections.abc import Generator
from pathlib import Path
from typing import Literal

from fastapi import Depends, FastAPI, File, HTTPException, Query, Response, UploadFile
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.db import Settings, get_db_session, get_settings, make_engine, make_sessionmaker
from app.models import Base, Note, Product
from app.schemas import (
    CSVRowError,
    HealthResponse,
    NoteCreate,
    NoteOut,
    OrderBy,
    OrderDir,
    ProductCreate,
    ProductImportPreview,
    ProductImportPreviewRow,
    ProductOut,
    ProductUpdate,
)


def create_app() -> FastAPI:
    app = FastAPI(title="Estoque Leigo (V1)")

    @app.on_event("startup")
    def _startup() -> None:
        settings = get_settings()
        engine = make_engine(settings)
        Base.metadata.create_all(engine)

        app.state.settings = settings
        app.state.engine = engine
        app.state.session_factory = make_sessionmaker(engine)

    def _get_settings_from_state() -> Settings:
        return app.state.settings  # type: ignore[no-any-return]

    def _get_session_factory() -> sessionmaker[Session]:
        return app.state.session_factory  # type: ignore[no-any-return]

    def db_session(
        factory: sessionmaker[Session] = Depends(_get_session_factory),  # noqa: B008
    ) -> Generator[Session, None, None]:
        yield from get_db_session(factory)

    @app.get("/health", response_model=HealthResponse)
    def health(
        settings: Settings = Depends(_get_settings_from_state),  # noqa: B008
        db: Session = Depends(db_session),  # noqa: B008
    ) -> HealthResponse:
        db.execute(text("SELECT 1"))
        return HealthResponse(status="ok", sqlite_path=settings.sqlite_path)

    @app.post("/api/notes", response_model=NoteOut)
    def create_note(payload: NoteCreate, db: Session = Depends(db_session)) -> NoteOut:  # noqa: B008
        note = Note(content=payload.content)
        db.add(note)
        db.commit()
        db.refresh(note)
        return NoteOut(id=note.id, content=note.content, created_at=note.created_at)

    @app.get("/api/notes", response_model=list[NoteOut])
    def list_notes(db: Session = Depends(db_session)) -> list[NoteOut]:  # noqa: B008
        rows = db.execute(select(Note).order_by(Note.id.desc())).scalars().all()
        return [NoteOut(id=n.id, content=n.content, created_at=n.created_at) for n in rows]

    def _to_product_out(p: Product) -> ProductOut:
        return ProductOut(
            id=p.id,
            name=p.name,
            sku=p.sku,
            category=p.category,
            supplier=p.supplier,
            quantity=p.quantity,
            min_stock=p.min_stock,
            cost=p.cost,
            price=p.price,
            created_at=p.created_at,
        )

    @app.post("/api/products", response_model=ProductOut)
    def create_product(payload: ProductCreate, db: Session = Depends(db_session)) -> ProductOut:  # noqa: B008
        p = Product(
            name=payload.name,
            sku=payload.sku,
            category=payload.category,
            supplier=payload.supplier,
            quantity=payload.quantity,
            min_stock=payload.min_stock,
            cost=payload.cost,
            price=payload.price,
        )
        db.add(p)
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise HTTPException(status_code=409, detail="SKU já existe") from exc
        db.refresh(p)
        return _to_product_out(p)

    @app.get("/api/products", response_model=list[ProductOut])
    def list_products(
        db: Session = Depends(db_session),  # noqa: B008
        search: str | None = Query(default=None, max_length=200),  # noqa: B008
        category: str | None = Query(default=None, max_length=100),  # noqa: B008
        supplier: str | None = Query(default=None, max_length=100),  # noqa: B008
        order_by: OrderBy = Query(default="name"),  # noqa: B008
        order_dir: OrderDir = Query(default="asc"),  # noqa: B008
    ) -> list[ProductOut]:
        stmt = select(Product)
        if search:
            like = f"%{search}%"
            stmt = stmt.where((Product.name.ilike(like)) | (Product.sku.ilike(like)))
        if category:
            stmt = stmt.where(Product.category == category)
        if supplier:
            stmt = stmt.where(Product.supplier == supplier)

        order_col = Product.name if order_by == "name" else Product.quantity
        stmt = stmt.order_by(order_col.asc() if order_dir == "asc" else order_col.desc())

        rows = db.execute(stmt).scalars().all()
        return [_to_product_out(p) for p in rows]

    @app.get("/api/products/{product_id}", response_model=ProductOut)
    def get_product(
        product_id: int,
        db: Session = Depends(db_session),  # noqa: B008
    ) -> ProductOut:
        p = db.get(Product, product_id)
        if p is None:
            raise HTTPException(status_code=404, detail="Produto não encontrado")
        return _to_product_out(p)

    @app.put("/api/products/{product_id}", response_model=ProductOut)
    def update_product(
        product_id: int,
        payload: ProductUpdate,
        db: Session = Depends(db_session),  # noqa: B008
    ) -> ProductOut:
        p = db.get(Product, product_id)
        if p is None:
            raise HTTPException(status_code=404, detail="Produto não encontrado")

        data = payload.model_dump(exclude_unset=True)
        for k, v in data.items():
            setattr(p, k, v)

        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise HTTPException(status_code=409, detail="SKU já existe") from exc

        db.refresh(p)
        return _to_product_out(p)

    @app.delete("/api/products/{product_id}", status_code=204)
    def delete_product(
        product_id: int,
        db: Session = Depends(db_session),  # noqa: B008
    ) -> Response:
        p = db.get(Product, product_id)
        if p is None:
            raise HTTPException(status_code=404, detail="Produto não encontrado")
        db.delete(p)
        db.commit()
        return Response(status_code=204)

    CSV_HEADERS = [
        "sku",
        "name",
        "category",
        "supplier",
        "quantity",
        "cost",
        "price",
        "min_stock",
    ]

    @app.get("/api/products.csv")
    def export_products_csv(db: Session = Depends(db_session)) -> Response:  # noqa: B008
        rows = db.execute(select(Product).order_by(Product.id.asc())).scalars().all()

        buf = io.StringIO(newline="")
        writer = csv.DictWriter(buf, fieldnames=CSV_HEADERS, extrasaction="ignore")
        writer.writeheader()
        for p in rows:
            writer.writerow(
                {
                    "sku": p.sku,
                    "name": p.name,
                    "category": p.category,
                    "supplier": p.supplier,
                    "quantity": p.quantity,
                    "cost": str(p.cost),
                    "price": str(p.price),
                    "min_stock": p.min_stock,
                }
            )

        # Add UTF-8 BOM to be Excel-friendly
        content = "\ufeff" + buf.getvalue()
        return Response(
            content=content,
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="products.csv"'},
        )

    def _parse_csv_upload(file: UploadFile) -> tuple[list[str], list[dict[str, str]]]:
        raw = file.file.read()
        text_data = raw.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text_data))
        headers = list(reader.fieldnames or [])
        data_rows: list[dict[str, str]] = []
        for r in reader:
            # DictReader returns None keys when columns mismatch; ignore those.
            clean: dict[str, str] = {
                (k or "").strip(): (v or "").strip() for k, v in r.items() if k is not None
            }
            data_rows.append(clean)
        return headers, data_rows

    @app.post("/api/products/import", response_model=ProductImportPreview)
    def import_products_csv(
        file: UploadFile = File(...),  # noqa: B008
        apply: bool = Query(default=False),  # noqa: B008
        mode: str = Query(default="upsert"),  # noqa: B008
        db: Session = Depends(db_session),  # noqa: B008
    ) -> ProductImportPreview:
        if not file.filename or not file.filename.lower().endswith(".csv"):
            raise HTTPException(status_code=400, detail="Envie um arquivo .csv")

        headers, data_rows = _parse_csv_upload(file)
        missing = [h for h in CSV_HEADERS if h not in headers]
        if missing:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "CSV inválido",
                    "missing_headers": missing,
                    "expected": CSV_HEADERS,
                },
            )

        preview_rows: list[ProductImportPreviewRow] = []
        summary = {"create": 0, "update": 0, "skip": 0, "invalid": 0}

        # Start at 2 because header is line 1
        for i, row in enumerate(data_rows, start=2):
            errors: list[CSVRowError] = []
            sku = row.get("sku", "").strip()
            if not sku:
                errors.append(CSVRowError(field="sku", message="SKU é obrigatório"))

            # Build payload dict converting types via Pydantic
            payload_dict = {
                "sku": sku,
                "name": row.get("name", ""),
                "category": row.get("category", ""),
                "supplier": row.get("supplier", ""),
                "quantity": row.get("quantity", "0"),
                "cost": row.get("cost", "0"),
                "price": row.get("price", "0"),
                "min_stock": row.get("min_stock", "0"),
            }

            payload: ProductCreate | None = None
            if not errors:
                try:
                    payload = ProductCreate.model_validate(payload_dict)
                except Exception as exc:  # noqa: BLE001
                    errors.append(CSVRowError(field="row", message=str(exc)))

            if errors or payload is None:
                preview_rows.append(
                    ProductImportPreviewRow(
                        line=i, sku=sku or None, action="invalid", errors=errors
                    )
                )
                summary["invalid"] += 1
                continue

            existing = db.execute(
                select(Product).where(Product.sku == payload.sku)
            ).scalar_one_or_none()

            action: Literal["create", "update", "skip"]
            if mode == "create":
                action = "skip" if existing else "create"
                if existing:
                    errors.append(CSVRowError(field="sku", message="SKU já existe (modo create)"))
            elif mode == "update":
                action = "update" if existing else "skip"
                if not existing:
                    errors.append(
                        CSVRowError(field="sku", message="SKU não encontrado (modo update)")
                    )
            else:
                # upsert
                action = "update" if existing else "create"

            if errors:
                preview_rows.append(
                    ProductImportPreviewRow(
                        line=i, sku=payload.sku, action="invalid", errors=errors
                    )
                )
                summary["invalid"] += 1
                continue

            preview_rows.append(ProductImportPreviewRow(line=i, sku=payload.sku, action=action))
            if action == "create":
                summary["create"] += 1
            elif action == "update":
                summary["update"] += 1
            else:
                summary["skip"] += 1

            if apply and action in {"create", "update"}:
                if action == "create":
                    obj = Product(
                        name=payload.name,
                        sku=payload.sku,
                        category=payload.category,
                        supplier=payload.supplier,
                        quantity=payload.quantity,
                        cost=payload.cost,
                        price=payload.price,
                        min_stock=payload.min_stock,
                    )
                    db.add(obj)
                else:
                    assert existing is not None
                    existing.name = payload.name
                    existing.category = payload.category
                    existing.supplier = payload.supplier
                    existing.quantity = payload.quantity
                    existing.cost = payload.cost
                    existing.price = payload.price
                    existing.min_stock = payload.min_stock

                try:
                    db.commit()
                except IntegrityError:
                    db.rollback()
                    # Mark last row as invalid and keep processing other rows
                    preview_rows[-1].action = "invalid"
                    preview_rows[-1].errors.append(
                        CSVRowError(field="sku", message="Conflito de SKU / integridade")
                    )
                    if action == "create":
                        summary["create"] -= 1
                    else:
                        summary["update"] -= 1
                    summary["invalid"] += 1

        return ProductImportPreview(headers=headers, rows=preview_rows, summary=summary)

    # Frontend (static)
    base_dir = Path(__file__).resolve().parents[1]
    static_dir = base_dir / "frontend" / "static"
    if static_dir.exists():
        # Mounted last so /api/* and /health keep working.
        app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="frontend")

    return app


app = create_app()
