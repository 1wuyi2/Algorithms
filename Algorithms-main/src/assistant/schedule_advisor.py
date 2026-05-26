"""Rule-based scheduling advisor.

This module is the first backend version of "AI-assisted scheduling". It does
not call an external large model yet. Instead, it turns graph, algorithm, and
evaluation signals into explainable suggestions that a teacher-facing product
can show directly or later feed into an LLM for richer wording.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Iterable, List, Mapping, Optional, Tuple

from src.algorithms import backtracking_schedule, greedy_color_schedule
from src.evaluation import EvaluationIssueType, EvaluationSeverity, ScheduleEvaluationResult, evaluate_schedule
from src.graph import ConflictGraph, build_conflict_graph
from src.models import Course, Room, ScheduleAssignment, TimeSlot


class AdvisorRiskLevel(str, Enum):
    """Overall scheduling risk level."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class SuggestionPriority(str, Enum):
    """Suggestion priority for follow-up actions."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass(frozen=True)
class ScheduleSuggestion:
    """One explainable optimization suggestion."""

    priority: SuggestionPriority
    title: str
    detail: str
    related_ids: Tuple[str, ...] = ()


@dataclass(frozen=True)
class ScheduleInsight:
    """AI-assisted scheduling analysis result."""

    risk_level: AdvisorRiskLevel
    summary: str
    metrics: Mapping[str, object]
    suggestions: Tuple[ScheduleSuggestion, ...]


def analyze_schedule(
    courses: Iterable[Course],
    time_slots: Iterable[TimeSlot],
    *,
    assignments: Iterable[ScheduleAssignment] = (),
    rooms: Iterable[Room] = (),
    conflict_graph: Optional[ConflictGraph] = None,
) -> ScheduleInsight:
    """Analyze scheduling state and produce explainable suggestions."""

    course_list = tuple(courses)
    time_slot_list = tuple(time_slots)
    assignment_list = tuple(assignments)
    room_list = tuple(rooms)
    graph = conflict_graph or build_conflict_graph(course_list)

    if assignment_list:
        evaluation = evaluate_schedule(course_list, assignment_list, conflict_graph=graph, rooms=room_list)
        greedy_result = None
        backtracking_result = None
    else:
        greedy_result = greedy_color_schedule(course_list, time_slot_list, conflict_graph=graph)
        backtracking_result = backtracking_schedule(course_list, time_slot_list, conflict_graph=graph)
        evaluation = evaluate_schedule(
            course_list,
            backtracking_result.assignments if backtracking_result.is_complete else greedy_result.assignments,
            conflict_graph=graph,
            rooms=room_list,
        )

    metrics = _build_metrics(course_list, time_slot_list, graph, evaluation, greedy_result, backtracking_result)
    suggestions = _build_suggestions(course_list, time_slot_list, graph, evaluation, greedy_result, backtracking_result)
    risk_level = _risk_level(evaluation, metrics)
    summary = _summary(risk_level, metrics, evaluation)
    return ScheduleInsight(risk_level=risk_level, summary=summary, metrics=metrics, suggestions=tuple(suggestions))


def _build_metrics(
    courses: Tuple[Course, ...],
    time_slots: Tuple[TimeSlot, ...],
    graph: ConflictGraph,
    evaluation: ScheduleEvaluationResult,
    greedy_result: object,
    backtracking_result: object,
) -> Dict[str, object]:
    course_count = len(courses)
    edge_count = len(graph.edges)
    max_edges = course_count * (course_count - 1) / 2 if course_count > 1 else 1
    conflict_density = round(edge_count / max_edges, 3) if max_edges else 0
    high_degree_courses = _high_degree_courses(graph, limit=5)

    metrics: Dict[str, object] = {
        "course_count": course_count,
        "time_slot_count": len(time_slots),
        "conflict_edge_count": edge_count,
        "conflict_density": conflict_density,
        "evaluation_score": evaluation.score,
        "error_count": len(evaluation.errors),
        "warning_count": len(evaluation.warnings),
        "high_degree_courses": high_degree_courses,
    }

    if greedy_result is not None:
        metrics["greedy_complete"] = greedy_result.is_complete
        metrics["greedy_unscheduled_count"] = len(greedy_result.unscheduled)

    if backtracking_result is not None:
        metrics["backtracking_complete"] = backtracking_result.is_complete
        metrics["backtracking_failed_count"] = len(backtracking_result.failed_course_ids)
        metrics["backtracking_search_steps"] = backtracking_result.search_steps

    return metrics


def _build_suggestions(
    courses: Tuple[Course, ...],
    time_slots: Tuple[TimeSlot, ...],
    graph: ConflictGraph,
    evaluation: ScheduleEvaluationResult,
    greedy_result: object,
    backtracking_result: object,
) -> List[ScheduleSuggestion]:
    suggestions = []

    if not courses:
        suggestions.append(
            ScheduleSuggestion(
                priority=SuggestionPriority.HIGH,
                title="先导入课程数据",
                detail="当前没有课程数据，无法进行冲突分析或自动排课。建议先完成 PDF/CSV 课程数据导入。",
            )
        )
        return suggestions

    if not time_slots:
        suggestions.append(
            ScheduleSuggestion(
                priority=SuggestionPriority.HIGH,
                title="补充可用时间槽",
                detail="当前没有可用时间槽，算法无法为课程分配上课时间。",
            )
        )

    for issue_type, title, detail in (
        (
            EvaluationIssueType.COURSE_CONFLICT,
            "优先处理课程时间冲突",
            "存在互相冲突的课程被安排到同一时间槽，建议先调整这些课程的时间候选范围。",
        ),
        (
            EvaluationIssueType.MISSING_ASSIGNMENT,
            "补齐未排课程",
            "存在没有排入课表的课程，建议增加时间槽或放宽课程候选时间。",
        ),
        (
            EvaluationIssueType.ROOM_DOUBLE_BOOKED,
            "避免教室重复占用",
            "同一教室同一时间被多门课程占用，后续教室分配模块需要优先处理。",
        ),
        (
            EvaluationIssueType.ROOM_CAPACITY,
            "检查教室容量",
            "部分课程人数超过教室容量，需要更换大教室或拆分教学班。",
        ),
    ):
        related_ids = _related_ids_for_issue(evaluation, issue_type)
        if related_ids:
            suggestions.append(ScheduleSuggestion(SuggestionPriority.HIGH, title, detail, related_ids))

    high_degree_courses = _high_degree_courses(graph, limit=3)
    if high_degree_courses:
        suggestions.append(
            ScheduleSuggestion(
                priority=SuggestionPriority.MEDIUM,
                title="优先安排高冲突课程",
                detail="这些课程与较多课程存在冲突，建议在贪心排序或人工调整时优先处理。",
                related_ids=tuple(course_id for course_id, _ in high_degree_courses),
            )
        )

    if greedy_result is not None and backtracking_result is not None:
        if not greedy_result.is_complete and backtracking_result.is_complete:
            suggestions.append(
                ScheduleSuggestion(
                    priority=SuggestionPriority.MEDIUM,
                    title="使用回溯结果替代贪心结果",
                    detail="当前数据下贪心算法未能排完全部课程，但回溯搜索找到了完整方案。",
                )
            )
        elif not backtracking_result.is_complete:
            suggestions.append(
                ScheduleSuggestion(
                    priority=SuggestionPriority.HIGH,
                    title="当前约束可能过紧",
                    detail="回溯搜索也无法找到完整方案，建议增加时间槽、减少固定时间或放宽候选时间。",
                    related_ids=tuple(backtracking_result.failed_course_ids),
                )
            )

    if not suggestions and evaluation.is_feasible:
        suggestions.append(
            ScheduleSuggestion(
                priority=SuggestionPriority.LOW,
                title="当前课表基础可行",
                detail="未发现硬冲突。后续可以继续优化教师课程分布、班级每日负载和教室利用率。",
            )
        )

    return suggestions


def _risk_level(evaluation: ScheduleEvaluationResult, metrics: Mapping[str, object]) -> AdvisorRiskLevel:
    if len(evaluation.errors) >= 3 or metrics.get("backtracking_complete") is False:
        return AdvisorRiskLevel.HIGH
    if evaluation.errors or evaluation.score < 80:
        return AdvisorRiskLevel.MEDIUM
    if metrics.get("course_count", 0) >= 5 and metrics.get("conflict_density", 0) >= 0.35:
        return AdvisorRiskLevel.MEDIUM
    return AdvisorRiskLevel.LOW


def _summary(
    risk_level: AdvisorRiskLevel,
    metrics: Mapping[str, object],
    evaluation: ScheduleEvaluationResult,
) -> str:
    return (
        f"当前共有 {metrics['course_count']} 门课程、{metrics['time_slot_count']} 个时间槽，"
        f"冲突边 {metrics['conflict_edge_count']} 条，评价分数 {evaluation.score}。"
        f"整体风险等级为 {risk_level.value}。"
    )


def _high_degree_courses(graph: ConflictGraph, *, limit: int) -> Tuple[Tuple[str, int], ...]:
    ranked = sorted(((course_id, graph.degree(course_id)) for course_id in graph.node_ids), key=lambda item: (-item[1], item[0]))
    return tuple((course_id, degree) for course_id, degree in ranked[:limit] if degree > 0)


def _related_ids_for_issue(
    evaluation: ScheduleEvaluationResult,
    issue_type: EvaluationIssueType,
) -> Tuple[str, ...]:
    related_ids = []
    for issue in evaluation.issues:
        if issue.issue_type == issue_type and issue.severity == EvaluationSeverity.ERROR:
            related_ids.extend(issue.related_ids)
    return tuple(dict.fromkeys(related_ids))
