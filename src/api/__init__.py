"""API helpers and service entry points."""

from .errors import ApiError, error_payload
from .responses import success_payload
from .services import (
    ai_analyze_schedule_payload,
    ai_answer_question_payload,
    ai_explain_schedule_payload,
    analyze_schedule_payload,
    authenticate_user_payload,
    compare_schedule_algorithms,
    evaluate_schedule_payload,
    health_response,
    recommend_courses_payload,
    run_backtracking_schedule,
    run_greedy_schedule,
)

__all__ = [
    "ApiError",
    "ai_analyze_schedule_payload",
    "ai_answer_question_payload",
    "ai_explain_schedule_payload",
    "analyze_schedule_payload",
    "authenticate_user_payload",
    "compare_schedule_algorithms",
    "error_payload",
    "evaluate_schedule_payload",
    "health_response",
    "recommend_courses_payload",
    "run_backtracking_schedule",
    "run_greedy_schedule",
    "success_payload",
]
