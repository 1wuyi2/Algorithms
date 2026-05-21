"""Shared API response helpers."""

from __future__ import annotations

from typing import Mapping


def success_payload(data: Mapping[str, object], meta: Mapping[str, object] | None = None) -> dict[str, object]:
    """Wrap successful API data while keeping legacy top-level fields."""

    response: dict[str, object] = {
        "success": True,
        "data": dict(data),
        "meta": dict(meta or {}),
    }
    response.update(data)
    return response
