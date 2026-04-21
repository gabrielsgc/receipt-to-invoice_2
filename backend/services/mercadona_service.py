"""
Mercadona Tickets Portal — automated ticket lookup via Playwright.

Portal: https://www.portalcliente.mercadona.es/tickets/?lang=es&country=ES

Two flows:
  A. Tarjeta Bancaria — needs: date, amount, last 4 digits, store
  B. Efectivo         — needs: date, time range, amount, products, store, email

No login required! The tickets portal is public and not behind WAF.
"""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)

logger = logging.getLogger(__name__)

TICKETS_URL = "https://www.portalcliente.mercadona.es/tickets/?lang=es&country=ES"


def _get_proxy_config() -> dict | None:
    """Get proxy config from environment."""
    proxy = (
        os.getenv("HTTPS_PROXY")
        or os.getenv("HTTP_PROXY")
        or os.getenv("https_proxy")
        or os.getenv("http_proxy")
    )
    if proxy:
        return {"server": proxy}
    return None


class MercadonaError(Exception):
    pass


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
    """
    Automate Mercadona tickets portal to find/request a purchase ticket.

    Args:
        payment_method: 'card' or 'cash'
        purchase_date: Date in DD/MM/YYYY format
        total_amount: Total amount (e.g. '45,32')
        card_last4: Last 4 digits of bank card (only for card payments)
        store_address: Store address/city/postal code for store lookup
        time_range: Time range of purchase (only for cash)
        products_hint: Product names hint (only for cash)
        email: Email for cash ticket request
        headless: Run browser without UI
        timeout_ms: Max wait per action in ms

    Returns:
        dict with success, tickets_found, message, screenshots
    """
    from playwright.async_api import async_playwright

    screenshots = []

    async with async_playwright() as p:
        launch_args = [
            "--ignore-certificate-errors",
            "--no-sandbox",
            "--disable-blink-features=AutomationControlled",
        ]
        proxy_conf = _get_proxy_config()
        browser = await p.chromium.launch(
            headless=headless,
            args=launch_args,
            proxy=proxy_conf,
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            locale="es-ES",
            ignore_https_errors=True,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )
        await context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        page = await context.new_page()
        page.set_default_timeout(timeout_ms)

        try:
            # Step 1: Navigate to tickets portal
            logger.info("Step 1: Navigating to Mercadona tickets portal...")
            await page.goto(TICKETS_URL, wait_until="domcontentloaded")
            await page.wait_for_timeout(3000)

            # Accept cookies if present
            try:
                await page.click("#btnCookies", timeout=3000)
                await page.wait_for_timeout(1000)
            except Exception:
                pass

            screenshots.append(await page.screenshot())

            if payment_method == "card":
                return await _handle_card_flow(
                    page, screenshots, purchase_date, total_amount,
                    card_last4, store_address,
                )
            else:
                return await _handle_cash_flow(
                    page, screenshots, purchase_date, total_amount,
                    store_address, time_range, products_hint, email,
                )

        except Exception as e:
            logger.error(f"Mercadona portal error: {e}")
            try:
                screenshots.append(await page.screenshot())
            except Exception:
                pass
            return {
                "success": False,
                "tickets_found": [],
                "message": f"Error en automatización del portal: {str(e)}",
                "screenshots": screenshots,
            }
        finally:
            await browser.close()


async def _handle_card_flow(
    page, screenshots, purchase_date, total_amount, card_last4, store_address,
) -> dict:
    """Handle Tarjeta Bancaria flow."""
    logger.info("Step 2: Selecting Tarjeta Bancaria...")
    await page.click("button:has-text('Tarjeta Bancaria')", timeout=5000)
    await page.wait_for_timeout(3000)
    screenshots.append(await page.screenshot())

    # Date: #m-input-2  (format: DD/MM/YYYY)
    if purchase_date:
        logger.info(f"Filling date: {purchase_date}")
        await page.fill("#m-input-2", purchase_date)

    # Amount: #m-input-0
    if total_amount:
        logger.info(f"Filling amount: {total_amount}")
        await page.fill("#m-input-0", total_amount)

    # Last 4 digits: #m-input-1
    if card_last4:
        logger.info(f"Filling card last 4: {card_last4}")
        await page.fill("#m-input-1", card_last4)

    # Store: #m-input-3
    if store_address:
        logger.info(f"Filling store: {store_address}")
        await page.fill("#m-input-3", store_address)
        await page.wait_for_timeout(2000)
        try:
            suggestion = page.locator("[role='option'], .suggestion, li").first
            if await suggestion.count() > 0:
                await suggestion.click(timeout=3000)
                await page.wait_for_timeout(1000)
        except Exception:
            pass

    screenshots.append(await page.screenshot())

    # Submit
    logger.info("Step 3: Submitting search...")
    await page.click("button:has-text('Encontrar mi ticket')")
    await page.wait_for_timeout(5000)
    screenshots.append(await page.screenshot())

    return await _extract_results(page, screenshots)


async def _handle_cash_flow(
    page, screenshots, purchase_date, total_amount,
    store_address, time_range, products_hint, email,
) -> dict:
    """Handle Efectivo (cash) flow."""
    logger.info("Step 2: Selecting Efectivo...")
    await page.click("button:has-text('Efectivo')", timeout=5000)
    await page.wait_for_timeout(3000)
    screenshots.append(await page.screenshot())

    # Date: #m-input-3
    if purchase_date:
        await page.fill("#m-input-3", purchase_date)

    # Time range: #m-input-4 (dropdown)
    if time_range:
        await page.click("#m-input-4")
        await page.wait_for_timeout(1000)
        try:
            option = page.locator(f"[role='option']:has-text('{time_range}')")
            if await option.count() > 0:
                await option.first.click()
                await page.wait_for_timeout(500)
        except Exception:
            await page.fill("#m-input-4", time_range)

    # Amount: #m-input-0
    if total_amount:
        await page.fill("#m-input-0", total_amount)

    # Products hint: #m-input-1 (textarea)
    if products_hint:
        await page.fill("#m-input-1", products_hint)

    # Store: #m-input-5
    if store_address:
        await page.fill("#m-input-5", store_address)
        await page.wait_for_timeout(2000)
        try:
            suggestion = page.locator("[role='option'], .suggestion, li").first
            if await suggestion.count() > 0:
                await suggestion.click(timeout=3000)
                await page.wait_for_timeout(1000)
        except Exception:
            pass

    # Email: #m-input-2
    user_email = email or os.getenv("MERCADONA_EMAIL", "")
    if user_email:
        await page.fill("#m-input-2", user_email)

    screenshots.append(await page.screenshot())

    # Submit
    logger.info("Step 3: Submitting request...")
    await page.click("button:has-text('Enviar solicitud de ticket')")
    await page.wait_for_timeout(5000)
    screenshots.append(await page.screenshot())

    return await _extract_results(page, screenshots)


async def _extract_results(page, screenshots) -> dict:
    """Extract results from the tickets page after search/submit."""
    body_text = await page.evaluate("() => document.body.innerText")

    # Check for success indicators
    if any(w in body_text.lower() for w in ["ticket encontrado", "descargar", "enviar por correo", "resultado"]):
        download_btns = await page.locator(
            "button:has-text('Descargar'), a:has-text('Descargar'), "
            "button:has-text('Enviar'), button:has-text('PDF')"
        ).all()

        tickets = []
        for i, btn in enumerate(download_btns):
            try:
                text = await btn.inner_text()
                tickets.append({"index": i, "action": text.strip()})
            except Exception:
                pass

        pdf_bytes = None
        if download_btns:
            try:
                async with page.expect_download(timeout=10000) as dl_info:
                    await download_btns[0].click()
                download = await dl_info.value
                path = await download.path()
                if path:
                    pdf_bytes = Path(path).read_bytes()
            except Exception as e:
                logger.info(f"Download attempt: {e}")

        screenshots.append(await page.screenshot())
        return {
            "success": True,
            "tickets_found": tickets,
            "pdf_bytes": pdf_bytes,
            "message": f"Ticket(s) encontrado(s): {len(tickets)}",
            "screenshots": screenshots,
        }

    elif "no se han encontrado" in body_text.lower() or "no se han realizado" in body_text.lower():
        return {
            "success": False,
            "tickets_found": [],
            "pdf_bytes": None,
            "message": "No se encontraron tickets con los datos proporcionados.",
            "screenshots": screenshots,
        }

    elif "solicitud" in body_text.lower() and "enviada" in body_text.lower():
        return {
            "success": True,
            "tickets_found": [],
            "pdf_bytes": None,
            "message": "Solicitud de ticket enviada. Recibirás el ticket por email.",
            "screenshots": screenshots,
        }

    else:
        return {
            "success": False,
            "tickets_found": [],
            "pdf_bytes": None,
            "message": f"Estado desconocido. Texto: {body_text[:500]}",
            "screenshots": screenshots,
        }
