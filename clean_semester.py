# clean_semester.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.database.session import init_db, get_session
from src.database.models import CourseDB

def delete_semester(semester):
    init_db()
    session = get_session()
    # 删除该学期所有课程
    deleted = session.query(CourseDB).filter(CourseDB.semester == semester).delete()
    session.commit()
    print(f"已删除 {deleted} 条学期为 {semester} 的课程记录")
    session.close()

if __name__ == "__main__":
    # 要删除的学期，修改这里
    semester = "2025-2026-2"
    delete_semester(semester)   