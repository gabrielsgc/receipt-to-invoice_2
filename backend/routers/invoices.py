from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from services.pdf_service import generate_invoice_pdf
from models.invoice import InvoiceData

router = APIRouter()


@router.post("/generate")
def generate_invoice(invoice: InvoiceData):
    """Receive invoice data and return a PDF file."""
    try:
        pdf_bytes = generate_invoice_pdf(invoice)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")

    filename = f"invoice-{invoice.invoice_number}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
