from fastapi import APIRouter, UploadFile, File, HTTPException
from services.gpt_service import extract_receipt_data
from services.ocr_service import pdf_to_image_bytes
from models.receipt import ReceiptData
import asyncio
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

ALLOWED_TYPES = {
    "image/jpeg", "image/jpg", "image/png", "image/webp", "image/gif",
    "application/pdf",
}


async def _process_single(file: UploadFile) -> dict:
    """Process a single file and return result or error dict."""
    if file.content_type not in ALLOWED_TYPES:
        return {"filename": file.filename, "success": False, "error": f"Unsupported type: {file.content_type}"}

    file_bytes = await file.read()
    if len(file_bytes) > 10 * 1024 * 1024:
        return {"filename": file.filename, "success": False, "error": "File too large (max 10 MB)"}

    mime_type = file.content_type
    if mime_type == "application/pdf":
        try:
            file_bytes, mime_type = pdf_to_image_bytes(file_bytes)
        except Exception as e:
            return {"filename": file.filename, "success": False, "error": f"PDF error: {e}"}

    try:
        data = extract_receipt_data(file_bytes, mime_type)
        return {"filename": file.filename, "success": True, "data": ReceiptData(**data).model_dump()}
    except Exception as e:
        return {"filename": file.filename, "success": False, "error": str(e)}


@router.post("/analyze", response_model=ReceiptData)
async def analyze_receipt(file: UploadFile = File(...)):
    """Upload a receipt image or PDF and extract structured data."""
    result = await _process_single(file)
    if not result["success"]:
        raise HTTPException(status_code=502, detail=f"GPT extraction failed: {result['error']}")
    return ReceiptData(**result["data"])


@router.post("/analyze-batch")
async def analyze_batch(files: list[UploadFile] = File(...)):
    """Upload multiple receipts. Returns list of results with success/error per file."""
    if len(files) > 20:
        raise HTTPException(status_code=400, detail="Maximum 20 files per batch")

    results = []
    for file in files:
        logger.info(f"Processing {file.filename}...")
        result = await _process_single(file)
        results.append(result)

    return {"results": results, "total": len(results), "success_count": sum(1 for r in results if r["success"])}
