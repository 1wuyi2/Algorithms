"""JSON conversion helpers for the scheduling API."""

from __future__ import annotations

from typing import Any, Mapping, Optional, Tuple

from src.assistant import ScheduleInsight, ScheduleSuggestion
from src.evaluation import EvaluationIssue, ScheduleEvaluationResult
from src.models import Campus, Course, Room, RoomType, ScheduleAssignment, TimeSlot


def parse_courses(items: object) -> Tuple[Course, ...]:
    """Parse JSON-like course dictionaries into Course objects."""

    return tuple(_parse_course(_expect_mapping(item, "course")) for item in _expect_list(items, "courses"))


def parse_time_slots(items: object) -> Tuple[TimeSlot, ...]:
    """Parse JSON-like time-slot dictionaries into TimeSlot objects."""

    return tuple(_parse_time_slot(_expect_mapping(item, "time_slot")) for item in _expect_list(items, "time_slots"))


def parse_rooms(items: object) -> Tuple[Room, ...]:
    """Parse JSON-like room dictionaries into Room objects."""

    return tuple(_parse_room(_expect_mapping(item, "room")) for item in _expect_list(items, "rooms"))


def parse_assignments(items: object) -> Tuple[ScheduleAssignment, ...]:
    """Parse JSON-like assignment dictionaries into ScheduleAssignment objects."""

    return tuple(_parse_assignment(_expect_mapping(item, "assignment")) for item in _expect_list(items, "assignments"))


def serialize_assignments(assignments: Tuple[ScheduleAssignment, ...]) -> list[dict[str, Optional[str]]]:
    """Convert assignments to JSON-serializable dictionaries."""

    return [
        {
            "course_id": assignment.course_id,
            "time_slot_id": assignment.time_slot_id,
            "room_id": assignment.room_id,
        }
        for assignment in assignments
    ]


def serialize_evaluation(result: ScheduleEvaluationResult) -> dict[str, object]:
    """Convert an evaluation result to a JSON-serializable dictionary."""

    return {
        "score": result.score,
        "is_feasible": result.is_feasible,
        "issues": [_serialize_issue(issue) for issue in result.issues],
        "errors": [_serialize_issue(issue) for issue in result.errors],
        "warnings": [_serialize_issue(issue) for issue in result.warnings],
    }


def serialize_insight(insight: ScheduleInsight) -> dict[str, object]:
    """Convert an AI-assisted schedule insight to a JSON-serializable dict."""

    return {
        "risk_level": insight.risk_level.value,
        "summary": insight.summary,
        "metrics": dict(insight.metrics),
        "suggestions": [_serialize_suggestion(suggestion) for suggestion in insight.suggestions],
    }


def _parse_course(item: Mapping[str, Any]) -> Course:
    return Course(
        id=str(_required(item, "id")),
        name=str(_required(item, "name")),
        teacher_id=str(_required_any(item, "teacher_id", "teacherId")),
        class_group_ids=tuple(str(value) for value in _required_any(item, "class_group_ids", "classGroupIds")),
        weekly_hours=int(_required_any(item, "weekly_hours", "weeklyHours")),
        required_room_type=_parse_room_type(_optional_any(item, "required_room_type", "requiredRoomType")),
        required_campus=_parse_campus(_optional_any(item, "required_campus", "requiredCampus")),
        expected_students=_optional_int(_optional_any(item, "expected_students", "expectedStudents")),
        fixed_time_slot_id=_optional_str(_optional_any(item, "fixed_time_slot_id", "fixedTimeSlotId")),
        candidate_time_slot_ids=tuple(
            str(value)
            for value in (_optional_any(item, "candidate_time_slot_ids", "candidateTimeSlotIds") or ())
        ),
        required_consecutive_slots=int(_optional_any(item, "required_consecutive_slots", "requiredConsecutiveSlots") or 1),
    )


def _parse_time_slot(item: Mapping[str, Any]) -> TimeSlot:
    return TimeSlot(
        id=str(_required(item, "id")),
        weekday=int(_required(item, "weekday")),
        start_section=int(_required_any(item, "start_section", "startSection")),
        end_section=int(_required_any(item, "end_section", "endSection")),
        start_time=_optional_str(_optional_any(item, "start_time", "startTime")),
        end_time=_optional_str(_optional_any(item, "end_time", "endTime")),
        label=_optional_str(item.get("label")),
    )


def _parse_room(item: Mapping[str, Any]) -> Room:
    return Room(
        id=str(_required(item, "id")),
        name=str(_required(item, "name")),
        capacity=int(_required(item, "capacity")),
        room_type=_parse_room_type(_optional_any(item, "room_type", "roomType")),
        campus=_parse_campus(item.get("campus")),
        building=_optional_str(item.get("building")),
        available_time_slot_ids=frozenset(
            str(value)
            for value in (_optional_any(item, "available_time_slot_ids", "availableTimeSlotIds") or ())
        ),
    )


def _parse_assignment(item: Mapping[str, Any]) -> ScheduleAssignment:
    return ScheduleAssignment(
        course_id=str(_required_any(item, "course_id", "courseId")),
        time_slot_id=str(_required_any(item, "time_slot_id", "timeSlotId")),
        room_id=_optional_str(_optional_any(item, "room_id", "roomId")),
    )


def _serialize_issue(issue: EvaluationIssue) -> dict[str, object]:
    return {
        "issue_type": issue.issue_type.value,
        "severity": issue.severity.value,
        "message": issue.message,
        "related_ids": list(issue.related_ids),
    }


def _serialize_suggestion(suggestion: ScheduleSuggestion) -> dict[str, object]:
    return {
        "priority": suggestion.priority.value,
        "title": suggestion.title,
        "detail": suggestion.detail,
        "related_ids": list(suggestion.related_ids),
    }


def _parse_room_type(value: object) -> RoomType:
    if value is None:
        return RoomType.GENERAL
    return RoomType(str(value))


def _parse_campus(value: object) -> Optional[Campus]:
    if value in (None, ""):
        return None
    return Campus(str(value))


def _required(item: Mapping[str, Any], key: str) -> object:
    if key not in item or item[key] in (None, ""):
        raise ValueError(f"Missing required field: {key}")
    return item[key]


def _required_any(item: Mapping[str, Any], snake_key: str, camel_key: str) -> object:
    if snake_key in item and item[snake_key] not in (None, ""):
        return item[snake_key]
    if camel_key in item and item[camel_key] not in (None, ""):
        return item[camel_key]
    raise ValueError(f"Missing required field: {snake_key}")


def _optional_any(item: Mapping[str, Any], snake_key: str, camel_key: str) -> object:
    if snake_key in item:
        return item[snake_key]
    return item.get(camel_key)


def _optional_int(value: object) -> Optional[int]:
    if value in (None, ""):
        return None
    return int(value)


def _optional_str(value: object) -> Optional[str]:
    if value in (None, ""):
        return None
    return str(value)


def _expect_mapping(value: object, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"Expected {name} to be an object")
    return value


def _expect_list(value: object, name: str) -> list[object] | tuple[object, ...]:
    if value is None:
        return []
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"Expected {name} to be a list")
    return value
