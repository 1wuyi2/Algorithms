"""Student-side personalized course recommendation.

The recommender is intentionally rule-based at this stage. The project does not
have real student records, course catalogs, prerequisite graphs, or historical
selection data yet, so this module focuses on deterministic and explainable
scoring that can be tested without external dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import FrozenSet, Iterable, List, Optional, Tuple

from src.models import ScheduleAssignment


@dataclass(frozen=True)
class StudentProfile:
    """Minimal student profile used by the recommendation algorithm."""

    id: str
    major: str
    grade: str
    completed_course_ids: frozenset[str] = field(default_factory=frozenset)
    interests: frozenset[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("StudentProfile.id cannot be empty")
        object.__setattr__(self, "major", self.major.strip())
        object.__setattr__(self, "grade", self.grade.strip())
        object.__setattr__(
            self,
            "completed_course_ids",
            frozenset(str(course_id).strip() for course_id in self.completed_course_ids if str(course_id).strip()),
        )
        object.__setattr__(
            self,
            "interests",
            frozenset(str(interest).strip() for interest in self.interests if str(interest).strip()),
        )


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
        if self.credit is not None and self.credit < 0:
            raise ValueError("RecommendableCourse.credit cannot be negative")


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


def recommend_courses(
    student: StudentProfile,
    candidate_courses: Iterable[RecommendableCourse],
    current_assignments: Iterable[ScheduleAssignment] = (),
    *,
    top_k: int = 5,
    include_conflicted: bool = True,
) -> Tuple[CourseRecommendation, ...]:
    """Rank candidate courses for a student.

    The scoring model combines curriculum fit, student interest, course history,
    prerequisite readiness, and time conflict checks. It returns the top-k
    results sorted by score from high to low. Conflicted courses are kept by
    default because the student UI needs to explain why a useful course may not
    be immediately selectable.
    """

    if top_k <= 0:
        raise ValueError("top_k must be positive")

    course_list = tuple(candidate_courses)
    _ensure_unique_course_ids(course_list)

    assignment_list = tuple(current_assignments)
    occupied_time_slot_ids = {assignment.time_slot_id for assignment in assignment_list}
    currently_selected_course_ids = {assignment.course_id for assignment in assignment_list}

    recommendations = tuple(
        _score_course(
            student,
            course,
            occupied_time_slot_ids=occupied_time_slot_ids,
            currently_selected_course_ids=currently_selected_course_ids,
        )
        for course in course_list
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
            item.course_name,
            item.course_id,
        ),
    )
    return tuple(ranked[:top_k])


def _score_course(
    student: StudentProfile,
    course: RecommendableCourse,
    *,
    occupied_time_slot_ids: set[str],
    currently_selected_course_ids: set[str],
) -> CourseRecommendation:
    score = 0
    reasons: List[str] = []
    normalized_major = _normalize(student.major)
    normalized_grade = _normalize(student.grade)
    normalized_interests = {_normalize(item) for item in student.interests}
    normalized_completed_ids = {_normalize(item) for item in student.completed_course_ids}

    major_tags = {_normalize(item) for item in course.major_tags}
    grade_tags = {_normalize(item) for item in course.grade_tags}
    interest_tag_map = {_normalize(item): item for item in course.interest_tags}
    prerequisite_ids = {_normalize(item) for item in course.prerequisite_course_ids}

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

    is_completed = _normalize(course.id) in normalized_completed_ids
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

    has_time_conflict = bool(course.time_slot_id and course.time_slot_id in occupied_time_slot_ids)
    if has_time_conflict:
        score -= 50
        reasons.append(f"该课程与已有课表存在时间冲突：{course.time_slot_id}")
    elif course.time_slot_id:
        score += 10
        reasons.append(f"该课程时间段可选：{course.time_slot_id}")
    else:
        reasons.append("该课程暂未提供明确上课时间，后续需结合正式课表确认")

    is_currently_selected = course.id in currently_selected_course_ids
    if is_currently_selected:
        score -= 100
        reasons.append("该课程已在当前课表中，不重复推荐")

    if course.category:
        reasons.append(f"课程类别：{course.category}")

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
    )


def _clean_tuple(values: Iterable[object]) -> Tuple[str, ...]:
    return tuple(str(value).strip() for value in values if str(value).strip())


def _normalize(value: object) -> str:
    return str(value).strip().casefold()


def _ensure_unique_course_ids(courses: Tuple[RecommendableCourse, ...]) -> None:
    ids = [course.id for course in courses]
    if len(ids) != len(set(ids)):
        raise ValueError("RecommendableCourse ids must be unique")
