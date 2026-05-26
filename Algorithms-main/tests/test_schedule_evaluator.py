"""Unit tests for schedule evaluation."""

import unittest

from src.evaluation import EvaluationIssueType, evaluate_schedule
from src.models import Campus, Course, Room, RoomType, ScheduleAssignment, TimeSlot


def course(course_id, teacher_id, class_group_ids, **kwargs):
    return Course(
        id=course_id,
        name=f"Course {course_id}",
        teacher_id=teacher_id,
        class_group_ids=tuple(class_group_ids),
        weekly_hours=2,
        **kwargs,
    )


def slot(slot_id, weekday, section):
    return TimeSlot(id=slot_id, weekday=weekday, start_section=section, end_section=section)


class ScheduleEvaluatorTests(unittest.TestCase):
    def test_accepts_feasible_time_slot_schedule(self):
        courses = (
            course("C001", "T001", ("G001",)),
            course("C002", "T001", ("G002",)),
        )
        assignments = (
            ScheduleAssignment(course_id="C001", time_slot_id="D1-S1"),
            ScheduleAssignment(course_id="C002", time_slot_id="D1-S2"),
        )

        result = evaluate_schedule(courses, assignments)

        self.assertTrue(result.is_feasible)
        self.assertEqual(result.score, 100)
        self.assertEqual(result.issues, ())
        self.assertEqual(result.metrics["assigned_course_count"], 2)

    def test_detects_course_time_conflict_and_missing_assignment(self):
        courses = (
            course("C001", "T001", ("G001",)),
            course("C002", "T001", ("G002",)),
            course("C003", "T003", ("G003",)),
        )
        assignments = (
            ScheduleAssignment(course_id="C001", time_slot_id="D1-S1"),
            ScheduleAssignment(course_id="C002", time_slot_id="D1-S1"),
        )

        result = evaluate_schedule(courses, assignments)
        issue_types = {issue.issue_type for issue in result.issues}

        self.assertFalse(result.is_feasible)
        self.assertIn(EvaluationIssueType.COURSE_CONFLICT, issue_types)
        self.assertIn(EvaluationIssueType.MISSING_ASSIGNMENT, issue_types)
        self.assertLess(result.score, 100)

    def test_detects_room_issues(self):
        courses = (
            course(
                "C001",
                "T001",
                ("G001",),
                expected_students=80,
                required_room_type=RoomType.COMPUTER_LAB,
                required_campus=Campus.JINNAN,
            ),
            course("C002", "T002", ("G002",)),
        )
        room = Room(
            id="R001",
            name="Room 001",
            capacity=60,
            room_type=RoomType.GENERAL,
            campus=Campus.BALITAI,
        )
        assignments = (
            ScheduleAssignment(course_id="C001", time_slot_id="D1-S1", room_id="R001"),
            ScheduleAssignment(course_id="C002", time_slot_id="D1-S1", room_id="R001"),
        )

        result = evaluate_schedule(courses, assignments, rooms=(room,))
        issue_types = {issue.issue_type for issue in result.issues}

        self.assertFalse(result.is_feasible)
        self.assertIn(EvaluationIssueType.ROOM_DOUBLE_BOOKED, issue_types)
        self.assertIn(EvaluationIssueType.ROOM_CAPACITY, issue_types)
        self.assertIn(EvaluationIssueType.ROOM_TYPE, issue_types)
        self.assertIn(EvaluationIssueType.CAMPUS, issue_types)

    def test_detects_unknown_course_and_room(self):
        courses = (course("C001", "T001", ("G001",)),)
        assignments = (
            ScheduleAssignment(course_id="UNKNOWN", time_slot_id="D1-S1"),
            ScheduleAssignment(course_id="C001", time_slot_id="D1-S1", room_id="UNKNOWN"),
        )

        result = evaluate_schedule(courses, assignments)
        issue_types = {issue.issue_type for issue in result.issues}

        self.assertFalse(result.is_feasible)
        self.assertIn(EvaluationIssueType.UNKNOWN_COURSE, issue_types)
        self.assertIn(EvaluationIssueType.UNKNOWN_ROOM, issue_types)

    def test_reports_daily_load_and_early_evening_metrics(self):
        courses = (
            course("C001", "T001", ("G001",)),
            course("C002", "T001", ("G001",)),
        )
        assignments = (
            ScheduleAssignment(course_id="C001", time_slot_id="D1-S1"),
            ScheduleAssignment(course_id="C002", time_slot_id="D1-S12"),
        )
        time_slots = (
            slot("D1-S1", 1, 1),
            slot("D1-S12", 1, 12),
        )

        result = evaluate_schedule(courses, assignments, time_slots=time_slots)

        self.assertEqual(result.metrics["teacher_daily_load"]["T001"]["1"], 2)
        self.assertEqual(result.metrics["class_group_daily_load"]["G001"]["1"], 2)
        self.assertEqual(result.metrics["max_teacher_daily_load"], 2)
        self.assertEqual(result.metrics["max_class_group_daily_load"], 2)
        self.assertEqual(result.metrics["early_section_count"], 1)
        self.assertEqual(result.metrics["evening_section_count"], 1)


if __name__ == "__main__":
    unittest.main()
