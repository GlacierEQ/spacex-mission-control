"""Expiring local command-intent authority for the mission-operations laboratory.

This module provides a repository-local authorization mechanism for simulated
subsystem actions. It does not communicate with hardware or grant real flight
command authority.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass
from typing import Callable, Mapping

EVIDENCE_STATE = "LOCAL_SIGNED_COMMAND_INTENT_NOT_FLIGHT_AUTHORITY"
DEFAULT_MAX_TTL_SECONDS = 300.0


def _b64encode(payload: bytes) -> str:
    return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")


def _b64decode(payload: str) -> bytes:
    padding = "=" * (-len(payload) % 4)
    return base64.urlsafe_b64decode(payload + padding)


@dataclass(frozen=True)
class AuthorityReceipt:
    authorized: bool
    reason: str
    token_id: str | None
    scope: str | None
    subject: str | None
    checked_at: float
    expires_at: float | None
    evidence_state: str = EVIDENCE_STATE

    def as_dict(self) -> dict:
        return {
            "authorized": self.authorized,
            "reason": self.reason,
            "token_id": self.token_id,
            "scope": self.scope,
            "subject": self.subject,
            "checked_at": self.checked_at,
            "expires_at": self.expires_at,
            "evidence_state": self.evidence_state,
        }


class CommandAuthorityHalfLife:
    """Issue and consume signed, expiring, one-use local command intents.

    Tokens are HMAC-SHA256 authenticated, scoped, subject-bound, expiring, and
    one-use when consumed. The authority plane is intentionally local: passing
    verification authorizes only a caller-provided simulation callback.
    """

    def __init__(
        self,
        secret: bytes,
        *,
        clock: Callable[[], float] = time.time,
        max_ttl_seconds: float = DEFAULT_MAX_TTL_SECONDS,
    ) -> None:
        if not isinstance(secret, bytes) or len(secret) < 32:
            raise ValueError("secret must contain at least 32 bytes")
        if max_ttl_seconds <= 0:
            raise ValueError("max_ttl_seconds must be positive")
        self._secret = secret
        self._clock = clock
        self._max_ttl_seconds = float(max_ttl_seconds)
        self._consumed_token_ids: set[str] = set()

    @classmethod
    def ephemeral(
        cls,
        *,
        clock: Callable[[], float] = time.time,
        max_ttl_seconds: float = DEFAULT_MAX_TTL_SECONDS,
    ) -> "CommandAuthorityHalfLife":
        """Build an in-memory authority plane with a process-local random key."""

        return cls(
            secrets.token_bytes(32),
            clock=clock,
            max_ttl_seconds=max_ttl_seconds,
        )

    def _sign(self, body: str) -> str:
        digest = hmac.new(self._secret, body.encode("utf-8"), hashlib.sha256).digest()
        return _b64encode(digest)

    def issue(
        self,
        *,
        subject: str,
        scope: str,
        ttl_seconds: float,
        metadata: Mapping[str, object] | None = None,
    ) -> str:
        subject = str(subject).strip()
        scope = str(scope).strip()
        ttl = float(ttl_seconds)
        if not subject:
            raise ValueError("subject is required")
        if not scope:
            raise ValueError("scope is required")
        if ttl <= 0 or ttl > self._max_ttl_seconds:
            raise ValueError("ttl_seconds exceeds the configured authority half-life")

        issued_at = float(self._clock())
        claims = {
            "v": 1,
            "token_id": secrets.token_hex(16),
            "subject": subject,
            "scope": scope,
            "issued_at": issued_at,
            "expires_at": issued_at + ttl,
            "nonce": secrets.token_hex(12),
            "metadata": dict(metadata or {}),
            "evidence_state": EVIDENCE_STATE,
        }
        body = _b64encode(
            json.dumps(claims, sort_keys=True, separators=(",", ":")).encode("utf-8")
        )
        return f"{body}.{self._sign(body)}"

    def _decode(self, token: str) -> tuple[dict | None, str]:
        if not isinstance(token, str) or token.count(".") != 1:
            return None, "malformed_token"
        body, supplied_signature = token.split(".", 1)
        expected_signature = self._sign(body)
        if not hmac.compare_digest(supplied_signature, expected_signature):
            return None, "invalid_signature"
        try:
            claims = json.loads(_b64decode(body))
        except (ValueError, TypeError, json.JSONDecodeError):
            return None, "malformed_claims"
        if not isinstance(claims, dict):
            return None, "malformed_claims"
        required = {"token_id", "subject", "scope", "issued_at", "expires_at"}
        if not required.issubset(claims):
            return None, "missing_claims"
        return claims, "decoded"

    def inspect(
        self,
        token: str,
        *,
        required_scope: str,
        required_subject: str | None = None,
    ) -> AuthorityReceipt:
        checked_at = float(self._clock())
        claims, reason = self._decode(token)
        if claims is None:
            return AuthorityReceipt(False, reason, None, None, None, checked_at, None)

        token_id = str(claims["token_id"])
        scope = str(claims["scope"])
        subject = str(claims["subject"])
        expires_at = float(claims["expires_at"])

        if token_id in self._consumed_token_ids:
            reason = "token_already_consumed"
        elif checked_at >= expires_at:
            reason = "token_expired"
        elif scope != required_scope:
            reason = "scope_mismatch"
        elif required_subject is not None and subject != required_subject:
            reason = "subject_mismatch"
        else:
            return AuthorityReceipt(
                True,
                "authorized",
                token_id,
                scope,
                subject,
                checked_at,
                expires_at,
            )

        return AuthorityReceipt(
            False,
            reason,
            token_id,
            scope,
            subject,
            checked_at,
            expires_at,
        )

    def consume(
        self,
        token: str,
        *,
        required_scope: str,
        required_subject: str | None = None,
    ) -> AuthorityReceipt:
        receipt = self.inspect(
            token,
            required_scope=required_scope,
            required_subject=required_subject,
        )
        if receipt.authorized and receipt.token_id is not None:
            self._consumed_token_ids.add(receipt.token_id)
        return receipt

    @property
    def consumed_count(self) -> int:
        return len(self._consumed_token_ids)
