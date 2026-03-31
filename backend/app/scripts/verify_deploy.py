"""Deploy verifier agent.

Validates a Railway deployment has all expected content.

Usage:
    python -m app.scripts.verify_deploy --url https://normalizer-api-production.up.railway.app
"""

import asyncio
import argparse
import os
import sys

import httpx


async def verify(base_url: str):
    results = []

    async with httpx.AsyncClient(timeout=15, follow_redirects=False) as client:
        checks = [
            ("/health", 200, "ok", "Health endpoint"),
            ("/", 200, "NORMALAIZER", "Landing page"),
            ("/signup", 200, "account", "Signup page"),
            ("/login", 200, "Sign in", "Login page"),
            ("/pricing", 200, "ricing", "Pricing page"),
        ]

        for path, expected_status, expected_text, name in checks:
            try:
                r = await client.get(f"{base_url}{path}")
                status_ok = r.status_code == expected_status
                content_ok = expected_text.lower() in r.text.lower()
                ok = status_ok and content_ok
                detail = f"{r.status_code}, {'has' if content_ok else 'missing'} '{expected_text}'"
                results.append((name, ok, detail))
            except Exception as e:
                results.append((name, False, str(e)))

        # Static file checks
        static_checks = [
            ("/static/js/auth.js?v=2", "credentials", "auth.js (credentials:include)"),
            ("/static/js/chat.js?v=2", "chatApp", "chat.js (chatApp function)"),
            ("/static/css/app.css?v=2", "", "app.css (loads)"),
        ]
        for path, expected_text, name in static_checks:
            try:
                r = await client.get(f"{base_url}{path}")
                ok = r.status_code == 200
                if expected_text:
                    ok = ok and expected_text in r.text
                size = len(r.content)
                results.append((name, ok, f"{r.status_code}, {size} bytes"))

                # Compare with local file if available
                local_path = os.path.join(
                    "app", "static", path.split("/static/")[1].split("?")[0]
                )
                if os.path.exists(local_path):
                    local_size = os.path.getsize(local_path)
                    if abs(size - local_size) > 100:
                        results.append(
                            (
                                f"{name} size match",
                                False,
                                f"remote={size} local={local_size}",
                            )
                        )
                    else:
                        results.append(
                            (
                                f"{name} size match",
                                True,
                                f"remote={size} local={local_size}",
                            )
                        )
            except Exception as e:
                results.append((name, False, str(e)))

        # 404 page check
        try:
            r = await client.get(
                f"{base_url}/nonexistent-12345", headers={"accept": "text/html"}
            )
            ok = r.status_code == 404 and "<html" in r.text.lower()
            results.append(("Styled 404 page", ok, r.status_code))
        except Exception as e:
            results.append(("Styled 404 page", False, str(e)))

    # Print results
    print(f"\nDeploy verification for {base_url}:\n")
    all_pass = True
    for name, passed, detail in results:
        status = "PASS" if passed else "FAIL"
        if not passed:
            all_pass = False
        print(f"  [{status}] {name} ({detail})")

    print(f"\n{'DEPLOY VERIFIED' if all_pass else 'DEPLOY VERIFICATION FAILED'}")
    return 0 if all_pass else 1


def main():
    parser = argparse.ArgumentParser(description="Verify a Railway deployment")
    parser.add_argument("--url", required=True, help="Deployment URL to verify")
    args = parser.parse_args()
    sys.exit(asyncio.run(verify(base_url=args.url.rstrip("/"))))


if __name__ == "__main__":
    main()
