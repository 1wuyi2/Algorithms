"""Unit tests for API service functions."""

import unittest

from src.api import (
    analyze_schedule_payload,
    evaluate_schedule_payload,
    health_response,
    run_backtracking_schedule,
    run_greedy_schedule,
)


def course(course_id, teacher_id, class_group_ids, **kwargs):
    payload = {
        "id": course_id,
        "name": f"Course {course_id}",
        "teacher_id": teacher_id,
        "class_group_ids": list(class_group_ids),
        "weekly_hours": 2,
    }
    payload.update(kwargs)
    return payload


def time_slot(slot_id, section):
    return {
        "id": slot_id,
        "weekday": 1,
        "start_section": section,
        "end_section": section,
    }


class ApiServiceTests(unittest.TestCase):
    def test_health_response(self):
        response = health_response()

        self.assertEqual(response["status"], "ok")

    def test_run_greedy_schedule(self):
        payload = {
            "courses": (
                course("C001", "T001", ("G001",)),
                course("C002", "T001", ("G002",)),
            ),
            "time_slots": (
                time_slot("D1-S1", 1),
                time_slot("D1-S2", 2),
            ),
        }

        response = run_greedy_schedule(payload)

        self.assertEqual(response["algorithm"], "greedy_coloring")
        self.assertTrue(response["is_complete"])
        self.assertEqual(len(response["assignments"]), 2)

    def test_run_backtracking_schedule(self):
        payload = {
            "courses": (
                course("C001", "T001", ("G001",)),
                course("C002", "T001", ("G002",)),
            ),
            "timeSlots": (
                time_slot("D1-S1", 1),
                time_slot("D1-S2", 2),
            ),
            "maxSteps": 1000,
        }

        response = run_backtracking_schedule(payload)

        self.assertEqual(response["algorithm"], "backtracking_search")
        self.assertTrue(response["is_complete"])
        self.assertEqual(response["failed_course_ids"], [])

    def test_evaluate_schedule_payload(self):
        payload = {
            "courses": (
                course("C001", "T001", ("G001",)),
                course("C002", "T001", ("G002",)),
            ),
            "assignments": (
                {"course_id": "C001", "time_slot_id": "D1-S1"},
                {"course_id": "C002", "time_slot_id": "D1-S1"},
            ),
        }

        response = evaluate_schedule_payload(payload)

        self.assertFalse(response["is_feasible"])
        self.assertLess(response["score"], 100)
        self.assertTrue(response["errors"])

    def test_analyze_schedule_payload(self):
        payload = {
            "courses": [
                course("C001", "T001", ("G001",)),
                course("C002", "T001", ("G002",)),
            ],
            "time_slots": [
                time_slot("D1-S1", 1),
                time_slot("D1-S2", 2),
            ],
        }

        response = analyze_schedule_payload(payload)

        self.assertIn(response["risk_level"], {"low", "medium", "high"})
        self.assertIn("metrics", response)
        self.assertTrue(response["suggestions"])

    def test_rejects_missing_required_fields(self):
        with self.assertRaises(ValueError):
            run_greedy_schedule({"courses": [{"id": "C001"}], "time_slots": []})


if __name__ == "__main__":
    unittest.main()
