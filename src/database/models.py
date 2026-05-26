from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class CourseDB(Base):
    """课程表 - 对应选课手册内容，支持多学期"""
    __tablename__ = "courses"
    id = Column(Integer, primary_key=True, autoincrement=True)
    course_code = Column(String(20), nullable=False, index=True)      # 选课序号
    course_name = Column(String(200), nullable=False)                 # 课程名称
    module = Column(String(100))                                      # 课程归属模块
    quota = Column(Integer, default=0)                                # 选课名额
    cross_major_quota = Column(Integer, default=0)                    # 跨专业名额
    teacher_name = Column(String(200))                                # 教师，多教师逗号分隔
    weekday = Column(Integer)                                         # 星期几（1-7）
    start_section = Column(Integer)                                   # 开始节次
    end_section = Column(Integer)                                     # 结束节次
    weeks = Column(String(50))                                        # 起止周次
    classroom = Column(String(100))                                   # 教室
    remark = Column(Text)                                             # 备注
    credit = Column(Float, nullable=True)                             # 学分（待补充）
    weekly_hours = Column(Integer, nullable=True)                     # 周学时（推算）
    campus = Column(String(20))                                       # 校区（八里台/津南/泰达）
    semester = Column(String(20), nullable=False, index=True)         # 学期，如 "2025-2026-1"
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (UniqueConstraint('course_code', 'semester', name='_course_semester_uc'),)

class TeacherDB(Base):
    """教师表 - 从课程中提取去重"""
    __tablename__ = "teachers"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    college = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)

class ClassroomDB(Base):
    """教室表 - 从课程中提取去重"""
    __tablename__ = "classrooms"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    campus = Column(String(20))
    building = Column(String(100))
    room_no = Column(String(50))
    capacity = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

class TimeSlotDB(Base):
    """时间槽表 - 预定义全校统一节次"""
    __tablename__ = "time_slots"
    id = Column(Integer, primary_key=True, autoincrement=True)
    weekday = Column(Integer, nullable=False)        # 1-7
    start_section = Column(Integer, nullable=False)
    end_section = Column(Integer, nullable=False)
    label = Column(String(50))
    start_time = Column(String(10))
    end_time = Column(String(10))

class ScheduleResultDB(Base):
    """排课结果表 - 与任务一算法对接"""
    __tablename__ = "schedule_results"
    id = Column(Integer, primary_key=True, autoincrement=True)
    course_code = Column(String(20), ForeignKey("courses.course_code"), nullable=False)
    teacher_id = Column(Integer, ForeignKey("teachers.id"))
    classroom_id = Column(Integer, ForeignKey("classrooms.id"))
    time_slot_id = Column(Integer, ForeignKey("time_slots.id"))
    semester = Column(String(20), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)