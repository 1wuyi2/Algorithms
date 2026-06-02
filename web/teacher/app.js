const API_BASE_URL = window.location.protocol.startsWith("http")
  ? window.location.origin
  : "http://127.0.0.1:8000";
const AUTH_KEY = "nankai-auth-session-v1";
const STORAGE_KEY = "nankai-teacher-admin-state-v1";

const authSession = readAuthSession();
if (!authSession || authSession.role !== "teacher") {
  window.location.replace("../login/index.html");
  throw new Error("Teacher authentication required");
}

const weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"];
const sectionTimeLabels = {
  1: "8:00-8:45",
  2: "8:55-9:40",
  3: "10:00-10:45",
  4: "10:55-11:40",
  5: "12:00-12:45",
  6: "12:55-13:40",
  7: "14:00-14:45",
  8: "14:55-15:40",
  9: "16:00-16:45",
  10: "16:55-17:40",
  11: "18:30-19:15",
  12: "19:25-20:10",
  13: "20:20-21:05",
  14: "21:15-22:00",
};
const roomTypeLabels = {
  general: "普通教室",
  computer_lab: "机房",
  lab: "实验室",
  multimedia: "多媒体教室",
};
const campusLabels = {
  jinnan: "津南校区",
  balitai: "八里台校区",
};

const sampleState = {
  courses: [
    {
      id: "COCS0010",
      name: "数据结构",
      teacherId: "9920260001",
      classGroupIds: ["1001"],
      weeklyHours: 2,
      expectedStudents: 58,
      requiredRoomType: "general",
      requiredCampus: "jinnan",
      candidateTimeSlotIds: ["D1-S1", "D1-S2", "D2-S3", "D3-S4"],
    },
    {
      id: "COCS0020",
      name: "算法设计与分析",
      teacherId: "9920260001",
      classGroupIds: ["1002"],
      weeklyHours: 2,
      expectedStudents: 52,
      requiredRoomType: "general",
      requiredCampus: "jinnan",
      candidateTimeSlotIds: ["D1-S1", "D2-S3", "D4-S5"],
    },
    {
      id: "COCS0030",
      name: "操作系统",
      teacherId: "9920260002",
      classGroupIds: ["2001"],
      weeklyHours: 2,
      expectedStudents: 60,
      requiredRoomType: "computer_lab",
      requiredCampus: "jinnan",
      candidateTimeSlotIds: ["D1-S2", "D3-S4", "D5-S6"],
    },
    {
      id: "COCS0040",
      name: "数据库系统",
      teacherId: "9920260003",
      classGroupIds: ["1003"],
      weeklyHours: 2,
      expectedStudents: 48,
      requiredRoomType: "multimedia",
      requiredCampus: "balitai",
      fixedTimeSlotId: "D2-S1",
    },
  ],
  teachers: [
    { id: "9920260001", name: "王老师", unavailableTimeSlotIds: ["D5-S6"] },
    { id: "9920260002", name: "李老师", unavailableTimeSlotIds: ["D1-S1"] },
    { id: "9920260003", name: "赵老师", unavailableTimeSlotIds: [] },
  ],
  rooms: [
    { id: "公教楼A101", name: "津南公教 A101", capacity: 80, roomType: "general", campus: "jinnan", building: "公共教学楼 A 区" },
    { id: "实验楼B203", name: "津南实验楼 B203", capacity: 64, roomType: "computer_lab", campus: "jinnan", building: "实验楼 B 区" },
    { id: "二主楼201", name: "八里台二主楼 201", capacity: 70, roomType: "multimedia", campus: "balitai", building: "二主楼" },
  ],
  timeSlots: buildDefaultWeekSlots(),
  assignments: [],
  evaluation: null,
  insight: null,
  latestRun: null,
  logs: [],
};

let state = loadState();
let selectedAlgorithm = "greedy";
let selectedOverviewDetail = "courses";
let collapsedOverviewRoomIds = new Set();

const elements = {
  appShell: document.querySelector(".app-shell"),
  teacherIdentity: document.querySelector("#teacherIdentity"),
  logoutButton: document.querySelector("#logoutButton"),
  sidebarToggle: document.querySelector("#sidebarToggle"),
  views: document.querySelectorAll(".view"),
  navTabs: document.querySelectorAll(".nav-tab"),
  apiBaseLabel: document.querySelector("#apiBaseLabel"),
  courseCount: document.querySelector("#courseCount"),
  teacherCount: document.querySelector("#teacherCount"),
  roomCount: document.querySelector("#roomCount"),
  timeSlotCount: document.querySelector("#timeSlotCount"),
  assignmentCount: document.querySelector("#assignmentCount"),
  scoreValue: document.querySelector("#scoreValue"),
  latestSummary: document.querySelector("#latestSummary"),
  metricCards: document.querySelectorAll("[data-overview-detail]"),
  overviewDetailTitle: document.querySelector("#overviewDetailTitle"),
  overviewDetailHint: document.querySelector("#overviewDetailHint"),
  overviewDetailBody: document.querySelector("#overviewDetailBody"),
  courseForm: document.querySelector("#courseForm"),
  teacherForm: document.querySelector("#teacherForm"),
  roomForm: document.querySelector("#roomForm"),
  timeSlotForm: document.querySelector("#timeSlotForm"),
  courseTableBody: document.querySelector("#courseTableBody"),
  teacherTableBody: document.querySelector("#teacherTableBody"),
  roomTableBody: document.querySelector("#roomTableBody"),
  timeSlotTableBody: document.querySelector("#timeSlotTableBody"),
  courseTableHint: document.querySelector("#courseTableHint"),
  algorithmControl: document.querySelector("#algorithmControl"),
  runLog: document.querySelector("#runLog"),
  timetableGrid: document.querySelector("#timetableGrid"),
  timetableFilter: document.querySelector("#timetableFilter"),
  assignmentTableBody: document.querySelector("#assignmentTableBody"),
  assignmentHint: document.querySelector("#assignmentHint"),
  metricsGrid: document.querySelector("#metricsGrid"),
  issueList: document.querySelector("#issueList"),
  suggestionList: document.querySelector("#suggestionList"),
  issueCountLabel: document.querySelector("#issueCountLabel"),
  feasibleBadge: document.querySelector("#feasibleBadge"),
  riskBadge: document.querySelector("#riskBadge"),
  teacherIds: document.querySelector("#teacherIds"),
  timeSlotIds: document.querySelector("#timeSlotIds"),
  semesterSelect: document.querySelector("#semesterSelect"),
  loadBackendDataBtn: document.querySelector("#loadBackendDataBtn"),
};

elements.apiBaseLabel.textContent = API_BASE_URL;
elements.teacherIdentity.textContent = `${authSession.name || "教师用户"} ${authSession.account}`;

elements.sidebarToggle.addEventListener("click", () => {
  const collapsed = elements.appShell.classList.toggle("sidebar-collapsed");
  elements.sidebarToggle.setAttribute("aria-expanded", String(!collapsed));
  elements.sidebarToggle.setAttribute("aria-label", collapsed ? "展开导航" : "收起导航");
});

elements.logoutButton.addEventListener("click", () => {
  localStorage.removeItem(AUTH_KEY);
  window.location.href = "../login/index.html";
});

elements.navTabs.forEach((tab) => {
  tab.addEventListener("click", () => showView(tab.dataset.view));
});

elements.metricCards.forEach((card) => {
  card.addEventListener("click", () => {
    selectedOverviewDetail = card.dataset.overviewDetail;
    showView("overview");
    renderMetricCards();
    renderOverviewDetail();
  });
});

elements.overviewDetailBody.addEventListener("click", (event) => {
  const button = event.target.closest("[data-room-toggle]");
  if (!button) return;
  const roomId = button.dataset.roomToggle;
  if (collapsedOverviewRoomIds.has(roomId)) {
    collapsedOverviewRoomIds.delete(roomId);
  } else {
    collapsedOverviewRoomIds.add(roomId);
  }
  renderRoomOverviewDetail();
});

document.querySelector("#loadSampleButton").addEventListener("click", () => {
  state = structuredClone(sampleState);
  addLog("已载入教师端联调样例数据。");
  persistAndRender();
});

document.querySelector("#clearAllButton").addEventListener("click", () => {
  state = emptyState();
  addLog("已清空浏览器本地数据。");
  persistAndRender();
});

document.querySelector("#healthCheckButton").addEventListener("click", checkHealth);
document.querySelector("#exportJsonButton").addEventListener("click", exportStateJson);
document.querySelector("#generateWeekSlotsButton").addEventListener("click", () => {
  state.timeSlots = buildDefaultWeekSlots();
  state.assignments = [];
  state.evaluation = null;
  state.insight = null;
  addLog("已生成 7 天 x 14 节的默认时间槽。");
  persistAndRender();
});
document.querySelector("#runScheduleButton").addEventListener("click", runSchedule);
document.querySelector("#clearLogButton").addEventListener("click", () => {
  state.logs = [];
  persistAndRender();
});
document.querySelector("#evaluateButton").addEventListener("click", evaluateCurrentSchedule);
document.querySelector("#analyzeButton").addEventListener("click", analyzeCurrentSchedule);
elements.timetableFilter.addEventListener("input", renderTimetable);

elements.algorithmControl.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-algorithm]");
  if (!button) return;
  selectedAlgorithm = button.dataset.algorithm;
  elements.algorithmControl.querySelectorAll("button").forEach((item) => item.classList.remove("selected"));
  button.classList.add("selected");
});

elements.courseForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const formData = new FormData(elements.courseForm);
  const course = {
    id: field(formData, "id"),
    name: field(formData, "name"),
    teacherId: field(formData, "teacherId"),
    classGroupIds: splitCsv(formData.get("classGroupIds")),
    weeklyHours: Number(formData.get("weeklyHours") || 2),
    expectedStudents: optionalNumber(formData.get("expectedStudents")),
    requiredRoomType: field(formData, "requiredRoomType") || "general",
    requiredCampus: optionalString(formData.get("requiredCampus")),
    fixedTimeSlotId: optionalString(formData.get("fixedTimeSlotId")),
    candidateTimeSlotIds: splitCsv(formData.get("candidateTimeSlotIds")),
  };
  upsertById(state.courses, course);
  clearRunResults();
  elements.courseForm.reset();
  elements.courseForm.weeklyHours.value = "2";
  addLog(`已保存课程 ${course.id}。`);
  persistAndRender();
});

elements.teacherForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const formData = new FormData(elements.teacherForm);
  const teacher = {
    id: field(formData, "id"),
    name: field(formData, "name"),
    unavailableTimeSlotIds: splitCsv(formData.get("unavailableTimeSlotIds")),
  };
  upsertById(state.teachers, teacher);
  elements.teacherForm.reset();
  addLog(`已保存教师 ${teacher.id}。`);
  persistAndRender();
});

elements.roomForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const formData = new FormData(elements.roomForm);
  const room = {
    id: field(formData, "id"),
    name: field(formData, "name"),
    capacity: Number(formData.get("capacity") || 1),
    roomType: field(formData, "roomType") || "general",
    campus: optionalString(formData.get("campus")),
    building: optionalString(formData.get("building")),
    availableTimeSlotIds: splitCsv(formData.get("availableTimeSlotIds")),
  };
  upsertById(state.rooms, room);
  elements.roomForm.reset();
  elements.roomForm.capacity.value = "60";
  addLog(`已保存教室 ${room.id}。`);
  persistAndRender();
});

elements.timeSlotForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const formData = new FormData(elements.timeSlotForm);
  const slot = {
    id: field(formData, "id"),
    weekday: Number(formData.get("weekday") || 1),
    startSection: Number(formData.get("startSection") || 1),
    endSection: Number(formData.get("endSection") || 1),
    startTime: optionalString(formData.get("startTime")),
    endTime: optionalString(formData.get("endTime")),
    label: optionalString(formData.get("label")),
  };
  upsertById(state.timeSlots, slot);
  clearRunResults();
  elements.timeSlotForm.reset();
  elements.timeSlotForm.startSection.value = "1";
  elements.timeSlotForm.endSection.value = "1";
  addLog(`已保存时间槽 ${slot.id}。`);
  persistAndRender();
});

document.body.addEventListener("click", (event) => {
  const button = event.target.closest("[data-action]");
  if (!button) return;
  const { action, type, id } = button.dataset;
  if (action === "edit") editEntity(type, id);
  if (action === "delete") deleteEntity(type, id);
});

if (elements.loadBackendDataBtn) {
  elements.loadBackendDataBtn.addEventListener("click", loadBackendData);
}


checkHealth();
render();

function showView(viewName) {
  elements.navTabs.forEach((item) => item.classList.toggle("active", item.dataset.view === viewName));
  elements.views.forEach((view) => view.classList.toggle("active", view.id === `view-${viewName}`));
}

async function checkHealth() {
  setApiStatus("检测中", "neutral");
  try {
    const result = await apiRequest("/health", { method: "GET" });
    setApiStatus(`${result.service || result.data?.service || "API"} 在线`, "online");
    addLog("后端健康检查通过。");
  } catch (error) {
    setApiStatus("API 未启动", "offline");
    addLog(`后端健康检查失败：${error.message}`);
  }
  persistAndRender();
}

async function runSchedule() {
  if (!state.courses.length || !state.timeSlots.length) {
    addLog("排课失败：请至少录入课程和时间槽。");
    showView("issues");
    return;
  }

  const freeReschedule = Boolean(document.querySelector("#freeRescheduleMode")?.checked);
  addLog(`开始调用 ${selectedAlgorithm} 排课接口。${freeReschedule ? "模式：重新自动排课，忽略导入时间。" : "模式：尊重导入时间。"}。`);
  try {
    const payload = buildSchedulePayload();
    const endpoint = selectedAlgorithm === "backtracking"
      ? "/schedule/backtracking"
      : selectedAlgorithm === "compare"
        ? "/schedule/compare"
        : "/schedule/greedy";
    const result = await apiRequest(endpoint, {
      method: "POST",
      body: JSON.stringify(payload),
    });

    applyScheduleResult(result);
    await evaluateCurrentSchedule({ silent: true });
    await analyzeCurrentSchedule({ silent: true });
    addLog("排课、评价和辅助分析已完成。");
    showView("timetable");
  } catch (error) {
    addLog(`排课接口调用失败：${error.message}`);
    state.evaluation = {
      score: 0,
      is_feasible: false,
      errors: [{ severity: "error", message: error.message, related_ids: [] }],
      warnings: [],
      issues: [{ severity: "error", message: error.message, related_ids: [] }],
      metrics: {},
    };
    persistAndRender();
    showView("issues");
  }
}

async function evaluateCurrentSchedule(options = {}) {
  if (!state.assignments.length) {
    const missingIssues = state.courses.map((course) => ({
      issue_type: "missing_assignment",
      severity: "error",
      message: "A course has no schedule assignment.",
      related_ids: [course.id],
    }));
    state.evaluation = {
      score: 0,
      is_feasible: false,
      issues: missingIssues,
      errors: missingIssues,
      warnings: [],
      metrics: {
        assigned_course_count: 0,
        missing_assignment_count: state.courses.length,
        assignments_with_known_time_slots: 0,
        teacher_daily_load: {},
        class_group_daily_load: {},
        max_teacher_daily_load: 0,
        max_class_group_daily_load: 0,
        early_section_count: 0,
        evening_section_count: 0,
      },
    };
    if (!options.silent) addLog("课表评价完成，当前没有排课结果，评分 0。");
    persistAndRender();
    return;
  }
  try {
    const result = await apiRequest("/schedule/evaluate", {
      method: "POST",
      body: JSON.stringify({
        courses: state.courses,
        timeSlots: state.timeSlots,
        assignments: state.assignments,
        rooms: state.rooms,
      }),
    });
    state.evaluation = result;
    if (!options.silent) addLog(`课表评价完成，评分 ${result.score}。`);
    persistAndRender();
  } catch (error) {
    addLog(`课表评价失败：${error.message}`);
    persistAndRender();
  }
}

async function analyzeCurrentSchedule(options = {}) {
  try {
    const result = await apiRequest("/assistant/analyze", {
      method: "POST",
      body: JSON.stringify({
        courses: state.courses,
        timeSlots: state.timeSlots,
        assignments: state.assignments,
        rooms: state.rooms,
      }),
    });
    state.insight = result;
    if (!options.silent) addLog(`辅助分析完成，风险等级 ${result.risk_level}。`);
    persistAndRender();
  } catch (error) {
    addLog(`辅助分析失败：${error.message}`);
    persistAndRender();
  }
}

function buildSchedulePayload() {
  const freeReschedule = Boolean(document.querySelector("#freeRescheduleMode")?.checked);
  const courses = state.courses.map((course) => normalizeCourseForApi(course, { freeReschedule }));
  const timeSlots = state.timeSlots.map(normalizeTimeSlotForApi);
  const rooms = state.rooms.map(normalizeRoomForApi);
  return {
    semester: elements.semesterSelect ? elements.semesterSelect.value : "2025-2026-1", 
    courses,
    time_slots: timeSlots,
    timeSlots,
    rooms,
    options: {
      prioritizeFixedTime: !freeReschedule && document.querySelector("#prioritizeFixedTime").checked,
      sortByConflictDegree: document.querySelector("#sortByConflictDegree").checked,
      sortByCandidateCount: document.querySelector("#sortByCandidateCount").checked,
    },
    maxSteps: Number(document.querySelector("#maxStepsInput").value || 100000),
  };
}

function applyScheduleResult(result) {
  if (selectedAlgorithm === "compare") {
    const recommended = result.recommended_algorithm === "backtracking_search" ? result.backtracking : result.greedy;
    state.assignments = normalizeAssignments(recommended.assignments || []);
    state.latestRun = {
      algorithm: result.recommended_algorithm,
      isComplete: Boolean(recommended.is_complete),
      summary: result.recommendation_reason,
      raw: result,
    };
    addLog(`算法对比完成：推荐 ${result.recommended_algorithm}。${result.recommendation_reason}`);
    return;
  }

  state.assignments = normalizeAssignments(result.assignments || []);
  state.latestRun = {
    algorithm: result.algorithm,
    isComplete: Boolean(result.is_complete),
    summary: result.is_complete ? "所有课程已排入时间槽。" : `${(result.unscheduled || result.failure_details || []).length} 门课程未排入。`,
    raw: result,
  };

  const blocked = result.unscheduled || result.failure_details || [];
  if (blocked.length) {
    blocked.forEach((item) => addLog(`未排课程 ${item.course_id}：${item.reason}`));
  }
}

async function apiRequest(path, options = {}) {
  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
  } catch (error) {
    throw new Error(`无法连接后端服务：${error.message}`);
  }

  let result = {};
  const rawText = response.status === 204 ? "" : await response.text();
  if (rawText) {
    try {
      result = JSON.parse(rawText);
    } catch {
      throw new Error("后端返回了无法解析的数据");
    }
  }
  if (!response.ok || result.success === false) {
    throw new Error(result.error || result.message || `HTTP ${response.status}`);
  }
  return result;
}

function render() {
  elements.courseCount.textContent = state.courses.length;
  elements.teacherCount.textContent = state.teachers.length;
  elements.roomCount.textContent = state.rooms.length;
  elements.timeSlotCount.textContent = state.timeSlots.length;
  elements.assignmentCount.textContent = state.assignments.length;
  elements.scoreValue.textContent = state.evaluation ? state.evaluation.score : "--";
  elements.latestSummary.textContent = state.latestRun
    ? `${state.latestRun.algorithm}：${state.latestRun.summary}`
    : "尚未生成课表。";

  renderDatalists();
  renderMetricCards();
  renderOverviewDetail();
  renderCourses();
  renderTeachers();
  renderRooms();
  renderTimeSlots();
  renderLog();
  renderTimetable();
  renderEvaluation();
  saveState();
}

function renderDatalists() {
  elements.teacherIds.innerHTML = state.teachers.map((teacher) => `<option value="${escapeHtml(teacher.id)}"></option>`).join("");
  elements.timeSlotIds.innerHTML = state.timeSlots.map((slot) => `<option value="${escapeHtml(slot.id)}"></option>`).join("");
}

function renderMetricCards() {
  elements.metricCards.forEach((card) => {
    card.classList.toggle("active", card.dataset.overviewDetail === selectedOverviewDetail);
  });
}

function renderOverviewDetail() {
  const renderers = {
    courses: renderCourseOverviewDetail,
    teachers: renderTeacherOverviewDetail,
    rooms: renderRoomOverviewDetail,
    timeSlots: renderTimeSlotOverviewDetail,
    assignments: renderAssignmentOverviewDetail,
    score: renderScoreOverviewDetail,
  };
  const renderer = renderers[selectedOverviewDetail] || renderCourseOverviewDetail;
  renderer();
}

function renderCourseOverviewDetail() {
  setOverviewDetailHeader("课程详情", `${state.courses.length} 门课程`);
  if (!state.courses.length) {
    renderOverviewEmpty("暂无课程数据");
    return;
  }
  renderOverviewTable(
    ["课程编号", "课程名称"],
    state.courses.flatMap((course) => (course.classGroupIds || []).map((courseNumber) => [
      courseNumber,
      course.name,
    ])),
  );
}

function renderTeacherOverviewDetail() {
  setOverviewDetailHeader("教师详情", `${state.teachers.length} 位教师`);
  const rows = [];
  state.teachers.forEach((teacher) => {
    const courses = state.courses.filter((course) => course.teacherId === teacher.id);
    if (!courses.length) {
      rows.push([teacher.name, teacher.id, "未关联", "未关联课程"]);
      return;
    }
    courses.forEach((course) => {
      rows.push([teacher.name, teacher.id, (course.classGroupIds || []).join(", "), course.name]);
    });
  });
  if (!rows.length) {
    renderOverviewEmpty("暂无教师数据");
    return;
  }
  renderOverviewTable(["教师名称", "教师学工号", "课程编号", "课程名称"], rows);
}

function renderRoomOverviewDetail() {
  setOverviewDetailHeader("教室详情", `${state.rooms.length} 间教室`);
  if (!state.rooms.length) {
    renderOverviewEmpty("暂无教室数据");
    return;
  }

  const primarySlots = [...state.timeSlots].sort(compareSlots).slice(0, 14);
  const roomGroups = state.rooms.map((room) => {
    if (!primarySlots.length) {
      return {
        room,
        rows: [["未设置时间槽", "空闲"]],
      };
    }
    return {
      room,
      rows: primarySlots.map((slot) => {
      const assignments = state.assignments.filter((assignment) => {
        if (assignment.timeSlotId !== slot.id) return false;
        return !assignment.roomId || assignment.roomId === room.id;
      });
      const courseNumbers = assignments
        .map((assignment) => findById(state.courses, assignment.courseId))
        .filter(Boolean)
        .flatMap((course) => course.classGroupIds || []);
        return [formatSlot(slot.id), courseNumbers.join(", ") || "空闲"];
      }),
    };
  });
  renderRoomOverviewTable(roomGroups);
}

function renderTimeSlotOverviewDetail() {
  setOverviewDetailHeader("时间槽详情", `${state.timeSlots.length} 个时间槽`);
  if (!state.timeSlots.length) {
    renderOverviewEmpty("暂无时间槽数据");
    return;
  }
  renderOverviewTable(
    ["时间槽编号", "星期", "节次", "时间"],
    [...state.timeSlots].sort(compareSlots).map((slot) => [
      slot.id,
      weekdays[slot.weekday - 1] || slot.weekday,
      `${slot.startSection}-${slot.endSection}`,
      [slot.startTime, slot.endTime].filter(Boolean).join("-") || slot.label || "未设置",
    ]),
  );
}

function renderAssignmentOverviewDetail() {
  setOverviewDetailHeader("已排课程详情", `${state.assignments.length} 条排课`);
  if (!state.assignments.length) {
    renderOverviewEmpty("暂无排课结果");
    return;
  }
  renderOverviewTable(
    ["课程编号", "课程名称", "教师", "时间段"],
    state.assignments.map((assignment) => {
      const course = findById(state.courses, assignment.courseId);
      const teacher = course ? findById(state.teachers, course.teacherId) : null;
      return [
        (course?.classGroupIds || [assignment.courseId]).join(", "),
        course?.name || assignment.courseId,
        teacher?.name || course?.teacherId || "-",
        formatSlot(assignment.timeSlotId),
      ];
    }),
  );
}

function renderScoreOverviewDetail() {
  setOverviewDetailHeader("课表评分详情", state.evaluation ? `${state.evaluation.score} 分` : "未评价");
  if (!state.evaluation) {
    renderOverviewEmpty("暂无课表评分，请先生成课表或重新评价。");
    return;
  }
  const metrics = state.evaluation.metrics || {};
  renderOverviewTable(
    ["指标", "数值"],
    [
      ["课表评分", state.evaluation.score],
      ["是否可行", state.evaluation.is_feasible ? "可行" : "存在硬冲突"],
      ["已排课程", metrics.assigned_course_count ?? state.assignments.length],
      ["未排课程", metrics.missing_assignment_count ?? Math.max(state.courses.length - state.assignments.length, 0)],
      ["早课数量", metrics.early_section_count ?? 0],
      ["晚课数量", metrics.evening_section_count ?? 0],
    ],
  );
}

function setOverviewDetailHeader(title, hint) {
  elements.overviewDetailTitle.textContent = title;
  elements.overviewDetailHint.textContent = hint;
}

function renderOverviewTable(headers, rows) {
  elements.overviewDetailBody.innerHTML = `<div class="table-wrap"><table class="overview-detail-table">
    <thead><tr>${headers.map((header) => `<th>${escapeHtml(header)}</th>`).join("")}</tr></thead>
    <tbody>${rows.map((row) => `<tr>${row.map((cell) => `<td>${escapeHtml(cell)}</td>`).join("")}</tr>`).join("")}</tbody>
  </table></div>`;
}

function renderRoomOverviewTable(roomGroups) {
  const rowsHtml = roomGroups.flatMap((group) => {
    const collapsed = collapsedOverviewRoomIds.has(group.room.id);
    const visibleRows = collapsed ? group.rows.slice(0, 1) : group.rows;
    return visibleRows.map((row, index) => {
      const roomCell = index === 0
        ? `<td class="overview-room-cell">
            <button class="room-toggle" type="button" data-room-toggle="${escapeHtml(group.room.id)}" aria-label="${collapsed ? "展开教室排课" : "折叠教室排课"}">${collapsed ? "+" : "-"}</button>
            <span>${escapeHtml(group.room.name || group.room.id)}</span>
          </td>`
        : `<td class="overview-room-cell repeat">${escapeHtml(group.room.name || group.room.id)}</td>`;
      return `<tr>${roomCell}<td>${escapeHtml(row[0])}</td><td>${escapeHtml(row[1])}</td></tr>`;
    });
  });

  elements.overviewDetailBody.innerHTML = `<div class="table-wrap"><table class="overview-detail-table">
    <thead><tr><th>教室名称</th><th>时间段</th><th>排课情况</th></tr></thead>
    <tbody>${rowsHtml.join("")}</tbody>
  </table></div>`;
}

function renderOverviewEmpty(message) {
  elements.overviewDetailBody.innerHTML = `<div class="empty-state">${escapeHtml(message)}</div>`;
}

function renderCourses() {
  elements.courseTableHint.textContent = `${state.courses.length} 门课程`;
  if (!state.courses.length) {
    elements.courseTableBody.innerHTML = '<tr><td colspan="6">暂无课程数据</td></tr>';
    return;
  }
  elements.courseTableBody.innerHTML = state.courses.map((course) => {
    const teacher = findById(state.teachers, course.teacherId);
    const constraints = [
      `${course.weeklyHours || 2} 学时`,
      course.expectedStudents ? `${course.expectedStudents} 人` : "",
      roomTypeLabels[course.requiredRoomType] || "",
      course.requiredCampus ? campusLabels[course.requiredCampus] : "",
      course.fixedTimeSlotId ? `固定 ${course.fixedTimeSlotId}` : "",
      course.candidateTimeSlotIds?.length ? `候选 ${course.candidateTimeSlotIds.length} 个` : "",
    ].filter(Boolean).join(" / ");
    return `<tr>
      <td>${escapeHtml(course.id)}</td>
      <td>${escapeHtml(course.name)}</td>
      <td>${escapeHtml(teacher ? teacher.name : course.teacherId)}</td>
      <td>${escapeHtml((course.classGroupIds || []).join(", "))}</td>
      <td>${escapeHtml(constraints || "无特殊约束")}</td>
      <td><div class="row-actions">${actionButtons("courses", course.id)}</div></td>
    </tr>`;
  }).join("");
}

function renderTeachers() {
  if (!state.teachers.length) {
    elements.teacherTableBody.innerHTML = '<tr><td colspan="4">暂无教师数据</td></tr>';
    return;
  }
  elements.teacherTableBody.innerHTML = state.teachers.map((teacher) => `<tr>
    <td>${escapeHtml(teacher.employeeId || teacher.account || teacher.id)}</td>
    <td>${escapeHtml(teacher.name)}</td>
    <td>${escapeHtml((teacher.unavailableTimeSlotIds || []).join(", ") || "未设置")}</td>
    <td><div class="row-actions">${actionButtons("teachers", teacher.id)}</div></td>
  </tr>`).join("");
}

function renderRooms() {
  if (!state.rooms.length) {
    elements.roomTableBody.innerHTML = '<tr><td colspan="6">暂无教室数据</td></tr>';
    return;
  }
  elements.roomTableBody.innerHTML = state.rooms.map((room) => `<tr>
    <td>${escapeHtml(room.id)}</td>
    <td>${escapeHtml(room.name)}</td>
    <td>${escapeHtml(room.capacity)}</td>
    <td>${escapeHtml(roomTypeLabels[room.roomType] || room.roomType || "普通教室")}</td>
    <td>${escapeHtml(campusLabels[room.campus] || "未指定")}</td>
    <td><div class="row-actions">${actionButtons("rooms", room.id)}</div></td>
  </tr>`).join("");
}

function renderTimeSlots() {
  if (!state.timeSlots.length) {
    elements.timeSlotTableBody.innerHTML = '<tr><td colspan="5">暂无时间槽数据</td></tr>';
    return;
  }
  elements.timeSlotTableBody.innerHTML = [...state.timeSlots]
    .sort(compareSlots)
    .map((slot) => `<tr>
      <td>${escapeHtml(slot.id)}</td>
      <td>${escapeHtml(weekdays[slot.weekday - 1] || slot.weekday)}</td>
      <td>${escapeHtml(`${slot.startSection}-${slot.endSection}`)}</td>
      <td>${escapeHtml([slot.startTime, slot.endTime].filter(Boolean).join("-") || slot.label || "未设置")}</td>
      <td><div class="row-actions">${actionButtons("timeSlots", slot.id)}</div></td>
    </tr>`).join("");
}

function renderLog() {
  elements.runLog.textContent = state.logs.length ? state.logs.slice(-12).join("\n") : "等待运行。";
}

function renderTimetable() {
  const filter = elements.timetableFilter.value.trim().toLowerCase();
  const assignments = state.assignments.filter((assignment) => assignmentMatchesFilter(assignment, filter));
  const slotsByKey = new Map();
  assignments.forEach((assignment) => {
    const slot = findById(state.timeSlots, assignment.timeSlotId);
    if (!slot) return;
    const key = `${slot.startSection}:${slot.weekday}`;
    const list = slotsByKey.get(key) || [];
    list.push(assignment);
    slotsByKey.set(key, list);
  });

  const sections = Array.from({ length: 14 }, (_, index) => index + 1);
  const cells = ['<div class="day-cell">节次</div>', ...weekdays.map((day) => `<div class="day-cell">${day}</div>`)];
  sections.forEach((section) => {
    const timeLabel = sectionTimeLabels[section];
    const periodClass = section <= 6 ? "morning-section" : section <= 10 ? "afternoon-section" : "evening-section";
    const timeCellClass = timeLabel ? `time-cell ${periodClass}` : "time-cell";
    cells.push(`<div class="${timeCellClass}">
      <span>第 ${section} 节</span>
      ${timeLabel ? `<small>${timeLabel}</small>` : ""}
    </div>`);
    for (let weekday = 1; weekday <= 7; weekday += 1) {
      const list = slotsByKey.get(`${section}:${weekday}`) || [];
      cells.push(`<div class="slot-cell">${list.map(renderSlotCard).join("")}</div>`);
    }
  });
  elements.timetableGrid.innerHTML = cells.join("");

  elements.assignmentHint.textContent = `${assignments.length} 条排课`;
  if (!assignments.length) {
    elements.assignmentTableBody.innerHTML = '<tr><td colspan="5">暂无排课结果</td></tr>';
    return;
  }
  elements.assignmentTableBody.innerHTML = assignments.map((assignment) => {
    const course = findById(state.courses, assignment.courseId);
    const teacher = course ? findById(state.teachers, course.teacherId) : null;
    return `<tr>
      <td>${escapeHtml(course ? `${course.name} (${course.id})` : assignment.courseId)}</td>
      <td>${escapeHtml(teacher ? teacher.name : course?.teacherId || "-")}</td>
      <td>${escapeHtml((course?.classGroupIds || []).join(", ") || "-")}</td>
      <td>${escapeHtml(formatSlot(assignment.timeSlotId))}</td>
      <td>${escapeHtml(assignment.roomId || "未分配")}</td>
    </tr>`;
  }).join("");
}

function renderSlotCard(assignment) {
  const course = findById(state.courses, assignment.courseId);
  const teacher = course ? findById(state.teachers, course.teacherId) : null;
  return `<div class="slot-card">
    <strong>${escapeHtml(course?.name || assignment.courseId)}</strong>
    <span>${escapeHtml(teacher?.name || course?.teacherId || "-")}</span>
    <span>${escapeHtml((course?.classGroupIds || []).join(", ") || "-")}</span>
  </div>`;
}

function renderEvaluation() {
  const evaluation = state.evaluation;
  const insight = state.insight;
  const issues = evaluation ? (evaluation.issues || [...(evaluation.errors || []), ...(evaluation.warnings || [])]) : [];
  elements.issueCountLabel.textContent = evaluation ? `${issues.length} 项` : "";

  if (!evaluation) {
    elements.metricsGrid.innerHTML = '<div class="empty-state">暂无评价指标</div>';
    elements.issueList.innerHTML = '<div class="empty-state">暂无冲突信息</div>';
    elements.feasibleBadge.className = "badge neutral";
    elements.feasibleBadge.textContent = "未评价";
  } else {
    elements.feasibleBadge.className = `badge ${evaluation.is_feasible ? "success" : "danger"}`;
    elements.feasibleBadge.textContent = evaluation.is_feasible ? "可行" : "存在硬冲突";
    const metrics = evaluation.metrics || {};
    elements.metricsGrid.innerHTML = [
      metricDetail("课表评分", evaluation.score),
      metricDetail("已排课程", metrics.assigned_course_count ?? state.assignments.length),
      metricDetail("未排课程", metrics.missing_assignment_count ?? Math.max(state.courses.length - state.assignments.length, 0)),
      metricDetail("早课数量", metrics.early_section_count ?? 0),
      metricDetail("晚课数量", metrics.evening_section_count ?? 0),
      metricDetail("教师最大日负载", metrics.max_teacher_daily_load ?? 0),
    ].join("");
    elements.issueList.innerHTML = issues.length
      ? issues.map(renderIssue).join("")
      : '<div class="empty-state">未发现冲突或警告</div>';
  }

  if (!insight) {
    elements.riskBadge.className = "badge neutral";
    elements.riskBadge.textContent = "未分析";
    elements.suggestionList.innerHTML = '<div class="empty-state">暂无建议</div>';
    return;
  }
  elements.riskBadge.className = `badge ${riskClass(insight.risk_level)}`;
  elements.riskBadge.textContent = `风险 ${riskLabel(insight.risk_level)}`;
  elements.suggestionList.innerHTML = `<div class="result-strip">${escapeHtml(insight.summary)}</div>` +
    ((insight.suggestions || []).length
      ? insight.suggestions.map(renderSuggestion).join("")
      : '<div class="empty-state">暂无建议</div>');
}

function renderIssue(issue) {
  const severity = issue.severity || "info";
  return `<div class="issue-item ${escapeHtml(severity)}">
    <strong>${escapeHtml(issue.issue_type || severity)}</strong>
    <p>${escapeHtml(issue.message || "")}</p>
    <p>${escapeHtml((issue.related_ids || []).join(", "))}</p>
  </div>`;
}

function renderSuggestion(item) {
  return `<div class="suggestion-item">
    <strong>${escapeHtml(item.title || "建议")}</strong>
    <p>${escapeHtml(item.detail || "")}</p>
    <p>${escapeHtml((item.related_ids || []).join(", "))}</p>
  </div>`;
}

function metricDetail(label, value) {
  return `<div class="metric-detail"><strong>${escapeHtml(label)}</strong><span>${escapeHtml(value)}</span></div>`;
}

function editEntity(type, id) {
  const item = findById(state[type], id);
  if (!item) return;
  const form = {
    courses: elements.courseForm,
    teachers: elements.teacherForm,
    rooms: elements.roomForm,
    timeSlots: elements.timeSlotForm,
  }[type];
  if (!form) return;

  Object.entries(item).forEach(([key, value]) => {
    const input = form.elements[key];
    if (!input) return;
    input.value = Array.isArray(value) ? value.join(", ") : value ?? "";
  });
  const viewByType = { courses: "courses", teachers: "teachers", rooms: "rooms", timeSlots: "timeslots" };
  showView(viewByType[type]);
}

function deleteEntity(type, id) {
  state[type] = state[type].filter((item) => item.id !== id);
  if (type === "courses") {
    state.assignments = state.assignments.filter((item) => item.courseId !== id);
  }
  if (type === "timeSlots") {
    state.assignments = state.assignments.filter((item) => item.timeSlotId !== id);
  }
  clearRunResults();
  addLog(`已删除 ${id}。`);
  persistAndRender();
}

function actionButtons(type, id) {
  return `<button class="text-button" type="button" data-action="edit" data-type="${type}" data-id="${escapeHtml(id)}">编辑</button>
    <button class="text-button danger" type="button" data-action="delete" data-type="${type}" data-id="${escapeHtml(id)}">删除</button>`;
}

function setApiStatus(text, mode) {
  return { text, mode };
}

function addLog(message) {
  const now = new Date();
  state.logs.push(`${now.toLocaleTimeString("zh-CN", { hour12: false })} ${message}`);
}

function clearRunResults() {
  state.assignments = [];
  state.evaluation = null;
  state.insight = null;
  state.latestRun = null;
}

function normalizeAssignments(assignments) {
  return assignments.map((assignment) => ({
    courseId: textField(assignment, "courseId", "course_id", "course_code", "id"),
    timeSlotId: normalizeSlotId(textField(assignment, "timeSlotId", "time_slot_id", "slotId", "slot_id")),
    roomId: optionalTextField(assignment, "roomId", "room_id", "classroom", "classroom_name") || null,
  }));
}

function normalizeCourseForApi(course, options = {}) {
  const id = textField(course, "id", "course_id", "course_code");
  const classGroupIds = arrayField(course, "classGroupIds", "class_group_ids", "classGroups", "class_groups", "teachingClassIds");
  const freeReschedule = Boolean(options.freeReschedule);
  return {
    id,
    name: textField(course, "name", "course_name"),
    teacherId: textField(course, "teacherId", "teacher_id", "teacherName", "teacher_name") || "未知教师",
    classGroupIds: classGroupIds.length ? classGroupIds : [`COURSE-${id}`],
    weeklyHours: numberField(course, "weeklyHours", "weekly_hours") || 1,
    expectedStudents: optionalNumberField(course, "expectedStudents", "expected_students", "quota"),
    requiredRoomType: optionalTextField(course, "requiredRoomType", "required_room_type") || "general",
    requiredCampus: normalizeCampus(optionalTextField(course, "requiredCampus", "required_campus", "campus")),
    fixedTimeSlotId: freeReschedule ? null : normalizeSlotId(optionalTextField(course, "fixedTimeSlotId", "fixed_time_slot_id")),
    candidateTimeSlotIds: freeReschedule ? [] : arrayField(course, "candidateTimeSlotIds", "candidate_time_slot_ids").map(normalizeSlotId).filter(Boolean),
  };
}

function normalizeTimeSlotForApi(slot) {
  return {
    id: normalizeSlotId(textField(slot, "id", "timeSlotId", "time_slot_id")),
    weekday: numberField(slot, "weekday", "day") || 1,
    startSection: numberField(slot, "startSection", "start_section", "start") || 1,
    endSection: numberField(slot, "endSection", "end_section", "end") || numberField(slot, "startSection", "start_section", "start") || 1,
    startTime: optionalTextField(slot, "startTime", "start_time"),
    endTime: optionalTextField(slot, "endTime", "end_time"),
    label: optionalTextField(slot, "label"),
  };
}

function normalizeRoomForApi(room) {
  return {
    id: textField(room, "id", "roomId", "room_id", "name"),
    name: textField(room, "name", "roomName", "room_name") || textField(room, "id", "roomId", "room_id"),
    capacity: numberField(room, "capacity") || 60,
    roomType: optionalTextField(room, "roomType", "room_type") || "general",
    campus: normalizeCampus(optionalTextField(room, "campus")),
    building: optionalTextField(room, "building"),
    availableTimeSlotIds: arrayField(room, "availableTimeSlotIds", "available_time_slot_ids").map(normalizeSlotId).filter(Boolean),
  };
}

function assignmentMatchesFilter(assignment, filter) {
  if (!filter) return true;
  const course = findById(state.courses, assignment.courseId);
  const values = [
    assignment.courseId,
    assignment.timeSlotId,
    course?.name,
    course?.teacherId,
    ...(course?.classGroupIds || []),
  ];
  return values.some((value) => String(value || "").toLowerCase().includes(filter));
}

function formatSlot(slotId) {
  const slot = findById(state.timeSlots, slotId);
  if (!slot) return slotId;
  return `${slot.label || `${weekdays[slot.weekday - 1]} 第${slot.startSection}-${slot.endSection}节`} (${slot.id})`;
}

function exportStateJson() {
  const blob = new Blob([JSON.stringify(state, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "teacher-scheduling-data.json";
  link.click();
  URL.revokeObjectURL(url);
}

function buildDefaultWeekSlots() {
  const sectionTimes = [
    ["08:00", "08:45"],
    ["08:55", "09:40"],
    ["10:00", "10:45"],
    ["10:55", "11:40"],
    ["12:00", "12:45"],
    ["12:55", "13:40"],
    ["14:00", "14:45"],
    ["14:55", "15:40"],
    ["16:00", "16:45"],
    ["16:55", "17:40"],
    ["18:30", "19:15"],
    ["19:25", "20:10"],
    ["20:20", "21:05"],
    ["21:15", "22:00"],
  ];
  const slots = [];
  for (let weekday = 1; weekday <= 7; weekday += 1) {
    for (let section = 1; section <= 14; section += 1) {
      const [startTime, endTime] = sectionTimes[section - 1];
      slots.push({
        id: `D${weekday}-S${section}`,
        weekday,
        startSection: section,
        endSection: section,
        startTime,
        endTime,
        label: `${weekdays[weekday - 1]}第${section}节`,
      });
    }
  }
  return slots;
}

function loadState() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || "null");
    if (saved && Array.isArray(saved.courses)) {
      return migrateSavedState({
        ...emptyState(),
        ...saved,
        timeSlots: Array.isArray(saved.timeSlots) ? saved.timeSlots : [],
      });
    }
  } catch {
    localStorage.removeItem(STORAGE_KEY);
  }
  return structuredClone(sampleState);
}

function readAuthSession() {
  try {
    return JSON.parse(localStorage.getItem(AUTH_KEY) || "null");
  } catch {
    localStorage.removeItem(AUTH_KEY);
    return null;
  }
}

function migrateSavedState(saved) {
  const legacyCourseIdMap = new Map();
  const legacyTeacherIdMap = new Map([
    ["T001", "9920260001"],
    ["T002", "9920260002"],
    ["T003", "9920260003"],
  ]);
  const legacyRoomIdMap = new Map([
    ["R001", "公教楼A101"],
    ["R002", "实验楼B203"],
    ["R003", "二主楼201"],
  ]);
  const legacyClassGroupIdMap = new Map([
    ["G001", "1001"],
    ["G002", "1002"],
    ["G003", "1003"],
  ]);

  const courses = (saved.courses || []).map((course) => {
    const originalId = textField(course, "id", "courseId", "course_id", "course_code");
    const nextId = normalizeCourseId(originalId);
    if (nextId !== originalId) {
      legacyCourseIdMap.set(originalId, nextId);
    }
    return {
      ...course,
      id: nextId,
      name: textField(course, "name", "courseName", "course_name") || "未命名课程",
      teacherId: legacyTeacherIdMap.get(textField(course, "teacherId", "teacher_id", "teacherName", "teacher_name")) ||
        textField(course, "teacherId", "teacher_id", "teacherName", "teacher_name") ||
        "未知教师",
      classGroupIds: arrayField(course, "classGroupIds", "class_group_ids", "classGroups", "class_groups").map((id) => {
        const migratedId = legacyClassGroupIdMap.get(id) || id;
        if (nextId === "COCS0030" && migratedId === "1001") {
          return "2001";
        }
        return migratedId;
      }),
      weeklyHours: numberField(course, "weeklyHours", "weekly_hours") || 2,
      expectedStudents: optionalNumberField(course, "expectedStudents", "expected_students", "quota"),
      requiredRoomType: optionalTextField(course, "requiredRoomType", "required_room_type") || "general",
      requiredCampus: normalizeCampus(optionalTextField(course, "requiredCampus", "required_campus", "campus")),
      fixedTimeSlotId: normalizeSlotId(optionalTextField(course, "fixedTimeSlotId", "fixed_time_slot_id")),
      candidateTimeSlotIds: arrayField(course, "candidateTimeSlotIds", "candidate_time_slot_ids").map(normalizeSlotId).filter(Boolean),
    };
  });

  return {
    ...saved,
    courses,
    teachers: (saved.teachers || []).map((teacher) => ({
      ...teacher,
      id: legacyTeacherIdMap.get(textField(teacher, "id", "teacherId", "teacher_id", "name")) ||
        textField(teacher, "id", "teacherId", "teacher_id", "name"),
      employeeId: optionalTextField(teacher, "employeeId", "employee_id", "account", "workNo", "work_no") ||
        (textField(teacher, "id", "teacherId", "teacher_id") === textField(teacher, "name", "teacherName", "teacher_name", "id") ? "x" : textField(teacher, "id", "teacherId", "teacher_id")),
      name: textField(teacher, "name", "teacherName", "teacher_name", "id"),
      unavailableTimeSlotIds: arrayField(teacher, "unavailableTimeSlotIds", "unavailable_time_slot_ids").map(normalizeSlotId).filter(Boolean),
    })),
    rooms: (saved.rooms || []).map((room) => ({
      ...room,
      id: legacyRoomIdMap.get(textField(room, "id", "roomId", "room_id", "name")) ||
        textField(room, "id", "roomId", "room_id", "name"),
      name: textField(room, "name", "roomName", "room_name", "classroom") || "未命名教室",
      capacity: optionalNumberField(room, "capacity") || 60,
      roomType: optionalTextField(room, "roomType", "room_type") || "general",
      campus: normalizeCampus(optionalTextField(room, "campus")),
    })),
    assignments: (saved.assignments || []).map((assignment) => ({
      ...assignment,
      courseId: legacyCourseIdMap.get(textField(assignment, "courseId", "course_id", "course_code")) ||
        textField(assignment, "courseId", "course_id", "course_code"),
      timeSlotId: normalizeSlotId(textField(assignment, "timeSlotId", "time_slot_id", "slotId", "slot_id")),
      roomId: legacyRoomIdMap.get(optionalTextField(assignment, "roomId", "room_id", "classroom")) ||
        optionalTextField(assignment, "roomId", "room_id", "classroom"),
    })),
  };
}

function normalizeCourseId(courseId) {
  const value = String(courseId || "").trim();
  if (!value) return "";
  const simpleMatch = value.match(/^C(\d{3})$/);
  if (simpleMatch) {
    return `COCS${simpleMatch[1]}0`;
  }
  const coscMatch = value.match(/^COSC(\d+)$/);
  if (coscMatch) {
    return `COCS${coscMatch[1]}`;
  }
  return value;
}

function saveState() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

function persistAndRender() {
  saveState();
  render();
}

function emptyState() {
  return {
    courses: [],
    teachers: [],
    rooms: [],
    timeSlots: [],
    assignments: [],
    evaluation: null,
    insight: null,
    latestRun: null,
    logs: [],
  };
}

function upsertById(list, item) {
  const index = list.findIndex((entry) => entry.id === item.id);
  if (index >= 0) {
    list[index] = item;
  } else {
    list.push(item);
  }
}

function findById(list, id) {
  return list.find((item) => item.id === id);
}

function compareSlots(a, b) {
  return a.weekday - b.weekday || a.startSection - b.startSection || a.id.localeCompare(b.id);
}

function field(formData, name) {
  return String(formData.get(name) || "").trim();
}

function optionalString(value) {
  const trimmed = String(value || "").trim();
  return trimmed || undefined;
}

function optionalNumber(value) {
  const trimmed = String(value || "").trim();
  return trimmed ? Number(trimmed) : undefined;
}

function splitCsv(value) {
  return String(value || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function riskClass(level) {
  if (level === "low") return "success";
  if (level === "medium") return "warning";
  return "danger";
}

function riskLabel(level) {
  if (level === "low") return "低";
  if (level === "medium") return "中";
  if (level === "high") return "高";
  return level || "未知";
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function responseData(result) {
  return result && Array.isArray(result.data) ? result.data : result?.data?.items || result?.items || [];
}

function textField(item, ...keys) {
  const value = optionalTextField(item, ...keys);
  return value || "";
}

function optionalTextField(item, ...keys) {
  for (const key of keys) {
    const value = item?.[key];
    if (value !== undefined && value !== null && String(value).trim() !== "") {
      return String(value).replace(/\s+/g, " ").trim();
    }
  }
  return "";
}

function numberField(item, ...keys) {
  return Number(optionalNumberField(item, ...keys) || 0);
}

function optionalNumberField(item, ...keys) {
  for (const key of keys) {
    const value = item?.[key];
    if (value !== undefined && value !== null && String(value).trim() !== "") {
      const numberValue = Number(value);
      return Number.isFinite(numberValue) ? numberValue : undefined;
    }
  }
  return undefined;
}

function arrayField(item, ...keys) {
  for (const key of keys) {
    const value = item?.[key];
    if (Array.isArray(value)) return value.map((entry) => String(entry).trim()).filter(Boolean);
    if (value instanceof Set) return Array.from(value).map((entry) => String(entry).trim()).filter(Boolean);
    if (typeof value === "string" && value.trim()) {
      return value.split(/[,\n，、;；]+/).map((entry) => entry.trim()).filter(Boolean);
    }
  }
  return [];
}

function normalizeCampus(value) {
  const text = String(value || "").trim().toLowerCase();
  if (!text) return null;
  if (text.includes("津南") || text === "jinnan") return "jinnan";
  if (text.includes("八里台") || text === "balitai") return "balitai";
  return null;
}

function normalizeSlotId(value) {
  const raw = String(value || "").trim();
  if (!raw) return "";
  const match = raw.match(/^D(\d+)-S(\d+)(?:-(\d+))?$/i);
  if (!match) return raw;
  const weekday = Number(match[1]);
  const start = Number(match[2]);
  const end = Number(match[3] || match[2]);
  return start === end ? `D${weekday}-S${start}` : `D${weekday}-S${start}-${end}`;
}

function slotIdFromParts(weekday, startSection, endSection = startSection) {
  const day = Number(weekday);
  const start = Number(startSection);
  const end = Number(endSection || startSection);
  if (!day || !start || !end) return "";
  return start === end ? `D${day}-S${start}` : `D${day}-S${start}-${end}`;
}

function slotFromId(slotId) {
  const match = String(slotId || "").match(/^D(\d+)-S(\d+)(?:-(\d+))?$/i);
  if (!match) return null;
  const weekday = Number(match[1]);
  const startSection = Number(match[2]);
  const endSection = Number(match[3] || match[2]);
  return {
    id: normalizeSlotId(slotId),
    weekday,
    startSection,
    endSection,
    label: `${weekdays[weekday - 1] || `周${weekday}`}第${startSection}-${endSection}节`,
  };
}

async function loadBackendData() {
  const semester = elements.semesterSelect.value;
  addLog(`正在从后端加载学期 ${semester} 的课程数据...`);
  try {
    const coursesResult = await apiRequest(`/courses?semester=${encodeURIComponent(semester)}`, { method: "GET" });
    const backendCourses = responseData(coursesResult).map(mapBackendCourseToTeacher).filter(Boolean);
    if (!backendCourses.length) {
      throw new Error(`学期 ${semester} 暂无可用课程数据`);
    }

    const teachersResult = await apiRequest("/teachers", { method: "GET" });
    const backendTeachers = responseData(teachersResult).map((teacher) => {
      const name = textField(teacher, "name", "teacherName", "teacher_name", "id") || "未知教师";
      const employeeId = textField(teacher, "employeeId", "employee_id", "account", "teacherId", "teacher_id", "workNo", "work_no") || "x";
      return {
        id: name,
        employeeId,
        name,
        college: optionalTextField(teacher, "college", "department"),
        unavailableTimeSlotIds: arrayField(teacher, "unavailableTimeSlotIds", "unavailable_time_slot_ids").map(normalizeSlotId).filter(Boolean),
      };
    });

    const teacherMap = new Map(backendTeachers.map((teacher) => [teacher.id, teacher]));
    backendCourses.forEach((course) => {
      if (!teacherMap.has(course.teacherId)) {
        teacherMap.set(course.teacherId, {
          id: course.teacherId,
          employeeId: "x",
          name: course.teacherId,
          college: "",
          unavailableTimeSlotIds: [],
        });
      }
    });

    const roomsResult = await apiRequest("/classrooms", { method: "GET" });
    const backendRooms = responseData(roomsResult).map((room) => {
      const name = textField(room, "name", "roomName", "room_name", "classroom") || "未命名教室";
      return {
        id: textField(room, "id", "roomId", "room_id") || name,
        name,
        capacity: optionalNumberField(room, "capacity") || 60,
        campus: normalizeCampus(optionalTextField(room, "campus")),
        roomType: optionalTextField(room, "roomType", "room_type") || "general",
        building: optionalTextField(room, "building"),
      };
    });
    const importedSlots = backendCourses
      .flatMap((course) => [course.fixedTimeSlotId, ...(course.candidateTimeSlotIds || [])])
      .filter(Boolean)
      .map(slotFromId)
      .filter(Boolean);
    const slotMap = new Map([...state.timeSlots, ...importedSlots].map((slot) => [slot.id, slot]));

    state.courses = backendCourses;
    state.teachers = Array.from(teacherMap.values());
    state.rooms = backendRooms;
    state.timeSlots = Array.from(slotMap.values()).sort(compareSlots);
    clearRunResults();
    const dataSourceBadge = document.querySelector("#dataSourceBadge");
    if (dataSourceBadge) dataSourceBadge.textContent = `数据来源：后端课程库 (${semester})`;
    addLog(`已从后端加载 ${state.courses.length} 门课程、${state.teachers.length} 位教师、${state.rooms.length} 间教室。`);
    persistAndRender();
  } catch (error) {
    addLog(`加载后端数据失败：${error.message}`);
  }
}

function mapBackendCourseToTeacher(row) {
  const id = textField(row, "id", "courseId", "course_id", "course_code");
  const name = textField(row, "name", "courseName", "course_name").replace(/\n/g, "");
  if (!id || !name) return null;
  const weekday = optionalNumberField(row, "weekday", "day");
  const startSection = optionalNumberField(row, "startSection", "start_section", "start");
  const endSection = optionalNumberField(row, "endSection", "end_section", "end") || startSection;
  const fixedSlot = normalizeSlotId(optionalTextField(row, "fixedTimeSlotId", "fixed_time_slot_id"));
  const explicitCandidates = arrayField(row, "candidateTimeSlotIds", "candidate_time_slot_ids").map(normalizeSlotId).filter(Boolean);
  const importedSlot = slotIdFromParts(weekday, startSection, endSection);
  const teacherName = textField(row, "teacherId", "teacher_id", "teacherName", "teacher_name") || "未知教师";
  return {
    id,
    name,
    teacherId: teacherName,
    classGroupIds: arrayField(row, "classGroupIds", "class_group_ids", "teachingClassIds", "teaching_class_ids").length
      ? arrayField(row, "classGroupIds", "class_group_ids", "teachingClassIds", "teaching_class_ids")
      : [`COURSE-${id}`],
    weeklyHours: numberField(row, "weeklyHours", "weekly_hours") || Math.max((endSection || startSection || 1) - (startSection || 1) + 1, 1),
    expectedStudents: optionalNumberField(row, "expectedStudents", "expected_students", "quota"),
    requiredRoomType: optionalTextField(row, "requiredRoomType", "required_room_type") || "general",
    requiredCampus: normalizeCampus(optionalTextField(row, "requiredCampus", "required_campus", "campus")),
    fixedTimeSlotId: fixedSlot || null,
    candidateTimeSlotIds: fixedSlot ? [fixedSlot] : explicitCandidates.length ? explicitCandidates : importedSlot ? [importedSlot] : [],
  };
}
