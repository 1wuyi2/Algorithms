# 后端 API 文档

当前 API 使用 Python 标准库实现，启动命令：

```bash
python -m src.api.server
```

默认地址：

```text
http://127.0.0.1:8000
```

## 统一响应格式

成功响应统一包含：

```json
{
  "success": true,
  "data": {},
  "meta": {}
}
```

为了兼容早期前端和测试，当前仍然保留旧版顶层字段，例如 `algorithm`、`assignments`、`is_complete`。

错误响应统一包含：

```json
{
  "success": false,
  "code": "VALIDATION_ERROR",
  "error": "Missing required field: id"
}
```

## 通用数据结构

课程示例：

```json
{
  "id": "C001",
  "name": "数据结构",
  "teacher_id": "T001",
  "class_group_ids": ["G001"],
  "weekly_hours": 2,
  "candidate_time_slot_ids": ["D1-S1", "D1-S2"]
}
```

时间槽示例：

```json
{
  "id": "D1-S1",
  "weekday": 1,
  "start_section": 1,
  "end_section": 1,
  "start_time": "08:00",
  "end_time": "08:45",
  "label": "周一第1节"
}
```

排课结果示例：

```json
{
  "course_id": "C001",
  "time_slot_id": "D1-S1",
  "room_id": null
}
```

## GET /health

健康检查。

响应示例：

```json
{
  "success": true,
  "data": {
    "status": "ok",
    "service": "nankai-scheduling-api"
  },
  "meta": {},
  "status": "ok",
  "service": "nankai-scheduling-api"
}
```

## POST /schedule/greedy

运行贪心图染色排课。

请求示例：

```json
{
  "courses": [
    {
      "id": "C001",
      "name": "数据结构",
      "teacher_id": "T001",
      "class_group_ids": ["G001"],
      "weekly_hours": 2
    },
    {
      "id": "C002",
      "name": "操作系统",
      "teacher_id": "T001",
      "class_group_ids": ["G002"],
      "weekly_hours": 2
    }
  ],
  "time_slots": [
    {"id": "D1-S1", "weekday": 1, "start_section": 1, "end_section": 1},
    {"id": "D1-S2", "weekday": 1, "start_section": 2, "end_section": 2}
  ],
  "options": {
    "prioritize_fixed_time": true,
    "sort_by_conflict_degree": true,
    "sort_by_candidate_count": false
  }
}
```

`options` 可选，用于调整贪心算法的课程排序策略：

- `prioritize_fixed_time`：是否优先安排固定时间课程
- `sort_by_conflict_degree`：是否优先安排冲突度更高的课程
- `sort_by_candidate_count`：是否优先安排候选时间更少的课程

响应中的 `unscheduled` 会给出未排课程原因、候选时间槽和阻塞课程。

## POST /schedule/backtracking

运行回溯搜索 / 约束满足排课。

请求参数与 `/schedule/greedy` 基本一致，可额外传入：

```json
{
  "max_steps": 100000
}
```

响应中的 `failure_details` 会给出失败课程、候选时间槽、当前可行时间槽和阻塞课程。

## POST /schedule/compare

同时运行贪心图染色和回溯搜索，并返回推荐算法。

请求参数与 `/schedule/greedy` 基本一致，也支持 `options` 和 `max_steps`。

响应示例字段：

```json
{
  "recommended_algorithm": "backtracking_search",
  "recommendation_reason": "Backtracking found a complete schedule while greedy did not.",
  "greedy": {
    "is_complete": false,
    "score": 80,
    "metrics": {}
  },
  "backtracking": {
    "is_complete": true,
    "score": 100,
    "metrics": {}
  }
}
```

## POST /schedule/evaluate

评价已有排课结果。

请求示例：

```json
{
  "courses": [
    {
      "id": "C001",
      "name": "数据结构",
      "teacher_id": "T001",
      "class_group_ids": ["G001"],
      "weekly_hours": 2
    }
  ],
  "time_slots": [
    {"id": "D1-S1", "weekday": 1, "start_section": 1, "end_section": 1}
  ],
  "assignments": [
    {"course_id": "C001", "time_slot_id": "D1-S1"}
  ],
  "rooms": []
}
```

评价结果包含：

- `score`：课表评分
- `is_feasible`：是否无硬性错误
- `errors`：错误列表
- `warnings`：警告列表
- `metrics`：评价指标

当前 `metrics` 包含：

- `teacher_daily_load`：教师每日课程数量
- `class_group_daily_load`：班级每日课程数量
- `max_teacher_daily_load`：单个教师最大日负载
- `max_class_group_daily_load`：单个班级最大日负载
- `early_section_count`：早课数量
- `evening_section_count`：晚课数量

## POST /assistant/analyze

生成规则化的辅助排课分析，不调用外部大模型。

请求参数与 `/schedule/evaluate` 类似，可传入课程、时间槽、排课结果和教室。

响应包含：

- `risk_level`：风险等级
- `summary`：分析摘要
- `metrics`：结构化指标
- `suggestions`：优化建议
