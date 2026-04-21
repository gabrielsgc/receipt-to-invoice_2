import base64
import json
import os
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

_client = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set. Copy .env.example to .env and add your key.")
        _client = OpenAI(api_key=api_key)
    return _client

EXTRACTION_PROMPT = """Analyze this receipt image and extract all relevant information.
Return a JSON object with the following structure (use null for missing fields):
{
  "vendor_name": "string",
  "vendor_address": "string",
  "vendor_phone": "string",
  "date": "YYYY-MM-DD",
  "receipt_number": "string",
  "items": [
    {
      "description": "string",
      "quantity": number,
      "unit_price": number,
      "total": number
    }
  ],
  "subtotal": number,
  "tax": number,
  "total": number,
  "currency": "USD",
  "notes": "string"
}
Return ONLY the JSON object, no extra text."""


def extract_receipt_data(image_bytes: bytes, mime_type: str) -> dict:
    """Send image to GPT-4o Vision and extract structured receipt data."""
    encoded = base64.b64encode(image_bytes).decode("utf-8")
    data_url = f"data:{mime_type};base64,{encoded}"

    response = _get_client().chat.completions.create(
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

    raw = response.choices[0].message.content.strip()
    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw)
