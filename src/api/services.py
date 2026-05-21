"""Service functions used by HTTP handlers or future web frameworks."""

from __future__ import annotations

from typing import Any, Mapping

from src.algorithms import backtracking_schedule, greedy_color_schedule
from src.assistant import analyze_schedule
from src.evaluation import evaluate_schedule

from .responses import success_payload
from .schemas import (
    parse_assignments,
    parse_courses,
    parse_greedy_options,
    parse_rooms,
    parse_time_slots,
    serialize_assignments,
    serialize_evaluation,
    serialize_insight,
)


def health_response() -> dict[str, object]:
    """Return a lightweight service health response."""

    data = {
        "status": "ok",
        "service": "nankai-scheduling-api",
    }
    return success_payload(data)


def run_greedy_schedule(payload: Mapping[str, Any]) -> dict[str, object]:
    """Run greedy graph-coloring scheduling from JSON-like payload."""

    courses = parse_courses(payload.get("courses"))
    time_slots = parse_time_slots(payload.get("time_slots") or payload.get("timeSlots"))
    options = parse_greedy_options(payload.get("options"))
    result = greedy_color_schedule(courses, time_slots, options=options)
    data = {
        "algorithm": "greedy_coloring",
        "is_complete": result.is_complete,
        "options": {
            "prioritize_fixed_time": options.prioritize_fixed_time,
            "sort_by_conflict_degree": options.sort_by_conflict_degree,
            "sort_by_candidate_count": options.sort_by_candidate_count,
        },
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
    return success_payload(data)


def run_backtracking_schedule(payload: Mapping[str, Any]) -> dict[str, object]:
    """Run backtracking scheduling from JSON-like payload."""

    courses = parse_courses(payload.get("courses"))
    time_slots = parse_time_slots(payload.get("time_slots") or payload.get("timeSlots"))
    max_steps = int(payload.get("max_steps") or payload.get("maxSteps") or 100_000)
    result = backtracking_schedule(courses, time_slots, max_steps=max_steps)
    data = {
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
    return success_payload(data)


def compare_schedule_algorithms(payload: Mapping[str, Any]) -> dict[str, object]:
    """Run greedy and backtracking scheduling, then recommend one result."""

    courses = parse_courses(payload.get("courses"))
    time_slots = parse_time_slots(payload.get("time_slots") or payload.get("timeSlots"))
    max_steps = int(payload.get("max_steps") or payload.get("maxSteps") or 100_000)
    options = parse_greedy_options(payload.get("options"))

    greedy_result = greedy_color_schedule(courses, time_slots, options=options)
    backtracking_result = backtracking_schedule(courses, time_slots, conflict_graph=greedy_result.conflict_graph, max_steps=max_steps)
    greedy_evaluation = evaluate_schedule(
        courses,
        greedy_result.assignments,
        conflict_graph=greedy_result.conflict_graph,
        time_slots=time_slots,
    )
    backtracking_evaluation = evaluate_schedule(
        courses,
        backtracking_result.assignments,
        conflict_graph=greedy_result.conflict_graph,
        time_slots=time_slots,
    )
    recommended_algorithm, recommendation_reason = _recommend_algorithm(
        greedy_complete=greedy_result.is_complete,
        greedy_score=greedy_evaluation.score,
        backtracking_complete=backtracking_result.is_complete,
        backtracking_score=backtracking_evaluation.score,
    )

    data = {
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
            "metrics": dict(greedy_evaluation.metrics),
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
            "metrics": dict(backtracking_evaluation.metrics),
        },
    }
    return success_payload(data)


def evaluate_schedule_payload(payload: Mapping[str, Any]) -> dict[str, object]:
    """Evaluate a schedule from JSON-like payload."""

    courses = parse_courses(payload.get("courses"))
    assignments = parse_assignments(payload.get("assignments"))
    rooms = parse_rooms(payload.get("rooms"))
    time_slots = parse_time_slots(payload.get("time_slots") or payload.get("timeSlots"))
    return success_payload(serialize_evaluation(evaluate_schedule(courses, assignments, rooms=rooms, time_slots=time_slots)))


def analyze_schedule_payload(payload: Mapping[str, Any]) -> dict[str, object]:
    """Generate AI-assisted scheduling analysis from JSON-like payload."""

    courses = parse_courses(payload.get("courses"))
    time_slots = parse_time_slots(payload.get("time_slots") or payload.get("timeSlots"))
    assignments = parse_assignments(payload.get("assignments"))
    rooms = parse_rooms(payload.get("rooms"))
    return success_payload(serialize_insight(
        analyze_schedule(
            courses,
            time_slots,
            assignments=assignments,
            rooms=rooms,
        )
    ))


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
