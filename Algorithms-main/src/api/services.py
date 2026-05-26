"""Service functions used by HTTP handlers or future web frameworks."""

from __future__ import annotations

from typing import Any, Dict, Mapping

from src.algorithms import GreedySchedulingOptions, backtracking_schedule, greedy_color_schedule
from src.assistant import AIScheduleAssistant, analyze_schedule
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
from .responses import success_payload


def health_response() -> Dict[str, object]:
    """Return a lightweight service health response."""

    return success_payload({
        "status": "ok",
        "service": "nankai-scheduling-api",
    })


def run_greedy_schedule(payload: Mapping[str, Any]) -> Dict[str, object]:
    """Run greedy graph-coloring scheduling from JSON-like payload."""

    courses = parse_courses(payload.get("courses"))
    time_slots = parse_time_slots(payload.get("time_slots") or payload.get("timeSlots"))
    options = _parse_greedy_options(payload.get("options"))
    result = greedy_color_schedule(courses, time_slots, options=options)
    return success_payload({
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
    })


def run_backtracking_schedule(payload: Mapping[str, Any]) -> Dict[str, object]:
    """Run backtracking scheduling from JSON-like payload."""

    courses = parse_courses(payload.get("courses"))
    time_slots = parse_time_slots(payload.get("time_slots") or payload.get("timeSlots"))
    max_steps = int(payload.get("max_steps") or payload.get("maxSteps") or 100_000)
    result = backtracking_schedule(courses, time_slots, max_steps=max_steps)
    return success_payload({
        "algorithm": "backtracking_search",
        "is_complete": result.is_complete,
        "assignments": serialize_assignments(result.assignments),
        "failed_course_ids": list(result.failed_course_ids),
        "reason": result.reason,
        "search_steps": result.search_steps,
        "pruned_branches": result.pruned_branches,
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
    })


def compare_schedule_algorithms(payload: Mapping[str, Any]) -> Dict[str, object]:
    """Run greedy and backtracking scheduling, then recommend one result."""

    courses = parse_courses(payload.get("courses"))
    time_slots = parse_time_slots(payload.get("time_slots") or payload.get("timeSlots"))
    max_steps = int(payload.get("max_steps") or payload.get("maxSteps") or 100_000)
    options = _parse_greedy_options(payload.get("options"))

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

    return success_payload({
        "recommended_algorithm": recommended_algorithm,
        "recommendation_reason": recommendation_reason,
        "greedy": {
            "is_complete": greedy_result.is_complete,
            "score": greedy_evaluation.score,
            "metrics": dict(greedy_evaluation.metrics),
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
            "metrics": dict(backtracking_evaluation.metrics),
            "assignments": serialize_assignments(backtracking_result.assignments),
            "failed_course_ids": list(backtracking_result.failed_course_ids),
            "reason": backtracking_result.reason,
            "search_steps": backtracking_result.search_steps,
            "pruned_branches": backtracking_result.pruned_branches,
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
    })


def evaluate_schedule_payload(payload: Mapping[str, Any]) -> Dict[str, object]:
    """Evaluate a schedule from JSON-like payload."""

    courses = parse_courses(payload.get("courses"))
    assignments = parse_assignments(payload.get("assignments"))
    rooms = parse_rooms(payload.get("rooms"))
    time_slots = parse_time_slots(payload.get("time_slots") or payload.get("timeSlots"))
    return success_payload(serialize_evaluation(evaluate_schedule(courses, assignments, rooms=rooms, time_slots=time_slots)))


def analyze_schedule_payload(payload: Mapping[str, Any]) -> Dict[str, object]:
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


def recommend_courses_payload(payload: Mapping[str, Any]) -> Dict[str, object]:
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
    return success_payload({
        "student_id": student.id,
        "candidate_count": len(courses),
        "top_k": top_k,
        "recommendations": serialize_course_recommendations(recommendations),
    })


def _parse_greedy_options(value: object) -> GreedySchedulingOptions:
    if value in (None, ""):
        return GreedySchedulingOptions()
    if not isinstance(value, Mapping):
        raise ValueError("Expected options to be an object")
    return GreedySchedulingOptions(
        prioritize_fixed_time=_optional_bool(
            value.get("prioritize_fixed_time")
            if "prioritize_fixed_time" in value
            else value.get("prioritizeFixedTime"),
            default=True,
        ),
        sort_by_conflict_degree=_optional_bool(
            value.get("sort_by_conflict_degree")
            if "sort_by_conflict_degree" in value
            else value.get("sortByConflictDegree"),
            default=True,
        ),
        sort_by_candidate_count=_optional_bool(
            value.get("sort_by_candidate_count")
            if "sort_by_candidate_count" in value
            else value.get("sortByCandidateCount"),
            default=False,
        ),
    )


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


# AI 助手服务函数

def ai_analyze_schedule_payload(payload: Mapping[str, Any]) -> Dict[str, object]:
    """Generate AI-assisted scheduling analysis with natural language output."""
    
    courses = parse_courses(payload.get("courses"))
    time_slots = parse_time_slots(payload.get("time_slots") or payload.get("timeSlots"))
    assignments = parse_assignments(payload.get("assignments"))
    rooms = parse_rooms(payload.get("rooms"))
    use_llm = _optional_bool(payload.get("use_llm") if "use_llm" in payload else payload.get("useLlm"), default=True)
    
    assistant = AIScheduleAssistant()
    insight = assistant.analyze_schedule(
        courses,
        time_slots,
        assignments=assignments,
        rooms=rooms,
        use_llm=use_llm,
    )
    
    result = {
        "risk_level": insight.risk_level.value,
        "summary": insight.summary,
        "metrics": dict(insight.metrics),
        "suggestions": [
            {
                "priority": s.priority.value,
                "title": s.title,
                "detail": s.detail,
                "related_ids": list(s.related_ids),
            }
            for s in insight.suggestions
        ],
    }
    
    if insight.llm_summary:
        result["llm_summary"] = insight.llm_summary
    if insight.llm_suggestions:
        result["llm_suggestions"] = insight.llm_suggestions
    
    return success_payload(result)


def ai_answer_question(payload: Mapping[str, Any]) -> Dict[str, object]:
    """Answer scheduling-related questions using AI."""
    
    question = payload.get("question", "")
    if not isinstance(question, str) or not question.strip():
        raise ValueError("Question is required")
    
    assistant = AIScheduleAssistant()
    answer = assistant.answer_question(question)
    
    return success_payload({
        "question": answer.question,
        "answer": answer.answer,
        "confidence": answer.confidence,
        "source": answer.source,
    })


def ai_explain_schedule(payload: Mapping[str, Any]) -> Dict[str, object]:
    """Generate natural language explanation of schedule evaluation results."""
    
    courses = parse_courses(payload.get("courses"))
    assignments = parse_assignments(payload.get("assignments"))
    rooms = parse_rooms(payload.get("rooms"))
    time_slots = parse_time_slots(payload.get("time_slots") or payload.get("timeSlots"))
    
    evaluation = evaluate_schedule(courses, assignments, rooms=rooms, time_slots=time_slots)
    
    assistant = AIScheduleAssistant()
    explanation = assistant.explain_schedule(evaluation, dict(evaluation.metrics))
    
    return success_payload({
        "explanation": explanation,
        "score": evaluation.score,
        "is_feasible": evaluation.is_feasible,
        "error_count": len(evaluation.errors),
        "warning_count": len(evaluation.warnings),
    })
