const state = {
  courses: [],
  teachers: [],
  rooms: [],
  issues: [],
};

const views = document.querySelectorAll(".view");
const navTabs = document.querySelectorAll(".nav-tab");
const courseCount = document.querySelector("#courseCount");
const teacherCount = document.querySelector("#teacherCount");
const roomCount = document.querySelector("#roomCount");
const courseTableBody = document.querySelector("#courseTableBody");
const issueList = document.querySelector("#issueList");

navTabs.forEach((tab) => {
  tab.addEventListener("click", () => {
    navTabs.forEach((item) => item.classList.remove("active"));
    views.forEach((view) => view.classList.remove("active"));
    tab.classList.add("active");
    document.querySelector(`#view-${tab.dataset.view}`).classList.add("active");
  });
});

document.querySelector("#courseForm").addEventListener("submit", (event) => {
  event.preventDefault();
  const data = new FormData(event.currentTarget);
  state.courses.push({
    id: data.get("id").trim(),
    name: data.get("name").trim(),
    teacherId: data.get("teacherId").trim(),
    classGroupId: data.get("classGroupId").trim(),
  });
  event.currentTarget.reset();
  render();
});

document.querySelector("#teacherForm").addEventListener("submit", (event) => {
  event.preventDefault();
  const data = new FormData(event.currentTarget);
  state.teachers.push({
    id: data.get("id").trim(),
    name: data.get("name").trim(),
  });
  event.currentTarget.reset();
  render();
});

document.querySelector("#roomForm").addEventListener("submit", (event) => {
  event.preventDefault();
  const data = new FormData(event.currentTarget);
  state.rooms.push({
    id: data.get("id").trim(),
    name: data.get("name").trim(),
    capacity: Number(data.get("capacity")),
  });
  event.currentTarget.reset();
  render();
});

document.querySelector("#clearDataButton").addEventListener("click", () => {
  state.courses = [];
  state.teachers = [];
  state.rooms = [];
  state.issues = [];
  render();
});

document.querySelector("#runScheduleButton").addEventListener("click", async () => {
  if (state.courses.length === 0) {
    state.issues = [
      {
        title: "缺少课程数据",
        detail: "请先在基础数据页面录入课程，或等待后续数据导入模块接入。",
      },
    ];
    renderIssues();
    document.querySelector('[data-view="issues"]').click();
    return;
  }

  try {
    const response = await fetch("http://127.0.0.1:8000/schedule/greedy", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        courses: state.courses.map(toApiCourse),
        time_slots: buildDefaultTimeSlots(),
      }),
    });
    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.error || "排课接口返回错误");
    }
    state.issues = result.is_complete
      ? [{ title: "排课完成", detail: `已生成 ${result.assignments.length} 条课程时间安排。` }]
      : result.unscheduled.map((item) => ({ title: `课程 ${item.course_id} 未排入`, detail: item.reason }));
  } catch (error) {
    state.issues = [
      {
        title: "后端接口未启动",
        detail: `请先运行 python -m src.api.server，再重新生成课表。错误信息：${error.message}`,
      },
    ];
  }
  renderIssues();
  document.querySelector('[data-view="issues"]').click();
});

function render() {
  courseCount.textContent = state.courses.length;
  teacherCount.textContent = state.teachers.length;
  roomCount.textContent = state.rooms.length;
  renderCourses();
  renderIssues();
}

function renderCourses() {
  if (state.courses.length === 0) {
    courseTableBody.innerHTML = '<tr><td colspan="4">暂无课程数据</td></tr>';
    return;
  }

  courseTableBody.innerHTML = state.courses
    .map((course) => {
      return `<tr>
        <td>${escapeHtml(course.id)}</td>
        <td>${escapeHtml(course.name)}</td>
        <td>${escapeHtml(course.teacherId)}</td>
        <td>${escapeHtml(course.classGroupId)}</td>
      </tr>`;
    })
    .join("");
}

function renderIssues() {
  if (state.issues.length === 0) {
    issueList.innerHTML = '<div class="empty-state">暂无冲突信息</div>';
    return;
  }

  issueList.innerHTML = state.issues
    .map((issue) => {
      return `<div class="issue-item">
        <strong>${escapeHtml(issue.title)}</strong>
        <p>${escapeHtml(issue.detail)}</p>
      </div>`;
    })
    .join("");
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function toApiCourse(course) {
  return {
    id: course.id,
    name: course.name,
    teacher_id: course.teacherId,
    class_group_ids: [course.classGroupId],
    weekly_hours: 2,
  };
}

function buildDefaultTimeSlots() {
  return Array.from({ length: 14 }, (_, index) => {
    const section = index + 1;
    return {
      id: `D1-S${section}`,
      weekday: 1,
      start_section: section,
      end_section: section,
    };
  });
}

render();
