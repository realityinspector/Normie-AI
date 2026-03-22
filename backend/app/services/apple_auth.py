import logging

import jwt
from jwt import PyJWKClient, PyJWKClientConnectionError, PyJWKClientError
from app.config import get_settings

logger = logging.getLogger(__name__)

APPLE_KEYS_URL = "https://appleid.apple.com/auth/keys"
APPLE_ISSUER = "https://appleid.apple.com"

_jwk_client = PyJWKClient(APPLE_KEYS_URL, cache_keys=True, timeout=10)


async def verify_apple_identity_token(identity_token: str) -> dict:
    """Verify an Apple Sign-In identity token and return claims.

    Returns dict with 'sub' (Apple user ID), 'email', etc.
    Raises an exception with a clear error message on timeout or connection failure.
    """
    settings = get_settings()

    try:
        signing_key = _jwk_client.get_signing_key_from_jwt(identity_token)
    except (PyJWKClientConnectionError, PyJWKClientError) as exc:
        logger.error("Failed to fetch Apple signing keys: %s", str(exc))
        raise RuntimeError(
            "Apple sign-in temporarily unavailable: could not verify signing keys"
        ) from exc
    except Exception as exc:
        logger.error("Unexpected error fetching Apple signing keys: %s", str(exc))
        raise RuntimeError(
            "Apple sign-in temporarily unavailable"
        ) from exc

    claims = jwt.decode(
        identity_token,
        signing_key.key,
        algorithms=["RS256"],
        audience=settings.apple_bundle_id,
        issuer=APPLE_ISSUER,
    )

    return claims
