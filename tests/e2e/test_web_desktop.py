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
