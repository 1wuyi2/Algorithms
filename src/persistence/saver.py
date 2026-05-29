from src.database.session import get_session
from src.database.models import ScheduleResultDB, CourseDB, TeacherDB, ClassroomDB

def save_schedule_assignments(assignments: list, semester: str):
    """
    保存排课结果到数据库
    assignments: list of dict, 每个 dict 包含 course_code, teacher_name, classroom, time_slot_id
    """
    session = get_session()
    try:
        for assign in assignments:
            course = session.query(CourseDB).filter_by(course_code=assign["course_code"]).first()
            if not course:
                continue
            teacher = session.query(TeacherDB).filter_by(name=assign["teacher_name"]).first()
            teacher_id = teacher.id if teacher else None
            classroom = session.query(ClassroomDB).filter_by(name=assign["classroom"]).first()
            classroom_id = classroom.id if classroom else None
            record = ScheduleResultDB(
                course_code=assign["course_code"],
                teacher_id=teacher_id,
                classroom_id=classroom_id,
                time_slot_id=assign["time_slot_id"],
                semester=semester
            )
            session.merge(record)
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()