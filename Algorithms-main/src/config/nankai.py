"""Nankai University scheduling configuration.

This module records only rule-level information provided by the project owner.
It intentionally contains no real course, teacher, class, or classroom data.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from src.models import Campus, TimeSlot


@dataclass(frozen=True)
class BreakRule:
    """Rest interval rule after a section group."""

    minutes: int
    reason: str
    after_section: Optional[int] = None


NANKAI_CAMPUSES: Tuple[Campus, ...] = (
    Campus.JINNAN,
    Campus.BALITAI,
)

NANKAI_WEEKDAYS: Tuple[int, ...] = tuple(range(1, 8))
NANKAI_SECTIONS_PER_DAY = 14
NANKAI_DAY_START = "08:00"
NANKAI_DAY_END = "22:00"
NANKAI_HAS_EVENING_CLASSES = True

NANKAI_DINNER_BREAK_START = "17:40"
NANKAI_DINNER_BREAK_END = "18:30"

NANKAI_DEFAULT_BREAK_MINUTES = 10
NANKAI_LONG_BREAK_MINUTES = 20
NANKAI_BREAK_RULES: Tuple[BreakRule, ...] = (
    BreakRule(minutes=20, reason="after first two morning sections", after_section=2),
    BreakRule(minutes=20, reason="after first two afternoon sections"),
)


def build_nankai_section_slots() -> Tuple[TimeSlot, ...]:
    """Create one single-section TimeSlot for each weekday and section.

    Exact section start/end timestamps are not filled here because the current
    project has not received an official Nankai timetable table. The known
    school-level rules are kept as constants above, and exact timestamps can be
    added later without changing downstream data structures.
    """

    slots = []
    for weekday in NANKAI_WEEKDAYS:
        for section in range(1, NANKAI_SECTIONS_PER_DAY + 1):
            slots.append(
                TimeSlot(
                    id=f"D{weekday}-S{section}",
                    weekday=weekday,
                    start_section=section,
                    end_section=section,
                    label=f"weekday {weekday}, section {section}",
                )
            )
    return tuple(slots)
