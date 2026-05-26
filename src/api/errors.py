"""API error helpers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ApiError(Exception):
    """Structured API error used by HTTP handlers."""

    code: str
    message: str
    status: int = 400


def error_payload(code: str, message: str) -> dict[str, object]:
    """Return a consistent error payload without breaking simple clients."""

    return {
        "success": False,
        "code": code,
        "error": message,
    }
