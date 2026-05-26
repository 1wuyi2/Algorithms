"""Minimal HTTP API server for the scheduling project.

Run from the repository root with:
    python -m src.api.server
"""


from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable, Mapping

from .errors import ApiError, error_payload
from .services import (
    analyze_schedule_payload,
    authenticate_user_payload,
    compare_schedule_algorithms,
    evaluate_schedule_payload,
    health_response,
    recommend_courses_payload,
    run_backtracking_schedule,
    run_greedy_schedule,
)

# 新增导入
from src.database.session import init_db, get_session
from src.database.models import CourseDB, TeacherDB, ClassroomDB
from src.importer.parser import parse_catalog_file
from src.importer.cleaner import clean_course_data
from src.importer.validator import validate_all
import os

JsonHandler = Callable[[Mapping[str, Any]], dict[str, object]]

POST_ROUTES: dict[str, JsonHandler] = {
    "/auth/login": authenticate_user_payload,
    "/schedule/greedy": run_greedy_schedule,
    "/schedule/backtracking": run_backtracking_schedule,
    "/schedule/compare": compare_schedule_algorithms,
    "/schedule/evaluate": evaluate_schedule_payload,
    "/assistant/analyze": analyze_schedule_payload,
    "/student/recommend": recommend_courses_payload,
}


class SchedulingApiHandler(BaseHTTPRequestHandler):
    """HTTP request handler for JSON scheduling APIs."""

    server_version = "NankaiSchedulingAPI/0.1"

    def do_OPTIONS(self) -> None:
        self._send_json({}, status=204)

    def do_GET(self) -> None:
        if self.path == "/health":
            self._send_json(health_response())
            return
        # 新增课程列表查询
        if self.path.startswith("/courses"):
            self._handle_get_courses()
            return
        self._send_json(error_payload("NOT_FOUND", "Not found"), status=404)

    def _handle_get_courses(self) -> None:
        from urllib.parse import parse_qs, urlparse
        session = get_session()
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        semester = params.get("semester", [None])[0]
        query = session.query(CourseDB)
        if semester:
            query = query.filter(CourseDB.semester == semester)
        courses = query.limit(500).all()
        data = [
            {
                "course_code": c.course_code,
                "course_name": c.course_name,
                "teacher_name": c.teacher_name,
                "weekday": c.weekday,
                "start_section": c.start_section,
                "end_section": c.end_section,
                "classroom": c.classroom,
                "semester": c.semester,
            }
            for c in courses
        ]
        self._send_json({"success": True, "data": data})



    def do_POST(self) -> None:
        handler = POST_ROUTES.get(self.path)
        if handler is None:
            self._send_json(error_payload("NOT_FOUND", "Not found"), status=404)
            return

        try:
            payload = self._read_json_body()
            response = handler(payload)
        except ApiError as exc:
            self._send_json(error_payload(exc.code, exc.message), status=exc.status)
            return
        except ValueError as exc:
            self._send_json(error_payload("VALIDATION_ERROR", str(exc)), status=400)
            return
        except Exception as exc:  # pragma: no cover - final API guard
            self._send_json(error_payload("INTERNAL_ERROR", f"Internal server error: {exc}"), status=500)
            return

        self._send_json(response)

    def _read_json_body(self) -> Mapping[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        raw_body = self.rfile.read(length)
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ApiError("INVALID_JSON", "Request body must be valid JSON", status=400) from exc
        if not isinstance(payload, Mapping):
            raise ValueError("Request JSON body must be an object")
        return payload

    def _send_json(self, payload: Mapping[str, Any], *, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if status != 204:
            self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        """Keep default server output concise."""

        return


def run(host: str = "127.0.0.1", port: int = 8000) -> None:
    """Start the API server."""
    init_db() 
    server = ThreadingHTTPServer((host, port), SchedulingApiHandler)
    print(f"Scheduling API running at http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run()
