"""Schedule evaluation utilities.

The evaluator checks generated assignments and returns structured issues that
can be displayed by a future web UI. It does not require real imported data;
optional room checks only run when room objects are provided.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Iterable, Mapping, Optional, Tuple

from src.graph import ConflictGraph, build_conflict_graph
from src.models import Course, Room, ScheduleAssignment


class EvaluationSeverity(str, Enum):
    """Issue severity levels for schedule evaluation."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class EvaluationIssueType(str, Enum):
    """Supported schedule evaluation issue categories."""

    UNKNOWN_COURSE = "unknown_course"
    DUPLICATE_ASSIGNMENT = "duplicate_assignment"
    MISSING_ASSIGNMENT = "missing_assignment"
    COURSE_CONFLICT = "course_conflict"
    UNKNOWN_ROOM = "unknown_room"
    ROOM_DOUBLE_BOOKED = "room_double_booked"
    ROOM_CAPACITY = "room_capacity"
    ROOM_TYPE = "room_type"
    CAMPUS = "campus"


@dataclass(frozen=True)
class EvaluationIssue:
    """One issue found in a generated schedule."""

    issue_type: EvaluationIssueType
    severity: EvaluationSeverity
    message: str
    related_ids: Tuple[str, ...] = ()


@dataclass(frozen=True)
class ScheduleEvaluationResult:
    """Evaluation result returned to algorithms or web handlers."""

    score: int
    issues: Tuple[EvaluationIssue, ...]

    @property
    def is_feasible(self) -> bool:
        """Return whether the schedule has no hard errors."""

        return all(issue.severity != EvaluationSeverity.ERROR for issue in self.issues)

    @property
    def errors(self) -> Tuple[EvaluationIssue, ...]:
        """Return hard errors only."""

        return tuple(issue for issue in self.issues if issue.severity == EvaluationSeverity.ERROR)

    @property
    def warnings(self) -> Tuple[EvaluationIssue, ...]:
        """Return warnings only."""

        return tuple(issue for issue in self.issues if issue.severity == EvaluationSeverity.WARNING)


def evaluate_schedule(
    courses: Iterable[Course],
    assignments: Iterable[ScheduleAssignment],
    *,
    conflict_graph: Optional[ConflictGraph] = None,
    rooms: Iterable[Room] = (),
) -> ScheduleEvaluationResult:
    """Evaluate a generated schedule.

    The score starts at 100 and is reduced by hard errors and warnings. The
    current scoring is intentionally simple and can be tuned later after real
    scheduling goals are confirmed.
    """

    course_list = tuple(courses)
    assignment_list = tuple(assignments)
    room_list = tuple(rooms)

    course_by_id = {course.id: course for course in course_list}
    if len(course_by_id) != len(course_list):
        raise ValueError("Course ids must be unique for schedule evaluation")

    room_by_id = {room.id: room for room in room_list}
    if len(room_by_id) != len(room_list):
        raise ValueError("Room ids must be unique for schedule evaluation")

    graph = conflict_graph or build_conflict_graph(course_list)
    _ensure_graph_covers_courses(graph, course_list)

    issues = []
    assignment_by_course_id: Dict[str, ScheduleAssignment] = {}

    for assignment in assignment_list:
        if assignment.course_id not in course_by_id:
            issues.append(
                EvaluationIssue(
                    issue_type=EvaluationIssueType.UNKNOWN_COURSE,
                    severity=EvaluationSeverity.ERROR,
                    message="Assignment references an unknown course.",
                    related_ids=(assignment.course_id,),
                )
            )
            continue

        if assignment.course_id in assignment_by_course_id:
            issues.append(
                EvaluationIssue(
                    issue_type=EvaluationIssueType.DUPLICATE_ASSIGNMENT,
                    severity=EvaluationSeverity.ERROR,
                    message="A course has more than one assignment.",
                    related_ids=(assignment.course_id,),
                )
            )
            continue

        assignment_by_course_id[assignment.course_id] = assignment

    issues.extend(_find_missing_assignments(course_list, assignment_by_course_id))
    issues.extend(_find_course_time_conflicts(graph, assignment_by_course_id))
    issues.extend(_find_room_issues(course_by_id, assignment_list, room_by_id))

    score = _score_issues(issues)
    return ScheduleEvaluationResult(score=score, issues=tuple(issues))


def _find_missing_assignments(
    courses: Tuple[Course, ...],
    assignment_by_course_id: Mapping[str, ScheduleAssignment],
) -> Tuple[EvaluationIssue, ...]:
    issues = []
    for course in courses:
        if course.id not in assignment_by_course_id:
            issues.append(
                EvaluationIssue(
                    issue_type=EvaluationIssueType.MISSING_ASSIGNMENT,
                    severity=EvaluationSeverity.ERROR,
                    message="A course has no schedule assignment.",
                    related_ids=(course.id,),
                )
            )
    return tuple(issues)


def _find_course_time_conflicts(
    graph: ConflictGraph,
    assignment_by_course_id: Mapping[str, ScheduleAssignment],
) -> Tuple[EvaluationIssue, ...]:
    issues = []
    for edge in graph.edges:
        assignment_a = assignment_by_course_id.get(edge.course_a_id)
        assignment_b = assignment_by_course_id.get(edge.course_b_id)
        if assignment_a is None or assignment_b is None:
            continue
        if assignment_a.time_slot_id == assignment_b.time_slot_id:
            issues.append(
                EvaluationIssue(
                    issue_type=EvaluationIssueType.COURSE_CONFLICT,
                    severity=EvaluationSeverity.ERROR,
                    message="Conflicting courses are assigned to the same time slot.",
                    related_ids=(edge.course_a_id, edge.course_b_id, assignment_a.time_slot_id),
                )
            )
    return tuple(issues)


def _find_room_issues(
    course_by_id: Mapping[str, Course],
    assignments: Tuple[ScheduleAssignment, ...],
    room_by_id: Mapping[str, Room],
) -> Tuple[EvaluationIssue, ...]:
    issues = []
    room_time_usage: Dict[Tuple[str, str], str] = {}

    for assignment in assignments:
        course = course_by_id.get(assignment.course_id)
        if course is None or assignment.room_id is None:
            continue

        room = room_by_id.get(assignment.room_id)
        if room is None:
            issues.append(
                EvaluationIssue(
                    issue_type=EvaluationIssueType.UNKNOWN_ROOM,
                    severity=EvaluationSeverity.ERROR,
                    message="Assignment references an unknown room.",
                    related_ids=(assignment.course_id, assignment.room_id),
                )
            )
            continue

        usage_key = (assignment.room_id, assignment.time_slot_id)
        previous_course_id = room_time_usage.get(usage_key)
        if previous_course_id is not None:
            issues.append(
                EvaluationIssue(
                    issue_type=EvaluationIssueType.ROOM_DOUBLE_BOOKED,
                    severity=EvaluationSeverity.ERROR,
                    message="A room is assigned to multiple courses in the same time slot.",
                    related_ids=(previous_course_id, assignment.course_id, assignment.room_id, assignment.time_slot_id),
                )
            )
        else:
            room_time_usage[usage_key] = assignment.course_id

        if course.expected_students is not None and course.expected_students > room.capacity:
            issues.append(
                EvaluationIssue(
                    issue_type=EvaluationIssueType.ROOM_CAPACITY,
                    severity=EvaluationSeverity.ERROR,
                    message="The assigned room capacity is smaller than the expected student count.",
                    related_ids=(course.id, room.id),
                )
            )

        if course.required_room_type != room.room_type:
            issues.append(
                EvaluationIssue(
                    issue_type=EvaluationIssueType.ROOM_TYPE,
                    severity=EvaluationSeverity.WARNING,
                    message="The assigned room type does not match the course requirement.",
                    related_ids=(course.id, room.id),
                )
            )

        if course.required_campus is not None and room.campus is not None and course.required_campus != room.campus:
            issues.append(
                EvaluationIssue(
                    issue_type=EvaluationIssueType.CAMPUS,
                    severity=EvaluationSeverity.WARNING,
                    message="The assigned room campus does not match the course requirement.",
                    related_ids=(course.id, room.id),
                )
            )

    return tuple(issues)


def _score_issues(issues: Iterable[EvaluationIssue]) -> int:
    score = 100
    for issue in issues:
        if issue.severity == EvaluationSeverity.ERROR:
            score -= 20
        elif issue.severity == EvaluationSeverity.WARNING:
            score -= 5
    return max(score, 0)


def _ensure_graph_covers_courses(graph: ConflictGraph, courses: Tuple[Course, ...]) -> None:
    graph_node_ids = set(graph.node_ids)
    course_ids = {course.id for course in courses}
    if graph_node_ids != course_ids:
        raise ValueError("Conflict graph nodes must match the provided courses")
