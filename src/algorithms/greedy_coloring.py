"""Greedy graph-coloring scheduler.

The current scheduler assigns courses to time slots only. Rooms are intentionally
left for a later room-assignment module because they require imported classroom
capacity, type, campus, and availability data.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Mapping, Optional, Tuple

from src.graph import ConflictGraph, build_conflict_graph
from src.models import Course, ScheduleAssignment, TimeSlot


@dataclass(frozen=True)
class UnscheduledCourse:
    """A course that could not be assigned by the greedy scheduler."""

    course_id: str
    reason: str
    candidate_time_slot_ids: Tuple[str, ...] = ()
    blocking_course_ids: Tuple[str, ...] = ()


@dataclass(frozen=True)
class GreedyScheduleResult:
    """Result of greedy time-slot scheduling."""

    assignments: Tuple[ScheduleAssignment, ...]
    unscheduled: Tuple[UnscheduledCourse, ...]
    conflict_graph: ConflictGraph

    @property
    def is_complete(self) -> bool:
        """Return whether every course received a time slot."""

        return not self.unscheduled

    def assignment_map(self) -> Dict[str, str]:
        """Return course_id -> time_slot_id mapping for downstream code."""

        return {assignment.course_id: assignment.time_slot_id for assignment in self.assignments}


def greedy_color_schedule(
    courses: Iterable[Course],
    time_slots: Iterable[TimeSlot],
    *,
    conflict_graph: Optional[ConflictGraph] = None,
) -> GreedyScheduleResult:
    """Assign courses to time slots using a greedy graph-coloring strategy.

    Fixed-time courses are processed first, then remaining courses are ordered
    by descending graph degree. A course uses its fixed time slot if present;
    otherwise it uses candidate_time_slot_ids when provided, or all given time
    slots when no candidate list is specified.
    """

    course_list = tuple(courses)
    time_slot_list = tuple(time_slots)
    _ensure_unique_ids((course.id for course in course_list), "Course")
    _ensure_unique_ids((slot.id for slot in time_slot_list), "TimeSlot")

    time_slot_ids = tuple(slot.id for slot in time_slot_list)
    time_slot_id_set = set(time_slot_ids)
    graph = conflict_graph or build_conflict_graph(course_list)
    _ensure_graph_covers_courses(graph, course_list)

    assigned: Dict[str, str] = {}
    unscheduled = []

    ordered_courses = sorted(
        course_list,
        key=lambda course: (
            0 if course.fixed_time_slot_id else 1,
            -graph.degree(course.id),
            course.id,
        ),
    )

    for course in ordered_courses:
        candidate_ids = _candidate_time_slot_ids(course, time_slot_ids, time_slot_id_set)
        if not candidate_ids:
            unscheduled.append(
                UnscheduledCourse(
                    course_id=course.id,
                    reason=_no_candidate_reason(course, time_slot_ids),
                )
            )
            continue

        selected_time_slot_id = _first_feasible_time_slot(course.id, candidate_ids, graph, assigned)
        if selected_time_slot_id is None:
            blocking_course_ids = _blocking_course_ids(course.id, candidate_ids, graph, assigned)
            unscheduled.append(
                UnscheduledCourse(
                    course_id=course.id,
                    reason="All candidate time slots conflict with already scheduled neighboring courses.",
                    candidate_time_slot_ids=candidate_ids,
                    blocking_course_ids=blocking_course_ids,
                )
            )
            continue

        assigned[course.id] = selected_time_slot_id

    assignments = tuple(
        ScheduleAssignment(course_id=course.id, time_slot_id=assigned[course.id])
        for course in course_list
        if course.id in assigned
    )
    return GreedyScheduleResult(assignments=assignments, unscheduled=tuple(unscheduled), conflict_graph=graph)


def _candidate_time_slot_ids(
    course: Course,
    time_slot_ids: Tuple[str, ...],
    time_slot_id_set: set[str],
) -> Tuple[str, ...]:
    if course.fixed_time_slot_id is not None:
        return (course.fixed_time_slot_id,) if course.fixed_time_slot_id in time_slot_id_set else ()

    if course.candidate_time_slot_ids:
        return tuple(slot_id for slot_id in course.candidate_time_slot_ids if slot_id in time_slot_id_set)

    return time_slot_ids


def _no_candidate_reason(course: Course, time_slot_ids: Tuple[str, ...]) -> str:
    if not time_slot_ids:
        return "No time slots were provided."
    if course.fixed_time_slot_id is not None:
        return "The fixed time slot is not included in the available time slots."
    if course.candidate_time_slot_ids:
        return "None of the course candidate time slots are included in the available time slots."
    return "No available time slot candidates for this course."


def _first_feasible_time_slot(
    course_id: str,
    candidate_ids: Tuple[str, ...],
    graph: ConflictGraph,
    assigned: Mapping[str, str],
) -> Optional[str]:
    neighbor_ids = graph.neighbors(course_id)
    for time_slot_id in candidate_ids:
        if all(assigned.get(neighbor_id) != time_slot_id for neighbor_id in neighbor_ids):
            return time_slot_id
    return None


def _blocking_course_ids(
    course_id: str,
    candidate_ids: Tuple[str, ...],
    graph: ConflictGraph,
    assigned: Mapping[str, str],
) -> Tuple[str, ...]:
    blocking_ids = []
    candidate_id_set = set(candidate_ids)
    for neighbor_id in graph.neighbors(course_id):
        assigned_time_slot_id = assigned.get(neighbor_id)
        if assigned_time_slot_id in candidate_id_set:
            blocking_ids.append(neighbor_id)
    return tuple(sorted(blocking_ids))


def _ensure_unique_ids(ids: Iterable[str], entity_name: str) -> None:
    id_list = tuple(ids)
    if len(id_list) != len(set(id_list)):
        raise ValueError(f"{entity_name} ids must be unique")


def _ensure_graph_covers_courses(graph: ConflictGraph, courses: Tuple[Course, ...]) -> None:
    graph_node_ids = set(graph.node_ids)
    course_ids = {course.id for course in courses}
    if graph_node_ids != course_ids:
        raise ValueError("Conflict graph nodes must match the provided courses")
