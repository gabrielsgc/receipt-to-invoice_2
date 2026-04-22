from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
import base64
import logging

from services.mercadona_service import request_mercadona_ticket

router = APIRouter()
logger = logging.getLogger(__name__)


class MercadonaTicketRequest(BaseModel):
    payment_method: str = "card"  # "card" or "cash"
    purchase_date: Optional[str] = None  # DD/MM/YYYY
    total_amount: Optional[str] = None  # e.g. "45,32"
    card_last4: Optional[str] = None  # last 4 digits
    store_address: Optional[str] = None  # city or postal code
    time_range: Optional[str] = None  # for cash payments
    products_hint: Optional[str] = None  # for cash payments
    email: Optional[str] = None  # for cash payments


class MercadonaTicketResponse(BaseModel):
    success: bool
    message: str
    tickets_found: list = []
    pdf_base64: Optional[str] = None
    screenshots_base64: list[str] = []


@router.post("/request-ticket", response_model=MercadonaTicketResponse)
async def request_ticket(req: MercadonaTicketRequest):
    """Search for ticket on Mercadona tickets portal."""
    logger.info(f"Requesting Mercadona ticket: method={req.payment_method}, date={req.purchase_date}")

    try:
        result = await request_mercadona_ticket(
            payment_method=req.payment_method,
            purchase_date=req.purchase_date,
            total_amount=req.total_amount,
            card_last4=req.card_last4,
            store_address=req.store_address,
            time_range=req.time_range,
            products_hint=req.products_hint,
            email=req.email,
            headless=True,
        )
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        print(f"MERCADONA ERROR: {tb}", flush=True)
        return MercadonaTicketResponse(
            success=False,
            message=f"Error: {repr(e)} | {tb[-500:]}",
            tickets_found=[],
            pdf_base64=None,
            screenshots_base64=[],
        )

    pdf_b64 = None
    if result.get("pdf_bytes"):
        pdf_b64 = base64.b64encode(result["pdf_bytes"]).decode("utf-8")

    screenshots_b64 = [
        base64.b64encode(s).decode("utf-8") for s in result.get("screenshots", [])
    ]

    return MercadonaTicketResponse(
        success=result["success"],
        message=result["message"],
        tickets_found=result.get("tickets_found", []),
        pdf_base64=pdf_b64,
        screenshots_base64=screenshots_b64,
    )
