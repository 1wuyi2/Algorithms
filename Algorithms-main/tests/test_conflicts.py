"""Unit tests for conflict detection."""

import unittest

from src.constraints import ConflictType, find_assignment_conflicts, find_course_conflicts, has_conflict
from src.models import Campus, ClassGroup, Course, Room, RoomType, ScheduleAssignment, Teacher


class CourseConflictTests(unittest.TestCase):
    def test_detects_teacher_and_class_group_conflicts(self):
        course_a = Course(
            id="C001",
            name="Course A",
            teacher_id="T001",
            class_group_ids=("G001",),
            weekly_hours=2,
        )
        course_b = Course(
            id="C002",
            name="Course B",
            teacher_id="T001",
            class_group_ids=("G001", "G002"),
            weekly_hours=2,
        )

        result = find_course_conflicts(course_a, course_b)
        conflict_types = {reason.conflict_type for reason in result.reasons}

        self.assertTrue(result.has_conflict)
        self.assertTrue(has_conflict(course_a, course_b))
        self.assertIn(ConflictType.SAME_TEACHER, conflict_types)
        self.assertIn(ConflictType.SAME_CLASS_GROUP, conflict_types)

    def test_detects_assignment_conflicts(self):
        course = Course(
            id="C001",
            name="Course A",
            teacher_id="T001",
            class_group_ids=("G001",),
            weekly_hours=2,
            required_room_type=RoomType.COMPUTER_LAB,
            required_campus=Campus.JINNAN,
            expected_students=80,
        )
        assignment = ScheduleAssignment(course_id="C001", time_slot_id="D1-S1", room_id="R001")
        teacher = Teacher(id="T001", name="Teacher A", unavailable_time_slot_ids=frozenset({"D1-S1"}))
        class_group = ClassGroup(id="G001", name="Class A", unavailable_time_slot_ids=frozenset({"D1-S1"}))
        room = Room(
            id="R001",
            name="Room A",
            capacity=60,
            room_type=RoomType.GENERAL,
            campus=Campus.BALITAI,
            available_time_slot_ids=frozenset({"D1-S2"}),
        )

        result = find_assignment_conflicts(
            course,
            assignment,
            teacher=teacher,
            room=room,
            class_groups=(class_group,),
        )
        conflict_types = {reason.conflict_type for reason in result.reasons}

        self.assertTrue(result.has_conflict)
        self.assertIn(ConflictType.TEACHER_UNAVAILABLE, conflict_types)
        self.assertIn(ConflictType.CLASS_GROUP_UNAVAILABLE, conflict_types)
        self.assertIn(ConflictType.ROOM_UNAVAILABLE, conflict_types)
        self.assertIn(ConflictType.ROOM_CAPACITY, conflict_types)
        self.assertIn(ConflictType.ROOM_TYPE, conflict_types)
        self.assertIn(ConflictType.CAMPUS, conflict_types)


if __name__ == "__main__":
    unittest.main()
