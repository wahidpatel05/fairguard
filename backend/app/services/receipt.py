"""Ed25519 receipt signing service using PyNaCl."""
from __future__ import annotations

import base64
import hashlib
import json
import logging
import pathlib
from datetime import datetime, timezone
from uuid import UUID

import nacl.encoding
import nacl.exceptions
import nacl.signing
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings

logger = logging.getLogger(__name__)


class ReceiptService:
    """Service for creating and verifying tamper-evident audit receipts."""

    def __init__(self, key_path: str) -> None:
        self.key_path = pathlib.Path(key_path)
        self._signing_key: nacl.signing.SigningKey | None = None
        self._verify_key: nacl.signing.VerifyKey | None = None

    def initialize(self) -> None:
        """Load existing Ed25519 key or generate a new keypair.

        If key_path exists, load the SigningKey from raw 32 bytes.
        Otherwise generate a new key, create parent directories, and persist it.
        Logs the public-key fingerprint (base64url) on startup.
        """
        if self.key_path.exists():
            raw_bytes = self.key_path.read_bytes()
            self._signing_key = nacl.signing.SigningKey(raw_bytes)
        else:
            self._signing_key = nacl.signing.SigningKey.generate()
            self.key_path.parent.mkdir(parents=True, exist_ok=True)
            self.key_path.write_bytes(bytes(self._signing_key))

        self._verify_key = self._signing_key.verify_key
        fingerprint = (
            base64.urlsafe_b64encode(bytes(self._verify_key)).rstrip(b"=").decode()
        )
        logger.info("Signing key initialized. Public key fingerprint: %s", fingerprint)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_canonical_payload(self, data: dict) -> bytes:
        """Return canonical UTF-8 JSON bytes suitable for signing.

        Keys are sorted recursively; output has no whitespace.
        """

        def _sort(obj: object) -> object:
            if isinstance(obj, dict):
                return {k: _sort(obj[k]) for k in sorted(obj.keys())}
            if isinstance(obj, list):
                return [_sort(item) for item in obj]
            return obj

        return json.dumps(_sort(data), separators=(",", ":"), default=str).encode(
            "utf-8"
        )

    @staticmethod
    def _b64url_encode(data: bytes) -> str:
        """Encode bytes as unpadded base64url string."""
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

    @staticmethod
    def _b64url_decode(s: str) -> bytes:
        """Decode an unpadded base64url string to bytes."""
        padding = "=" * (-len(s) % 4)
        return base64.urlsafe_b64decode(s + padding)

    # ------------------------------------------------------------------
    # Signing / verification
    # ------------------------------------------------------------------

    def create_receipt_signature(
        self, payload_dict: dict
    ) -> tuple[str, str, str]:
        """Sign canonical payload with Ed25519.

        Returns:
            (signed_payload_b64, signature_b64, public_key_b64) all base64url-encoded.
            signed_payload_b64: base64url of canonical JSON bytes
            signature_b64: base64url of 64-byte Ed25519 signature
            public_key_b64: base64url of 32-byte verify key
        """
        if self._signing_key is None:
            raise RuntimeError(
                "ReceiptService not initialized. Call initialize() first."
            )

        canonical_bytes = self._get_canonical_payload(payload_dict)
        signed = self._signing_key.sign(canonical_bytes)

        signed_payload_b64 = self._b64url_encode(canonical_bytes)
        signature_b64 = self._b64url_encode(signed.signature)
        public_key_b64 = self._b64url_encode(bytes(self._verify_key))

        return signed_payload_b64, signature_b64, public_key_b64

    def verify_signature(
        self,
        signed_payload_b64: str,
        signature_b64: str,
        public_key_b64: str,
    ) -> bool:
        """Verify an Ed25519 signature over a stored payload.

        Decodes all three arguments from base64url, then calls
        VerifyKey.verify(message, signature).

        Returns:
            True if the signature is valid, False otherwise.
        """
        try:
            message_bytes = self._b64url_decode(signed_payload_b64)
            signature_bytes = self._b64url_decode(signature_b64)
            public_key_bytes = self._b64url_decode(public_key_b64)

            vk = nacl.signing.VerifyKey(public_key_bytes)
            vk.verify(message_bytes, signature_bytes)
            return True
        except nacl.exceptions.BadSignatureError:
            return False
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Database operations
    # ------------------------------------------------------------------

    async def create_receipt(
        self,
        db: AsyncSession,
        audit_id: UUID,
        project_id: UUID,
        dataset_hash: str,
        contract_version: int,
        contracts_summary: list[dict],
        metrics_summary: dict,
        verdict: str,
    ) -> "FairnessReceipt":
        """Create and sign a tamper-evident receipt for an audit.

        Builds the canonical payload, signs it, persists a FairnessReceipt
        record, and returns the saved ORM object.
        """
        from app.models.receipt import FairnessReceipt  # avoid circular import

        # Build payload
        metrics_bytes = json.dumps(
            metrics_summary, sort_keys=True, default=str
        ).encode("utf-8")
        metrics_fingerprint = hashlib.sha256(metrics_bytes).hexdigest()

        payload = {
            "audit_id": str(audit_id),
            "project_id": str(project_id),
            "dataset_hash": dataset_hash,
            "contract_version": contract_version,
            "verdict": verdict,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metrics_fingerprint": metrics_fingerprint,
        }

        signed_payload_b64, signature_b64, public_key_b64 = (
            self.create_receipt_signature(payload)
        )

        receipt = FairnessReceipt(
            audit_id=audit_id,
            project_id=project_id,
            dataset_hash=dataset_hash,
            contract_version=contract_version,
            contracts_summary=contracts_summary,
            metrics_summary=metrics_summary,
            verdict=verdict,
            signed_payload=signed_payload_b64,
            signature=signature_b64,
            public_key=public_key_b64,
        )
        db.add(receipt)
        await db.flush()
        await db.refresh(receipt)
        return receipt

    async def verify_receipt_by_id(
        self, db: AsyncSession, receipt_id: UUID
    ) -> dict:
        """Fetch a receipt and verify its Ed25519 signature.

        Returns a dict with keys: valid, receipt_id, verified_at, reason.
        """
        from app.models.receipt import FairnessReceipt  # avoid circular import

        result = await db.execute(
            select(FairnessReceipt).where(FairnessReceipt.id == receipt_id)
        )
        receipt = result.scalar_one_or_none()

        verified_at = datetime.now(timezone.utc).isoformat()

        if receipt is None:
            return {
                "valid": False,
                "receipt_id": str(receipt_id),
                "verified_at": verified_at,
                "reason": "Receipt not found",
            }

        valid = self.verify_signature(
            receipt.signed_payload or "",
            receipt.signature or "",
            receipt.public_key or "",
        )

        return {
            "valid": valid,
            "receipt_id": str(receipt.id),
            "verified_at": verified_at,
            "reason": None if valid else "Signature verification failed",
        }


# Module-level singleton – call initialize() during application startup.
receipt_service = ReceiptService(settings.SIGNING_KEY_PATH)


# TYPE_CHECKING import to avoid runtime circular dependency
from typing import TYPE_CHECKING  # noqa: E402

if TYPE_CHECKING:
    from app.models.receipt import FairnessReceipt
