# src/database/loader.py
from typing import List, Optional
from src.database.session import get_session
from src.database.models import CourseDB, TeacherDB, ClassroomDB, TimeSlotDB
from src.models.entities import Course, Teacher, Room, TimeSlot, Campus, RoomType

def load_courses_for_semester(semester: str) -> List[Course]:
    session = get_session()
    db_courses = session.query(CourseDB).filter(CourseDB.semester == semester).all()
    
    # 获取所有可用的时间槽 ID（用于无时间信息的课程）
    all_time_slots = session.query(TimeSlotDB).all()
    if all_time_slots:
        all_time_slot_ids = tuple(slot.id for slot in all_time_slots)
    else:
        # 如果没有预定义时间槽，生成默认的（周一至周日，每两节一个槽）
        all_time_slot_ids = tuple(f"D{w}-S{start}-{start+1}" for w in range(1,8) for start in range(1,14,2))
    
    courses = []
    for c in db_courses:
        # 候选时间槽：如果有具体时间则用该时间槽，否则用全部时间槽
        if c.weekday and c.start_section and c.end_section:
            candidate_ids = (f"D{c.weekday}-S{c.start_section}-{c.end_section}",)
        else:
            candidate_ids = all_time_slot_ids  # 所有时间槽都候选
        
        # 教师姓名处理
        teacher_name = c.teacher_name.strip() if c.teacher_name else ""
        teacher_id = teacher_name if teacher_name else "未知教师"
        
        course = Course(
            id=c.course_code,
            name=c.course_name,
            teacher_id=teacher_id,
            class_group_ids=("DEFAULT",),
            weekly_hours=c.weekly_hours or 3,
            required_room_type=RoomType.GENERAL,
            required_campus=_parse_campus(c.campus),
            expected_students=c.quota,
            fixed_time_slot_id=None,
            candidate_time_slot_ids=candidate_ids,
            required_consecutive_slots=1
        )
        courses.append(course)
    session.close()
    return courses

def load_all_teachers() -> List[Teacher]:
    """加载所有教师，转换为 entities.Teacher 对象"""
    session = get_session()
    db_teachers = session.query(TeacherDB).all()
    teachers = []
    for t in db_teachers:
        teacher = Teacher(
            id=t.name,
            name=t.name,
            unavailable_time_slot_ids=set(),
            available_course_ids=set(),
            campus_preferences=set()
        )
        teachers.append(teacher)
    session.close()
    return teachers

def load_all_rooms() -> List[Room]:
    """加载所有教室，转换为 entities.Room 对象"""
    session = get_session()
    db_rooms = session.query(ClassroomDB).all()
    rooms = []
    for r in db_rooms:
        # 确保容量为正整数
        capacity = r.capacity if r.capacity and r.capacity > 0 else 100
        room = Room(
            id=r.name,
            name=r.name,
            capacity=capacity,
            room_type=_parse_room_type(r.name),
            campus=_parse_campus(r.campus),
            building=None,
            available_time_slot_ids=set()
        )
        rooms.append(room)
    session.close()
    return rooms

def load_time_slots() -> List[TimeSlot]:
    """加载时间槽，若表为空则生成默认时间槽"""
    session = get_session()
    db_slots = session.query(TimeSlotDB).all()
    if db_slots:
        slots = [TimeSlot(id=s.id, weekday=s.weekday, start_section=s.start_section, end_section=s.end_section) for s in db_slots]
    else:
        slots = []
        for w in range(1, 8):
            for start in range(1, 14, 2):
                end = start + 1
                slots.append(TimeSlot(id=f"D{w}-S{start}-{end}", weekday=w, start_section=start, end_section=end))
    session.close()
    return slots

def _parse_campus(campus_str: Optional[str]) -> Optional[Campus]:
    if not campus_str:
        return None
    if "津南" in campus_str:
        return Campus.JINNAN
    if "八里台" in campus_str:
        return Campus.BALITAI
    return None

def _parse_room_type(room_name: str) -> RoomType:
    if "机房" in room_name or "实验室" in room_name:
        return RoomType.COMPUTER_LAB
    if "多媒体" in room_name:
        return RoomType.MULTIMEDIA
    return RoomType.GENERAL