import io
import zipfile
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
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

    filename = f"factura-{invoice.invoice_number}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


class BatchGenerateRequest(BaseModel):
    invoices: list[InvoiceData]


@router.post("/generate-batch")
def generate_batch(request: BatchGenerateRequest):
    """Generate multiple invoice PDFs and return as ZIP."""
    if len(request.invoices) > 20:
        raise HTTPException(status_code=400, detail="Maximum 20 invoices per batch")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for inv in request.invoices:
            try:
                pdf_bytes = generate_invoice_pdf(inv)
                filename = f"factura-{inv.invoice_number}.pdf"
                zf.writestr(filename, pdf_bytes)
            except Exception as e:
                # Include error file
                zf.writestr(f"ERROR-{inv.invoice_number}.txt", f"Failed: {str(e)}")

    return Response(
        content=buf.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="facturas.zip"'},
    )
