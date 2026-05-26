from src.database.session import init_db, get_session
from src.database.models import CourseDB

init_db()
session = get_session()


s1 = session.query(CourseDB).filter(CourseDB.semester == "2025-2026-1").count()
s2 = session.query(CourseDB).filter(CourseDB.semester == "2025-2026-2").count()

print(f"第一学期课程数: {s1}")
print(f"第二学期课程数: {s2}")


first_course = session.query(CourseDB).filter(CourseDB.semester == "2025-2026-1").first()
if first_course:
    print(f"\n样例课程: {first_course.course_code} {first_course.course_name} 教师:{first_course.teacher_name}")