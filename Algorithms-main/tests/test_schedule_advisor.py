"""Unit tests for AI-assisted scheduling advisor."""

import unittest

from src.assistant import AdvisorRiskLevel, analyze_schedule
from src.models import Course, ScheduleAssignment, TimeSlot


def slot(slot_id, section):
    return TimeSlot(id=slot_id, weekday=1, start_section=section, end_section=section)


def course(course_id, teacher_id, class_group_ids, **kwargs):
    return Course(
        id=course_id,
        name=f"Course {course_id}",
        teacher_id=teacher_id,
        class_group_ids=tuple(class_group_ids),
        weekly_hours=2,
        **kwargs,
    )


class ScheduleAdvisorTests(unittest.TestCase):
    def test_reports_low_risk_for_feasible_schedule(self):
        courses = (
            course("C001", "T001", ("G001",)),
            course("C002", "T001", ("G002",)),
        )
        assignments = (
            ScheduleAssignment(course_id="C001", time_slot_id="D1-S1"),
            ScheduleAssignment(course_id="C002", time_slot_id="D1-S2"),
        )
        insight = analyze_schedule(courses, (slot("D1-S1", 1), slot("D1-S2", 2)), assignments=assignments)

        self.assertEqual(insight.risk_level, AdvisorRiskLevel.LOW)
        self.assertEqual(insight.metrics["evaluation_score"], 100)
        self.assertTrue(insight.suggestions)

    def test_detects_tight_constraints_without_assignments(self):
        courses = (
            course("C001", "T001", ("G001",), candidate_time_slot_ids=("D1-S1", "D1-S2")),
            course("C002", "T001", ("G002",), candidate_time_slot_ids=("D1-S1",)),
            course("C003", "T003", ("G001",), candidate_time_slot_ids=("D1-S1", "D1-S2")),
        )
        insight = analyze_schedule(courses, (slot("D1-S1", 1), slot("D1-S2", 2)))
        suggestion_titles = {suggestion.title for suggestion in insight.suggestions}

        self.assertEqual(insight.metrics["greedy_complete"], False)
        self.assertEqual(insight.metrics["backtracking_complete"], True)
        self.assertIn("使用回溯结果替代贪心结果", suggestion_titles)


if __name__ == "__main__":
    unittest.main()
