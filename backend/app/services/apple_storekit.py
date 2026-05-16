"""Apple StoreKit 2 JWS transaction verification.

Validates the JWS string sent from iOS (Transaction.jwsRepresentation) against
Apple's certificate chain. Without this verification a malicious client could
craft any JWS and grant itself a subscription server-side.

Verification steps:
1. Parse JWS header, extract the x5c cert chain (leaf, intermediate, root).
2. Confirm the root cert in the chain matches Apple Root CA - G3 by SHA-256
   fingerprint (defense in depth against PEM tampering).
3. Verify the cert chain signatures (root signs intermediate, intermediate
   signs leaf) and each cert's validity window.
4. Verify the JWS ES256 signature using the leaf cert's public key.
5. Validate payload claims: bundleId matches our app, signedDate within
   tolerance to limit replay window.

The caller is still responsible for de-duplicating by transactionId.
"""

import base64
import binascii
import json
import logging
import time
from datetime import datetime, timezone

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.ec import EllipticCurvePublicKey
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature
from cryptography.hazmat.primitives.hashes import HashAlgorithm

logger = logging.getLogger("normalaizer")

# Apple Root CA - G3 (valid until 2039-04-30).
# Source: https://www.apple.com/certificateauthority/AppleRootCA-G3.cer
# Verified by SHA-256 fingerprint below.
APPLE_ROOT_CA_G3_PEM = b"""-----BEGIN CERTIFICATE-----
MIICQzCCAcmgAwIBAgIILcX8iNLFS5UwCgYIKoZIzj0EAwMwZzEbMBkGA1UEAwwS
QXBwbGUgUm9vdCBDQSAtIEczMSYwJAYDVQQLDB1BcHBsZSBDZXJ0aWZpY2F0aW9u
IEF1dGhvcml0eTETMBEGA1UECgwKQXBwbGUgSW5jLjELMAkGA1UEBhMCVVMwHhcN
MTQwNDMwMTgxOTA2WhcNMzkwNDMwMTgxOTA2WjBnMRswGQYDVQQDDBJBcHBsZSBS
b290IENBIC0gRzMxJjAkBgNVBAsMHUFwcGxlIENlcnRpZmljYXRpb24gQXV0aG9y
aXR5MRMwEQYDVQQKDApBcHBsZSBJbmMuMQswCQYDVQQGEwJVUzB2MBAGByqGSM49
AgEGBSuBBAAiA2IABJjpLz1AcqTtkyJygRMc3RCV8cWjTnHcFBbZDuWmBSp3ZHtf
TjjTuxxEtX/1H7YyYl3J6YRbTzBPEVoA/VhYDKX1DyxNB0cTddqXl5dvMVztK517
IDvYuVTZXpmkOlEKMaNCMEAwHQYDVR0OBBYEFLuw3qFYM4iapIqZ3r6966/ayySr
MA8GA1UdEwEB/wQFMAMBAf8wDgYDVR0PAQH/BAQDAgEGMAoGCCqGSM49BAMDA2gA
MGUCMQCD6cHEFl4aXTQY2e3v9GwOAEZLuN+yRhHFD/3meoyhpmvOwgPUnPWTxnS4
at+qIxUCMG1mihDK1A3UT82NQz60imOlM27jbdoXt2QfyFMm+YhidDkLF1vLUagM
6BgD56KyKA==
-----END CERTIFICATE-----
"""

# SHA-256 fingerprint of Apple Root CA - G3 (uppercase hex, no separators).
APPLE_ROOT_CA_G3_SHA256 = (
    "63343ABFB89A6A03EBB57E9B3F5FA7BE7C4F5C756F3017B3A8C488C3653E9179"
)

# Allow a 10 minute skew between server clock and StoreKit signedDate.
_SIGNED_DATE_TOLERANCE_SECONDS = 600


class JWSVerificationError(Exception):
    """Raised when an Apple StoreKit JWS fails verification."""


def _b64url_decode(data: str) -> bytes:
    padding_needed = -len(data) % 4
    return base64.urlsafe_b64decode(data + ("=" * padding_needed))


def _load_apple_root() -> x509.Certificate:
    root = x509.load_pem_x509_certificate(APPLE_ROOT_CA_G3_PEM)
    fp = binascii.hexlify(root.fingerprint(hashes.SHA256())).decode().upper()
    if fp != APPLE_ROOT_CA_G3_SHA256:
        # Defensive: PEM constant was tampered with at build time.
        raise JWSVerificationError("Embedded Apple root CA fingerprint mismatch")
    return root


def _verify_cert_chain(
    leaf: x509.Certificate,
    intermediate: x509.Certificate,
    root: x509.Certificate,
) -> None:
    expected_root = _load_apple_root()
    if root.fingerprint(hashes.SHA256()) != expected_root.fingerprint(hashes.SHA256()):
        raise JWSVerificationError("JWS root cert is not Apple Root CA - G3")

    # Validity windows
    now = datetime.now(timezone.utc)
    for cert in (leaf, intermediate, root):
        if cert.not_valid_before_utc > now or cert.not_valid_after_utc < now:
            raise JWSVerificationError("Certificate in chain is expired or not yet valid")

    # Signature chain: root signs intermediate, intermediate signs leaf.
    # Apple's StoreKit chain is ECDSA top to bottom — narrow the union for type checkers
    # and to fail loudly if Apple ever rotates to a non-EC key.
    try:
        for parent, child in ((root, intermediate), (intermediate, leaf)):
            parent_key = parent.public_key()
            if not isinstance(parent_key, EllipticCurvePublicKey):
                raise JWSVerificationError("Non-EC key in Apple cert chain")
            hash_alg = child.signature_hash_algorithm
            if not isinstance(hash_alg, HashAlgorithm):
                raise JWSVerificationError("Cert in chain has no signature hash")
            parent_key.verify(
                child.signature,
                child.tbs_certificate_bytes,
                ec.ECDSA(hash_alg),
            )
    except JWSVerificationError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise JWSVerificationError(f"Certificate chain signature invalid: {exc}") from exc


def verify_jws(jws: str, expected_bundle_id: str) -> dict:
    """Verify an Apple StoreKit 2 JWS and return the validated payload claims.

    Raises JWSVerificationError on any failure. Never returns unverified data.
    """
    if not jws or not isinstance(jws, str):
        raise JWSVerificationError("Missing JWS")
    if not expected_bundle_id:
        # Refuse to run without a bundle ID configured — would be safe-by-default
        # but useless in production. Caller must provide one.
        raise JWSVerificationError("Server is not configured with apple_bundle_id")

    parts = jws.split(".")
    if len(parts) != 3:
        raise JWSVerificationError("Malformed JWS (expected 3 segments)")
    header_b64, payload_b64, sig_b64 = parts

    try:
        header = json.loads(_b64url_decode(header_b64))
    except Exception as exc:  # noqa: BLE001
        raise JWSVerificationError(f"Unable to decode JWS header: {exc}") from exc

    if header.get("alg") != "ES256":
        raise JWSVerificationError(f"Unexpected JWS alg: {header.get('alg')}")

    x5c = header.get("x5c")
    if not isinstance(x5c, list) or len(x5c) != 3:
        raise JWSVerificationError("JWS header missing 3-cert x5c chain")

    try:
        certs = [x509.load_der_x509_certificate(base64.b64decode(c)) for c in x5c]
    except Exception as exc:  # noqa: BLE001
        raise JWSVerificationError(f"Could not parse x5c certificates: {exc}") from exc

    leaf, intermediate, root = certs
    _verify_cert_chain(leaf, intermediate, root)

    # Verify the JWS signature with the leaf cert's public key.
    signing_input = f"{header_b64}.{payload_b64}".encode()
    raw_sig = _b64url_decode(sig_b64)
    if len(raw_sig) % 2 != 0:
        raise JWSVerificationError("Malformed JWS signature length")
    half = len(raw_sig) // 2
    r = int.from_bytes(raw_sig[:half], "big")
    s = int.from_bytes(raw_sig[half:], "big")
    der_sig = encode_dss_signature(r, s)

    leaf_key = leaf.public_key()
    if not isinstance(leaf_key, EllipticCurvePublicKey):
        raise JWSVerificationError("Leaf cert public key is not EC")
    try:
        leaf_key.verify(der_sig, signing_input, ec.ECDSA(hashes.SHA256()))
    except Exception as exc:  # noqa: BLE001
        raise JWSVerificationError(f"JWS signature does not verify: {exc}") from exc

    try:
        payload = json.loads(_b64url_decode(payload_b64))
    except Exception as exc:  # noqa: BLE001
        raise JWSVerificationError(f"Unable to decode JWS payload: {exc}") from exc

    if payload.get("bundleId") != expected_bundle_id:
        raise JWSVerificationError(
            f"bundleId mismatch: expected {expected_bundle_id!r}, "
            f"got {payload.get('bundleId')!r}"
        )

    signed_date_ms = payload.get("signedDate")
    if not isinstance(signed_date_ms, (int, float)):
        raise JWSVerificationError("Payload missing numeric signedDate")
    drift = abs(time.time() - (signed_date_ms / 1000))
    if drift > _SIGNED_DATE_TOLERANCE_SECONDS:
        raise JWSVerificationError(
            f"signedDate drift {drift:.0f}s exceeds tolerance"
        )

    return payload
