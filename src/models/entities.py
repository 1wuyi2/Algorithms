"""Core data models for the scheduling system.

These classes describe the entities used by later constraint checks,
conflict graph construction, and scheduling algorithms. They do not contain
any real school data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import FrozenSet, Optional, Tuple


class Campus(str, Enum):
    """Supported campus values for Nankai-oriented scheduling."""

    JINNAN = "jinnan"
    BALITAI = "balitai"


class RoomType(str, Enum):
    """Basic classroom categories used by courses and rooms."""

    GENERAL = "general"
    COMPUTER_LAB = "computer_lab"
    LAB = "lab"
    MULTIMEDIA = "multimedia"


@dataclass(frozen=True)
class TimeSlot:
    """A schedulable time block, such as Monday periods 1-2."""

    id: str
    weekday: int
    start_section: int
    end_section: int
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    label: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("TimeSlot.id cannot be empty")
        if self.weekday < 1 or self.weekday > 7:
            raise ValueError("TimeSlot.weekday must be between 1 and 7")
        if self.start_section <= 0 or self.end_section <= 0:
            raise ValueError("TimeSlot sections must be positive")
        if self.start_section > self.end_section:
            raise ValueError("TimeSlot.start_section cannot be greater than end_section")


@dataclass(frozen=True)
class Teacher:
    """Teacher information needed for scheduling constraints."""

    id: str
    name: str
    unavailable_time_slot_ids: FrozenSet[str] = field(default_factory=frozenset)
    available_course_ids: FrozenSet[str] = field(default_factory=frozenset)
    campus_preferences: FrozenSet[Campus] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("Teacher.id cannot be empty")
        if not self.name:
            raise ValueError("Teacher.name cannot be empty")
        object.__setattr__(self, "unavailable_time_slot_ids", frozenset(self.unavailable_time_slot_ids))
        object.__setattr__(self, "available_course_ids", frozenset(self.available_course_ids))
        object.__setattr__(self, "campus_preferences", frozenset(self.campus_preferences))


@dataclass(frozen=True)
class ClassGroup:
    """A student class, cohort, or teaching group."""

    id: str
    name: str
    major: Optional[str] = None
    grade: Optional[str] = None
    student_count: int = 0
    campus: Optional[Campus] = None
    unavailable_time_slot_ids: FrozenSet[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("ClassGroup.id cannot be empty")
        if not self.name:
            raise ValueError("ClassGroup.name cannot be empty")
        if self.student_count < 0:
            raise ValueError("ClassGroup.student_count cannot be negative")
        object.__setattr__(self, "unavailable_time_slot_ids", frozenset(self.unavailable_time_slot_ids))


@dataclass(frozen=True)
class Room:
    """Classroom information used for capacity and room-type constraints."""

    id: str
    name: str
    capacity: int
    room_type: RoomType = RoomType.GENERAL
    campus: Optional[Campus] = None
    building: Optional[str] = None
    available_time_slot_ids: FrozenSet[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("Room.id cannot be empty")
        if not self.name:
            raise ValueError("Room.name cannot be empty")
        if self.capacity <= 0:
            raise ValueError("Room.capacity must be positive")
        object.__setattr__(self, "available_time_slot_ids", frozenset(self.available_time_slot_ids))


@dataclass(frozen=True)
class Course:
    """A course section that needs to be scheduled."""

    id: str
    name: str
    teacher_id: str
    class_group_ids: Tuple[str, ...]
    weekly_hours: int
    required_room_type: RoomType = RoomType.GENERAL
    required_campus: Optional[Campus] = None
    expected_students: Optional[int] = None
    fixed_time_slot_id: Optional[str] = None
    candidate_time_slot_ids: Tuple[str, ...] = field(default_factory=tuple)
    required_consecutive_slots: int = 1

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("Course.id cannot be empty")
        if not self.name:
            raise ValueError("Course.name cannot be empty")
        if not self.teacher_id:
            raise ValueError("Course.teacher_id cannot be empty")
        if not self.class_group_ids:
            raise ValueError("Course.class_group_ids cannot be empty")
        if self.weekly_hours <= 0:
            raise ValueError("Course.weekly_hours must be positive")
        if self.expected_students is not None and self.expected_students < 0:
            raise ValueError("Course.expected_students cannot be negative")
        if self.required_consecutive_slots <= 0:
            raise ValueError("Course.required_consecutive_slots must be positive")
        object.__setattr__(self, "class_group_ids", tuple(self.class_group_ids))
        object.__setattr__(self, "candidate_time_slot_ids", tuple(self.candidate_time_slot_ids))


@dataclass(frozen=True)
class ScheduleAssignment:
    """A future scheduling result: course + time slot + room."""

    course_id: str
    time_slot_id: str
    room_id: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.course_id:
            raise ValueError("ScheduleAssignment.course_id cannot be empty")
        if not self.time_slot_id:
            raise ValueError("ScheduleAssignment.time_slot_id cannot be empty")

