"""
Shared webhook verification utilities for bot integrations.

Each integration platform (Slack, Discord, Telegram) uses a different mechanism
to verify that incoming webhook requests are authentic:

- **Slack**: HMAC-SHA256 signature using signing secret
  https://api.slack.com/authentication/verifying-requests-from-slack
- **Discord**: Ed25519 signature verification
  https://discord.com/developers/docs/interactions/overview#setting-up-an-endpoint
- **Telegram**: Secret token header or IP allowlisting
  https://core.telegram.org/bots/api#setwebhook

This module provides a common interface and utilities for webhook verification
so that each integration router can implement platform-specific logic consistently.
"""

import hashlib
import hmac
from typing import Optional

from fastapi import HTTPException, Request, status


async def get_raw_body(request: Request) -> bytes:
    """Read and return the raw request body.

    Many webhook verification schemes require signing the raw body bytes.
    This helper reads the body once and caches it for later use.

    Args:
        request: The incoming FastAPI request.

    Returns:
        The raw request body as bytes.
    """
    return await request.body()


def verify_hmac_sha256(
    *,
    body: bytes,
    secret: str,
    signature: str,
    timestamp: Optional[str] = None,
    version: str = "v0",
) -> bool:
    """Verify an HMAC-SHA256 signature against a request body.

    This is the pattern used by Slack and similar platforms. The signature
    is computed over a versioned string: ``{version}:{timestamp}:{body}``.

    Args:
        body: Raw request body bytes.
        secret: The platform-provided signing secret.
        signature: The signature from the request header to verify against.
        timestamp: Optional timestamp string included in the signed payload.
        version: Version prefix for the signed string (default "v0").

    Returns:
        True if the computed signature matches the provided signature.
    """
    if timestamp is not None:
        sig_basestring = f"{version}:{timestamp}:{body.decode('utf-8')}"
    else:
        sig_basestring = body.decode("utf-8")

    computed = (
        f"{version}="
        + hmac.new(
            secret.encode("utf-8"),
            sig_basestring.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
    )

    return hmac.compare_digest(computed, signature)


def raise_not_implemented(integration_name: str) -> None:
    """Raise a 501 Not Implemented response for a stub endpoint.

    Args:
        integration_name: Name of the integration (e.g. "Slack", "Discord").

    Raises:
        HTTPException: Always raises 501 Not Implemented.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=f"{integration_name} integration is not yet implemented.",
    )
