#!/usr/bin/env python3
"""
独立数据导入脚本
用法: python scripts/import_catalog.py --file 选课手册.pdf --semester 2025-2026-1
"""
import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.session import init_db, get_session
from src.database.models import CourseDB, TeacherDB, ClassroomDB
from src.importer.parser import parse_catalog_file
from src.importer.cleaner import clean_course_data
from src.importer.validator import validate_all

def import_catalog(file_path: str, semester: str, db_url: str = "sqlite:///timetable.db"):
    print(f"开始导入: {file_path} (学期: {semester})")
    # 1. 解析
    df_raw = parse_catalog_file(file_path, semester)
    print(f"解析到 {len(df_raw)} 条原始记录")
    # 2. 清洗
    df_clean = clean_course_data(df_raw)
    print(f"清洗后剩余 {len(df_clean)} 条记录")
    # 3. 校验
    records = df_clean.to_dict(orient="records")
    result = validate_all(records)
    if not result.is_valid():
        print("数据校验失败:")
        for err in result.errors:
            print(f"  {err}")
        return False
    for warn in result.warnings:
        print(f"警告: {warn}")

    # 4. 初始化数据库
    init_db(db_url, echo=False)
    session = get_session()

    # 5. 插入课程表（使用 merge 避免重复）
    inserted_courses = 0
    for _, row in df_clean.iterrows():
        # 处理教师姓名为空的情况：替换为默认值
        teacher_name = row.get("teacher_name", "").strip()
        if not teacher_name:
            teacher_name = "未知教师"
        course = CourseDB(
            course_code=row["course_code"],
            course_name=row["course_name"],
            module=row.get("module"),
            quota=row.get("quota", 0),
            cross_major_quota=row.get("cross_major_quota", 0),
            teacher_name=teacher_name,
            weekday=row.get("weekday"),
            start_section=row.get("start_section"),
            end_section=row.get("end_section"),
            weeks=row.get("weeks"),
            classroom=row.get("classroom"),
            remark=row.get("remark"),
            credit=row.get("credit"),
            weekly_hours=row.get("weekly_hours"),
            campus=row.get("campus"),
            semester=semester
        )
        session.merge(course)
        inserted_courses += 1
    session.commit()
    print(f"课程表处理完成，共 {inserted_courses} 条记录")

    # 6. 提取教师去重，并安全插入（避免唯一约束冲突）
    teacher_names = set()
    for _, row in df_clean.iterrows():
        # 同样处理空教师（避免空字符串被加入）
        raw_name = row.get("teacher_name", "").strip()
        if not raw_name:
            raw_name = "未知教师"
        for t in raw_name.split(","):
            if t.strip():
                teacher_names.add(t.strip())
    
    inserted_teachers = 0
    for name in teacher_names:
        # 先检查教师是否已存在
        existing = session.query(TeacherDB).filter_by(name=name).first()
        if not existing:
            session.add(TeacherDB(name=name))
            inserted_teachers += 1
    session.commit()
    print(f"教师表处理完成，新增 {inserted_teachers} 位教师，总教师数（含之前）: {session.query(TeacherDB).count()}")

    # 7. 提取教室去重，并安全插入
    classroom_names = set()
    for _, row in df_clean.iterrows():
        room = row.get("classroom")
        if room and str(room).strip():
            classroom_names.add(str(room).strip())
    
    inserted_classrooms = 0
    for name in classroom_names:
        existing = session.query(ClassroomDB).filter_by(name=name).first()
        if not existing:
            session.add(ClassroomDB(name=name))
            inserted_classrooms += 1
    session.commit()
    print(f"教室表处理完成，新增 {inserted_classrooms} 间教室，总教室数（含之前）: {session.query(ClassroomDB).count()}")

    session.close()
    print(f"导入完成！共插入 {inserted_courses} 门课程，{len(teacher_names)} 位教师（新增 {inserted_teachers}），{len(classroom_names)} 间教室（新增 {inserted_classrooms}）")
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="导入选课手册")
    parser.add_argument("--file", required=True, help="选课手册文件路径（PDF/Excel/CSV）")
    parser.add_argument("--semester", required=True, help="学期，如 2025-2026-1")
    parser.add_argument("--db", default="sqlite:///timetable.db", help="数据库连接字符串")
    args = parser.parse_args()
    if not os.path.exists(args.file):
        print(f"文件不存在: {args.file}")
        sys.exit(1)
    success = import_catalog(args.file, args.semester, args.db)
    sys.exit(0 if success else 1)