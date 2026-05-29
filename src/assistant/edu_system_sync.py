"""Educational-system synchronization adapter.

This module does not depend on a real Nankai internal API. It defines a small
adapter layer that can call a compatible external service later and convert the
returned data into the project's core scheduling models.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Mapping, Optional, Tuple

from src.models import Course, Room, RoomType, Teacher, TimeSlot


class EduSystemType(str, Enum):
    """Supported educational system adapter types."""

    NANKAI = "nankai"
    GENERIC = "generic"
    TEST = "test"


@dataclass(frozen=True)
class EduSystemConfig:
    """Connection settings for an educational system."""

    system_type: EduSystemType
    api_url: str
    api_key: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    timeout: int = 30


@dataclass(frozen=True)
class SyncResult:
    """Summary of an educational-system synchronization attempt."""

    success: bool
    imported_courses: int = 0
    imported_teachers: int = 0
    imported_rooms: int = 0
    imported_time_slots: int = 0
    message: str = ""
    error_details: Optional[str] = None


class EduSystemClient:
    """Client for fetching teaching data from a compatible external service."""

    def __init__(self, config: EduSystemConfig):
        self.config = config

    def sync_all_data(self) -> SyncResult:
        """Fetch all supported data categories and return a count summary."""

        try:
            courses = self.fetch_courses()
            teachers = self.fetch_teachers()
            rooms = self.fetch_rooms()
            time_slots = self.fetch_time_slots()
            return SyncResult(
                success=True,
                imported_courses=len(courses),
                imported_teachers=len(teachers),
                imported_rooms=len(rooms),
                imported_time_slots=len(time_slots),
                message="Educational system data synchronized successfully.",
            )
        except Exception as exc:  # pragma: no cover - external service dependent.
            return SyncResult(
                success=False,
                message="Educational system data synchronization failed.",
                error_details=str(exc),
            )

    def fetch_courses(self) -> Tuple[Course, ...]:
        return tuple(_parse_course(item) for item in self._get_data("/courses"))

    def fetch_teachers(self) -> Tuple[Teacher, ...]:
        return tuple(_parse_teacher(item) for item in self._get_data("/teachers"))

    def fetch_rooms(self) -> Tuple[Room, ...]:
        return tuple(_parse_room(item) for item in self._get_data("/rooms"))

    def fetch_time_slots(self) -> Tuple[TimeSlot, ...]:
        return tuple(_parse_time_slot(item) for item in self._get_data("/time_slots"))

    def _get_data(self, path: str) -> Tuple[Mapping[str, Any], ...]:
        url = self.config.api_url.rstrip("/") + path
        request = urllib.request.Request(url, method="GET", headers=self._headers())
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Educational system API error {exc.code}: {detail}") from exc

        data = payload.get("data", payload)
        if not isinstance(data, list):
            raise ValueError(f"Expected list data from {path}")
        return tuple(item for item in data if isinstance(item, Mapping))

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        return headers


EDU_SYSTEM_FIELD_MAPPING = {
    "nankai": {
        "course": {
            "id": ("course_code", "kch", "id"),
            "name": ("course_name", "kcmc", "name"),
            "teacher_id": ("teacher_id", "jsgh", "teacherCode"),
            "class_group_ids": ("class_group_ids", "bjbh_list", "classes"),
            "weekly_hours": ("weekly_hours", "zxcs", "hours"),
        },
        "teacher": {
            "id": ("teacher_id", "gh", "id"),
            "name": ("teacher_name", "xm", "name"),
        },
        "room": {
            "id": ("room_id", "jsh", "id"),
            "name": ("room_name", "jsmc", "name"),
            "capacity": ("capacity", "rz"),
        },
    }
}


def generate_sync_report(result: SyncResult) -> str:
    """Generate a human-readable synchronization report."""

    status = "success" if result.success else "failed"
    lines = [
        "Educational system synchronization report",
        f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Status: {status}",
        f"Courses: {result.imported_courses}",
        f"Teachers: {result.imported_teachers}",
        f"Rooms: {result.imported_rooms}",
        f"Time slots: {result.imported_time_slots}",
        result.message,
    ]
    if result.error_details:
        lines.append(f"Error details: {result.error_details}")
    return "\n".join(lines)


def _parse_course(raw: Mapping[str, Any]) -> Course:
    class_group_ids = tuple(
        str(value) for value in _list_value(_first(raw, "class_group_ids", "classes", "bjbh_list", default=()))
    )
    if not class_group_ids:
        class_group_ids = ("UNKNOWN_CLASS",)

    return Course(
        id=str(_first(raw, "course_code", "id", "kch")),
        name=str(_first(raw, "course_name", "name", "kcmc")),
        teacher_id=str(_first(raw, "teacher_id", "teacher_code", "jsgh", default="UNKNOWN_TEACHER")),
        class_group_ids=class_group_ids,
        weekly_hours=int(_first(raw, "weekly_hours", "hours", "zxcs", default=2)),
        expected_students=_optional_int(_first(raw, "expected_students", "students", "rs", default=None)),
    )


def _parse_teacher(raw: Mapping[str, Any]) -> Teacher:
    return Teacher(
        id=str(_first(raw, "teacher_id", "id", "gh")),
        name=str(_first(raw, "teacher_name", "name", "xm")),
        unavailable_time_slot_ids=frozenset(str(value) for value in _list_value(raw.get("unavailable_slots", ()))),
    )


def _parse_room(raw: Mapping[str, Any]) -> Room:
    return Room(
        id=str(_first(raw, "room_id", "id", "jsh")),
        name=str(_first(raw, "room_name", "name", "jsmc")),
        capacity=int(_first(raw, "capacity", "rz", default=60)),
        room_type=_parse_room_type(raw.get("room_type") or raw.get("jxlx")),
        building=str(raw.get("building") or ""),
        available_time_slot_ids=frozenset(str(value) for value in _list_value(raw.get("available_slots", ()))),
    )


def _parse_time_slot(raw: Mapping[str, Any]) -> TimeSlot:
    return TimeSlot(
        id=str(_first(raw, "slot_id", "id")),
        weekday=int(_first(raw, "weekday", default=1)),
        start_section=int(_first(raw, "start_section", "start", default=1)),
        end_section=int(_first(raw, "end_section", "end", default=1)),
        start_time=_optional_str(raw.get("start_time")),
        end_time=_optional_str(raw.get("end_time")),
        label=_optional_str(raw.get("label")),
    )


def _first(raw: Mapping[str, Any], *keys: str, default: object = "") -> object:
    for key in keys:
        value = raw.get(key)
        if value not in (None, ""):
            return value
    return default


def _list_value(value: object) -> Tuple[object, ...]:
    if value in (None, ""):
        return ()
    if isinstance(value, str):
        return tuple(item.strip() for item in value.split(",") if item.strip())
    if isinstance(value, (list, tuple, set, frozenset)):
        return tuple(value)
    return (value,)


def _optional_int(value: object) -> Optional[int]:
    if value in (None, ""):
        return None
    return int(value)


def _optional_str(value: object) -> Optional[str]:
    if value in (None, ""):
        return None
    return str(value)


def _parse_room_type(value: object) -> RoomType:
    if value in (None, ""):
        return RoomType.GENERAL
    try:
        return RoomType(str(value))
    except ValueError:
        return RoomType.GENERAL


__all__ = [
    "EDU_SYSTEM_FIELD_MAPPING",
    "EduSystemClient",
    "EduSystemConfig",
    "EduSystemType",
    "SyncResult",
    "generate_sync_report",
]
