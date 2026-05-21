"""Unit tests for API service functions."""

import unittest

from src.api import (
    analyze_schedule_payload,
    compare_schedule_algorithms,
    error_payload,
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

        self.assertTrue(response["success"])
        self.assertEqual(response["data"]["status"], "ok")
        self.assertEqual(response["status"], "ok")

    def test_error_payload_keeps_simple_error_field(self):
        response = error_payload("VALIDATION_ERROR", "Missing field")

        self.assertFalse(response["success"])
        self.assertEqual(response["code"], "VALIDATION_ERROR")
        self.assertEqual(response["error"], "Missing field")

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

        self.assertTrue(response["success"])
        self.assertEqual(response["data"]["algorithm"], "greedy_coloring")
        self.assertEqual(response["algorithm"], "greedy_coloring")
        self.assertTrue(response["is_complete"])
        self.assertEqual(len(response["assignments"]), 2)

    def test_run_greedy_schedule_accepts_strategy_options(self):
        payload = {
            "courses": (
                course("C001", "T001", ("G001",)),
                course("C100", "T001", ("G002",), fixed_time_slot_id="D1-S1"),
            ),
            "time_slots": (
                time_slot("D1-S1", 1),
                time_slot("D1-S2", 2),
            ),
            "options": {
                "prioritize_fixed_time": False,
                "sort_by_conflict_degree": False,
            },
        }

        response = run_greedy_schedule(payload)

        self.assertFalse(response["is_complete"])
        self.assertFalse(response["options"]["prioritize_fixed_time"])
        self.assertEqual(response["unscheduled"][0]["course_id"], "C100")

    def test_run_greedy_schedule_reports_unscheduled_diagnostics(self):
        payload = {
            "courses": (
                course("C001", "T001", ("G001",)),
                course("C002", "T001", ("G002",)),
                course("C003", "T001", ("G003",)),
            ),
            "time_slots": (
                time_slot("D1-S1", 1),
                time_slot("D1-S2", 2),
            ),
        }

        response = run_greedy_schedule(payload)

        self.assertFalse(response["is_complete"])
        self.assertEqual(response["unscheduled"][0]["candidate_time_slot_ids"], ["D1-S1", "D1-S2"])
        self.assertEqual(response["unscheduled"][0]["blocking_course_ids"], ["C001", "C002"])

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

        self.assertTrue(response["success"])
        self.assertEqual(response["algorithm"], "backtracking_search")
        self.assertTrue(response["is_complete"])
        self.assertEqual(response["failed_course_ids"], [])
        self.assertEqual(response["failure_details"], [])

    def test_run_backtracking_schedule_reports_failure_details(self):
        payload = {
            "courses": (
                course("C001", "T001", ("G001",), fixed_time_slot_id="UNKNOWN"),
            ),
            "timeSlots": (
                time_slot("D1-S1", 1),
            ),
        }

        response = run_backtracking_schedule(payload)

        self.assertFalse(response["is_complete"])
        self.assertEqual(response["failure_details"][0]["course_id"], "C001")
        self.assertEqual(response["failure_details"][0]["reason"], "The fixed time slot is not included in the available time slots.")

    def test_compare_schedule_algorithms_recommends_backtracking_when_greedy_gets_stuck(self):
        payload = {
            "courses": (
                course("C001", "T001", ("G001",), candidate_time_slot_ids=("D1-S1", "D1-S2")),
                course("C002", "T001", ("G002",), candidate_time_slot_ids=("D1-S1",)),
                course("C003", "T003", ("G001",), candidate_time_slot_ids=("D1-S1", "D1-S2")),
            ),
            "time_slots": (
                time_slot("D1-S1", 1),
                time_slot("D1-S2", 2),
            ),
        }

        response = compare_schedule_algorithms(payload)

        self.assertTrue(response["success"])
        self.assertEqual(response["recommended_algorithm"], "backtracking_search")
        self.assertFalse(response["greedy"]["is_complete"])
        self.assertTrue(response["backtracking"]["is_complete"])
        self.assertIn("metrics", response["greedy"])

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
            "time_slots": (
                time_slot("D1-S1", 1),
            ),
        }

        response = evaluate_schedule_payload(payload)

        self.assertTrue(response["success"])
        self.assertFalse(response["is_feasible"])
        self.assertLess(response["score"], 100)
        self.assertTrue(response["errors"])
        self.assertIn("teacher_daily_load", response["metrics"])

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

        self.assertTrue(response["success"])
        self.assertIn(response["risk_level"], {"low", "medium", "high"})
        self.assertIn("metrics", response)
        self.assertTrue(response["suggestions"])

    def test_rejects_missing_required_fields(self):
        with self.assertRaises(ValueError):
            run_greedy_schedule({"courses": [{"id": "C001"}], "time_slots": []})


if __name__ == "__main__":
    unittest.main()
