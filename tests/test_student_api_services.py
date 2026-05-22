"""Unit tests for student recommendation API service function."""

import unittest

from src.api import recommend_courses_payload


class StudentRecommendationApiTests(unittest.TestCase):
    def test_recommend_courses_payload(self):
        payload = {
            "student": {
                "id": "S001",
                "major": "Computer Science",
                "grade": "2023",
                "completedCourseIds": ["C001"],
                "interests": ["algorithm"],
            },
            "courses": [
                {
                    "id": "C002",
                    "name": "算法设计与分析",
                    "majorTags": ["Computer Science"],
                    "gradeTags": ["2023"],
                    "interestTags": ["algorithm"],
                    "prerequisiteCourseIds": ["C001"],
                    "timeSlotId": "D1-S3",
                    "category": "专业必修",
                },
                {
                    "id": "C003",
                    "name": "数据库系统",
                    "majorTags": ["Computer Science"],
                    "gradeTags": ["2023"],
                    "interestTags": ["database"],
                    "timeSlotId": "D1-S1",
                },
            ],
            "currentAssignments": [
                {"courseId": "C010", "timeSlotId": "D1-S1"},
            ],
            "topK": 2,
        }

        response = recommend_courses_payload(payload)

        self.assertEqual(response["student_id"], "S001")
        self.assertEqual(response["candidate_count"], 2)
        self.assertEqual(response["recommendations"][0]["course_id"], "C002")
        self.assertFalse(response["recommendations"][0]["has_time_conflict"])
        self.assertTrue(response["recommendations"][1]["has_time_conflict"])
        self.assertTrue(response["recommendations"][0]["reasons"])

    def test_recommend_courses_payload_supports_filtering_conflicted_courses(self):
        payload = {
            "student": {
                "id": "S001",
                "major": "Computer Science",
                "grade": "2023",
                "interests": ["algorithm"],
            },
            "candidateCourses": [
                {
                    "id": "C002",
                    "name": "算法设计与分析",
                    "majorTags": ["Computer Science"],
                    "gradeTags": ["2023"],
                    "interestTags": ["algorithm"],
                    "timeSlotId": "D1-S1",
                },
            ],
            "currentSchedule": [
                {"courseId": "C010", "timeSlotId": "D1-S1"},
            ],
            "includeConflicted": False,
        }

        response = recommend_courses_payload(payload)

        self.assertEqual(response["recommendations"], [])


if __name__ == "__main__":
    unittest.main()
