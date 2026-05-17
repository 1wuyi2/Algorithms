"""Unit tests for greedy graph-coloring scheduling."""

import unittest

from src.algorithms import greedy_color_schedule
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


class GreedyColoringTests(unittest.TestCase):
    def test_assigns_conflicting_courses_to_different_time_slots(self):
        courses = (
            course("C001", "T001", ("G001",)),
            course("C002", "T001", ("G002",)),
            course("C003", "T003", ("G003",)),
        )
        time_slots = (slot("D1-S1", 1), slot("D1-S2", 2))

        result = greedy_color_schedule(courses, time_slots)
        assignments = result.assignment_map()

        self.assertTrue(result.is_complete)
        self.assertNotEqual(assignments["C001"], assignments["C002"])
        self.assertIn(assignments["C003"], {"D1-S1", "D1-S2"})

    def test_respects_fixed_time_slots(self):
        courses = (
            course("C001", "T001", ("G001",), fixed_time_slot_id="D1-S1"),
            course("C002", "T001", ("G002",)),
        )
        time_slots = (slot("D1-S1", 1), slot("D1-S2", 2))

        result = greedy_color_schedule(courses, time_slots)
        assignments = result.assignment_map()

        self.assertTrue(result.is_complete)
        self.assertEqual(assignments["C001"], "D1-S1")
        self.assertEqual(assignments["C002"], "D1-S2")

    def test_respects_candidate_time_slots(self):
        courses = (
            course("C001", "T001", ("G001",), candidate_time_slot_ids=("D1-S2",)),
            course("C002", "T002", ("G002",)),
        )
        time_slots = (slot("D1-S1", 1), slot("D1-S2", 2))

        result = greedy_color_schedule(courses, time_slots)
        assignments = result.assignment_map()

        self.assertTrue(result.is_complete)
        self.assertEqual(assignments["C001"], "D1-S2")

    def test_reports_unscheduled_courses_when_slots_are_insufficient(self):
        courses = (
            course("C001", "T001", ("G001",)),
            course("C002", "T001", ("G002",)),
            course("C003", "T001", ("G003",)),
        )
        time_slots = (slot("D1-S1", 1), slot("D1-S2", 2))

        result = greedy_color_schedule(courses, time_slots)

        self.assertFalse(result.is_complete)
        self.assertEqual(len(result.assignments), 2)
        self.assertEqual(len(result.unscheduled), 1)
        self.assertEqual(result.unscheduled[0].course_id, "C003")

    def test_rejects_duplicate_time_slot_ids(self):
        courses = (course("C001", "T001", ("G001",)),)
        time_slots = (slot("D1-S1", 1), slot("D1-S1", 2))

        with self.assertRaises(ValueError):
            greedy_color_schedule(courses, time_slots)


if __name__ == "__main__":
    unittest.main()
