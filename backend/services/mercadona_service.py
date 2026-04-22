"""
Mercadona Tickets Portal — automated ticket lookup via Playwright.

Portal: https://www.portalcliente.mercadona.es/tickets/?lang=es&country=ES

Two flows:
  A. Tarjeta Bancaria — needs: date, amount, last 4 digits, store
  B. Efectivo         — needs: date, time range, amount, products, store, email

No login required! The tickets portal is public and not behind WAF.

Runs Playwright in a separate subprocess (mercadona_worker.py) to avoid
Windows asyncio event loop incompatibility inside uvicorn.
"""

import asyncio
import base64
import json
import logging
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)

logger = logging.getLogger(__name__)

WORKER_SCRIPT = Path(__file__).parent / "mercadona_worker.py"


async def request_mercadona_ticket(
    payment_method: str = "card",
    purchase_date: str | None = None,
    total_amount: str | None = None,
    card_last4: str | None = None,
    store_address: str | None = None,
    time_range: str | None = None,
    products_hint: str | None = None,
    email: str | None = None,
    headless: bool = True,
    timeout_ms: int = 30000,
) -> dict:
    """Run Playwright automation in a separate process and return result."""
    params = {
        "payment_method": payment_method,
        "purchase_date": purchase_date,
        "total_amount": total_amount,
        "card_last4": card_last4,
        "store_address": store_address,
        "time_range": time_range,
        "products_hint": products_hint,
        "email": email or os.getenv("MERCADONA_EMAIL", ""),
        "headless": headless,
        "timeout_ms": timeout_ms,
    }

    result = await asyncio.to_thread(_run_worker, params)

    # Convert base64 screenshots back to bytes for the router
    screenshots_bytes = []
    for s in result.get("screenshots", []):
        try:
            screenshots_bytes.append(base64.b64decode(s))
        except Exception:
            pass
    result["screenshots"] = screenshots_bytes

    # Convert pdf_bytes from base64 back to bytes
    if result.get("pdf_bytes"):
        result["pdf_bytes"] = base64.b64decode(result["pdf_bytes"])

    return result


def _run_worker(params: dict) -> dict:
    """Spawn mercadona_worker.py as a subprocess."""
    import subprocess

    try:
        proc = subprocess.run(
            [sys.executable, str(WORKER_SCRIPT)],
            input=json.dumps(params),
            capture_output=True,
            text=True,
            timeout=120,
            env={**os.environ},
        )

        if proc.returncode != 0:
            return {
                "success": False,
                "tickets_found": [],
                "pdf_bytes": None,
                "message": f"Worker error (rc={proc.returncode}): {proc.stderr[:500]}",
                "screenshots": [],
            }

        return json.loads(proc.stdout)

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "tickets_found": [],
            "pdf_bytes": None,
            "message": "Timeout: la automatización tardó más de 120 segundos.",
            "screenshots": [],
        }
    except json.JSONDecodeError as e:
        return {
            "success": False,
            "tickets_found": [],
            "pdf_bytes": None,
            "message": f"Error parsing worker output: {e}",
            "screenshots": [],
        }
    except Exception as e:
        return {
            "success": False,
            "tickets_found": [],
            "pdf_bytes": None,
            "message": f"Error launching worker: {e}",
            "screenshots": [],
        }
