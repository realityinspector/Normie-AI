"""Transactional email delivery via the Resend HTTP API.

Resend is used over SMTP because it needs nothing more than an API key and a
verified sender domain — no SMTP credentials, no port juggling. If the API
key is not configured the service raises EmailNotConfigured so callers can
return a clean 503 instead of silently dropping the message.
"""

from __future__ import annotations

import logging

import httpx

from app.config import get_settings

logger = logging.getLogger("normalaizer")

_RESEND_URL = "https://api.resend.com/emails"


class EmailNotConfigured(Exception):
    """Email provider credentials are missing."""


class EmailSendError(Exception):
    """The email provider rejected or failed to deliver the message."""


async def send_email(*, to: str, subject: str, html: str, text: str) -> None:
    settings = get_settings()
    if not settings.resend_api_key or not settings.resend_from_email:
        raise EmailNotConfigured(
            "RESEND_API_KEY and RESEND_FROM_EMAIL must be set to send email"
        )

    payload = {
        "from": settings.resend_from_email,
        "to": [to],
        "subject": subject,
        "html": html,
        "text": text,
    }
    headers = {
        "Authorization": f"Bearer {settings.resend_api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            r = await client.post(_RESEND_URL, json=payload, headers=headers)
        except httpx.HTTPError as exc:
            raise EmailSendError(f"Resend HTTP error: {exc}") from exc

    if r.status_code >= 400:
        # Don't leak the API response body to callers, but log it.
        logger.error(
            "Resend rejected email: status=%s body=%s to=%s",
            r.status_code,
            r.text[:500],
            to,
        )
        raise EmailSendError(f"Resend returned status {r.status_code}")


async def send_password_reset(*, to: str, reset_url: str) -> None:
    subject = "Reset your NORMALAIZER password"
    text = (
        "Someone requested a password reset for your NORMALAIZER account.\n\n"
        f"Reset link (valid for 1 hour):\n{reset_url}\n\n"
        "If you didn't request this, you can safely ignore this email."
    )
    html = (
        "<div style=\"font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;"
        "max-width:480px;margin:0 auto;padding:24px;color:#111\">"
        "<h2 style=\"margin:0 0 16px;font-size:18px\">Reset your password</h2>"
        "<p style=\"font-size:14px;line-height:1.5;color:#444\">"
        "Someone requested a password reset for your NORMALAIZER account. "
        "Use the button below to choose a new password — the link expires in one hour."
        "</p>"
        f"<p style=\"margin:24px 0\"><a href=\"{reset_url}\" "
        "style=\"display:inline-block;background:#4f46e5;color:#fff;text-decoration:none;"
        "padding:10px 18px;border-radius:8px;font-weight:600;font-size:14px\">"
        "Reset password</a></p>"
        "<p style=\"font-size:12px;color:#888\">"
        "If you didn't request this, you can safely ignore this email."
        "</p></div>"
    )
    await send_email(to=to, subject=subject, html=html, text=text)
