"""End-to-end coverage for MVP gates the layout test doesn't cover.

Asserts:
- Gate 1 (auth): email/password signup returns a token; login round-trip works.
- Gate 4 (transcripts): /t/{slug} renders with og:title/og:description/og:image
  meta tags pointing at the right values.
- Gate 5 (rooms): /r/{room_id}/invite renders with og:title mentioning the
  room and og:image set.
- Gate 7 (developer API): a freshly created key authenticates against
  POST /api/v1/translate and GET /api/v1/usage.

Run:
    python3 tests/e2e/test_mvp_gates.py
Or against a different base:
    BASE=http://localhost:8000 python3 tests/e2e/test_mvp_gates.py
"""

import asyncio
import os
import sys
import time
import uuid

import httpx

BASE = os.environ.get("BASE", "https://normalizer-api-production.up.railway.app").rstrip("/")


def _fresh_email() -> str:
    return f"e2e-{int(time.time() * 1000)}-{uuid.uuid4().hex[:6]}@example.com"


async def _signup(client: httpx.AsyncClient, *, style: str = "neurotypical") -> tuple[str, str]:
    email = _fresh_email()
    password = "e2e-password-1234"
    r = await client.post(
        "/auth/signup",
        json={
            "email": email,
            "password": password,
            "display_name": "E2E User",
            "communication_style": style,
        },
    )
    r.raise_for_status()
    return email, r.json()["access_token"]


async def gate_1_auth(client: httpx.AsyncClient) -> list[str]:
    fails: list[str] = []
    try:
        email, signup_token = await _signup(client)
    except httpx.HTTPError as exc:
        return [f"gate1: signup failed: {exc}"]
    if not signup_token:
        fails.append("gate1: signup returned empty token")

    # Login round-trip with the same credentials
    r = await client.post(
        "/auth/login",
        json={"email": email, "password": "e2e-password-1234"},
    )
    if r.status_code != 200:
        fails.append(f"gate1: login returned {r.status_code}: {r.text[:120]}")
    elif not r.json().get("access_token"):
        fails.append("gate1: login returned no access_token")

    # Bad input should be 4xx not 5xx
    r_bad = await client.post(
        "/auth/login",
        json={"email": email, "password": "wrong-password"},
    )
    if r_bad.status_code >= 500:
        fails.append(f"gate1: bad-password login returned {r_bad.status_code} (expected 4xx)")
    return fails


async def gate_4_transcript_og(client: httpx.AsyncClient) -> list[str]:
    fails: list[str] = []
    try:
        _, token = await _signup(client)
    except httpx.HTTPError as exc:
        return [f"gate4: signup failed: {exc}"]
    auth = {"Authorization": f"Bearer {token}"}

    # Create a room so we can attach a transcript to it
    r = await client.post(
        "/rooms",
        json={"name": "E2E Transcript Room", "is_public": True},
        headers=auth,
    )
    if r.status_code != 201:
        return [f"gate4: room create failed: {r.status_code} {r.text[:120]}"]
    room_id = r.json()["id"]

    r = await client.post(
        "/transcripts",
        json={"room_id": room_id, "title": "E2E Transcript"},
        headers=auth,
    )
    if r.status_code not in (200, 201):
        return [f"gate4: transcript create failed: {r.status_code} {r.text[:120]}"]
    slug = r.json().get("slug")
    if not slug:
        return ["gate4: transcript response missing slug"]

    r = await client.get(f"/t/{slug}")
    if r.status_code != 200:
        return [f"gate4: /t/{slug} returned {r.status_code}"]
    html = r.text.lower()
    for needle in ('property="og:title"', 'property="og:description"', 'property="og:image"', 'property="og:url"'):
        if needle not in html:
            fails.append(f"gate4: /t/{{slug}} missing meta {needle}")
    if slug.lower() not in r.text.lower():
        # OG URL should reference the slug
        fails.append("gate4: /t/{slug} HTML doesn't reference the slug")
    return fails


async def gate_5_room_invite_og(client: httpx.AsyncClient) -> list[str]:
    fails: list[str] = []
    try:
        _, token = await _signup(client)
    except httpx.HTTPError as exc:
        return [f"gate5: signup failed: {exc}"]
    auth = {"Authorization": f"Bearer {token}"}

    r = await client.post(
        "/rooms",
        json={"name": "E2E Invite Room", "is_public": True},
        headers=auth,
    )
    if r.status_code != 201:
        return [f"gate5: room create failed: {r.status_code} {r.text[:120]}"]
    room_id = r.json()["id"]

    r = await client.get(f"/r/{room_id}/invite")
    if r.status_code != 200:
        return [f"gate5: /r/{room_id}/invite returned {r.status_code}"]
    html = r.text.lower()
    for needle in ('property="og:title"', 'property="og:description"', 'property="og:image"'):
        if needle not in html:
            fails.append(f"gate5: /r/{{id}}/invite missing meta {needle}")
    if "e2e invite room" not in html:
        fails.append("gate5: /r/{id}/invite HTML doesn't mention room name")
    return fails


async def gate_7_developer_api(client: httpx.AsyncClient) -> list[str]:
    fails: list[str] = []
    try:
        _, token = await _signup(client)
    except httpx.HTTPError as exc:
        return [f"gate7: signup failed: {exc}"]
    auth = {"Authorization": f"Bearer {token}"}

    r = await client.post(
        "/api/v1/keys",
        json={"name": "e2e-key", "rate_limit": 100},
        headers=auth,
    )
    if r.status_code not in (200, 201):
        return [f"gate7: key create failed: {r.status_code} {r.text[:120]}"]
    api_key = r.json().get("key") or r.json().get("api_key")
    if not api_key:
        return [f"gate7: key create response missing 'key' field: {r.text[:160]}"]

    headers = {"X-API-Key": api_key}
    r = await client.post(
        "/api/v1/translate",
        json={"text": "hello", "direction": "neurotypical_to_autistic"},
        headers=headers,
    )
    if r.status_code != 200:
        fails.append(f"gate7: /api/v1/translate with key returned {r.status_code}: {r.text[:160]}")
    else:
        body = r.json()
        if not body.get("translated_text"):
            fails.append("gate7: /api/v1/translate response missing translated_text")

    r = await client.get("/api/v1/usage", headers=headers)
    if r.status_code != 200:
        fails.append(f"gate7: /api/v1/usage returned {r.status_code}: {r.text[:160]}")

    # No key → 401, not 500
    r = await client.post(
        "/api/v1/translate",
        json={"text": "hello", "direction": "neurotypical_to_autistic"},
    )
    if r.status_code >= 500:
        fails.append(f"gate7: missing-key request returned {r.status_code} (expected 4xx)")
    return fails


async def main() -> int:
    suites = [
        ("gate 1 (auth)", gate_1_auth),
        ("gate 4 (transcript OG)", gate_4_transcript_og),
        ("gate 5 (room invite OG)", gate_5_room_invite_og),
        ("gate 7 (developer API)", gate_7_developer_api),
    ]
    all_fails: list[str] = []
    async with httpx.AsyncClient(base_url=BASE, timeout=30.0, follow_redirects=False) as client:
        for label, suite in suites:
            try:
                fails = await suite(client)
            except Exception as exc:  # noqa: BLE001
                fails = [f"{label}: uncaught exception: {exc}"]
            if fails:
                print(f"[{label}] FAIL")
                for f in fails:
                    print(f"  {f}")
                all_fails.extend(fails)
            else:
                print(f"[{label}] PASS")
    print("\n" + "=" * 40)
    if all_fails:
        print(f"FAILED ({len(all_fails)} assertion(s))")
        return 1
    print("ALL PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
