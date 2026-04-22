"""
Mercadona Playwright worker — runs as a separate process.

Receives parameters via JSON on stdin, outputs result JSON on stdout.
This avoids uvicorn's event loop incompatibility with Playwright on Windows.
"""

import asyncio
import base64
import json
import os
import sys
from pathlib import Path

TICKETS_URL = "https://www.portalcliente.mercadona.es/tickets/?lang=es&country=ES"


async def _fill_input(page, selector, value):
    """Fill a regular (non-readonly) input field."""
    el = page.locator(selector)
    if await el.count() == 0:
        return
    await el.click(force=True)
    await el.fill(value)


async def _select_date(page, selector, date_str):
    """Select a date via the Angular datepicker component.
    
    date_str should be DD/MM/YYYY format.
    Clicks the date input to open calendar, navigates to correct month, clicks day.
    """
    parts = date_str.split("/")
    if len(parts) != 3:
        return
    target_day = int(parts[0])
    target_month = int(parts[1])
    target_year = int(parts[2])
    
    # Month names in Spanish
    month_names = {
        1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
        5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
        9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
    }
    target_month_name = month_names[target_month]
    
    # Click to open datepicker
    await page.locator(selector).click()
    await page.wait_for_timeout(1000)
    
    # Navigate months backwards/forwards until we reach the target month/year
    for _ in range(24):  # max 2 years of navigation
        header = await page.locator(".m-datepicker-selector-divider").evaluate_all(
            """els => els.map(e => e.parentElement.textContent.trim())"""
        )
        header_text = header[0] if header else ""
        # Header looks like "Abril | 2026"
        if f"{target_month_name}" in header_text and str(target_year) in header_text:
            break
        # Need to go backwards (earlier date) — click left arrow
        await page.locator(".prev-double-arrow, m-icon.prev-double-arrow").first.click()
        await page.wait_for_timeout(300)
    
    # Click the target day — find cells that match and are in the current month
    # Day cells with class containing "current-month" or without "other-month"
    day_cells = page.locator(".m-datepicker-day-cell-container")
    count = await day_cells.count()
    
    # The calendar shows prev month days, current month days, and next month days
    # We need to find the right day in the current month
    # Strategy: collect all day texts and click the one matching target_day
    # Current month days are typically in the middle of the grid
    clicked = False
    for i in range(count):
        cell = day_cells.nth(i)
        text = (await cell.inner_text()).strip()
        if text == str(target_day):
            # Check if this cell is for the current month (not grayed out)
            classes = await cell.get_attribute("class") or ""
            if "disabled" not in classes and "other" not in classes:
                await cell.click()
                clicked = True
                break
    
    if not clicked:
        # Fallback: just click the first matching day number
        await page.locator(f".m-datepicker-day-cell-content:text-is('{target_day}')").first.click()
    
    await page.wait_for_timeout(500)


async def _select_store(page, selector, store_query):
    """Select a store via the Angular m-select autocomplete component.
    
    Clicks the store input to open dropdown, types in the search box, selects first result.
    """
    # Click to open the dropdown
    await page.locator(selector).click()
    await page.wait_for_timeout(1000)
    
    # Find and type in the search input inside the dropdown
    search_input = page.locator(".m-select-search-input")
    if await search_input.count() > 0:
        await search_input.click()
        await search_input.fill("")
        await search_input.type(store_query, delay=80)
        await page.wait_for_timeout(5000)  # Wait for API results
        
        # Check if results appeared
        no_results = page.locator(".m-select-no-results-option")
        if await no_results.count() > 0 and await no_results.is_visible():
            # No results — try shorter query
            short = store_query.split(",")[0].split(" ")[0]
            if short != store_query:
                await search_input.fill("")
                await search_input.type(short, delay=80)
                await page.wait_for_timeout(5000)
        
        # Click first result option
        option = page.locator("m-select-option").first
        if await option.count() > 0:
            await option.click(timeout=5000)
            await page.wait_for_timeout(500)
        else:
            # Close dropdown
            await page.keyboard.press("Escape")
    else:
        await page.keyboard.press("Escape")


async def _handle_card_flow(page, screenshots, purchase_date, total_amount, card_last4, store_address):
    """Handle Tarjeta Bancaria flow."""
    await page.click("button:has-text('Tarjeta Bancaria')", timeout=5000)
    await page.wait_for_timeout(3000)
    screenshots.append(await page.screenshot())

    # Fill regular fields first
    if total_amount:
        await _fill_input(page, "#m-input-0", total_amount)
    if card_last4:
        await _fill_input(page, "#m-input-1", card_last4)
    
    # Select date via datepicker
    if purchase_date:
        await _select_date(page, "#m-input-2", purchase_date)
    
    # Select store via autocomplete dropdown
    if store_address:
        await _select_store(page, "#m-input-3", store_address)

    screenshots.append(await page.screenshot())

    await page.click("button:has-text('Encontrar mi ticket')")
    await page.wait_for_timeout(5000)
    screenshots.append(await page.screenshot())

    return await _extract_results(page, screenshots)


async def _handle_cash_flow(page, screenshots, purchase_date, total_amount,
                            store_address, time_range, products_hint, email):
    """Handle Efectivo (cash) flow."""
    await page.click("button:has-text('Efectivo')", timeout=5000)
    await page.wait_for_timeout(3000)
    screenshots.append(await page.screenshot())

    # Fill regular fields first
    if total_amount:
        await _fill_input(page, "#m-input-0", total_amount)
    if products_hint:
        await _fill_input(page, "#m-input-1", products_hint)
    
    user_email = email or os.getenv("MERCADONA_EMAIL", "")
    if user_email:
        await _fill_input(page, "#m-input-2", user_email)

    # Select date via datepicker
    if purchase_date:
        await _select_date(page, "#m-input-3", purchase_date)

    # Time range selector
    if time_range:
        await page.click("#m-input-4")
        await page.wait_for_timeout(1000)
        try:
            option = page.locator(f"[role='option']:has-text('{time_range}')")
            if await option.count() > 0:
                await option.first.click()
                await page.wait_for_timeout(500)
        except Exception:
            await _fill_input(page, "#m-input-4", time_range)
    
    # Select store via autocomplete dropdown
    if store_address:
        await _select_store(page, "#m-input-5", store_address)

    screenshots.append(await page.screenshot())

    await page.click("button:has-text('Enviar solicitud de ticket')")
    await page.wait_for_timeout(5000)
    screenshots.append(await page.screenshot())

    return await _extract_results(page, screenshots)


async def _extract_results(page, screenshots):
    """Extract results from the tickets page after search/submit."""
    body_text = await page.evaluate("() => document.body.innerText")

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
            except Exception:
                pass

        screenshots.append(await page.screenshot())
        return {
            "success": True,
            "tickets_found": tickets,
            "pdf_bytes": base64.b64encode(pdf_bytes).decode() if pdf_bytes else None,
            "message": f"Ticket(s) encontrado(s): {len(tickets)}",
            "screenshots": [base64.b64encode(s).decode() for s in screenshots],
        }

    elif "no se han encontrado" in body_text.lower() or "no se han realizado" in body_text.lower():
        return {
            "success": False,
            "tickets_found": [],
            "pdf_bytes": None,
            "message": "No se encontraron tickets con los datos proporcionados.",
            "screenshots": [base64.b64encode(s).decode() for s in screenshots],
        }

    elif "solicitud" in body_text.lower() and "enviada" in body_text.lower():
        return {
            "success": True,
            "tickets_found": [],
            "pdf_bytes": None,
            "message": "Solicitud de ticket enviada. Recibirás el ticket por email.",
            "screenshots": [base64.b64encode(s).decode() for s in screenshots],
        }

    else:
        return {
            "success": False,
            "tickets_found": [],
            "pdf_bytes": None,
            "message": f"Estado desconocido. Texto: {body_text[:500]}",
            "screenshots": [base64.b64encode(s).decode() for s in screenshots],
        }


async def run(params):
    from playwright.async_api import async_playwright

    screenshots = []
    proxy = (
        os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY")
        or os.getenv("https_proxy") or os.getenv("http_proxy")
    )
    proxy_conf = {"server": proxy} if proxy else None

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=params.get("headless", True),
            args=[
                "--ignore-certificate-errors",
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
            ],
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
        page.set_default_timeout(params.get("timeout_ms", 30000))

        try:
            await page.goto(TICKETS_URL, wait_until="domcontentloaded")
            await page.wait_for_timeout(3000)

            try:
                await page.click("#btnCookies", timeout=3000)
                await page.wait_for_timeout(1000)
            except Exception:
                pass

            screenshots.append(await page.screenshot())

            if params.get("payment_method") == "card":
                return await _handle_card_flow(
                    page, screenshots,
                    params.get("purchase_date"),
                    params.get("total_amount"),
                    params.get("card_last4"),
                    params.get("store_address"),
                )
            else:
                return await _handle_cash_flow(
                    page, screenshots,
                    params.get("purchase_date"),
                    params.get("total_amount"),
                    params.get("store_address"),
                    params.get("time_range"),
                    params.get("products_hint"),
                    params.get("email"),
                )

        except Exception as e:
            try:
                screenshots.append(await page.screenshot())
            except Exception:
                pass
            return {
                "success": False,
                "tickets_found": [],
                "pdf_bytes": None,
                "message": f"Error en automatización del portal: {str(e)}",
                "screenshots": [base64.b64encode(s).decode() for s in screenshots],
            }
        finally:
            await browser.close()


if __name__ == "__main__":
    params = json.loads(sys.stdin.read())
    result = asyncio.run(run(params))
    sys.stdout.write(json.dumps(result))
