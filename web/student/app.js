const API_BASE_URL = window.location.protocol.startsWith("http")
  ? window.location.origin
  : "http://127.0.0.1:8000";
const AUTH_KEY = "nankai-auth-session-v1";
const STORAGE_KEY = "nankai-student-portal-state-v2";

const session = readSession();
if (!session || session.role !== "student") {
  window.location.replace("../login/index.html");
  throw new Error("Student authentication required");
}

const majorLabels = {
  "Computer Science": "计算机科学与技术",
  "Information Management": "信息管理",
  Mathematics: "数学",
  "Chinese Literature": "汉语言文学",
};
const courseCategories = ["专业必修", "专业选修", "通识必修", "通识选修"];
const categoryAliases = {
  专业核心: "专业必修",
  高阶选修: "专业选修",
  公共必修: "通识必修",
  学科基础: "专业必修",
  后端课程: "专业选修",
};
const weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"];
const sectionTimeLabels = {
  1: "08:00-08:45",
  2: "08:55-09:40",
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

const sampleCourses = [
  {
    id: "C002",
    name: "算法设计与分析",
    majorTags: ["Computer Science"],
    gradeTags: ["2023"],
    interestTags: ["algorithm"],
    prerequisiteCourseIds: ["C001"],
    timeSlotId: "D1-S3-4",
    category: "专业必修",
    credit: 3,
    teacherName: "王老师",
    classroom: "津南公教 A201",
    weekday: 1,
    startSection: 3,
    endSection: 4,
  },
  {
    id: "C003",
    name: "人工智能导论",
    majorTags: ["Computer Science"],
    gradeTags: ["2023", "2024"],
    interestTags: ["AI", "machine learning"],
    prerequisiteCourseIds: ["C001"],
    timeSlotId: "D1-S1-2",
    category: "专业选修",
    credit: 2,
    teacherName: "刘老师",
    classroom: "津南公教 B112",
    weekday: 1,
    startSection: 1,
    endSection: 2,
  },
  {
    id: "C004",
    name: "数据库系统",
    majorTags: ["Computer Science", "Information Management"],
    gradeTags: ["2023"],
    interestTags: ["database", "system"],
    prerequisiteCourseIds: ["C001"],
    timeSlotId: "D1-S4-5",
    category: "专业必修",
    credit: 3,
    teacherName: "赵老师",
    classroom: "津南公教 C305",
    weekday: 1,
    startSection: 4,
    endSection: 5,
  },
  {
    id: "C005",
    name: "高级机器学习",
    majorTags: ["Computer Science"],
    gradeTags: ["2022", "2023"],
    interestTags: ["AI", "machine learning"],
    prerequisiteCourseIds: ["C099"],
    timeSlotId: "D2-S2-3",
    category: "专业选修",
    credit: 2,
    teacherName: "陈老师",
    classroom: "津南公教 D210",
    weekday: 2,
    startSection: 2,
    endSection: 3,
  },
  {
    id: "C006",
    name: "文学导论",
    majorTags: ["Chinese Literature"],
    gradeTags: ["2023"],
    interestTags: ["literature"],
    timeSlotId: "D1-S5-6",
    category: "通识选修",
    credit: 2,
    teacherName: "周老师",
    classroom: "八里台二主楼 204",
    weekday: 1,
    startSection: 5,
    endSection: 6,
  },
  {
    id: "C007",
    name: "计算机网络",
    majorTags: ["Computer Science"],
    gradeTags: ["2023"],
    interestTags: ["network", "system"],
    prerequisiteCourseIds: ["C001"],
    timeSlotId: "D3-S5-6",
    category: "专业必修",
    credit: 3,
    teacherName: "孙老师",
    classroom: "津南公教 A308",
    weekday: 3,
    startSection: 5,
    endSection: 6,
  },
];

const sampleAssignments = [
  {
    courseId: "C010",
    courseName: "大学英语",
    timeSlotId: "D1-S1-2",
    teacherName: "李老师",
    classroom: "津南公教 A103",
    courseType: "通识必修",
    weekday: 1,
    startSection: 1,
    endSection: 2,
  },
  {
    courseId: "C011",
    courseName: "线性代数",
    timeSlotId: "D3-S2-3",
    teacherName: "孙老师",
    classroom: "津南公教 B204",
    courseType: "专业必修",
    weekday: 3,
    startSection: 2,
    endSection: 3,
  },
];

let state = loadState();
let recommendations = [];
let selectedScheduleMode = "week";
let activeStudentView = "profile";
let selectionFeedback = null;

const elements = {
  appShell: document.querySelector(".app-shell"),
  navTabs: document.querySelectorAll(".nav-tab"),
  studentViews: document.querySelectorAll("[data-student-view]"),
  studentGrid: document.querySelector(".student-grid"),
  identity: document.querySelector("#studentIdentity"),
  logoutButton: document.querySelector("#logoutButton"),
  sidebarToggle: document.querySelector("#sidebarToggle"),
  studentName: document.querySelector("#studentName"),
  studentId: document.querySelector("#studentId"),
  studentMajorLabel: document.querySelector("#studentMajorLabel"),
  studentGrade: document.querySelector("#studentGrade"),
  studentInterestSummary: document.querySelector("#studentInterestSummary"),
  strategySummary: document.querySelector("#strategySummary"),
  dataSourceLabel: document.querySelector("#dataSourceLabel"),
  selectionStatus: document.querySelector("#selectionStatus"),
  profileStatus: document.querySelector("#profileStatus"),
  form: document.querySelector("#recommendForm"),
  recommendButton: document.querySelector("#recommendButton"),
  saveProfileButton: document.querySelector("#saveProfileButton"),
  loadCoursesButton: document.querySelector("#loadCoursesButton"),
  resetSampleButton: document.querySelector("#resetSampleButton"),
  recommendLimit: document.querySelector("#recommendLimit"),
  completedCount: document.querySelector("#completedCount"),
  catalogCount: document.querySelector("#catalogCount"),
  fixedCount: document.querySelector("#fixedCount"),
  recommendationMetric: document.querySelector("#recommendationMetric"),
  conflictMetric: document.querySelector("#conflictMetric"),
  recommendStatus: document.querySelector("#recommendStatus"),
  scheduleModeControl: document.querySelector("#scheduleModeControl"),
  timetableFilter: document.querySelector("#timetableFilter"),
  timetableDay: document.querySelector("#timetableDay"),
  timetableGrid: document.querySelector("#timetableGrid"),
  assignmentTableBody: document.querySelector("#assignmentTableBody"),
  assignmentHint: document.querySelector("#assignmentHint"),
  recommendationList: document.querySelector("#recommendationList"),
  recommendationCount: document.querySelector("#recommendationCount"),
  courseCatalogList: document.querySelector("#courseCatalogList"),
  catalogHint: document.querySelector("#catalogHint"),
  completedHint: document.querySelector("#completedHint"),
  completedList: document.querySelector("#completedList"),
  fixedHint: document.querySelector("#fixedHint"),
  fixedList: document.querySelector("#fixedList"),
  courseSearchInput: document.querySelector("#courseSearchInput"),
  categoryFilter: document.querySelector("#categoryFilter"),
  statusFilter: document.querySelector("#statusFilter"),
};

hydrateForm();
render();

elements.logoutButton.addEventListener("click", () => {
  localStorage.removeItem(AUTH_KEY);
  window.location.href = "../login/index.html";
});

elements.sidebarToggle.addEventListener("click", () => {
  const collapsed = elements.appShell.classList.toggle("sidebar-collapsed");
  elements.sidebarToggle.setAttribute("aria-expanded", String(!collapsed));
  elements.sidebarToggle.setAttribute("aria-label", collapsed ? "展开导航" : "收起导航");
});

elements.recommendButton.addEventListener("click", generateRecommendations);
elements.saveProfileButton.addEventListener("click", () => {
  syncStateFromForm();
  persistAndRender();
  setStatus("资料已保存，本次推荐会使用最新设置。");
});
elements.loadCoursesButton.addEventListener("click", loadCoursesFromBackend);
elements.resetSampleButton.addEventListener("click", () => {
  state = defaultState();
  recommendations = [];
  hydrateForm();
  persistAndRender();
  setStatus("已恢复示例课程和默认资料。");
});
elements.form.topK.addEventListener("input", () => {
  syncStateFromForm();
  renderMetrics();
});
elements.form.addEventListener("change", () => {
  syncStateFromForm();
  persistAndRender();
});
elements.courseSearchInput.addEventListener("input", renderCatalog);
elements.categoryFilter.addEventListener("change", renderCatalog);
elements.statusFilter.addEventListener("change", renderCatalog);
elements.timetableFilter.addEventListener("input", renderTimetable);
elements.timetableDay.addEventListener("change", renderTimetable);
elements.scheduleModeControl.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-mode]");
  if (!button) return;
  selectedScheduleMode = button.dataset.mode;
  elements.scheduleModeControl.querySelectorAll("button").forEach((item) => {
    item.classList.toggle("selected", item === button);
  });
  renderTimetable();
});
elements.navTabs.forEach((tab) => {
  tab.addEventListener("click", () => showStudentView(tab.dataset.view || "profile"));
});

document.body.addEventListener("click", (event) => {
  const button = event.target.closest("[data-action]");
  if (!button) return;
  const { action, courseId } = button.dataset;
  if (action === "complete") toggleSet(state.completedCourseIds, courseId);
  if (action === "fixed") toggleSet(state.fixedCourseIds, courseId);
  if (action === "recommend-one") recommendOne(courseId);
  if (action === "select-course") selectRecommendedCourse(courseId);
  if (action === "drop-course") dropSelectedCourse(courseId);
  recommendations = recommendations.map((item) => ({
    ...item,
    is_completed: state.completedCourseIds.includes(item.course_id),
    is_currently_selected: isCourseSelected(item.course_id),
    is_fixed_selected: state.fixedCourseIds.includes(item.course_id),
  }));
  persistAndRender();
});

async function generateRecommendations() {
  syncStateFromForm();
  const payload = buildRecommendationPayload();

  setLoading(true);
  setStatus("正在生成推荐...");
  try {
    const response = await fetch(`${API_BASE_URL}/student/recommend`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const result = await response.json();
    if (!response.ok || result.success === false) {
      throw new Error(result.error || "推荐接口返回错误");
    }
    recommendations = result.recommendations || result.data?.recommendations || [];
    state.lastSource = "后端推荐接口";
    setStatus(`已调用后端接口，从 ${result.candidate_count ?? state.courses.length} 门候选课程中生成推荐。`);
  } catch (error) {
    recommendations = localRecommend(payload);
    state.lastSource = "前端备用规则";
    setStatus(`后端接口暂不可用，已使用前端备用规则生成推荐：${error.message}`);
  } finally {
    setLoading(false);
    persistAndRender();
    showStudentView("recommendations");
  }
}

async function loadCoursesFromBackend() {
  syncStateFromForm();
  const semester = encodeURIComponent(state.profile.semester || "");
  const path = semester ? `/courses?semester=${semester}` : "/courses";
  elements.loadCoursesButton.disabled = true;
  setStatus("正在读取后端课程库...");
  try {
    const response = await fetch(`${API_BASE_URL}${path}`);
    const result = await response.json();
    if (!response.ok || result.success === false) {
      throw new Error(result.error || `HTTP ${response.status}`);
    }
    const rows = result.data || [];
    const mappedCourses = rows.map(mapBackendCourse).filter(Boolean);
    if (!mappedCourses.length) {
      throw new Error("后端暂无可用课程数据");
    }
    state.courses = mappedCourses;
    state.dataSource = "后端课程库";
    recommendations = [];
    setStatus(`已从后端读取 ${mappedCourses.length} 门课程。`);
  } catch (error) {
    setStatus(`读取后端课程失败，当前仍使用本地课程：${error.message}`);
  } finally {
    elements.loadCoursesButton.disabled = false;
    persistAndRender();
  }
}

function recommendOne(courseId) {
  const course = state.courses.find((item) => item.id === courseId);
  if (!course) return;
  syncStateFromForm();
  const payload = {
    ...buildRecommendationPayload(),
    courses: [course],
    topK: 1,
    includeConflicted: true,
    excludeSelected: false,
  };
  const [item] = localRecommend(payload);
  recommendations = item ? [item, ...recommendations.filter((entry) => entry.course_id !== item.course_id)] : recommendations;
  setStatus(`已把 ${course.name} 加入推荐预览。`);
}

function selectRecommendedCourse(courseId) {
  const course = findCourse(courseId) || courseFromRecommendation(courseId);
  if (!course) {
    setSelectionStatus("未找到课程详情，暂时不能选课。", "danger", courseId);
    return;
  }

  const validation = validateCourseSelection(course);
  if (!validation.ok) {
    setSelectionStatus(validation.reason, "danger", course.id);
    return;
  }

  state.currentAssignments.push({
    courseId: course.id,
    courseName: course.name,
    timeSlotId: course.timeSlotId,
    teacherName: course.teacherName,
    classroom: course.classroom,
    courseType: normalizeCourseCategory(course.category || course.courseType, course.name),
    weekday: course.weekday,
    startSection: course.startSection,
    endSection: course.endSection,
    selectedByStudent: true,
  });
  recommendations = recommendations.map((item) => item.course_id === course.id
    ? { ...item, is_currently_selected: true }
    : item);
  setSelectionStatus(`已选择 ${course.name}，课程已加入“我的课表”。`, "success", course.id);
}

function dropSelectedCourse(courseId) {
  const selected = state.currentAssignments.find((item) => item.courseId === courseId && item.selectedByStudent);
  if (!selected) {
    setSelectionStatus("该课程不是通过推荐选入的课程，不能在这里退课。", "danger", courseId);
    return;
  }
  state.currentAssignments = state.currentAssignments.filter((item) => !(item.courseId === courseId && item.selectedByStudent));
  recommendations = recommendations.map((item) => item.course_id === courseId
    ? {
        ...item,
        is_currently_selected: false,
        has_time_conflict: hasTimeConflict(recommendationToCourse(item), busyItemsForCourse(courseId)),
      }
    : item);
  setSelectionStatus(`已退选 ${selected.courseName}，课程已从“我的课表”移除。`, "success", courseId);
}

function validateCourseSelection(course) {
  if (state.completedCourseIds.includes(course.id)) {
    return { ok: false, reason: `${course.name} 已标记为已修课程，不能重复选课。` };
  }
  if (isCourseSelected(course.id)) {
    return { ok: false, reason: `${course.name} 已经在当前课表中，不能重复选课。` };
  }
  if (state.fixedCourseIds.includes(course.id)) {
    return { ok: false, reason: `${course.name} 已经是固定必选课程，不需要再次选课。` };
  }

  const selectedConflict = findConflict(course, state.currentAssignments);
  if (selectedConflict) {
    return {
      ok: false,
      reason: `${course.name} 与已选课程 ${selectedConflict.courseName || selectedConflict.name || selectedConflict.courseId} 在 ${formatCourseTime(course)} 冲突，不能选课。`,
    };
  }

  const fixedCourses = state.fixedCourseIds.map(findCourse).filter(Boolean);
  const fixedConflict = findConflict(course, fixedCourses);
  if (fixedConflict) {
    return {
      ok: false,
      reason: `${course.name} 与固定必选课程 ${fixedConflict.name || fixedConflict.courseName || fixedConflict.id} 在 ${formatCourseTime(course)} 冲突，不能选课。`,
    };
  }

  if (!course.weekday || !course.startSection || !course.endSection) {
    return { ok: false, reason: `${course.name} 暂无明确上课时间，不能直接选课。` };
  }
  return { ok: true };
}

function findConflict(course, items) {
  return items.find((item) => {
    if (item.id === course.id || item.courseId === course.id || item.course_id === course.id) return false;
    const left = blockFrom(course);
    const right = blockFrom(item);
    return left && right && blocksOverlap(left, right);
  });
}

function courseFromRecommendation(courseId) {
  const item = recommendations.find((entry) => entry.course_id === courseId);
  if (!item) return null;
  return recommendationToCourse(item);
}

function recommendationToCourse(item) {
  return {
    id: item.course_id,
    name: item.course_name,
    timeSlotId: item.time_slot_id,
    category: normalizeCourseCategory(item.course_type || item.category, item.course_name),
    courseType: normalizeCourseCategory(item.course_type || item.category, item.course_name),
    credit: item.credit,
    teacherName: item.teacher_name,
    classroom: item.classroom,
    weekday: item.weekday,
    startSection: item.start_section,
    endSection: item.end_section,
  };
}

function buildRecommendationPayload() {
  return {
    student: {
      id: state.profile.id,
      major: state.profile.major,
      grade: state.profile.grade,
      completedCourseIds: state.completedCourseIds,
      interests: state.profile.interests,
      fixedCourseIds: state.fixedCourseIds,
    },
    courses: normalizedCourses(),
    currentAssignments: state.currentAssignments,
    topK: state.settings.topK,
    includeConflicted: state.settings.includeConflicted,
    excludeSelected: state.settings.excludeSelected,
    fixedCourseIds: state.fixedCourseIds,
  };
}

function normalizedCourses() {
  return state.courses.map((course) => ({
    ...course,
    category: normalizeCourseCategory(course.category || course.courseType, course.name),
    courseType: normalizeCourseCategory(course.courseType || course.category, course.name),
  }));
}

function hydrateForm() {
  elements.form.name.value = state.profile.name;
  elements.form.major.value = state.profile.major;
  elements.form.grade.value = state.profile.grade;
  elements.form.interests.value = state.profile.interests.join(", ");
  elements.form.topK.value = state.settings.topK;
  elements.form.semester.value = state.profile.semester;
  elements.form.includeConflicted.checked = state.settings.includeConflicted;
  elements.form.excludeSelected.checked = state.settings.excludeSelected;
}

function syncStateFromForm() {
  const formData = new FormData(elements.form);
  state.profile.name = field(formData, "name") || state.profile.name;
  state.profile.major = field(formData, "major") || "Computer Science";
  state.profile.grade = field(formData, "grade") || "2023";
  state.profile.interests = splitCsv(formData.get("interests"));
  state.profile.semester = field(formData, "semester");
  state.settings.topK = clamp(Number(formData.get("topK") || 4), 1, 10);
  state.settings.includeConflicted = formData.get("includeConflicted") === "on";
  state.settings.excludeSelected = formData.get("excludeSelected") === "on";
}

function render() {
  renderIdentity();
  renderMetrics();
  renderCategoryFilter();
  renderCatalog();
  renderCompleted();
  renderFixed();
  renderTimetable();
  renderRecommendations(recommendations);
  showStudentView(activeStudentView, { preserveScroll: true });
}

function renderIdentity() {
  const name = state.profile.name || session.name || "学生用户";
  elements.identity.textContent = `${name} ${session.account}`;
  elements.studentName.textContent = name;
  elements.studentId.textContent = session.account || state.profile.id;
  elements.studentMajorLabel.textContent = majorLabels[state.profile.major] || state.profile.major;
  elements.studentGrade.textContent = state.profile.grade;
  elements.studentInterestSummary.textContent = state.profile.interests.join(", ") || "未设置";
  elements.strategySummary.textContent = [
    state.settings.includeConflicted ? "保留冲突课程" : "过滤冲突课程",
    state.settings.excludeSelected ? "不重复推荐已选课程" : "允许重复预览",
  ].join(" / ");
  elements.dataSourceLabel.textContent = state.lastSource || state.dataSource;
  elements.profileStatus.textContent = `本地保存于 ${new Date(state.updatedAt || Date.now()).toLocaleString("zh-CN", { hour12: false })}`;
}

function renderMetrics() {
  elements.completedCount.textContent = state.completedCourseIds.length;
  elements.catalogCount.textContent = state.courses.length;
  elements.fixedCount.textContent = state.fixedCourseIds.length;
  elements.recommendLimit.textContent = state.settings.topK;
  elements.recommendationMetric.textContent = recommendations.length;
  elements.conflictMetric.textContent = recommendations.filter((item) => item.has_time_conflict && !isCourseSelected(item.course_id)).length;
}

function renderCategoryFilter() {
  const current = elements.categoryFilter.value;
  elements.categoryFilter.innerHTML = '<option value="">全部类型</option>' +
    courseCategories.map((category) => `<option value="${escapeHtml(category)}">${escapeHtml(category)}</option>`).join("");
  if (courseCategories.includes(current)) {
    elements.categoryFilter.value = current;
  }
}

function renderCatalog() {
  const items = getFilteredCourses();
  elements.catalogHint.textContent = `${items.length} / ${state.courses.length} 门`;
  if (!items.length) {
    elements.courseCatalogList.innerHTML = '<div class="empty-state">没有匹配筛选条件的课程</div>';
    return;
  }
  elements.courseCatalogList.innerHTML = items.map(renderCourseCard).join("");
}

function renderCourseCard(course) {
  const completed = state.completedCourseIds.includes(course.id);
  const fixed = state.fixedCourseIds.includes(course.id);
  const conflicted = hasTimeConflict(course, busyItemsForCourse(course.id));
  const category = normalizeCourseCategory(course.category || course.courseType, course.name);
  const tags = [
    completed ? '<span class="badge success">已修</span>' : "",
    fixed ? '<span class="badge warning">固定</span>' : "",
    isCourseSelected(course.id) ? '<span class="badge warning">已选</span>' : "",
    conflicted ? '<span class="badge danger">时间冲突</span>' : '<span class="badge success">时间可选</span>',
    ...(course.interestTags || []).slice(0, 3).map((tag) => `<span class="badge neutral">${escapeHtml(tag)}</span>`),
  ].filter(Boolean).join("");
  return `<article class="course-card">
    <div class="course-head">
      <div>
        <strong>${escapeHtml(course.name)} (${escapeHtml(course.id)})</strong>
        <div class="course-meta">
          <span>${escapeHtml(category)}</span>
          <span class="meta-dot">/</span>
          <span>${escapeHtml(course.credit ?? "-")} 学分</span>
          <span class="meta-dot">/</span>
          <span>${escapeHtml(formatCourseTime(course))}</span>
          <span class="meta-dot">/</span>
          <span>${escapeHtml(course.teacherName || "教师待定")}</span>
          <span class="meta-dot">/</span>
          <span>${escapeHtml(course.classroom || "教室待定")}</span>
        </div>
      </div>
      <div class="row-actions">
        <button class="text-button" type="button" data-action="complete" data-course-id="${escapeHtml(course.id)}">${completed ? "取消已修" : "标记已修"}</button>
        <button class="text-button" type="button" data-action="fixed" data-course-id="${escapeHtml(course.id)}">${fixed ? "取消固定" : "设为固定"}</button>
        <button class="text-button" type="button" data-action="recommend-one" data-course-id="${escapeHtml(course.id)}">预览</button>
      </div>
    </div>
    <div class="tag-row">${tags}</div>
    <div class="course-reasons">${escapeHtml(courseSummary(course))}</div>
  </article>`;
}

function renderCompleted() {
  const items = state.completedCourseIds.map((id) => findCourse(id)).filter(Boolean);
  elements.completedHint.textContent = `${items.length} 门`;
  elements.completedList.innerHTML = items.length
    ? items.map((course) => compactItem(course, "complete", "移出已修")).join("")
    : '<div class="empty-state">可在课程库中标记已修课程</div>';
}

function renderFixed() {
  const items = state.fixedCourseIds.map((id) => findCourse(id)).filter(Boolean);
  elements.fixedHint.textContent = `${items.length} 门`;
  elements.fixedList.innerHTML = items.length
    ? items.map((course) => compactItem(course, "fixed", "取消固定")).join("")
    : '<div class="empty-state">固定课程会占用时间，并参与冲突判断</div>';
}

function compactItem(course, action, label) {
  return `<article class="compact-item">
    <div>
      <strong>${escapeHtml(course.name)}</strong>
      <span>${escapeHtml(course.id)} / ${escapeHtml(formatCourseTime(course))}</span>
    </div>
    <button class="text-button" type="button" data-action="${action}" data-course-id="${escapeHtml(course.id)}">${escapeHtml(label)}</button>
  </article>`;
}

function renderTimetable() {
  const items = getVisibleTimetableItems();
  elements.assignmentHint.textContent = `${items.length} 条课程`;
  elements.timetableDay.closest(".day-picker").classList.toggle("is-hidden", selectedScheduleMode !== "day");

  if (selectedScheduleMode === "day") {
    renderDayTimetable(items);
  } else if (selectedScheduleMode === "month") {
    renderMonthTimetable(items);
  } else {
    renderWeekTimetable(items);
  }
  renderAssignmentTable(items);
}

function renderWeekTimetable(items) {
  const itemsByKey = groupItemsBySectionAndWeekday(items);
  const cells = ['<div class="day-cell">节次</div>', ...weekdays.map((day) => `<div class="day-cell">${day}</div>`)];
  for (let section = 1; section <= 14; section += 1) {
    cells.push(renderTimeCell(section));
    for (let weekday = 1; weekday <= 7; weekday += 1) {
      const list = itemsByKey.get(`${section}:${weekday}`) || [];
      cells.push(`<div class="slot-cell">${list.map(renderSlotCard).join("")}</div>`);
    }
  }
  elements.timetableGrid.className = "timetable-grid week-view";
  elements.timetableGrid.innerHTML = cells.join("");
}

function renderDayTimetable(items) {
  const day = Number(elements.timetableDay.value || 1);
  const dayItems = items.filter((item) => Number(item.weekday) === day);
  const itemsBySection = new Map();
  dayItems.forEach((item) => {
    for (let section = item.startSection; section <= item.endSection; section += 1) {
      const list = itemsBySection.get(section) || [];
      if (section === item.startSection) list.push(item);
      itemsBySection.set(section, list);
    }
  });
  const cells = [`<div class="day-cell">节次</div><div class="day-cell">${weekdays[day - 1]}</div>`];
  for (let section = 1; section <= 14; section += 1) {
    cells.push(renderTimeCell(section));
    const list = itemsBySection.get(section) || [];
    cells.push(`<div class="slot-cell">${list.map(renderSlotCard).join("")}</div>`);
  }
  elements.timetableGrid.className = "timetable-grid day-view";
  elements.timetableGrid.innerHTML = cells.join("");
}

function renderMonthTimetable(items) {
  const cells = ['<div class="month-heading">教学月</div>', ...weekdays.map((day) => `<div class="month-heading">${day}</div>`)];
  for (let week = 1; week <= 4; week += 1) {
    cells.push(`<div class="month-week-label">第 ${week} 周</div>`);
    for (let weekday = 1; weekday <= 7; weekday += 1) {
      const list = items.filter((item) => Number(item.weekday) === weekday);
      cells.push(`<div class="month-cell">
        <strong>${weekdays[weekday - 1]}</strong>
        ${list.length ? list.map(renderMonthCourse).join("") : '<span>暂无课程</span>'}
      </div>`);
    }
  }
  elements.timetableGrid.className = "timetable-grid month-view";
  elements.timetableGrid.innerHTML = cells.join("");
}

function renderAssignmentTable(items) {
  if (!items.length) {
    elements.assignmentTableBody.innerHTML = '<tr><td colspan="7">暂无课程</td></tr>';
    return;
  }
  elements.assignmentTableBody.innerHTML = [...items]
    .sort((a, b) => Number(a.weekday) - Number(b.weekday) || Number(a.startSection) - Number(b.startSection) || a.courseName.localeCompare(b.courseName, "zh-CN"))
    .map((item) => `<tr>
      <td>${escapeHtml(`${item.courseName} (${item.courseId})`)}</td>
      <td>${escapeHtml(normalizeCourseCategory(item.courseType, item.courseName))}</td>
      <td>${escapeHtml(formatCourseTime(item))}</td>
      <td>${escapeHtml(item.teacherName || "教师待定")}</td>
      <td>${escapeHtml(item.classroom || "教室待定")}</td>
      <td>${escapeHtml(item.source || "当前占用")}</td>
      <td>${renderDropAction(item)}</td>
    </tr>`)
    .join("");
}

function renderDropAction(item) {
  if (item.selectedByStudent) {
    return `<button class="text-button danger" type="button" data-action="drop-course" data-course-id="${escapeHtml(item.courseId)}">退课</button>`;
  }
  return '<span class="muted-text">不可退</span>';
}

function getVisibleTimetableItems() {
  const filter = elements.timetableFilter.value.trim().toLowerCase();
  return buildTimetableItems().filter((item) => {
    if (!filter) return true;
    return [
      item.courseId,
      item.courseName,
      item.teacherName,
      item.classroom,
      item.courseType,
      item.source,
    ].some((value) => String(value || "").toLowerCase().includes(filter));
  });
}

function buildTimetableItems() {
  const current = state.currentAssignments.map((item) => normalizeTimetableItem(item, item.selectedByStudent ? "学生选课" : "当前占用"));
  const fixed = state.fixedCourseIds
    .map(findCourse)
    .filter(Boolean)
    .map((course) => normalizeTimetableItem({
      courseId: course.id,
      courseName: course.name,
      timeSlotId: course.timeSlotId,
      teacherName: course.teacherName,
      classroom: course.classroom,
      courseType: normalizeCourseCategory(course.category || course.courseType, course.name),
      weekday: course.weekday,
      startSection: course.startSection,
      endSection: course.endSection,
    }, "固定必选"));
  return [...current, ...fixed].filter((item) => item.weekday && item.startSection && item.endSection);
}

function normalizeTimetableItem(item, source) {
  const parsed = parseSlot(item.timeSlotId || item.time_slot_id);
  const weekday = Number(item.weekday || parsed.weekday);
  const startSection = Number(item.startSection || item.start_section || parsed.startSection);
  const endSection = Number(item.endSection || item.end_section || parsed.endSection || startSection);
  return {
    courseId: item.courseId || item.course_id || item.id,
    courseName: item.courseName || item.course_name || item.name || "未命名课程",
    timeSlotId: item.timeSlotId || item.time_slot_id || parsed.id,
    teacherName: item.teacherName || item.teacher_name,
    classroom: item.classroom,
    courseType: normalizeCourseCategory(item.courseType || item.course_type || item.category, item.courseName || item.name),
    weekday,
    startSection,
    endSection,
    source,
    selectedByStudent: Boolean(item.selectedByStudent),
  };
}

function groupItemsBySectionAndWeekday(items) {
  const groups = new Map();
  items.forEach((item) => {
    const key = `${item.startSection}:${item.weekday}`;
    const list = groups.get(key) || [];
    list.push(item);
    groups.set(key, list);
  });
  return groups;
}

function renderTimeCell(section) {
  const periodClass = section <= 6 ? "morning-section" : section <= 10 ? "afternoon-section" : "evening-section";
  return `<div class="time-cell ${periodClass}">
    <span>第 ${section} 节</span>
    <small>${sectionTimeLabels[section] || ""}</small>
  </div>`;
}

function renderSlotCard(item) {
  return `<div class="slot-card ${item.source === "固定必选" ? "fixed-slot" : ""}">
    <strong>${escapeHtml(item.courseName)}</strong>
    <span>${escapeHtml(item.teacherName || "教师待定")}</span>
    <span>${escapeHtml(item.classroom || "教室待定")}</span>
    <span>${escapeHtml(item.source)}</span>
  </div>`;
}

function renderMonthCourse(item) {
  return `<div class="month-course ${item.source === "固定必选" ? "fixed-slot" : ""}">
    <b>${escapeHtml(item.courseName)}</b>
    <span>${escapeHtml(`第 ${item.startSection}-${item.endSection} 节`)}</span>
  </div>`;
}

function renderRecommendations(items) {
  elements.recommendationCount.textContent = `${items.length} 门`;
  renderMetrics();
  if (!items.length) {
    elements.recommendationList.innerHTML = '<div class="empty-state">点击“生成推荐”查看课程列表</div>';
    return;
  }

  elements.recommendationList.innerHTML = items.map((item) => {
    const selected = isCourseSelected(item.course_id);
    const conflict = Boolean(item.has_time_conflict) && !selected;
    const missing = item.missing_prerequisite_ids || [];
    const tags = item.matched_interest_tags || [];
    const courseType = normalizeCourseCategory(item.course_type || item.category, item.course_name);
    const teacher = item.teacher_name || item.teacherName || "教师待定";
    const classroom = item.classroom || "教室待定";
    const credit = item.credit ?? "-";
    const canSelect = !selected && !item.is_completed && !item.is_fixed_selected && !item.has_time_conflict;
    return `<article class="course-card">
      <div class="course-head">
        <div>
          <strong>${escapeHtml(item.course_name)} (${escapeHtml(item.course_id)})</strong>
          <div class="course-meta">
            <span>${escapeHtml(courseType)}</span>
            <span class="meta-dot">/</span>
            <span>${escapeHtml(credit)} 学分</span>
            <span class="meta-dot">/</span>
            <span>${escapeHtml(formatCourseTime(item))}</span>
            <span class="meta-dot">/</span>
            <span>${escapeHtml(teacher)}</span>
            <span class="meta-dot">/</span>
            <span>${escapeHtml(classroom)}</span>
          </div>
        </div>
        <div class="recommend-actions">
          <div class="score" aria-label="推荐分数 ${escapeHtml(item.score)}">${escapeHtml(item.score)}</div>
          <button class="secondary-button select-button" type="button" data-action="select-course" data-course-id="${escapeHtml(item.course_id)}">${selected ? "已选" : "选课"}</button>
        </div>
      </div>
      <div class="tag-row">
        <span class="badge ${selected ? "success" : conflict ? "danger" : "success"}">${selected ? "已加入课表" : conflict ? "时间冲突" : "时间可选"}</span>
        ${item.is_completed ? '<span class="badge warning">已修</span>' : ""}
        ${selected ? '<span class="badge success">已选</span>' : ""}
        ${item.is_fixed_selected ? '<span class="badge warning">固定</span>' : ""}
        ${tags.map((tag) => `<span class="badge neutral">${escapeHtml(tag)}</span>`).join("")}
        ${missing.length ? `<span class="badge warning">缺少先修：${escapeHtml(missing.join(", "))}</span>` : ""}
        ${canSelect ? '<span class="badge success">可选课</span>' : ""}
      </div>
      <div class="course-reasons">${escapeHtml(summarizeRecommendation(item))}</div>
      ${renderSelectionFeedback(item.course_id)}
    </article>`;
  }).join("");
}

function renderSelectionFeedback(courseId) {
  if (!selectionFeedback || selectionFeedback.courseId !== courseId) {
    return "";
  }
  return `<div class="selection-feedback ${escapeHtml(selectionFeedback.mode)}">${escapeHtml(selectionFeedback.message)}</div>`;
}

function getFilteredCourses() {
  const keyword = elements.courseSearchInput.value.trim().toLowerCase();
  const category = elements.categoryFilter.value;
  const status = elements.statusFilter.value;
  return state.courses.filter((course) => {
    const haystack = [
      course.id,
      course.name,
      course.teacherName,
      normalizeCourseCategory(course.category || course.courseType, course.name),
      course.classroom,
      ...(course.interestTags || []),
    ].join(" ").toLowerCase();
    if (keyword && !haystack.includes(keyword)) return false;
    if (category && normalizeCourseCategory(course.category || course.courseType, course.name) !== category) return false;
    if (status === "completed" && !state.completedCourseIds.includes(course.id)) return false;
    if (status === "fixed" && !state.fixedCourseIds.includes(course.id)) return false;
    if (status === "conflict" && !hasTimeConflict(course, busyItemsForCourse(course.id))) return false;
    if (status === "available" && (state.completedCourseIds.includes(course.id) || state.fixedCourseIds.includes(course.id))) return false;
    return true;
  });
}

function localRecommend(payload) {
  const busyItems = [
    ...payload.currentAssignments,
    ...payload.courses.filter((course) => payload.fixedCourseIds.includes(course.id)),
  ];
  return payload.courses
    .map((course) => {
      let score = 50;
      const reasons = [];
      const matchedInterestTags = (course.interestTags || []).filter((tag) =>
        payload.student.interests.some((interest) => interest.toLowerCase() === tag.toLowerCase()),
      );
      const missing = (course.prerequisiteCourseIds || []).filter((id) => !payload.student.completedCourseIds.includes(id));
      const hasConflict = hasTimeConflict(course, busyItems);
      const isCompleted = payload.student.completedCourseIds.includes(course.id);
      const isFixed = payload.fixedCourseIds.includes(course.id);
      const isSelected = payload.currentAssignments.some((item) => item.courseId === course.id || item.course_id === course.id);

      if ((course.majorTags || []).includes(payload.student.major)) {
        score += 30;
        reasons.push("专业匹配");
      }
      if ((course.gradeTags || []).includes(payload.student.grade)) {
        score += 20;
        reasons.push("年级适配");
      }
      if (matchedInterestTags.length) {
        score += matchedInterestTags.length * 12;
        reasons.push(`命中兴趣：${matchedInterestTags.join(", ")}`);
      }
      if (missing.length) {
        score -= missing.length * 30;
        reasons.push(`缺少先修课程：${missing.join(", ")}`);
      }
      if (hasConflict) {
        score -= 50;
        reasons.push("与当前占用或固定课程存在时间冲突");
      }
      if (isCompleted) {
        score -= 100;
        reasons.push("该课程已修读");
      }
      if (isFixed || isSelected) {
        score -= 100;
        reasons.push("该课程已在当前选择中");
      }

      return {
        course_id: course.id,
        course_name: course.name,
        score,
        has_time_conflict: hasConflict,
        matched_interest_tags: matchedInterestTags,
        missing_prerequisite_ids: missing,
        reasons,
        time_slot_id: course.timeSlotId,
        category: normalizeCourseCategory(course.category || course.courseType, course.name),
        course_type: normalizeCourseCategory(course.courseType || course.category, course.name),
        credit: course.credit,
        teacher_name: course.teacherName,
        classroom: course.classroom,
        weekday: course.weekday,
        start_section: course.startSection,
        end_section: course.endSection,
        is_completed: isCompleted,
        is_currently_selected: isSelected,
        is_fixed_selected: isFixed,
      };
    })
    .filter((item) => payload.includeConflicted || !item.has_time_conflict)
    .filter((item) => !payload.excludeSelected || (!item.is_currently_selected && !item.is_fixed_selected))
    .sort((a, b) => b.score - a.score || Number(a.has_time_conflict) - Number(b.has_time_conflict) || a.course_name.localeCompare(b.course_name, "zh-CN"))
    .slice(0, payload.topK);
}

function summarizeRecommendation(item) {
  const parts = [];
  if ((item.matched_interest_tags || []).length) {
    parts.push(`兴趣方向与 ${item.matched_interest_tags.join(", ")} 匹配`);
  }
  if ((item.missing_prerequisite_ids || []).length) {
    parts.push(`需要补足先修课程 ${item.missing_prerequisite_ids.join(", ")}`);
  }
  if (isCourseSelected(item.course_id)) {
    parts.push("该课程已加入当前课表");
  } else {
    parts.push(item.has_time_conflict ? "当前已有同时间段课程" : "与当前占用不冲突");
  }
  if (item.reasons) {
    parts.push(...item.reasons.slice(0, 2));
  }
  return Array.from(new Set(parts)).join("；");
}

function courseSummary(course) {
  const parts = [];
  if ((course.majorTags || []).length) parts.push(`面向 ${course.majorTags.map((tag) => majorLabels[tag] || tag).join(", ")}`);
  if ((course.gradeTags || []).length) parts.push(`适合 ${course.gradeTags.join(", ")} 级`);
  if ((course.prerequisiteCourseIds || []).length) parts.push(`先修 ${course.prerequisiteCourseIds.join(", ")}`);
  return parts.join("；") || "暂无额外限制";
}

function mapBackendCourse(row) {
  const id = String(row.course_code || row.id || "").trim();
  const name = String(row.course_name || row.name || "").trim();
  if (!id || !name) return null;
  const weekday = optionalNumber(row.weekday);
  const startSection = optionalNumber(row.start_section || row.startSection);
  const endSection = optionalNumber(row.end_section || row.endSection) || startSection;
  return {
    id,
    name,
    majorTags: [state.profile.major],
    gradeTags: [state.profile.grade],
    interestTags: inferInterestTags(name),
    prerequisiteCourseIds: [],
    timeSlotId: weekday && startSection ? `D${weekday}-S${startSection}-${endSection}` : undefined,
    category: inferCourseCategory(row.category || row.course_type || row.courseType, name),
    credit: undefined,
    teacherName: row.teacher_name || row.teacherName || "教师待定",
    classroom: row.classroom || "教室待定",
    weekday,
    startSection,
    endSection,
    semester: row.semester,
  };
}

function inferInterestTags(name) {
  const tags = [];
  const lower = name.toLowerCase();
  if (name.includes("算法") || lower.includes("algorithm")) tags.push("algorithm");
  if (name.includes("智能") || lower.includes("ai")) tags.push("AI");
  if (name.includes("数据")) tags.push("database");
  if (name.includes("网络")) tags.push("network");
  if (name.includes("系统")) tags.push("system");
  return tags;
}

function hasTimeConflict(course, items) {
  const block = blockFrom(course);
  if (!block) return false;
  return items.some((item) => {
    if (item.id === course.id || item.courseId === course.id || item.course_id === course.id) return false;
    const other = blockFrom(item);
    return other && blocksOverlap(block, other);
  });
}

function blockFrom(item) {
  const timeSlotId = item.timeSlotId || item.time_slot_id;
  const parsed = parseSlot(timeSlotId);
  const weekday = item.weekday || parsed.weekday;
  const startSection = item.startSection || item.start_section || parsed.startSection;
  const endSection = item.endSection || item.end_section || parsed.endSection || startSection;
  if (!timeSlotId && !weekday) return null;
  return { timeSlotId, weekday, startSection, endSection };
}

function blocksOverlap(left, right) {
  if (left.timeSlotId && right.timeSlotId && left.timeSlotId === right.timeSlotId) return true;
  if (!left.weekday || !right.weekday || Number(left.weekday) !== Number(right.weekday)) return false;
  if (!left.startSection || !left.endSection || !right.startSection || !right.endSection) return false;
  return Number(left.startSection) <= Number(right.endSection) && Number(right.startSection) <= Number(left.endSection);
}

function formatCourseTime(item) {
  const weekday = item.weekday;
  const start = item.startSection || item.start_section;
  const end = item.endSection || item.end_section;
  if (weekday && start && end) {
    return `周${"一二三四五六日"[Number(weekday) - 1] || weekday} 第 ${start}-${end} 节`;
  }
  return formatSlot(item.time_slot_id || item.timeSlotId);
}

function formatSlot(slotId) {
  const parsed = parseSlot(slotId);
  if (!parsed.weekday) return slotId || "待定";
  return `周${"一二三四五六日"[parsed.weekday - 1] || parsed.weekday} 第 ${parsed.startSection}${parsed.endSection && parsed.endSection !== parsed.startSection ? `-${parsed.endSection}` : ""} 节`;
}

function parseSlot(slotId) {
  const match = String(slotId || "").match(/^D(\d+)-S(\d+)(?:-(\d+))?$/);
  if (!match) return {};
  return {
    weekday: Number(match[1]),
    startSection: Number(match[2]),
    endSection: Number(match[3] || match[2]),
  };
}

function findCourse(courseId) {
  return state.courses.find((course) => course.id === courseId);
}

function toggleSet(list, value) {
  const index = list.indexOf(value);
  if (index >= 0) {
    list.splice(index, 1);
  } else {
    list.push(value);
  }
}

function setLoading(isLoading) {
  elements.recommendButton.disabled = isLoading;
  elements.recommendButton.textContent = isLoading ? "生成中" : "生成推荐";
}

function setStatus(message) {
  elements.recommendStatus.textContent = message;
}

function setSelectionStatus(message, mode = "neutral", courseId = null) {
  selectionFeedback = courseId ? { courseId, message, mode } : null;
  elements.selectionStatus.textContent = message;
  elements.selectionStatus.className = `result-strip ${mode}`;
}

function isCourseSelected(courseId) {
  return state.currentAssignments.some((item) => item.courseId === courseId || item.course_id === courseId);
}

function busyItemsForCourse(courseId) {
  return [
    ...state.currentAssignments,
    ...state.fixedCourseIds
      .filter((id) => id !== courseId)
      .map(findCourse)
      .filter(Boolean),
  ];
}

function normalizeCourseCategory(value, courseName = "") {
  const raw = String(value || "").trim();
  if (courseCategories.includes(raw)) return raw;
  if (categoryAliases[raw]) return categoryAliases[raw];
  return inferCourseCategory(raw, courseName);
}

function inferCourseCategory(value, courseName = "") {
  const text = `${value || ""} ${courseName || ""}`;
  if (text.includes("通识") && text.includes("必修")) return "通识必修";
  if (text.includes("通识")) return "通识选修";
  if (text.includes("公共") || text.includes("英语") || text.includes("体育") || text.includes("思政")) return "通识必修";
  if (text.includes("必修") || text.includes("核心") || text.includes("基础")) return "专业必修";
  if (text.includes("选修") || text.includes("高阶")) return "专业选修";
  return "专业选修";
}

function showStudentView(viewName, options = {}) {
  activeStudentView = viewName || "profile";
  elements.navTabs.forEach((tab) => {
    tab.classList.toggle("active", tab.dataset.view === activeStudentView);
  });
  elements.studentViews.forEach((view) => {
    view.classList.toggle("active-student-view", view.dataset.studentView === activeStudentView);
    view.classList.toggle("student-view-hidden", view.dataset.studentView !== activeStudentView);
  });
  elements.studentGrid.classList.toggle("single-view", activeStudentView !== "profile");
  if (!options.preserveScroll) {
    document.querySelector(".workspace")?.scrollTo({ top: 0, behavior: "smooth" });
  }
  if (activeStudentView === "schedule") {
    renderTimetable();
  }
}

function defaultState() {
  return {
    profile: {
      id: session.account || "2611222",
      name: session.name || "学生用户",
      major: "Computer Science",
      grade: "2023",
      interests: ["algorithm", "AI"],
      semester: "2025-2026-2",
    },
    settings: {
      topK: 4,
      includeConflicted: true,
      excludeSelected: true,
    },
    courses: structuredClone(sampleCourses),
    currentAssignments: structuredClone(sampleAssignments),
    completedCourseIds: ["C001"],
    fixedCourseIds: [],
    dataSource: "示例课程",
    lastSource: "示例课程",
    updatedAt: Date.now(),
  };
}

function loadState() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || "null");
    if (saved && saved.profile && Array.isArray(saved.courses)) {
      return {
        ...defaultState(),
        ...saved,
        profile: { ...defaultState().profile, ...saved.profile },
        settings: { ...defaultState().settings, ...saved.settings },
      };
    }
  } catch {
    localStorage.removeItem(STORAGE_KEY);
  }
  return defaultState();
}

function saveState() {
  state.updatedAt = Date.now();
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

function persistAndRender() {
  saveState();
  render();
}

function readSession() {
  try {
    return JSON.parse(localStorage.getItem(AUTH_KEY) || "null");
  } catch {
    localStorage.removeItem(AUTH_KEY);
    return null;
  }
}

function field(formData, name) {
  return String(formData.get(name) || "").trim();
}

function optionalNumber(value) {
  const trimmed = String(value ?? "").trim();
  return trimmed ? Number(trimmed) : undefined;
}

function splitCsv(value) {
  return String(value || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function clamp(value, min, max) {
  if (Number.isNaN(value)) return min;
  return Math.max(min, Math.min(max, value));
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
