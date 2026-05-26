"""Shared API response helpers."""

from __future__ import annotations

from typing import Dict, Mapping, Optional


def success_payload(data: Mapping[str, object], meta: Optional[Mapping[str, object]] = None) -> Dict[str, object]:
    """Wrap successful API data while keeping legacy top-level fields."""

    response: Dict[str, object] = {
        "success": True,
        "data": dict(data),
        "meta": dict(meta or {}),
    }
    response.update(data)
    return response
