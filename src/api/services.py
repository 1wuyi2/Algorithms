"""Service functions used by HTTP handlers or future web frameworks."""

from __future__ import annotations

from typing import Any, Mapping

from src.algorithms import backtracking_schedule, greedy_color_schedule
from src.assistant import analyze_schedule
from src.evaluation import evaluate_schedule
from src.recommendation import build_fixed_schedule_items, recommend_courses

from .responses import success_payload
from .schemas import (
    parse_assignments,
    parse_courses,
    parse_greedy_options,
    parse_recommendable_courses,
    parse_rooms,
    parse_student_profile,
    parse_student_schedule_items,
    parse_time_slots,
    serialize_assignments,
    serialize_course_recommendations,
    serialize_student_schedule_items,
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
    result = _run_greedy_with_options(courses, time_slots, options)

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

    greedy_result = _run_greedy_with_options(courses, time_slots, options)
    backtracking_result = backtracking_schedule(
        courses,
        time_slots,
        conflict_graph=greedy_result.conflict_graph,
        max_steps=max_steps,
    )
    greedy_evaluation = _evaluate_schedule_with_time_slots(
        courses,
        greedy_result.assignments,
        conflict_graph=greedy_result.conflict_graph,
        time_slots=time_slots,
    )
    backtracking_evaluation = _evaluate_schedule_with_time_slots(
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
            "metrics": dict(getattr(greedy_evaluation, "metrics", {})),
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
            "metrics": dict(getattr(backtracking_evaluation, "metrics", {})),
        },
    }
    return success_payload(data)


def evaluate_schedule_payload(payload: Mapping[str, Any]) -> dict[str, object]:
    """Evaluate a schedule from JSON-like payload."""

    courses = parse_courses(payload.get("courses"))
    assignments = parse_assignments(payload.get("assignments"))
    rooms = parse_rooms(payload.get("rooms"))
    time_slots = parse_time_slots(payload.get("time_slots") or payload.get("timeSlots"))
    data = serialize_evaluation(_evaluate_schedule_with_time_slots(courses, assignments, rooms=rooms, time_slots=time_slots))
    return success_payload(data)


def analyze_schedule_payload(payload: Mapping[str, Any]) -> dict[str, object]:
    """Generate AI-assisted scheduling analysis from JSON-like payload."""

    courses = parse_courses(payload.get("courses"))
    time_slots = parse_time_slots(payload.get("time_slots") or payload.get("timeSlots"))
    assignments = parse_assignments(payload.get("assignments"))
    rooms = parse_rooms(payload.get("rooms"))
    data = serialize_insight(
        analyze_schedule(
            courses,
            time_slots,
            assignments=assignments,
            rooms=rooms,
        )
    )
    return success_payload(data)


def recommend_courses_payload(payload: Mapping[str, Any]) -> dict[str, object]:
    """Generate student-side personalized course recommendations."""

    student = parse_student_profile(payload.get("student"))
    courses = parse_recommendable_courses(
        payload.get("courses")
        or payload.get("candidate_courses")
        or payload.get("candidateCourses")
    )
    current_schedule = parse_student_schedule_items(
        payload.get("current_assignments")
        or payload.get("currentAssignments")
        or payload.get("current_schedule")
        or payload.get("currentSchedule")
        or payload.get("uploaded_schedule")
        or payload.get("uploadedSchedule")
        or ()
    )
    top_k = int(payload.get("top_k") or payload.get("topK") or 5)
    include_conflicted = _optional_bool(
        payload.get("include_conflicted")
        if "include_conflicted" in payload
        else payload.get("includeConflicted"),
        default=True,
    )
    exclude_selected = _optional_bool(
        payload.get("exclude_selected")
        if "exclude_selected" in payload
        else payload.get("excludeSelected"),
        default=True,
    )
    fixed_course_ids = _parse_string_list(
        payload.get("fixed_course_ids")
        or payload.get("fixedCourseIds")
        or payload.get("required_course_ids")
        or payload.get("requiredCourseIds")
        or ()
    )
    fixed_course_ids = tuple(dict.fromkeys(tuple(student.fixed_course_ids) + fixed_course_ids))
    fixed_schedule_items = build_fixed_schedule_items(courses, fixed_course_ids)
    selected_schedule = current_schedule + fixed_schedule_items

    recommendations = recommend_courses(
        student,
        courses,
        selected_schedule,
        top_k=top_k,
        include_conflicted=include_conflicted,
        fixed_course_ids=fixed_course_ids,
        exclude_selected=exclude_selected,
    )
    missing_fixed_course_ids = tuple(
        course_id
        for course_id in fixed_course_ids
        if course_id not in {course.id for course in courses}
    )
    data = {
        "student_id": student.id,
        "candidate_count": len(courses),
        "top_k": top_k,
        "include_conflicted": include_conflicted,
        "exclude_selected": exclude_selected,
        "fixed_course_ids": list(fixed_course_ids),
        "missing_fixed_course_ids": list(missing_fixed_course_ids),
        "selected_schedule": serialize_student_schedule_items(selected_schedule),
        "fixed_selected_courses": serialize_student_schedule_items(fixed_schedule_items),
        "recommendations": serialize_course_recommendations(recommendations),
    }
    return success_payload(data)


def _evaluate_schedule_with_time_slots(courses: object, assignments: object, **kwargs):
    try:
        return evaluate_schedule(courses, assignments, **kwargs)
    except TypeError as exc:
        if "time_slots" not in str(exc):
            raise
        kwargs.pop("time_slots", None)
        return evaluate_schedule(courses, assignments, **kwargs)

def _run_greedy_with_options(courses: object, time_slots: object, options: object):
    try:
        return greedy_color_schedule(courses, time_slots, options=options)
    except TypeError as exc:
        if "options" not in str(exc):
            raise
        return greedy_color_schedule(courses, time_slots)

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


def _parse_string_list(value: object) -> tuple[str, ...]:
    if value in (None, ""):
        return ()
    if isinstance(value, str):
        raw_items = value.replace("，", ",").replace("\n", ",").split(",")
        return tuple(item.strip() for item in raw_items if item.strip())
    if isinstance(value, (list, tuple, set, frozenset)):
        return tuple(str(item).strip() for item in value if str(item).strip())
    raise ValueError("Expected a string or list of strings")

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
