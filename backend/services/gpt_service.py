import base64
import json
import os
import ssl
import logging
from pathlib import Path
import httpx
import truststore
from openai import OpenAI
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)

logger = logging.getLogger(__name__)

_openai_client = None
_anthropic_client = None


def _get_ssl_http_client() -> httpx.Client:
    ctx = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    return httpx.Client(verify=ctx)


def _get_openai_client() -> OpenAI | None:
    global _openai_client
    if _openai_client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return None
        _openai_client = OpenAI(api_key=api_key, http_client=_get_ssl_http_client())
    return _openai_client


def _get_anthropic_client() -> Anthropic | None:
    global _anthropic_client
    if _anthropic_client is None:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            return None
        _anthropic_client = Anthropic(api_key=api_key, http_client=_get_ssl_http_client())
    return _anthropic_client

EXTRACTION_PROMPT = """Analyze this receipt/ticket image from a Spanish store and extract all relevant information.
Return a JSON object with the following structure (use null for missing fields):
{
  "vendor_name": "string (razón social del comercio)",
  "vendor_address": "string (dirección completa)",
  "vendor_phone": "string",
  "vendor_tax_id": "string (CIF/NIF del comercio, e.g. A46103834)",
  "date": "YYYY-MM-DD",
  "receipt_number": "string (número de ticket)",
  "simplified_invoice_number": "string (número de factura simplificada, e.g. 1234-001-123456)",
  "items": [
    {
      "description": "string",
      "quantity": number,
      "unit_price": number,
      "total": number
    }
  ],
  "subtotal": number,
  "tax": number (IVA amount),
  "total": number,
  "currency": "EUR",
  "notes": "string (store number, cashier, any other info)"
}
Important: currency is almost always EUR for Spanish stores. Look for CIF/NIF on the ticket header.
Look for "Factura simplificada" or "Fact. Simplificada" number which is different from the ticket number.
Return ONLY the JSON object, no extra text."""


def _extract_with_openai(data_url: str) -> dict:
    """Extract receipt data using OpenAI GPT-4o Vision."""
    client = _get_openai_client()
    if client is None:
        raise RuntimeError("OPENAI_API_KEY not set")
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": EXTRACTION_PROMPT},
                    {"type": "image_url", "image_url": {"url": data_url, "detail": "high"}},
                ],
            }
        ],
        max_tokens=1500,
    )
    return response.choices[0].message.content.strip()


def _extract_with_claude(image_bytes: bytes, mime_type: str) -> str:
    """Extract receipt data using Anthropic Claude Vision."""
    client = _get_anthropic_client()
    if client is None:
        raise RuntimeError("ANTHROPIC_API_KEY not set")
    encoded = base64.b64encode(image_bytes).decode("utf-8")
    # Claude accepts media_type directly for image content
    media_type = mime_type if mime_type in ("image/jpeg", "image/png", "image/gif", "image/webp") else "image/jpeg"
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": media_type, "data": encoded},
                    },
                    {"type": "text", "text": EXTRACTION_PROMPT},
                ],
            }
        ],
    )
    return response.content[0].text.strip()


def _parse_json(raw: str) -> dict:
    """Parse JSON from LLM response, stripping markdown fences if present."""
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw)


def extract_receipt_data(image_bytes: bytes, mime_type: str) -> dict:
    """Extract receipt data using OpenAI first, fallback to Claude."""
    encoded = base64.b64encode(image_bytes).decode("utf-8")
    data_url = f"data:{mime_type};base64,{encoded}"

    errors = []

    # Try OpenAI first
    if os.getenv("OPENAI_API_KEY"):
        try:
            logger.info("Trying OpenAI GPT-4o...")
            raw = _extract_with_openai(data_url)
            return _parse_json(raw)
        except Exception as e:
            logger.warning(f"OpenAI failed: {e}")
            errors.append(f"OpenAI: {e}")

    # Fallback to Claude
    if os.getenv("ANTHROPIC_API_KEY"):
        try:
            logger.info("Trying Anthropic Claude...")
            raw = _extract_with_claude(image_bytes, mime_type)
            return _parse_json(raw)
        except Exception as e:
            logger.warning(f"Claude failed: {e}")
            errors.append(f"Claude: {e}")

    if not os.getenv("OPENAI_API_KEY") and not os.getenv("ANTHROPIC_API_KEY"):
        raise RuntimeError("No API keys configured. Set OPENAI_API_KEY or ANTHROPIC_API_KEY in .env")

    raise RuntimeError(f"All AI providers failed: {'; '.join(errors)}")
