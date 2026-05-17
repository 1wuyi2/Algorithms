"""Backtracking constraint-search scheduler.

This scheduler assigns courses to time slots with recursive search. It is meant
as a comparison and optimization baseline for the greedy graph-coloring result.
Like the greedy scheduler, the current version only assigns time slots and does
not allocate rooms yet.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Mapping, Optional, Tuple

from src.graph import ConflictGraph, build_conflict_graph
from src.models import Course, ScheduleAssignment, TimeSlot


@dataclass(frozen=True)
class BacktrackingScheduleResult:
    """Result of backtracking time-slot scheduling."""

    assignments: Tuple[ScheduleAssignment, ...]
    failed_course_ids: Tuple[str, ...]
    reason: Optional[str]
    conflict_graph: ConflictGraph
    search_steps: int

    @property
    def is_complete(self) -> bool:
        """Return whether every course received a time slot."""

        return not self.failed_course_ids

    def assignment_map(self) -> Dict[str, str]:
        """Return course_id -> time_slot_id mapping for downstream code."""

        return {assignment.course_id: assignment.time_slot_id for assignment in self.assignments}


def backtracking_schedule(
    courses: Iterable[Course],
    time_slots: Iterable[TimeSlot],
    *,
    conflict_graph: Optional[ConflictGraph] = None,
    max_steps: int = 100_000,
) -> BacktrackingScheduleResult:
    """Assign courses to time slots using recursive constraint search.

    The search uses a minimum-remaining-values heuristic: at each step it picks
    the unscheduled course with the fewest currently feasible time slots.
    """

    if max_steps <= 0:
        raise ValueError("max_steps must be positive")

    course_list = tuple(courses)
    time_slot_list = tuple(time_slots)
    _ensure_unique_ids((course.id for course in course_list), "Course")
    _ensure_unique_ids((slot.id for slot in time_slot_list), "TimeSlot")

    time_slot_ids = tuple(slot.id for slot in time_slot_list)
    time_slot_id_set = set(time_slot_ids)
    graph = conflict_graph or build_conflict_graph(course_list)
    _ensure_graph_covers_courses(graph, course_list)

    course_by_id = {course.id: course for course in course_list}
    candidates_by_course_id = {
        course.id: _candidate_time_slot_ids(course, time_slot_ids, time_slot_id_set)
        for course in course_list
    }
    failed_course_ids = tuple(
        course_id for course_id, candidate_ids in candidates_by_course_id.items()
        if not candidate_ids
    )
    if failed_course_ids:
        return BacktrackingScheduleResult(
            assignments=(),
            failed_course_ids=failed_course_ids,
            reason="Some courses have no available time slot candidates.",
            conflict_graph=graph,
            search_steps=0,
        )

    assigned: Dict[str, str] = {}
    steps = 0
    stopped_by_limit = False

    def search(unassigned_ids: Tuple[str, ...]) -> bool:
        nonlocal steps, stopped_by_limit

        if not unassigned_ids:
            return True
        if steps >= max_steps:
            stopped_by_limit = True
            return False

        course_id, feasible_ids = _select_next_course(unassigned_ids, candidates_by_course_id, graph, assigned)
        if not feasible_ids:
            return False

        remaining_ids = tuple(candidate_id for candidate_id in unassigned_ids if candidate_id != course_id)
        for time_slot_id in feasible_ids:
            steps += 1
            assigned[course_id] = time_slot_id
            if search(remaining_ids):
                return True
            assigned.pop(course_id, None)
            if stopped_by_limit:
                return False
        return False

    all_course_ids = tuple(course.id for course in course_list)
    solved = search(all_course_ids)

    if solved:
        assignments = tuple(
            ScheduleAssignment(course_id=course.id, time_slot_id=assigned[course.id])
            for course in course_list
        )
        return BacktrackingScheduleResult(
            assignments=assignments,
            failed_course_ids=(),
            reason=None,
            conflict_graph=graph,
            search_steps=steps,
        )

    unsolved_ids = tuple(course_id for course_id in all_course_ids if course_id not in assigned)
    reason = "Search stopped after reaching max_steps." if stopped_by_limit else "No feasible assignment found."
    return BacktrackingScheduleResult(
        assignments=tuple(
            ScheduleAssignment(course_id=course.id, time_slot_id=assigned[course.id])
            for course in course_list
            if course.id in assigned
        ),
        failed_course_ids=unsolved_ids or tuple(course_by_id.keys()),
        reason=reason,
        conflict_graph=graph,
        search_steps=steps,
    )


def _select_next_course(
    unassigned_ids: Tuple[str, ...],
    candidates_by_course_id: Mapping[str, Tuple[str, ...]],
    graph: ConflictGraph,
    assigned: Mapping[str, str],
) -> Tuple[str, Tuple[str, ...]]:
    ranked = []
    for course_id in unassigned_ids:
        feasible_ids = tuple(
            time_slot_id for time_slot_id in candidates_by_course_id[course_id]
            if _is_feasible(course_id, time_slot_id, graph, assigned)
        )
        ranked.append((len(feasible_ids), -graph.degree(course_id), course_id, feasible_ids))

    _, _, selected_course_id, selected_feasible_ids = min(ranked)
    return selected_course_id, selected_feasible_ids


def _is_feasible(
    course_id: str,
    time_slot_id: str,
    graph: ConflictGraph,
    assigned: Mapping[str, str],
) -> bool:
    return all(assigned.get(neighbor_id) != time_slot_id for neighbor_id in graph.neighbors(course_id))


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


def _ensure_unique_ids(ids: Iterable[str], entity_name: str) -> None:
    id_list = tuple(ids)
    if len(id_list) != len(set(id_list)):
        raise ValueError(f"{entity_name} ids must be unique")


def _ensure_graph_covers_courses(graph: ConflictGraph, courses: Tuple[Course, ...]) -> None:
    graph_node_ids = set(graph.node_ids)
    course_ids = {course.id for course in courses}
    if graph_node_ids != course_ids:
        raise ValueError("Conflict graph nodes must match the provided courses")
