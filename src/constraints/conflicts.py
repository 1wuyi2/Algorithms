"""Conflict detection for courses and tentative assignments.

This module is intentionally data-agnostic: it only checks the model objects
passed in by callers. Real school data or imported educational records should
be supplied by later data modules or web APIs.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Optional, Tuple

from src.models import ClassGroup, Course, Room, ScheduleAssignment, Teacher


class ConflictType(str, Enum):
    """Supported conflict categories."""

    SAME_TEACHER = "same_teacher"
    SAME_CLASS_GROUP = "same_class_group"
    SAME_FIXED_TIME = "same_fixed_time"
    TEACHER_UNAVAILABLE = "teacher_unavailable"
    ROOM_UNAVAILABLE = "room_unavailable"
    ROOM_CAPACITY = "room_capacity"
    ROOM_TYPE = "room_type"
    CAMPUS = "campus"
    CLASS_GROUP_UNAVAILABLE = "class_group_unavailable"


@dataclass(frozen=True)
class ConflictReason:
    """A single conflict reason that can be shown in logs or web pages."""

    conflict_type: ConflictType
    message: str
    related_ids: Tuple[str, ...] = ()


@dataclass(frozen=True)
class ConflictCheckResult:
    """Result returned by conflict checking functions."""

    has_conflict: bool
    reasons: Tuple[ConflictReason, ...] = ()


def find_course_conflicts(
    course_a: Course,
    course_b: Course,
    *,
    include_same_fixed_time: bool = True,
) -> ConflictCheckResult:
    """Check whether two courses conflict with each other.

    The result is suitable for debugging and future web display because it
    keeps all detected reasons instead of returning only True or False.
    """

    reasons = []

    if course_a.teacher_id == course_b.teacher_id:
        reasons.append(
            ConflictReason(
                conflict_type=ConflictType.SAME_TEACHER,
                message="Two courses use the same teacher.",
                related_ids=(course_a.teacher_id,),
            )
        )

    shared_class_group_ids = tuple(sorted(set(course_a.class_group_ids) & set(course_b.class_group_ids)))
    if shared_class_group_ids:
        reasons.append(
            ConflictReason(
                conflict_type=ConflictType.SAME_CLASS_GROUP,
                message="Two courses include the same class group.",
                related_ids=shared_class_group_ids,
            )
        )

    if (
        include_same_fixed_time
        and course_a.fixed_time_slot_id is not None
        and course_a.fixed_time_slot_id == course_b.fixed_time_slot_id
    ):
        reasons.append(
            ConflictReason(
                conflict_type=ConflictType.SAME_FIXED_TIME,
                message="Two courses are fixed to the same time slot.",
                related_ids=(course_a.fixed_time_slot_id,),
            )
        )

    return ConflictCheckResult(has_conflict=bool(reasons), reasons=tuple(reasons))


def has_conflict(course_a: Course, course_b: Course) -> bool:
    """Return only whether two courses conflict."""

    return find_course_conflicts(course_a, course_b).has_conflict


def find_assignment_conflicts(
    course: Course,
    assignment: ScheduleAssignment,
    *,
    room: Optional[Room] = None,
    teacher: Optional[Teacher] = None,
    class_groups: Iterable[ClassGroup] = (),
) -> ConflictCheckResult:
    """Check whether one tentative course assignment violates known constraints.

    This function is prepared for later scheduling and web workflows. It can be
    called with only the data currently available; unknown objects are simply
    skipped instead of being guessed.
    """

    reasons = []

    if assignment.course_id != course.id:
        raise ValueError("assignment.course_id must match course.id")

    if teacher is not None and assignment.time_slot_id in teacher.unavailable_time_slot_ids:
        reasons.append(
            ConflictReason(
                conflict_type=ConflictType.TEACHER_UNAVAILABLE,
                message="The teacher is unavailable in the assigned time slot.",
                related_ids=(teacher.id, assignment.time_slot_id),
            )
        )

    if room is not None:
        if room.available_time_slot_ids and assignment.time_slot_id not in room.available_time_slot_ids:
            reasons.append(
                ConflictReason(
                    conflict_type=ConflictType.ROOM_UNAVAILABLE,
                    message="The room is unavailable in the assigned time slot.",
                    related_ids=(room.id, assignment.time_slot_id),
                )
            )

        if course.expected_students is not None and course.expected_students > room.capacity:
            reasons.append(
                ConflictReason(
                    conflict_type=ConflictType.ROOM_CAPACITY,
                    message="The expected student count exceeds the room capacity.",
                    related_ids=(course.id, room.id),
                )
            )

        if course.required_room_type != room.room_type:
            reasons.append(
                ConflictReason(
                    conflict_type=ConflictType.ROOM_TYPE,
                    message="The room type does not satisfy the course requirement.",
                    related_ids=(course.id, room.id),
                )
            )

        if course.required_campus is not None and room.campus is not None and course.required_campus != room.campus:
            reasons.append(
                ConflictReason(
                    conflict_type=ConflictType.CAMPUS,
                    message="The room campus does not match the course campus requirement.",
                    related_ids=(course.id, room.id),
                )
            )

    for class_group in class_groups:
        if assignment.time_slot_id in getattr(class_group, "unavailable_time_slot_ids", frozenset()):
            reasons.append(
                ConflictReason(
                    conflict_type=ConflictType.CLASS_GROUP_UNAVAILABLE,
                    message="The class group is unavailable in the assigned time slot.",
                    related_ids=(class_group.id, assignment.time_slot_id),
                )
            )

    return ConflictCheckResult(has_conflict=bool(reasons), reasons=tuple(reasons))

