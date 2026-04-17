"""Ed25519 receipt signing and verification."""
import base64
import json
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat, PrivateFormat, NoEncryption
from cryptography.exceptions import InvalidSignature


def generate_keypair() -> tuple[bytes, bytes]:
    """Generate an Ed25519 keypair, returning (private_key_bytes, public_key_bytes)."""
    private_key = Ed25519PrivateKey.generate()
    private_bytes = private_key.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())
    public_bytes = private_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    return private_bytes, public_bytes


def _canonical_bytes(data: dict) -> bytes:
    """Produce stable UTF-8 bytes from a dict for signing."""
    return json.dumps(data, sort_keys=True, default=str).encode("utf-8")


def sign_receipt(receipt_data: dict, private_key_bytes: bytes) -> bytes:
    """Sign a receipt dict with Ed25519, returning the signature bytes."""
    private_key = Ed25519PrivateKey.from_private_bytes(private_key_bytes)
    message = _canonical_bytes(receipt_data)
    return private_key.sign(message)


def verify_receipt(receipt_data: dict, signature_bytes: bytes, public_key_bytes: bytes) -> bool:
    """Verify an Ed25519 signature over a receipt dict. Returns True if valid."""
    public_key = Ed25519PublicKey.from_public_bytes(public_key_bytes)
    message = _canonical_bytes(receipt_data)
    try:
        public_key.verify(signature_bytes, message)
        return True
    except InvalidSignature:
        return False
