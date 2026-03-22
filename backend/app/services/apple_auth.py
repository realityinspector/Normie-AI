import jwt
from jwt import PyJWKClient
from app.config import get_settings

APPLE_KEYS_URL = "https://appleid.apple.com/auth/keys"
APPLE_ISSUER = "https://appleid.apple.com"

_jwk_client = PyJWKClient(APPLE_KEYS_URL, cache_keys=True)


async def verify_apple_identity_token(identity_token: str) -> dict:
    """Verify an Apple Sign-In identity token and return claims.

    Returns dict with 'sub' (Apple user ID), 'email', etc.
    """
    settings = get_settings()

    signing_key = _jwk_client.get_signing_key_from_jwt(identity_token)

    claims = jwt.decode(
        identity_token,
        signing_key.key,
        algorithms=["RS256"],
        audience=settings.apple_bundle_id,
        issuer=APPLE_ISSUER,
    )

    return claims
