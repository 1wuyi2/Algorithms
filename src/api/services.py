"""Service functions used by HTTP handlers or future web frameworks."""

from __future__ import annotations

from typing import Any, Mapping

from src.algorithms import backtracking_schedule, greedy_color_schedule
from src.assistant import analyze_schedule
from src.evaluation import evaluate_schedule
from src.recommendation import recommend_courses

from .schemas import (
    parse_assignments,
    parse_courses,
    parse_recommendable_courses,
    parse_rooms,
    parse_student_profile,
    parse_time_slots,
    serialize_assignments,
    serialize_evaluation,
    serialize_course_recommendations,
    serialize_insight,
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
                "candidate_time_slot_ids": list(item.candidate_time_slot_ids),
                "blocking_course_ids": list(item.blocking_course_ids),
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
        "stopped_by_limit": result.stopped_by_limit,
        "failure_details": [
            {
                "course_id": detail.course_id,
                "reason": detail.reason,
                "candidate_time_slot_ids": list(detail.candidate_time_slot_ids),
                "feasible_time_slot_ids": list(detail.feasible_time_slot_ids),
                "blocking_course_ids": list(detail.blocking_course_ids),
            }
            for detail in result.failure_details
        ],
    }


def compare_schedule_algorithms(payload: Mapping[str, Any]) -> dict[str, object]:
    """Run greedy and backtracking scheduling, then recommend one result."""

    courses = parse_courses(payload.get("courses"))
    time_slots = parse_time_slots(payload.get("time_slots") or payload.get("timeSlots"))
    max_steps = int(payload.get("max_steps") or payload.get("maxSteps") or 100_000)

    greedy_result = greedy_color_schedule(courses, time_slots)
    backtracking_result = backtracking_schedule(courses, time_slots, conflict_graph=greedy_result.conflict_graph, max_steps=max_steps)
    greedy_evaluation = evaluate_schedule(courses, greedy_result.assignments, conflict_graph=greedy_result.conflict_graph)
    backtracking_evaluation = evaluate_schedule(courses, backtracking_result.assignments, conflict_graph=greedy_result.conflict_graph)
    recommended_algorithm, recommendation_reason = _recommend_algorithm(
        greedy_complete=greedy_result.is_complete,
        greedy_score=greedy_evaluation.score,
        backtracking_complete=backtracking_result.is_complete,
        backtracking_score=backtracking_evaluation.score,
    )

    return {
        "recommended_algorithm": recommended_algorithm,
        "recommendation_reason": recommendation_reason,
        "greedy": {
            "is_complete": greedy_result.is_complete,
            "score": greedy_evaluation.score,
            "assignments": serialize_assignments(greedy_result.assignments),
            "unscheduled": [
                {
                    "course_id": item.course_id,
                    "reason": item.reason,
                    "candidate_time_slot_ids": list(item.candidate_time_slot_ids),
                    "blocking_course_ids": list(item.blocking_course_ids),
                }
                for item in greedy_result.unscheduled
            ],
            "issue_count": len(greedy_evaluation.issues),
        },
        "backtracking": {
            "is_complete": backtracking_result.is_complete,
            "score": backtracking_evaluation.score,
            "assignments": serialize_assignments(backtracking_result.assignments),
            "failed_course_ids": list(backtracking_result.failed_course_ids),
            "reason": backtracking_result.reason,
            "search_steps": backtracking_result.search_steps,
            "stopped_by_limit": backtracking_result.stopped_by_limit,
            "failure_details": [
                {
                    "course_id": detail.course_id,
                    "reason": detail.reason,
                    "candidate_time_slot_ids": list(detail.candidate_time_slot_ids),
                    "feasible_time_slot_ids": list(detail.feasible_time_slot_ids),
                    "blocking_course_ids": list(detail.blocking_course_ids),
                }
                for detail in backtracking_result.failure_details
            ],
            "issue_count": len(backtracking_evaluation.issues),
        },
    }


def evaluate_schedule_payload(payload: Mapping[str, Any]) -> dict[str, object]:
    """Evaluate a schedule from JSON-like payload."""

    courses = parse_courses(payload.get("courses"))
    assignments = parse_assignments(payload.get("assignments"))
    rooms = parse_rooms(payload.get("rooms"))
    return serialize_evaluation(evaluate_schedule(courses, assignments, rooms=rooms))


def analyze_schedule_payload(payload: Mapping[str, Any]) -> dict[str, object]:
    """Generate AI-assisted scheduling analysis from JSON-like payload."""

    courses = parse_courses(payload.get("courses"))
    time_slots = parse_time_slots(payload.get("time_slots") or payload.get("timeSlots"))
    assignments = parse_assignments(payload.get("assignments"))
    rooms = parse_rooms(payload.get("rooms"))
    return serialize_insight(
        analyze_schedule(
            courses,
            time_slots,
            assignments=assignments,
            rooms=rooms,
        )
    )


def recommend_courses_payload(payload: Mapping[str, Any]) -> dict[str, object]:
    """Generate student-side personalized course recommendations."""

    student = parse_student_profile(payload.get("student"))
    courses = parse_recommendable_courses(
        payload.get("courses")
        or payload.get("candidate_courses")
        or payload.get("candidateCourses")
    )
    current_assignments = parse_assignments(
        payload.get("current_assignments")
        or payload.get("currentAssignments")
        or payload.get("current_schedule")
        or payload.get("currentSchedule")
        or ()
    )
    top_k = int(payload.get("top_k") or payload.get("topK") or 5)
    include_conflicted = _optional_bool(
        payload.get("include_conflicted")
        if "include_conflicted" in payload
        else payload.get("includeConflicted"),
        default=True,
    )

    recommendations = recommend_courses(
        student,
        courses,
        current_assignments,
        top_k=top_k,
        include_conflicted=include_conflicted,
    )
    return {
        "student_id": student.id,
        "candidate_count": len(courses),
        "top_k": top_k,
        "recommendations": serialize_course_recommendations(recommendations),
    }


def _recommend_algorithm(
    *,
    greedy_complete: bool,
    greedy_score: int,
    backtracking_complete: bool,
    backtracking_score: int,
) -> tuple[str, str]:
    if backtracking_complete and not greedy_complete:
        return "backtracking_search", "Backtracking found a complete schedule while greedy did not."
    if greedy_complete and not backtracking_complete:
        return "greedy_coloring", "Greedy found a complete schedule while backtracking did not."
    if backtracking_score > greedy_score:
        return "backtracking_search", "Backtracking produced a higher evaluation score."
    if greedy_score > backtracking_score:
        return "greedy_coloring", "Greedy produced a higher evaluation score."
    if greedy_complete:
        return "greedy_coloring", "Both algorithms are complete with the same score; greedy is recommended for speed."
    return "backtracking_search", "Both algorithms are incomplete; backtracking provides stronger diagnostic information."


def _optional_bool(value: object, *, default: bool) -> bool:
    if value in (None, ""):
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().casefold()
        if normalized in {"true", "1", "yes", "y"}:
            return True
        if normalized in {"false", "0", "no", "n"}:
            return False
    raise ValueError("Expected a boolean value")
