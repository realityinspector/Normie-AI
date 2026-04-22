"""End-to-end browser tests that would have caught the desktop layout bug.

Runs headless Chromium at desktop + tablet + mobile widths, signs up a fresh
user, and asserts:

- /app: main chat column is actually wide on desktop (not crammed into 192px).
- /translate: submit renders a visible translated result, and it's not the
  `[translation unavailable]` fallback.

Run against prod:
    python3 tests/e2e/test_web_desktop.py
Or a local server:
    BASE=http://localhost:8000 python3 tests/e2e/test_web_desktop.py
"""

import asyncio
import json
import os
import sys
import time
from playwright.async_api import async_playwright

BASE = os.environ.get("BASE", "https://normalizer-api-production.up.railway.app")
VIEWS = [
    ("desktop-1440", {"width": 1440, "height": 900}),
    ("tablet-1024", {"width": 1024, "height": 700}),
    ("mobile-390", {"width": 390, "height": 844}),
]


async def run_one(browser, label: str, viewport: dict) -> list[str]:
    failures: list[str] = []
    ctx = await browser.new_context(viewport=viewport)  # type: ignore[arg-type]
    page = await ctx.new_page()
    email = f"e2e-{label}-{int(time.time())}@test.dev"

    # Signup — sets the `session` cookie in the context.
    r = await page.request.post(
        f"{BASE}/auth/signup",
        data=json.dumps(
            {
                "email": email,
                "password": "Test12345!",
                "display_name": "E2EUser",
                "communication_style": "autistic",
            }
        ),
        headers={"Content-Type": "application/json"},
    )
    if r.status != 200:
        failures.append(f"[{label}] signup returned {r.status}")
        await ctx.close()
        return failures

    # /app — measure sidebar + main column widths
    await page.goto(f"{BASE}/app", wait_until="domcontentloaded")
    await page.wait_for_timeout(1500)
    dims = await page.evaluate(
        """() => ({
            vw: window.innerWidth,
            aside: document.querySelector('aside')?.getBoundingClientRect().width ?? null,
            main:  document.querySelector('main')?.getBoundingClientRect().width ?? null,
        })"""
    )
    if viewport["width"] >= 640:
        expected_min_main = viewport["width"] - 320  # sidebar + slack
        if (dims["main"] or 0) < expected_min_main:
            failures.append(
                f"[{label}] /app main column too narrow: {dims['main']}px "
                f"(expected >= {expected_min_main}px at viewport {viewport['width']}px). "
                f"dims={dims}"
            )

    # /app — chat flow: create room, send message, assert bubble renders.
    # The earlier bug was the message-bubble partial having two root <template>
    # elements inside an x-for, which Alpine silently drops so sent messages
    # never appeared on screen.
    if viewport["width"] >= 640:  # chat requires room creation; skip on phones for now
        errors_chat: list[str] = []
        page.once("pageerror", lambda e: errors_chat.append(f"pageerror: {e}"))
        alpine_warnings: list[str] = []

        def on_console(m):  # type: ignore[no-untyped-def]
            if "Alpine" in m.text and "single root element" in m.text:
                alpine_warnings.append(m.text)

        page.on("console", on_console)

        await page.goto(f"{BASE}/app", wait_until="domcontentloaded")
        await page.wait_for_timeout(1500)
        await page.click("button:has-text('Create Your First Room')")
        await page.wait_for_timeout(500)
        # Modal now visible — fill the name and submit the form.
        await page.locator("input[placeholder*='Team Chat']").fill("E2E Room")
        await page.locator("form button[type='submit']").first.click()
        await page.wait_for_timeout(2500)

        ta = page.locator("textarea").first
        if await ta.count() == 0:
            failures.append(f"[{label}] /app never entered the room (no textarea)")
        else:
            await ta.fill("Hello from E2E")
            await page.locator("form button[type='submit']").first.click()
            try:
                await page.wait_for_selector("text=Hello from E2E", timeout=15_000)
            except Exception:
                failures.append(
                    f"[{label}] sent message never rendered. "
                    f"Alpine warnings: {alpine_warnings}"
                )
            if alpine_warnings:
                failures.append(
                    f"[{label}] Alpine 'single root element' warning — "
                    f"message bubble partial regressed: {alpine_warnings}"
                )
            # Solo-in-room: server should send a preview translation so the
            # chat doesn't look dead. Assert the preview bubble appears.
            async def has_preview():
                return await page.evaluate(
                    "document.body.innerText.toLowerCase().includes('preview')"
                )
            preview_seen = False
            for _ in range(45):
                if await has_preview():
                    preview_seen = True
                    break
                await page.wait_for_timeout(1000)
            if not preview_seen:
                failures.append(
                    f"[{label}] solo-room preview bubble never appeared — "
                    "chat feels dead when alone in a room"
                )

    # /translate — submit and verify a real result appears
    await page.goto(f"{BASE}/translate", wait_until="domcontentloaded")
    await page.wait_for_timeout(1200)
    await page.fill("#input-text", "The deploy is broken. Fix now.")
    await page.click("button:has-text('Translate')")
    try:
        await page.wait_for_selector("text=Translated", timeout=60_000)
    except Exception:
        failures.append(f"[{label}] /translate result never rendered within 60s")
        await ctx.close()
        return failures
    translated = await page.locator("p.text-indigo-900").inner_text()
    if "translation unavailable" in translated.lower():
        failures.append(
            f"[{label}] /translate returned fallback text: {translated[:80]!r}"
        )
    elif len(translated.strip()) < 20:
        failures.append(
            f"[{label}] /translate result suspiciously short: {translated!r}"
        )

    await ctx.close()
    return failures


async def main() -> int:
    all_failures: list[str] = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        for label, vp in VIEWS:
            fs = await run_one(browser, label, vp)
            if fs:
                all_failures.extend(fs)
                print(f"[{label}] FAIL")
                for f in fs:
                    print(f"  {f}")
            else:
                print(f"[{label}] PASS")
        await browser.close()
    print(f"\n{'=' * 40}")
    if all_failures:
        print(f"FAILED ({len(all_failures)} assertion(s))")
        return 1
    print("ALL PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
