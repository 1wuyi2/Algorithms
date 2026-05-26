from typing import List, Dict

class ValidationResult:
    def __init__(self):
        self.errors = []
        self.warnings = []
    def is_valid(self):
        return len(self.errors) == 0
    def add_error(self, course_code, field, msg):
        self.errors.append({"course_code": course_code, "field": field, "message": msg})
    def add_warning(self, course_code, field, msg):
        self.warnings.append({"course_code": course_code, "field": field, "message": msg})

def validate_course(row: Dict, result: ValidationResult):
    code = row.get("course_code", "")
    if not code or len(code) < 4:
        result.add_error(code, "course_code", "课程号无效")
    if not row.get("course_name"):
        result.add_error(code, "course_name", "课程名称为空")
    quota = row.get("quota", 0)
    if quota > 1000:
        result.add_warning(code, "quota", f"选课名额过大: {quota}")
    wd = row.get("weekday")
    if wd is not None and (wd < 1 or wd > 7):
        result.add_warning(code, "weekday", f"星期异常: {wd}")

def validate_all(rows: List[Dict]) -> ValidationResult:
    result = ValidationResult()
    for row in rows:
        validate_course(row, result)
    return result