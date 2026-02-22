from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query, Response
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.db import Settings, get_db_session, get_settings, make_engine, make_sessionmaker
from app.models import Base, Note, Product
from app.schemas import (
    HealthResponse,
    NoteCreate,
    NoteOut,
    OrderBy,
    OrderDir,
    ProductCreate,
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

    # Frontend (static)
    base_dir = Path(__file__).resolve().parents[1]
    static_dir = base_dir / "frontend" / "static"
    if static_dir.exists():
        # Mounted last so /api/* and /health keep working.
        app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="frontend")

    return app


app = create_app()
