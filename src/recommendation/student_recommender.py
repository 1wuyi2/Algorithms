"""Student-side personalized course recommendation.

This module provides a deterministic recommendation layer for the student
course-selection page. It supports imported student schedules, fixed selected
courses, course type labels, and time-conflict filtering.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Optional, Protocol, Tuple

from src.models import ScheduleAssignment


class ScheduleLike(Protocol):
    """Minimal protocol shared by schedule entries used for conflict checks."""

    course_id: str
    time_slot_id: str


@dataclass(frozen=True)
class StudentProfile:
    """Minimal student profile used by the recommendation algorithm."""

    id: str
    major: str
    grade: str
    completed_course_ids: frozenset[str] = field(default_factory=frozenset)
    interests: frozenset[str] = field(default_factory=frozenset)
    fixed_course_ids: frozenset[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("StudentProfile.id cannot be empty")
        object.__setattr__(self, "major", self.major.strip())
        object.__setattr__(self, "grade", self.grade.strip())
        object.__setattr__(self, "completed_course_ids", _clean_frozenset(self.completed_course_ids))
        object.__setattr__(self, "interests", _clean_frozenset(self.interests))
        object.__setattr__(self, "fixed_course_ids", _clean_frozenset(self.fixed_course_ids))


@dataclass(frozen=True)
class StudentScheduleItem:
    """A course already occupying the student's personal timetable.

    It is intentionally richer than ScheduleAssignment so the student page can
    display imported timetable information such as course name, teacher,
    classroom, weekday, sections and course type.
    """

    course_id: str
    time_slot_id: str
    course_name: str = ""
    weekday: Optional[int] = None
    start_section: Optional[int] = None
    end_section: Optional[int] = None
    weeks: Optional[str] = None
    teacher_name: Optional[str] = None
    classroom: Optional[str] = None
    course_type: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.course_id:
            raise ValueError("StudentScheduleItem.course_id cannot be empty")
        if not self.time_slot_id:
            raise ValueError("StudentScheduleItem.time_slot_id cannot be empty")
        if self.weekday is not None and (self.weekday < 1 or self.weekday > 7):
            raise ValueError("StudentScheduleItem.weekday must be between 1 and 7")
        if self.start_section is not None and self.start_section <= 0:
            raise ValueError("StudentScheduleItem.start_section must be positive")
        if self.end_section is not None and self.end_section <= 0:
            raise ValueError("StudentScheduleItem.end_section must be positive")
        if (
            self.start_section is not None
            and self.end_section is not None
            and self.start_section > self.end_section
        ):
            raise ValueError("StudentScheduleItem.start_section cannot be greater than end_section")
        object.__setattr__(self, "course_name", self.course_name.strip())
        object.__setattr__(self, "weeks", self.weeks.strip() if self.weeks else None)
        object.__setattr__(self, "teacher_name", self.teacher_name.strip() if self.teacher_name else None)
        object.__setattr__(self, "classroom", self.classroom.strip() if self.classroom else None)
        object.__setattr__(self, "course_type", self.course_type.strip() if self.course_type else None)


@dataclass(frozen=True)
class RecommendableCourse:
    """A course candidate enriched with student-recommendation metadata."""

    id: str
    name: str
    major_tags: Tuple[str, ...] = ()
    grade_tags: Tuple[str, ...] = ()
    interest_tags: Tuple[str, ...] = ()
    time_slot_id: Optional[str] = None
    prerequisite_course_ids: Tuple[str, ...] = ()
    category: Optional[str] = None
    credit: Optional[float] = None
    course_type: Optional[str] = None
    teacher_name: Optional[str] = None
    classroom: Optional[str] = None
    weekday: Optional[int] = None
    start_section: Optional[int] = None
    end_section: Optional[int] = None
    weeks: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("RecommendableCourse.id cannot be empty")
        if not self.name:
            raise ValueError("RecommendableCourse.name cannot be empty")
        object.__setattr__(self, "major_tags", _clean_tuple(self.major_tags))
        object.__setattr__(self, "grade_tags", _clean_tuple(self.grade_tags))
        object.__setattr__(self, "interest_tags", _clean_tuple(self.interest_tags))
        object.__setattr__(self, "prerequisite_course_ids", _clean_tuple(self.prerequisite_course_ids))
        object.__setattr__(self, "time_slot_id", self.time_slot_id.strip() if self.time_slot_id else None)
        object.__setattr__(self, "category", self.category.strip() if self.category else None)
        object.__setattr__(self, "course_type", self.course_type.strip() if self.course_type else None)
        object.__setattr__(self, "teacher_name", self.teacher_name.strip() if self.teacher_name else None)
        object.__setattr__(self, "classroom", self.classroom.strip() if self.classroom else None)
        object.__setattr__(self, "weeks", self.weeks.strip() if self.weeks else None)
        if self.weekday is not None and (self.weekday < 1 or self.weekday > 7):
            raise ValueError("RecommendableCourse.weekday must be between 1 and 7")
        if self.start_section is not None and self.start_section <= 0:
            raise ValueError("RecommendableCourse.start_section must be positive")
        if self.end_section is not None and self.end_section <= 0:
            raise ValueError("RecommendableCourse.end_section must be positive")
        if (
            self.start_section is not None
            and self.end_section is not None
            and self.start_section > self.end_section
        ):
            raise ValueError("RecommendableCourse.start_section cannot be greater than end_section")
        if self.credit is not None and self.credit < 0:
            raise ValueError("RecommendableCourse.credit cannot be negative")

    @property
    def display_course_type(self) -> Optional[str]:
        """Return the course type shown to students."""

        return self.course_type or self.category


@dataclass(frozen=True)
class CourseRecommendation:
    """Scored recommendation result for one candidate course."""

    course_id: str
    course_name: str
    score: int
    has_time_conflict: bool
    reasons: Tuple[str, ...]
    time_slot_id: Optional[str] = None
    matched_interest_tags: Tuple[str, ...] = ()
    missing_prerequisite_ids: Tuple[str, ...] = ()
    is_completed: bool = False
    is_currently_selected: bool = False
    is_fixed_selected: bool = False
    course_type: Optional[str] = None
    credit: Optional[float] = None
    teacher_name: Optional[str] = None
    classroom: Optional[str] = None
    weekday: Optional[int] = None
    start_section: Optional[int] = None
    end_section: Optional[int] = None
    weeks: Optional[str] = None


def recommend_courses(
    student: StudentProfile,
    candidate_courses: Iterable[RecommendableCourse],
    current_assignments: Iterable[ScheduleAssignment | StudentScheduleItem] = (),
    *,
    top_k: int = 5,
    include_conflicted: bool = True,
    fixed_course_ids: Iterable[str] = (),
    exclude_selected: bool = True,
) -> Tuple[CourseRecommendation, ...]:
    """Rank candidate courses for a student.

    Existing schedule items and fixed selected courses are treated as occupied
    time blocks. Candidate courses that overlap with those blocks can either be
    returned with conflict labels or filtered out by setting include_conflicted
    to False.
    """

    if top_k <= 0:
        raise ValueError("top_k must be positive")

    course_list = tuple(candidate_courses)
    _ensure_unique_course_ids(course_list)

    assignment_list = tuple(current_assignments)
    fixed_ids = _clean_frozenset(tuple(student.fixed_course_ids) + tuple(fixed_course_ids))
    course_map = {_normalize(course.id): course for course in course_list}

    occupied_blocks = [_block_from_schedule_item(item) for item in assignment_list]
    occupied_blocks.extend(
        _block_from_course(course_map[course_id])
        for course_id in sorted(_normalize(item) for item in fixed_ids)
        if course_id in course_map
    )
    occupied_blocks = [block for block in occupied_blocks if block is not None]

    currently_selected_course_ids = {_normalize(item.course_id) for item in assignment_list}
    fixed_normalized_ids = {_normalize(item) for item in fixed_ids}

    recommendations = tuple(
        _score_course(
            student,
            course,
            occupied_blocks=occupied_blocks,
            currently_selected_course_ids=currently_selected_course_ids,
            fixed_course_ids=fixed_normalized_ids,
        )
        for course in course_list
    )
    if exclude_selected:
        recommendations = tuple(
            item for item in recommendations if not item.is_currently_selected and not item.is_fixed_selected
        )
    if not include_conflicted:
        recommendations = tuple(item for item in recommendations if not item.has_time_conflict)

    ranked = sorted(
        recommendations,
        key=lambda item: (
            -item.score,
            item.has_time_conflict,
            item.is_completed,
            item.is_currently_selected,
            item.is_fixed_selected,
            item.course_name,
            item.course_id,
        ),
    )
    return tuple(ranked[:top_k])


def build_fixed_schedule_items(
    candidate_courses: Iterable[RecommendableCourse],
    fixed_course_ids: Iterable[str],
) -> Tuple[StudentScheduleItem, ...]:
    """Convert fixed selected course ids into schedule items for display."""

    course_map = {_normalize(course.id): course for course in candidate_courses}
    items: list[StudentScheduleItem] = []
    for course_id in _clean_tuple(fixed_course_ids):
        normalized = _normalize(course_id)
        course = course_map.get(normalized)
        if course is None:
            continue
        items.append(_schedule_item_from_course(course))
    return tuple(items)


def _score_course(
    student: StudentProfile,
    course: RecommendableCourse,
    *,
    occupied_blocks: list[dict[str, object]],
    currently_selected_course_ids: set[str],
    fixed_course_ids: set[str],
) -> CourseRecommendation:
    score = 0
    reasons: list[str] = []
    normalized_major = _normalize(student.major)
    normalized_grade = _normalize(student.grade)
    normalized_interests = {_normalize(item) for item in student.interests}
    normalized_completed_ids = {_normalize(item) for item in student.completed_course_ids}

    major_tags = {_normalize(item) for item in course.major_tags}
    grade_tags = {_normalize(item) for item in course.grade_tags}
    interest_tag_map = {_normalize(item): item for item in course.interest_tags}

    if normalized_major and major_tags:
        if normalized_major in major_tags:
            score += 30
            reasons.append(f"课程与学生专业匹配：{student.major}")
        else:
            score -= 10
            reasons.append("课程专业标签与学生专业不完全匹配")

    if normalized_grade and grade_tags:
        if normalized_grade in grade_tags:
            score += 20
            reasons.append(f"课程适合学生年级：{student.grade}")
        else:
            score -= 5
            reasons.append("课程年级标签与学生当前年级不完全匹配")

    matched_interest_keys = sorted(normalized_interests.intersection(interest_tag_map.keys()))
    matched_interest_tags = tuple(interest_tag_map[key] for key in matched_interest_keys)
    if matched_interest_tags:
        score += min(36, 12 * len(matched_interest_tags))
        reasons.append(f"命中兴趣方向：{', '.join(matched_interest_tags)}")
    elif course.interest_tags and student.interests:
        reasons.append("暂未命中学生填写的兴趣方向")

    normalized_course_id = _normalize(course.id)
    is_completed = normalized_course_id in normalized_completed_ids
    if is_completed:
        score -= 100
        reasons.append("学生已修读该课程，因此降低重复推荐优先级")
    else:
        score += 15
        reasons.append("学生尚未修读该课程")

    missing_prerequisite_ids = tuple(
        course_id
        for course_id in course.prerequisite_course_ids
        if _normalize(course_id) not in normalized_completed_ids
    )
    if missing_prerequisite_ids:
        score -= 30 * len(missing_prerequisite_ids)
        reasons.append(f"缺少先修课程：{', '.join(missing_prerequisite_ids)}")
    elif course.prerequisite_course_ids:
        score += 10
        reasons.append("先修课程已满足")

    is_currently_selected = normalized_course_id in currently_selected_course_ids
    is_fixed_selected = normalized_course_id in fixed_course_ids
    if is_currently_selected:
        score -= 100
        reasons.append("该课程已在当前课表中，不重复推荐")
    if is_fixed_selected:
        score -= 100
        reasons.append("该课程已被设为固定必选课，不重复推荐")

    has_time_conflict = _has_time_conflict(course, occupied_blocks)
    if has_time_conflict:
        score -= 50
        reasons.append("该课程与已有课表或固定必选课存在时间冲突")
    elif course.time_slot_id or course.weekday:
        score += 10
        reasons.append("该课程时间段可选")
    else:
        reasons.append("该课程暂未提供明确上课时间，后续需结合正式课表确认")

    course_type = course.display_course_type
    if course_type:
        reasons.append(f"课程类型：{course_type}")

    return CourseRecommendation(
        course_id=course.id,
        course_name=course.name,
        score=score,
        has_time_conflict=has_time_conflict,
        reasons=tuple(reasons),
        time_slot_id=course.time_slot_id,
        matched_interest_tags=matched_interest_tags,
        missing_prerequisite_ids=missing_prerequisite_ids,
        is_completed=is_completed,
        is_currently_selected=is_currently_selected,
        is_fixed_selected=is_fixed_selected,
        course_type=course_type,
        credit=course.credit,
        teacher_name=course.teacher_name,
        classroom=course.classroom,
        weekday=course.weekday,
        start_section=course.start_section,
        end_section=course.end_section,
        weeks=course.weeks,
    )


def _has_time_conflict(course: RecommendableCourse, occupied_blocks: list[dict[str, object]]) -> bool:
    course_block = _block_from_course(course)
    if course_block is None:
        return False
    for block in occupied_blocks:
        if _blocks_overlap(course_block, block):
            return True
    return False


def _blocks_overlap(left: dict[str, object], right: dict[str, object]) -> bool:
    left_id = left.get("time_slot_id")
    right_id = right.get("time_slot_id")
    if left_id and right_id and left_id == right_id:
        return True

    left_weekday = left.get("weekday")
    right_weekday = right.get("weekday")
    if not left_weekday or not right_weekday or left_weekday != right_weekday:
        return False

    left_start = left.get("start_section")
    left_end = left.get("end_section")
    right_start = right.get("start_section")
    right_end = right.get("end_section")
    if not all(isinstance(value, int) for value in (left_start, left_end, right_start, right_end)):
        return False
    return int(left_start) <= int(right_end) and int(right_start) <= int(left_end)


def _block_from_course(course: RecommendableCourse) -> dict[str, object] | None:
    if not course.time_slot_id and course.weekday is None:
        return None
    return {
        "time_slot_id": course.time_slot_id,
        "weekday": course.weekday,
        "start_section": course.start_section,
        "end_section": course.end_section,
    }


def _block_from_schedule_item(item: ScheduleAssignment | StudentScheduleItem) -> dict[str, object] | None:
    if isinstance(item, StudentScheduleItem):
        return {
            "time_slot_id": item.time_slot_id,
            "weekday": item.weekday,
            "start_section": item.start_section,
            "end_section": item.end_section,
        }
    return {
        "time_slot_id": item.time_slot_id,
        "weekday": None,
        "start_section": None,
        "end_section": None,
    }


def _schedule_item_from_course(course: RecommendableCourse) -> StudentScheduleItem:
    return StudentScheduleItem(
        course_id=course.id,
        course_name=course.name,
        time_slot_id=course.time_slot_id or _generated_time_slot_id(course.weekday, course.start_section, course.end_section),
        weekday=course.weekday,
        start_section=course.start_section,
        end_section=course.end_section,
        weeks=course.weeks,
        teacher_name=course.teacher_name,
        classroom=course.classroom,
        course_type=course.display_course_type,
    )


def _generated_time_slot_id(weekday: Optional[int], start_section: Optional[int], end_section: Optional[int]) -> str:
    if weekday and start_section and end_section:
        return f"D{weekday}-S{start_section}-{end_section}"
    return "unknown-time-slot"


def _clean_tuple(values: Iterable[object]) -> Tuple[str, ...]:
    return tuple(str(value).strip() for value in values if str(value).strip())


def _clean_frozenset(values: Iterable[object]) -> frozenset[str]:
    return frozenset(_clean_tuple(values))


def _normalize(value: object) -> str:
    return str(value).strip().casefold()


def _ensure_unique_course_ids(courses: Tuple[RecommendableCourse, ...]) -> None:
    ids = [course.id for course in courses]
    if len(ids) != len(set(ids)):
        raise ValueError("RecommendableCourse ids must be unique")
