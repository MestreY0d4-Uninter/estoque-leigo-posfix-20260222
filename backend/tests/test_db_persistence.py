from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from app.db import Base, make_engine
from app.models import Item


def test_sqlite_creates_and_persists(tmp_path: Path) -> None:
    db_file = tmp_path / "app.db"

    engine = make_engine(str(db_file))
    Base.metadata.create_all(bind=engine)

    with Session(bind=engine) as db:
        db.add(Item(name="Arroz"))
        db.commit()

    # Re-open a new connection to validate persistence within the same file
    engine2 = make_engine(str(db_file))
    with Session(bind=engine2) as db2:
        items = db2.query(Item).all()
        assert len(items) == 1
        assert items[0].name == "Arroz"
