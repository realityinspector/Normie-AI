"""Synthetic auth prober agent.

Tests the full signup-login-access flow against a live deployment.

Usage:
    python -m app.scripts.probe_auth --url https://normalizer-api-production.up.railway.app
"""

import asyncio
import argparse
import sys

import httpx


async def probe(base_url: str):
    results = []
    token = None

    async with httpx.AsyncClient(timeout=15, follow_redirects=False) as client:
        # Step 1: Health check
        try:
            r = await client.get(f"{base_url}/health")
            ok = r.status_code == 200 and r.json().get("status") == "ok"
            results.append(("Health check", ok, r.status_code))
        except Exception as e:
            results.append(("Health check", False, str(e)))

        # Step 2: Dev auth (create test user)
        try:
            r = await client.post(
                f"{base_url}/auth/dev",
                json={"name": "Probe Agent", "communication_style": "autistic"},
            )
            if r.status_code == 200:
                token = r.json().get("access_token")
                has_cookie = any(
                    "session" in c for c in r.headers.get_list("set-cookie")
                )
                results.append(("Dev auth + token", bool(token), r.status_code))
                results.append(
                    (
                        "Set-Cookie header",
                        has_cookie,
                        "present" if has_cookie else "missing",
                    )
                )
            elif r.status_code == 404:
                results.append(
                    (
                        "Dev auth",
                        False,
                        "DEV_AUTH_ENABLED=false (expected in prod)",
                    )
                )
            else:
                results.append(("Dev auth", False, r.status_code))
        except Exception as e:
            results.append(("Dev auth", False, str(e)))

        # Step 3: Access /app with token
        if token:
            try:
                r = await client.get(f"{base_url}/app", cookies={"session": token})
                ok = r.status_code == 200
                results.append(("GET /app with session", ok, r.status_code))
            except Exception as e:
                results.append(("GET /app with session", False, str(e)))

        # Step 4: Access /app without token (should redirect)
        try:
            r = await client.get(f"{base_url}/app")
            ok = r.status_code in (302, 307) and "/login" in r.headers.get(
                "location", ""
            )
            results.append(("GET /app no auth -> redirect", ok, r.status_code))
        except Exception as e:
            results.append(("GET /app no auth -> redirect", False, str(e)))

        # Step 5: Static file freshness
        try:
            r = await client.get(f"{base_url}/static/js/auth.js?v=2")
            has_credentials = "credentials" in r.text
            results.append(
                (
                    "auth.js has credentials:include",
                    has_credentials,
                    f"{len(r.content)} bytes",
                )
            )
        except Exception as e:
            results.append(("auth.js freshness", False, str(e)))

        # Step 6: Pages render
        for page, expected in [
            ("/", "NORMALAIZER"),
            ("/signup", "account"),
            ("/pricing", "ricing"),
        ]:
            try:
                r = await client.get(f"{base_url}{page}")
                ok = r.status_code == 200 and expected.lower() in r.text.lower()
                results.append((f"GET {page} renders", ok, r.status_code))
            except Exception as e:
                results.append((f"GET {page}", False, str(e)))

        # Step 7: 404 returns HTML
        try:
            r = await client.get(
                f"{base_url}/nonexistent-page-12345",
                headers={"accept": "text/html"},
            )
            ok = r.status_code == 404 and "<html" in r.text.lower()
            results.append(("404 returns HTML", ok, r.status_code))
        except Exception as e:
            results.append(("404 page", False, str(e)))

    # Print results
    print(f"\nProbe results for {base_url}:\n")
    all_pass = True
    for name, passed, detail in results:
        status = "PASS" if passed else "FAIL"
        if not passed:
            all_pass = False
        print(f"  [{status}] {name} ({detail})")

    print(f"\n{'ALL CHECKS PASSED' if all_pass else 'SOME CHECKS FAILED'}")
    return 0 if all_pass else 1


def main():
    parser = argparse.ArgumentParser(
        description="Probe auth flow against a live deployment"
    )
    parser.add_argument("--url", required=True, help="Base URL to probe")
    args = parser.parse_args()
    sys.exit(asyncio.run(probe(base_url=args.url.rstrip("/"))))


if __name__ == "__main__":
    main()
