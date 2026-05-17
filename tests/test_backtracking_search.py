"""Unit tests for backtracking scheduling."""

import unittest

from src.algorithms import backtracking_schedule, greedy_color_schedule
from src.models import Course, TimeSlot


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


class BacktrackingScheduleTests(unittest.TestCase):
    def test_finds_complete_schedule(self):
        courses = (
            course("C001", "T001", ("G001",)),
            course("C002", "T001", ("G002",)),
            course("C003", "T003", ("G003",)),
        )
        time_slots = (slot("D1-S1", 1), slot("D1-S2", 2))

        result = backtracking_schedule(courses, time_slots)
        assignments = result.assignment_map()

        self.assertTrue(result.is_complete)
        self.assertIsNone(result.reason)
        self.assertNotEqual(assignments["C001"], assignments["C002"])
        self.assertIn(assignments["C003"], {"D1-S1", "D1-S2"})

    def test_can_find_solution_when_greedy_order_gets_stuck(self):
        courses = (
            course("C001", "T001", ("G001",), candidate_time_slot_ids=("D1-S1", "D1-S2")),
            course("C002", "T001", ("G002",), candidate_time_slot_ids=("D1-S1",)),
            course("C003", "T003", ("G001",), candidate_time_slot_ids=("D1-S1", "D1-S2")),
        )
        time_slots = (slot("D1-S1", 1), slot("D1-S2", 2))

        greedy_result = greedy_color_schedule(courses, time_slots)
        backtracking_result = backtracking_schedule(courses, time_slots)

        self.assertFalse(greedy_result.is_complete)
        self.assertTrue(backtracking_result.is_complete)
        self.assertEqual(backtracking_result.assignment_map()["C001"], "D1-S2")
        self.assertEqual(backtracking_result.assignment_map()["C002"], "D1-S1")

    def test_reports_no_solution_when_constraints_are_too_tight(self):
        courses = (
            course("C001", "T001", ("G001",)),
            course("C002", "T001", ("G002",)),
            course("C003", "T001", ("G003",)),
        )
        time_slots = (slot("D1-S1", 1), slot("D1-S2", 2))

        result = backtracking_schedule(courses, time_slots)

        self.assertFalse(result.is_complete)
        self.assertEqual(result.reason, "No feasible assignment found.")
        self.assertTrue(result.failed_course_ids)

    def test_reports_courses_without_candidates(self):
        courses = (
            course("C001", "T001", ("G001",), fixed_time_slot_id="UNKNOWN"),
        )
        time_slots = (slot("D1-S1", 1),)

        result = backtracking_schedule(courses, time_slots)

        self.assertFalse(result.is_complete)
        self.assertEqual(result.failed_course_ids, ("C001",))
        self.assertEqual(result.search_steps, 0)

    def test_rejects_invalid_max_steps(self):
        courses = (course("C001", "T001", ("G001",)),)
        time_slots = (slot("D1-S1", 1),)

        with self.assertRaises(ValueError):
            backtracking_schedule(courses, time_slots, max_steps=0)


if __name__ == "__main__":
    unittest.main()

