"""Tests for task-five AI and educational-system integration helpers."""

import unittest

from src.assistant import (
    EDU_SYSTEM_FIELD_MAPPING,
    AIScheduleAssistant,
    SyncResult,
    generate_sync_report,
)
from src.evaluation import evaluate_schedule
from src.models import Course, ScheduleAssignment, TimeSlot


def course(course_id):
    return Course(
        id=course_id,
        name=f"Course {course_id}",
        teacher_id="T001",
        class_group_ids=("G001",),
        weekly_hours=2,
    )


class TaskFiveAssistantTests(unittest.TestCase):
    def test_assistant_explains_schedule_without_external_llm(self):
        courses = (course("C001"),)
        assignments = (ScheduleAssignment(course_id="C001", time_slot_id="D1-S1"),)
        time_slots = (TimeSlot(id="D1-S1", weekday=1, start_section=1, end_section=1),)
        evaluation = evaluate_schedule(courses, assignments, time_slots=time_slots)

        explanation = AIScheduleAssistant().explain_schedule(evaluation, dict(evaluation.metrics))

        self.assertIn("score", explanation.lower())
        self.assertIn("100", explanation)

    def test_edu_sync_report_and_field_mapping_are_available(self):
        result = SyncResult(
            success=True,
            imported_courses=3,
            imported_teachers=2,
            imported_rooms=1,
            imported_time_slots=14,
            message="ok",
        )

        report = generate_sync_report(result)

        self.assertIn("Courses: 3", report)
        self.assertIn("nankai", EDU_SYSTEM_FIELD_MAPPING)
        self.assertIn("course", EDU_SYSTEM_FIELD_MAPPING["nankai"])


if __name__ == "__main__":
    unittest.main()
