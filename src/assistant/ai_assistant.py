"""Natural-language AI assistant for scheduling analysis and Q&A."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Optional, Tuple

from src.evaluation import ScheduleEvaluationResult, evaluate_schedule
from src.graph import ConflictGraph
from src.models import Course, Room, ScheduleAssignment, TimeSlot

from .llm_client import LLMClient, create_default_client
from .schedule_advisor import (
    AdvisorRiskLevel,
    ScheduleInsight,
    ScheduleSuggestion,
    SuggestionPriority,
    analyze_schedule as rule_based_analyze_schedule,
)


@dataclass(frozen=True)
class AIAssistantInsight:
    """Scheduling insight with optional LLM-generated text."""

    risk_level: AdvisorRiskLevel
    summary: str
    metrics: Mapping[str, object]
    suggestions: Tuple[ScheduleSuggestion, ...]
    llm_summary: Optional[str] = None
    llm_suggestions: Optional[str] = None
    llm_enabled: bool = False


@dataclass(frozen=True)
class QAAnswer:
    """Answer returned by the AI scheduling assistant."""

    question: str
    answer: str
    confidence: float
    source: str


class AIScheduleAssistant:
    """Scheduling assistant with rule-based fallback and optional LLM output."""

    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm_client = llm_client or create_default_client()

    def analyze_schedule(
        self,
        courses: Iterable[Course],
        time_slots: Iterable[TimeSlot],
        *,
        assignments: Iterable[ScheduleAssignment] = (),
        rooms: Iterable[Room] = (),
        conflict_graph: Optional[ConflictGraph] = None,
        use_llm: bool = True,
    ) -> AIAssistantInsight:
        """Analyze a schedule and optionally rewrite the result with an LLM."""

        base_insight: ScheduleInsight = rule_based_analyze_schedule(
            courses,
            time_slots,
            assignments=assignments,
            rooms=rooms,
            conflict_graph=conflict_graph,
        )
        llm_summary = None
        llm_suggestions = None
        llm_enabled = bool(use_llm and self.llm_client)

        if llm_enabled:
            llm_summary = self._generate_llm_summary(base_insight)
            llm_suggestions = self._generate_llm_suggestions(base_insight)

        return AIAssistantInsight(
            risk_level=base_insight.risk_level,
            summary=base_insight.summary,
            metrics=base_insight.metrics,
            suggestions=base_insight.suggestions,
            llm_summary=llm_summary,
            llm_suggestions=llm_suggestions,
            llm_enabled=llm_enabled,
        )

    def answer_question(self, question: str, context: Optional[Mapping[str, Any]] = None) -> QAAnswer:
        """Answer a scheduling-related question."""

        normalized_question = question.strip()
        rule_answer = self._rule_based_answer(normalized_question)
        if rule_answer is not None:
            return QAAnswer(normalized_question, rule_answer, 0.95, "rule_based")

        if self.llm_client is not None:
            prompt = normalized_question
            if context:
                prompt += "\n\nScheduling context:\n" + json.dumps(dict(context), ensure_ascii=False, indent=2)
            response = self.llm_client.generate(prompt, _system_prompt())
            if response.success:
                return QAAnswer(normalized_question, response.content, 0.85, "llm")

        return QAAnswer(
            normalized_question,
            "I can answer questions about scheduling conflicts, greedy graph coloring, backtracking search, schedule scores, and optimization suggestions.",
            0.5,
            "rule_based",
        )

    def explain_schedule(self, evaluation: ScheduleEvaluationResult, metrics: Mapping[str, Any]) -> str:
        """Explain a schedule evaluation in natural language."""

        if self.llm_client is not None:
            prompt = (
                "Explain this timetable evaluation for a college scheduling user.\n"
                f"Score: {evaluation.score}\n"
                f"Feasible: {evaluation.is_feasible}\n"
                f"Errors: {len(evaluation.errors)}\n"
                f"Warnings: {len(evaluation.warnings)}\n"
                "Metrics:\n"
                f"{json.dumps(dict(metrics), ensure_ascii=False, indent=2)}"
            )
            response = self.llm_client.generate(prompt, _system_prompt())
            if response.success:
                return response.content

        return _rule_based_explanation(evaluation, metrics)

    def _generate_llm_summary(self, insight: AIAssistantInsight | ScheduleInsight) -> Optional[str]:
        prompt = (
            "Rewrite this scheduling analysis as a concise Chinese summary for teachers.\n"
            f"Summary: {insight.summary}\n"
            f"Metrics: {json.dumps(dict(insight.metrics), ensure_ascii=False)}"
        )
        response = self.llm_client.generate(prompt, _system_prompt()) if self.llm_client else None
        return response.content if response and response.success else None

    def _generate_llm_suggestions(self, insight: AIAssistantInsight | ScheduleInsight) -> Optional[str]:
        suggestions = [
            {
                "priority": suggestion.priority.value,
                "title": suggestion.title,
                "detail": suggestion.detail,
                "related_ids": list(suggestion.related_ids),
            }
            for suggestion in insight.suggestions
        ]
        prompt = (
            "Convert these structured scheduling suggestions into practical Chinese advice.\n"
            f"{json.dumps(suggestions, ensure_ascii=False, indent=2)}"
        )
        response = self.llm_client.generate(prompt, _system_prompt()) if self.llm_client else None
        return response.content if response and response.success else None

    def _rule_based_answer(self, question: str) -> Optional[str]:
        lowered = question.lower()
        if "greedy" in lowered or "贪心" in question:
            return "贪心图染色会按课程约束顺序快速分配时间槽，速度快，适合生成初始课表，但在约束较紧时可能排不全。"
        if "backtracking" in lowered or "回溯" in question:
            return "回溯搜索会在候选时间槽中递归尝试，并通过剪枝提前排除无效分支，适合用来补全或验证贪心结果。"
        if "冲突" in question or "conflict" in lowered:
            return "课程冲突通常来自同一教师、同一班级、固定时间、教室容量或校区等约束，系统会返回冲突原因和相关课程。"
        if "评分" in question or "score" in lowered or "评价" in question:
            return "课表评分会综合未排课程、课程冲突、教室冲突、容量、校区以及教师和班级负载等指标。"
        if "优化" in question or "建议" in question:
            return "可以先用贪心算法得到初始课表，再用回溯搜索补全，并继续通过局部调整减少早课、晚课和负载不均。"
        return None


def explain_schedule_payload_data(
    courses: Iterable[Course],
    assignments: Iterable[ScheduleAssignment],
    *,
    rooms: Iterable[Room] = (),
    time_slots: Iterable[TimeSlot] = (),
) -> tuple[str, ScheduleEvaluationResult]:
    """Build an explanation and return it together with the evaluation."""

    evaluation = evaluate_schedule(courses, assignments, rooms=rooms, time_slots=time_slots)
    assistant = AIScheduleAssistant()
    return assistant.explain_schedule(evaluation, dict(evaluation.metrics)), evaluation


def _rule_based_explanation(evaluation: ScheduleEvaluationResult, metrics: Mapping[str, Any]) -> str:
    status = "feasible" if evaluation.is_feasible else "not feasible"
    parts = [
        f"The current schedule is {status} with a score of {evaluation.score}.",
        f"It contains {len(evaluation.errors)} hard error(s) and {len(evaluation.warnings)} warning(s).",
    ]
    assigned_count = metrics.get("assigned_course_count")
    missing_count = metrics.get("missing_assignment_count")
    if assigned_count is not None:
        parts.append(f"Assigned courses: {assigned_count}.")
    if missing_count:
        parts.append(f"Missing assignments: {missing_count}.")
    if evaluation.errors:
        first_error = evaluation.errors[0]
        parts.append(f"First issue: {first_error.message}")
    return " ".join(parts)


def _system_prompt() -> str:
    return (
        "You are an assistant for a Nankai University college scheduling system. "
        "Answer in clear Chinese unless the user asks otherwise. Focus on constraints, "
        "conflicts, algorithms, schedule quality, and actionable optimization advice."
    )


__all__ = [
    "AIAssistantInsight",
    "AIScheduleAssistant",
    "QAAnswer",
    "explain_schedule_payload_data",
]
