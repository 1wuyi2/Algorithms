"""Unit tests for student-side course recommendation."""

import unittest

from src.models import ScheduleAssignment
from src.recommendation import RecommendableCourse, StudentProfile, recommend_courses


class StudentRecommenderTests(unittest.TestCase):
    def setUp(self):
        self.student = StudentProfile(
            id="S001",
            major="Computer Science",
            grade="2023",
            completed_course_ids=frozenset({"C001"}),
            interests=frozenset({"algorithm", "AI"}),
        )

    def test_ranks_matching_available_course_first(self):
        courses = (
            RecommendableCourse(
                id="C002",
                name="算法设计与分析",
                major_tags=("Computer Science",),
                grade_tags=("2023",),
                interest_tags=("algorithm",),
                prerequisite_course_ids=("C001",),
                time_slot_id="D1-S3",
            ),
            RecommendableCourse(
                id="C003",
                name="文学导论",
                major_tags=("Chinese Literature",),
                grade_tags=("2023",),
                interest_tags=("literature",),
                time_slot_id="D1-S4",
            ),
        )

        recommendations = recommend_courses(self.student, courses, top_k=2)

        self.assertEqual(recommendations[0].course_id, "C002")
        self.assertGreater(recommendations[0].score, recommendations[1].score)
        self.assertIn("algorithm", recommendations[0].matched_interest_tags)
        self.assertFalse(recommendations[0].has_time_conflict)

    def test_marks_time_conflict_and_can_filter_conflicted_courses(self):
        courses = (
            RecommendableCourse(
                id="C002",
                name="算法设计与分析",
                major_tags=("Computer Science",),
                grade_tags=("2023",),
                interest_tags=("algorithm",),
                time_slot_id="D1-S1",
            ),
            RecommendableCourse(
                id="C003",
                name="人工智能导论",
                major_tags=("Computer Science",),
                grade_tags=("2023",),
                interest_tags=("AI",),
                time_slot_id="D1-S2",
            ),
        )
        current_assignments = (ScheduleAssignment(course_id="C010", time_slot_id="D1-S1"),)

        recommendations = recommend_courses(self.student, courses, current_assignments, top_k=2)
        conflicted = next(item for item in recommendations if item.course_id == "C002")
        filtered = recommend_courses(
            self.student,
            courses,
            current_assignments,
            top_k=2,
            include_conflicted=False,
        )

        self.assertTrue(conflicted.has_time_conflict)
        self.assertTrue(any("时间冲突" in reason for reason in conflicted.reasons))
        self.assertEqual([item.course_id for item in filtered], ["C003"])

    def test_penalizes_completed_and_missing_prerequisite_courses(self):
        courses = (
            RecommendableCourse(
                id="C001",
                name="程序设计基础",
                major_tags=("Computer Science",),
                grade_tags=("2023",),
                interest_tags=("algorithm",),
                time_slot_id="D1-S3",
            ),
            RecommendableCourse(
                id="C004",
                name="高级机器学习",
                major_tags=("Computer Science",),
                grade_tags=("2023",),
                interest_tags=("AI",),
                prerequisite_course_ids=("C099",),
                time_slot_id="D1-S4",
            ),
        )

        recommendations = recommend_courses(self.student, courses, top_k=2)
        completed = next(item for item in recommendations if item.course_id == "C001")
        missing_prereq = next(item for item in recommendations if item.course_id == "C004")

        self.assertTrue(completed.is_completed)
        self.assertIn("C099", missing_prereq.missing_prerequisite_ids)
        self.assertTrue(any("缺少先修课程" in reason for reason in missing_prereq.reasons))

    def test_rejects_duplicate_candidate_course_ids(self):
        courses = (
            RecommendableCourse(id="C002", name="算法设计与分析"),
            RecommendableCourse(id="C002", name="算法实践"),
        )

        with self.assertRaises(ValueError):
            recommend_courses(self.student, courses)

    def test_rejects_non_positive_top_k(self):
        with self.assertRaises(ValueError):
            recommend_courses(self.student, (), top_k=0)


if __name__ == "__main__":
    unittest.main()

class StudentScheduleExtensionTests(unittest.TestCase):
    def test_fixed_courses_block_recommendation_time_slots(self):
        student = StudentProfile(
            id="S001",
            major="Computer Science",
            grade="2023",
            interests=frozenset({"system"}),
            fixed_course_ids=frozenset({"C007"}),
        )
        courses = (
            RecommendableCourse(
                id="C007",
                name="计算机组成原理",
                major_tags=("Computer Science",),
                grade_tags=("2023",),
                interest_tags=("system",),
                weekday=3,
                start_section=7,
                end_section=8,
                course_type="专业必修课",
            ),
            RecommendableCourse(
                id="C008",
                name="并行程序设计",
                major_tags=("Computer Science",),
                grade_tags=("2023",),
                interest_tags=("system",),
                weekday=3,
                start_section=8,
                end_section=10,
                course_type="专业选修课",
            ),
        )

        recommendations = recommend_courses(student, courses, include_conflicted=False)

        self.assertEqual(recommendations, ())

    def test_course_type_is_returned_in_recommendation(self):
        student = StudentProfile(id="S001", major="Computer Science", grade="2023")
        courses = (
            RecommendableCourse(
                id="C100",
                name="软件安全",
                major_tags=("Computer Science",),
                grade_tags=("2023",),
                course_type="专业选修课",
                weekday=2,
                start_section=3,
                end_section=4,
            ),
        )

        recommendations = recommend_courses(student, courses)

        self.assertEqual(recommendations[0].course_type, "专业选修课")
