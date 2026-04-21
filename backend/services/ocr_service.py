import io
from pdf2image import convert_from_bytes


def pdf_to_image_bytes(pdf_bytes: bytes) -> tuple[bytes, str]:
    """Convert the first page of a PDF to PNG image bytes."""
    images = convert_from_bytes(pdf_bytes, first_page=1, last_page=1, dpi=200)
    if not images:
        raise ValueError("Could not convert PDF to image")
    buf = io.BytesIO()
    images[0].save(buf, format="PNG")
    return buf.getvalue(), "image/png"
