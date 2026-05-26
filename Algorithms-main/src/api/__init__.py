"""API helpers and service entry points."""

from .errors import ApiError, error_payload
from .responses import success_payload
from .services import (
    analyze_schedule_payload,
    compare_schedule_algorithms,
    evaluate_schedule_payload,
    health_response,
    recommend_courses_payload,
    run_backtracking_schedule,
    run_greedy_schedule,
)

__all__ = [
    "ApiError",
    "analyze_schedule_payload",
    "compare_schedule_algorithms",
    "error_payload",
    "evaluate_schedule_payload",
    "health_response",
    "recommend_courses_payload",
    "run_backtracking_schedule",
    "run_greedy_schedule",
    "success_payload",
]
