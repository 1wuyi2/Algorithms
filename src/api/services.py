"""Service functions used by HTTP handlers or future web frameworks."""

from __future__ import annotations

from typing import Any, Mapping

from src.algorithms import backtracking_schedule, greedy_color_schedule
from src.evaluation import evaluate_schedule

from .schemas import (
    parse_assignments,
    parse_courses,
    parse_rooms,
    parse_time_slots,
    serialize_assignments,
    serialize_evaluation,
)


def health_response() -> dict[str, object]:
    """Return a lightweight service health response."""

    return {
        "status": "ok",
        "service": "nankai-scheduling-api",
    }


def run_greedy_schedule(payload: Mapping[str, Any]) -> dict[str, object]:
    """Run greedy graph-coloring scheduling from JSON-like payload."""

    courses = parse_courses(payload.get("courses"))
    time_slots = parse_time_slots(payload.get("time_slots") or payload.get("timeSlots"))
    result = greedy_color_schedule(courses, time_slots)
    return {
        "algorithm": "greedy_coloring",
        "is_complete": result.is_complete,
        "assignments": serialize_assignments(result.assignments),
        "unscheduled": [
            {
                "course_id": item.course_id,
                "reason": item.reason,
            }
            for item in result.unscheduled
        ],
    }


def run_backtracking_schedule(payload: Mapping[str, Any]) -> dict[str, object]:
    """Run backtracking scheduling from JSON-like payload."""

    courses = parse_courses(payload.get("courses"))
    time_slots = parse_time_slots(payload.get("time_slots") or payload.get("timeSlots"))
    max_steps = int(payload.get("max_steps") or payload.get("maxSteps") or 100_000)
    result = backtracking_schedule(courses, time_slots, max_steps=max_steps)
    return {
        "algorithm": "backtracking_search",
        "is_complete": result.is_complete,
        "assignments": serialize_assignments(result.assignments),
        "failed_course_ids": list(result.failed_course_ids),
        "reason": result.reason,
        "search_steps": result.search_steps,
    }


def evaluate_schedule_payload(payload: Mapping[str, Any]) -> dict[str, object]:
    """Evaluate a schedule from JSON-like payload."""

    courses = parse_courses(payload.get("courses"))
    assignments = parse_assignments(payload.get("assignments"))
    rooms = parse_rooms(payload.get("rooms"))
    return serialize_evaluation(evaluate_schedule(courses, assignments, rooms=rooms))
