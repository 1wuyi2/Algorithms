"""升级后的AI助手模块 - 支持自然语言交互.

将规则化建议升级为自然语言AI助手，支持：
- 排课结果解释
- AI优化建议生成
- 排课问答
- 自然语言交互
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

from src.algorithms import backtracking_schedule, greedy_color_schedule
from src.evaluation import EvaluationIssueType, EvaluationSeverity, ScheduleEvaluationResult, evaluate_schedule
from src.graph import ConflictGraph, build_conflict_graph
from src.models import Course, Room, ScheduleAssignment, TimeSlot

from .llm_client import LLMClient, create_default_client


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
    llm_summary: Optional[str] = None
    llm_suggestions: Optional[str] = None


@dataclass(frozen=True)
class QAAnswer:
    """AI问答结果."""
    question: str
    answer: str
    confidence: float
    source: str  # "llm" or "rule_based"


class AIScheduleAssistant:
    """AI排课助手 - 支持自然语言交互."""

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
    ) -> ScheduleInsight:
        """分析排课状态并生成解释性建议."""
        
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

        # 使用LLM生成自然语言总结和建议
        llm_summary = None
        llm_suggestions = None
        if use_llm and self.llm_client:
            llm_summary = self._generate_llm_summary(summary, metrics, evaluation)
            llm_suggestions = self._generate_llm_suggestions(suggestions, metrics, evaluation)

        return ScheduleInsight(
            risk_level=risk_level,
            summary=summary,
            metrics=metrics,
            suggestions=tuple(suggestions),
            llm_summary=llm_summary,
            llm_suggestions=llm_suggestions,
        )

    def answer_question(self, question: str, context: Optional[Dict[str, Any]] = None) -> QAAnswer:
        """回答排课相关问题."""
        # 首先尝试规则匹配
        rule_based_answer = self._match_rule_based_question(question)
        if rule_based_answer:
            return QAAnswer(
                question=question,
                answer=rule_based_answer,
                confidence=0.95,
                source="rule_based"
            )

        # 使用LLM回答
        if self.llm_client:
            system_prompt = """你是一个智能排课系统的AI助手。请用中文回答用户关于排课的问题。

排课系统相关概念：
1. 课程冲突：指两门或多门课程不能在同一时间上课（如同一教师、同一班级的课程）
2. 贪心图染色算法：一种快速的排课算法，按课程冲突程度排序后依次分配时间
3. 回溯搜索算法：一种穷举搜索算法，能找到最优解但速度较慢
4. 时间槽：表示一个上课时间段（如周一第1-2节）

请提供专业且友好的回答。
"""
            response = self.llm_client.generate(question, system_prompt)
            if response.success:
                return QAAnswer(
                    question=question,
                    answer=response.content,
                    confidence=0.85,
                    source="llm"
                )

        # 默认回答
        return QAAnswer(
            question=question,
            answer="抱歉，我无法回答这个问题。请尝试询问与排课相关的问题。",
            confidence=0.5,
            source="rule_based"
        )

    def explain_schedule(self, evaluation: ScheduleEvaluationResult, metrics: Mapping[str, Any]) -> str:
        """生成排课结果的自然语言解释."""
        if self.llm_client:
            prompt = f"""请解释以下排课结果：

评价分数: {evaluation.score}
可行性: {'可行' if evaluation.is_feasible else '不可行'}
错误数量: {len(evaluation.errors)}
警告数量: {len(evaluation.warnings)}

指标:
{json.dumps(metrics, indent=2, ensure_ascii=False)}

请用自然、友好的语言解释这些结果。
"""
            response = self.llm_client.generate(prompt)
            if response.success:
                return response.content
        
        # 规则化解释
        return _generate_rule_based_explanation(evaluation, metrics)

    def _generate_llm_summary(self, summary: str, metrics: Mapping[str, Any], evaluation: ScheduleEvaluationResult) -> Optional[str]:
        """使用LLM生成自然语言总结."""
        prompt = f"""请将以下排课分析结果转换成自然、友好的中文总结：

原始总结: {summary}

详细指标:
- 课程数量: {metrics.get('course_count', 0)}
- 时间槽数量: {metrics.get('time_slot_count', 0)}
- 冲突边数: {metrics.get('conflict_edge_count', 0)}
- 冲突密度: {metrics.get('conflict_density', 0)}
- 评价分数: {evaluation.score}
- 错误数量: {len(evaluation.errors)}
- 警告数量: {len(evaluation.warnings)}

请用简洁、易懂的语言描述当前排课状态。
"""
        response = self.llm_client.generate(prompt)
        return response.content if response.success else None

    def _generate_llm_suggestions(self, suggestions: List[ScheduleSuggestion], metrics: Mapping[str, Any], 
                                  evaluation: ScheduleEvaluationResult) -> Optional[str]:
        """使用LLM生成优化建议."""
        suggestions_text = "\n".join([f"- [{s.priority.value}] {s.title}: {s.detail}" for s in suggestions])
        
        prompt = f"""请根据以下排课分析结果生成优化建议：

当前状态:
- 风险等级: {_risk_level(evaluation, metrics).value}
- 评价分数: {evaluation.score}
- 课程数: {metrics.get('course_count', 0)}
- 时间槽数: {metrics.get('time_slot_count', 0)}

现有建议:
{suggestions_text}

请用自然、友好的中文给出具体的优化建议。
"""
        response = self.llm_client.generate(prompt)
        return response.content if response.success else None

    def _match_rule_based_question(self, question: str) -> Optional[str]:
        """规则匹配常见问题."""
        question_lower = question.lower()
        
        if any(keyword in question_lower for keyword in ["什么是", "什么叫", "什么是排课"]):
            return "排课系统是一个自动化工具，用于将课程合理分配到时间和教室，同时避免冲突（如同一教师不能同时上两门课）。"
        
        if any(keyword in question_lower for keyword in ["贪心", "贪心算法"]):
            return "贪心图染色算法是一种快速的排课算法。它按课程的冲突程度排序，然后依次为每门课程分配第一个可用的时间槽。优点是速度快，缺点是不一定能找到最优解。"
        
        if any(keyword in question_lower for keyword in ["回溯", "回溯算法"]):
            return "回溯搜索算法是一种穷举搜索算法，会尝试所有可能的分配组合来找到最优解。优点是能找到最优解，缺点是在课程较多时速度较慢。"
        
        if any(keyword in question_lower for keyword in ["冲突", "什么是冲突"]):
            return "课程冲突指两门或多门课程不能安排在同一时间。常见的冲突类型包括：同一教师的课程冲突、同一班级的课程冲突等。"
        
        if any(keyword in question_lower for keyword in ["评价", "评分", "分数"]):
            return "课表评分范围是0-100分，基于错误和警告计算。每个错误扣20分，每个警告扣5分。分数越高表示课表质量越好。"
        
        return None


# 保留原有函数以保持兼容性
def analyze_schedule(
    courses: Iterable[Course],
    time_slots: Iterable[TimeSlot],
    *,
    assignments: Iterable[ScheduleAssignment] = (),
    rooms: Iterable[Room] = (),
    conflict_graph: Optional[ConflictGraph] = None,
) -> ScheduleInsight:
    """兼容原有API的分析函数."""
    assistant = AIScheduleAssistant()
    return assistant.analyze_schedule(
        courses, time_slots,
        assignments=assignments,
        rooms=rooms,
        conflict_graph=conflict_graph,
        use_llm=False  # 保持原有行为
    )


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
                detail="当前没有课程数据，无法进行冲突分析或自动排课。建议先完成课程数据导入。",
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
            "同一教室同一时间被多门课程占用，需要优先处理。",
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


def _generate_rule_based_explanation(evaluation: ScheduleEvaluationResult, metrics: Mapping[str, Any]) -> str:
    """生成规则化的排课结果解释."""
    parts = []
    
    if evaluation.is_feasible:
        parts.append(f"课表评价分数为 {evaluation.score} 分，当前课表可行。")
    else:
        parts.append(f"课表评价分数为 {evaluation.score} 分，当前课表存在问题。")
    
    if evaluation.errors:
        parts.append(f"检测到 {len(evaluation.errors)} 个错误：")
        for issue in evaluation.errors[:3]:
            parts.append(f"- {issue.message}")
    
    if evaluation.warnings:
        parts.append(f"检测到 {len(evaluation.warnings)} 个警告。")
    
    if metrics.get('assigned_course_count'):
        parts.append(f"已安排 {metrics['assigned_course_count']} 门课程。")
    
    return " ".join(parts)