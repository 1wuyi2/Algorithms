"""Minimal HTTP API server for the scheduling project.

Run from the repository root with:
    python -m src.api.server
"""


from __future__ import annotations

import json
import mimetypes
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable, Mapping
from urllib.parse import unquote, urlparse

from .errors import ApiError, error_payload
from .services import (
    ai_analyze_schedule_payload,
    ai_answer_question_payload,
    ai_explain_schedule_payload,
    analyze_schedule_payload,
    authenticate_user_payload,
    compare_schedule_algorithms,
    evaluate_schedule_payload,
    health_response,
    recommend_courses_payload,
    run_backtracking_schedule,
    run_greedy_schedule,
)

from src.database.models import CourseDB, TeacherDB, ClassroomDB
from src.database.session import get_session, init_db
from src.persistence.saver import save_schedule_assignments

JsonHandler = Callable[[Mapping[str, Any]], dict[str, object]]
PROJECT_ROOT = Path(__file__).resolve().parents[2]
WEB_ROOT = PROJECT_ROOT / "web"


def save_schedule_handler(payload: Mapping[str, Any]) -> dict[str, object]:
    """Save schedule assignments to the database."""
    semester = payload.get("semester")
    assignments = payload.get("assignments")
    if not semester or not assignments:
        raise ApiError("MISSING_PARAMS", "Need 'semester' and 'assignments'", status=400)
    save_schedule_assignments(assignments, semester)
    return {"success": True, "message": "Schedule saved"}


POST_ROUTES: dict[str, JsonHandler] = {
    "/auth/login": authenticate_user_payload,
    "/schedule/greedy": run_greedy_schedule,
    "/schedule/backtracking": run_backtracking_schedule,
    "/schedule/compare": compare_schedule_algorithms,
    "/schedule/evaluate": evaluate_schedule_payload,
    "/assistant/analyze": analyze_schedule_payload,
    "/assistant/ai-analyze": ai_analyze_schedule_payload,
    "/assistant/ask": ai_answer_question_payload,
    "/assistant/explain": ai_explain_schedule_payload,
    "/student/recommend": recommend_courses_payload,
    "/schedule/save": save_schedule_handler,
}


class SchedulingApiHandler(BaseHTTPRequestHandler):
    """HTTP request handler for JSON scheduling APIs."""

    server_version = "NankaiSchedulingAPI/0.1"

    def do_OPTIONS(self) -> None:
        self._send_json({}, status=204)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        request_path = parsed.path

        if request_path == "/health":
            self._send_json(health_response())
            return

        if request_path.startswith("/courses"):
            self._handle_get_courses()
            return

        if request_path.startswith("/teachers"):
            self._handle_get_teachers()
            return

        if request_path.startswith("/classrooms"):
            self._handle_get_classrooms()
            return

        if request_path == "/":
            self._redirect("/login/index.html")
            return

        if self._handle_static_file(request_path):
            return

        self._send_json(error_payload("NOT_FOUND", "Not found"), status=404)

    def _handle_get_courses(self) -> None:
        from urllib.parse import parse_qs

        session = get_session()
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        semester = params.get("semester", [None])[0]
        try:
            query = session.query(CourseDB)
            if semester:
                query = query.filter(CourseDB.semester == semester)
            courses = query.limit(1600).all()
            data = [
                {
                    "course_code": c.course_code,
                    "course_name": c.course_name,
                    "module": c.module,
                    "teacher_name": c.teacher_name,
                    "weekday": c.weekday,
                    "start_section": c.start_section,
                    "end_section": c.end_section,
                    "classroom": c.classroom,
                    "semester": c.semester,
                    "campus": c.campus,
                    "quota": c.quota,
                }
                for c in courses
            ]
        finally:
            session.close()
        self._send_json({"success": True, "data": data})

    def _handle_get_teachers(self) -> None:
        session = get_session()
        try:
            teachers = session.query(TeacherDB).all()
            data = [
                {
                    "name": t.name,
                    "college": t.college,
                }
                for t in teachers
            ]
        finally:
            session.close()
        self._send_json({"success": True, "data": data})

    def _handle_get_classrooms(self) -> None:
        session = get_session()
        try:
            classrooms = session.query(ClassroomDB).all()
            data = [
                {
                    "name": c.name,
                    "campus": c.campus,
                    "capacity": c.capacity,
                }
                for c in classrooms
            ]
        finally:
            session.close()
        self._send_json({"success": True, "data": data})

    def _handle_static_file(self, request_path: str) -> bool:
        relative_path = unquote(request_path.lstrip("/"))
        if not relative_path:
            return False

        file_path = (WEB_ROOT / relative_path).resolve()
        try:
            file_path.relative_to(WEB_ROOT.resolve())
        except ValueError:
            return False

        if file_path.is_dir():
            file_path = file_path / "index.html"

        if not file_path.is_file():
            return False

        content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        if content_type.startswith("text/") or content_type == "application/javascript":
            content_type += "; charset=utf-8"

        body = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
        return True

    def _redirect(self, location: str) -> None:
        self.send_response(302)
        self.send_header("Location", location)
        self.send_header("Content-Length", "0")
        self.end_headers()

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
    print(f"Scheduling website running at http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run(host=os.getenv("HOST", "0.0.0.0"), port=int(os.getenv("PORT", "8000")))
