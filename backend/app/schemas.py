from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    sqlite_path: str


class NoteCreate(BaseModel):
    content: str = Field(min_length=1, max_length=500)


class NoteOut(BaseModel):
    id: int
    content: str
    created_at: datetime


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    sku: str = Field(min_length=1, max_length=64)
    category: str = Field(default="", max_length=100)
    supplier: str = Field(default="", max_length=100)
    quantity: int = Field(default=0, ge=0)
    min_stock: int = Field(default=0, ge=0)
    cost: Decimal = Field(default=Decimal("0"), ge=0)
    price: Decimal = Field(default=Decimal("0"), ge=0)


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    sku: str | None = Field(default=None, min_length=1, max_length=64)
    category: str | None = Field(default=None, max_length=100)
    supplier: str | None = Field(default=None, max_length=100)
    quantity: int | None = Field(default=None, ge=0)
    min_stock: int | None = Field(default=None, ge=0)
    cost: Decimal | None = Field(default=None, ge=0)
    price: Decimal | None = Field(default=None, ge=0)


class ProductOut(BaseModel):
    id: int
    name: str
    sku: str
    category: str
    supplier: str
    quantity: int
    min_stock: int
    low_stock: bool
    cost: Decimal
    price: Decimal
    created_at: datetime


class MovementCreate(BaseModel):
    type: Literal["entry", "exit"]
    occurred_at: datetime | None = None
    quantity: int = Field(ge=1)
    note: str = Field(default="", max_length=500)


class MovementOut(BaseModel):
    id: int
    product_id: int
    type: Literal["entry", "exit"]
    occurred_at: datetime
    quantity: int
    note: str


OrderBy = Literal["name", "quantity"]
OrderDir = Literal["asc", "desc"]
