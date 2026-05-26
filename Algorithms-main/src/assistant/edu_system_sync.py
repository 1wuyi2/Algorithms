"""教务系统数据同步模块.

提供与真实教务系统对接的接口和数据同步方案，支持：
- 教务系统数据模型映射
- 数据同步策略
- 外部接口调用
- 数据格式转换
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

import requests

from src.models import Course, Room, Teacher, TimeSlot


class EduSystemType(str, Enum):
    """支持的教务系统类型."""
    NANKAI = "nankai"
    GENERIC = "generic"
    TEST = "test"


@dataclass(frozen=True)
class SyncResult:
    """数据同步结果."""
    success: bool
    imported_courses: int = 0
    imported_teachers: int = 0
    imported_rooms: int = 0
    imported_time_slots: int = 0
    message: str = ""
    error_details: Optional[str] = None


@dataclass(frozen=True)
class EduSystemConfig:
    """教务系统配置."""
    system_type: EduSystemType
    api_url: str
    api_key: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    sync_interval_hours: int = 24


class EduSystemClient:
    """教务系统客户端."""

    def __init__(self, config: EduSystemConfig):
        self.config = config
        self.session = requests.Session()
        if config.api_key:
            self.session.headers.update({"Authorization": f"Bearer {config.api_key}"})

    def sync_all_data(self) -> SyncResult:
        """同步所有数据."""
        try:
            courses = self.fetch_courses()
            teachers = self.fetch_teachers()
            rooms = self.fetch_rooms()
            time_slots = self.fetch_time_slots()
            
            return SyncResult(
                success=True,
                imported_courses=len(courses),
                imported_teachers=len(teachers),
                imported_rooms=len(rooms),
                imported_time_slots=len(time_slots),
                message="数据同步成功"
            )
        except Exception as e:
            return SyncResult(
                success=False,
                message="数据同步失败",
                error_details=str(e)
            )

    def fetch_courses(self) -> List[Course]:
        """从教务系统获取课程数据."""
        url = f"{self.config.api_url}/courses"
        response = self.session.get(url)
        data = response.json()
        return [self._parse_course(item) for item in data.get("data", [])]

    def fetch_teachers(self) -> List[Teacher]:
        """从教务系统获取教师数据."""
        url = f"{self.config.api_url}/teachers"
        response = self.session.get(url)
        data = response.json()
        return [self._parse_teacher(item) for item in data.get("data", [])]

    def fetch_rooms(self) -> List[Room]:
        """从教务系统获取教室数据."""
        url = f"{self.config.api_url}/rooms"
        response = self.session.get(url)
        data = response.json()
        return [self._parse_room(item) for item in data.get("data", [])]

    def fetch_time_slots(self) -> List[TimeSlot]:
        """从教务系统获取时间槽数据."""
        url = f"{self.config.api_url}/time_slots"
        response = self.session.get(url)
        data = response.json()
        return [self._parse_time_slot(item) for item in data.get("data", [])]

    def _parse_course(self, raw: Dict[str, Any]) -> Course:
        """解析教务系统课程数据."""
        return Course(
            id=raw.get("course_code", raw.get("id", "")),
            name=raw.get("course_name", raw.get("name", "")),
            teacher_id=raw.get("teacher_id", raw.get("teacher_code", "")),
            class_group_ids=raw.get("class_group_ids", raw.get("classes", [])),
            weekly_hours=raw.get("weekly_hours", raw.get("hours", 2)),
            expected_students=raw.get("expected_students", raw.get("students", 0)),
            required_room_type=raw.get("room_type", "general"),
            required_campus=raw.get("campus", ""),
            fixed_time_slot_id=raw.get("fixed_time_slot", ""),
            candidate_time_slot_ids=raw.get("candidate_time_slots", []),
        )

    def _parse_teacher(self, raw: Dict[str, Any]) -> Teacher:
        """解析教务系统教师数据."""
        return Teacher(
            id=raw.get("teacher_id", raw.get("id", "")),
            name=raw.get("teacher_name", raw.get("name", "")),
            unavailable_time_slot_ids=raw.get("unavailable_slots", []),
        )

    def _parse_room(self, raw: Dict[str, Any]) -> Room:
        """解析教务系统教室数据."""
        return Room(
            id=raw.get("room_id", raw.get("id", "")),
            name=raw.get("room_name", raw.get("name", "")),
            capacity=raw.get("capacity", 60),
            room_type=raw.get("room_type", "general"),
            campus=raw.get("campus", ""),
            building=raw.get("building", ""),
            available_time_slot_ids=raw.get("available_slots", []),
        )

    def _parse_time_slot(self, raw: Dict[str, Any]) -> TimeSlot:
        """解析教务系统时间槽数据."""
        return TimeSlot(
            id=raw.get("slot_id", raw.get("id", "")),
            weekday=raw.get("weekday", 1),
            start_section=raw.get("start_section", raw.get("start", 1)),
            end_section=raw.get("end_section", raw.get("end", 1)),
            start_time=raw.get("start_time", ""),
            end_time=raw.get("end_time", ""),
            label=raw.get("label", ""),
        )


# 数据字段映射配置
EDU_SYSTEM_FIELD_MAPPING = {
    "nankai": {
        "course": {
            "id": ["course_code", "kch"],
            "name": ["course_name", "kcmc"],
            "teacher_id": ["teacher_id", "jsgh"],
            "class_group_ids": ["class_group_ids", "bjbh_list"],
            "weekly_hours": ["weekly_hours", "zxcs"],
            "expected_students": ["expected_students", "rs"],
            "required_room_type": ["room_type", "jxlx"],
            "required_campus": ["campus", "xq"],
        },
        "teacher": {
            "id": ["teacher_id", "gh"],
            "name": ["teacher_name", "xm"],
            "unavailable_time_slot_ids": ["unavailable_slots", "bkyx"],
        },
        "room": {
            "id": ["room_id", "jsh"],
            "name": ["room_name", "jsmc"],
            "capacity": ["capacity", "rz"],
            "room_type": ["room_type", "jxlx"],
            "campus": ["campus", "xq"],
        },
    }
}


def generate_sync_report(sync_result: SyncResult) -> str:
    """生成同步报告."""
    if sync_result.success:
        return f"""数据同步报告
时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
状态: 成功

同步统计:
- 课程: {sync_result.imported_courses} 门
- 教师: {sync_result.imported_teachers} 人
- 教室: {sync_result.imported_rooms} 间
- 时间槽: {sync_result.imported_time_slots} 个

{sync_result.message}"""
    else:
        return f"""数据同步报告
时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
状态: 失败

错误信息: {sync_result.message}
详细信息: {sync_result.error_details}"""