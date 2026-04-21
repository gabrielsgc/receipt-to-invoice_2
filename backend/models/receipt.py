from pydantic import BaseModel
from typing import Optional


class ReceiptItem(BaseModel):
    description: str
    quantity: float
    unit_price: float
    total: float


class ReceiptData(BaseModel):
    vendor_name: Optional[str] = None
    vendor_address: Optional[str] = None
    vendor_phone: Optional[str] = None
    date: Optional[str] = None
    receipt_number: Optional[str] = None
    items: list[ReceiptItem] = []
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    total: Optional[float] = None
    currency: Optional[str] = "USD"
    notes: Optional[str] = None
