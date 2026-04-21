from pydantic import BaseModel
from typing import Optional
from models.receipt import ReceiptItem


class InvoiceParty(BaseModel):
    name: str
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    tax_id: Optional[str] = None


class InvoiceData(BaseModel):
    invoice_number: str
    simplified_invoice_number: Optional[str] = None
    date: str
    due_date: Optional[str] = None
    issuer: InvoiceParty
    client: InvoiceParty
    items: list[ReceiptItem]
    subtotal: float
    tax_rate: Optional[float] = 0.0
    tax_amount: Optional[float] = 0.0
    total: float
    currency: Optional[str] = "EUR"
    notes: Optional[str] = None
    payment_terms: Optional[str] = None
