"""Unit tests for conflict graph construction."""

import unittest

from src.constraints import ConflictType
from src.graph import build_conflict_graph
from src.models import Course


def make_course(course_id, teacher_id, class_group_ids, fixed_time_slot_id=None):
    return Course(
        id=course_id,
        name=f"Course {course_id}",
        teacher_id=teacher_id,
        class_group_ids=tuple(class_group_ids),
        weekly_hours=2,
        fixed_time_slot_id=fixed_time_slot_id,
    )


class ConflictGraphTests(unittest.TestCase):
    def test_builds_adjacency_list_with_isolated_courses(self):
        course_a = make_course("C001", "T001", ("G001",))
        course_b = make_course("C002", "T001", ("G002",))
        course_c = make_course("C003", "T003", ("G001",))
        course_d = make_course("C004", "T004", ("G004",))

        graph = build_conflict_graph((course_a, course_b, course_c, course_d))

        self.assertEqual(graph.node_ids, ("C001", "C002", "C003", "C004"))
        self.assertEqual(graph.neighbors("C001"), ("C002", "C003"))
        self.assertEqual(graph.neighbors("C002"), ("C001",))
        self.assertEqual(graph.neighbors("C003"), ("C001",))
        self.assertEqual(graph.neighbors("C004"), ())
        self.assertEqual(graph.degree("C001"), 2)
        self.assertEqual(len(graph.edges), 2)

    def test_keeps_conflict_reasons_on_edges(self):
        course_a = make_course("C001", "T001", ("G001",), fixed_time_slot_id="D1-S1")
        course_b = make_course("C002", "T001", ("G001",), fixed_time_slot_id="D1-S1")

        graph = build_conflict_graph((course_a, course_b))
        edge = graph.edge_between("C001", "C002")
        reason_types = {reason.conflict_type for reason in edge.reasons}

        self.assertIsNotNone(edge)
        self.assertIn(ConflictType.SAME_TEACHER, reason_types)
        self.assertIn(ConflictType.SAME_CLASS_GROUP, reason_types)
        self.assertIn(ConflictType.SAME_FIXED_TIME, reason_types)

    def test_rejects_duplicate_course_ids(self):
        course_a = make_course("C001", "T001", ("G001",))
        course_b = make_course("C001", "T002", ("G002",))

        with self.assertRaises(ValueError):
            build_conflict_graph((course_a, course_b))


if __name__ == "__main__":
    unittest.main()
