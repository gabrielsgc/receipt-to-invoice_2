from fastapi import APIRouter, UploadFile, File, HTTPException
from services.gpt_service import extract_receipt_data
from services.ocr_service import pdf_to_image_bytes
from models.receipt import ReceiptData

router = APIRouter()

ALLOWED_TYPES = {
    "image/jpeg", "image/jpg", "image/png", "image/webp", "image/gif",
    "application/pdf",
}


@router.post("/analyze", response_model=ReceiptData)
async def analyze_receipt(file: UploadFile = File(...)):
    """Upload a receipt image or PDF and extract structured data using GPT-4o Vision."""
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}. Allowed: images and PDF.",
        )

    file_bytes = await file.read()
    if len(file_bytes) > 10 * 1024 * 1024:  # 10 MB limit
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 10 MB.")

    mime_type = file.content_type

    # Convert PDF to image for GPT Vision
    if mime_type == "application/pdf":
        try:
            file_bytes, mime_type = pdf_to_image_bytes(file_bytes)
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"Could not process PDF: {str(e)}")

    try:
        data = extract_receipt_data(file_bytes, mime_type)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"GPT extraction failed: {str(e)}")

    return ReceiptData(**data)
