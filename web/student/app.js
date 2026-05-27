const API_BASE_URL = window.location.protocol.startsWith("http")
  ? window.location.origin
  : "http://127.0.0.1:8000";
const AUTH_KEY = "nankai-auth-session-v1";

const session = readSession();
if (!session || session.role !== "student") {
  window.location.replace("../login/index.html");
  throw new Error("Student authentication required");
}

const studentProfile = {
  id: "2611222",
  name: "学生用户",
  major: "Computer Science",
  majorLabel: "计算机科学与技术",
  grade: "2023",
  completedCourseIds: ["C001"],
  interests: ["algorithm", "AI"],
};

const sampleCourses = [
  {
    id: "C002",
    name: "算法设计与分析",
    majorTags: ["Computer Science"],
    gradeTags: ["2023"],
    interestTags: ["algorithm"],
    prerequisiteCourseIds: ["C001"],
    timeSlotId: "D1-S3",
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
    timeSlotId: "D1-S1",
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
    timeSlotId: "D1-S4",
    category: "专业核心",
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
    timeSlotId: "D2-S2",
    category: "高阶选修",
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
    timeSlotId: "D1-S5",
    category: "通识选修",
    credit: 2,
    teacherName: "周老师",
    classroom: "八里台二主楼 204",
    weekday: 1,
    startSection: 5,
    endSection: 6,
  },
];

const currentAssignments = [
  {
    courseId: "C010",
    courseName: "大学英语",
    timeSlotId: "D1-S1",
    teacherName: "李老师",
    classroom: "津南公教 A103",
    courseType: "公共必修",
  },
  {
    courseId: "C011",
    courseName: "线性代数",
    timeSlotId: "D3-S2",
    teacherName: "孙老师",
    classroom: "津南公教 B204",
    courseType: "学科基础",
  },
];

const elements = {
  appShell: document.querySelector(".app-shell"),
  navTabs: document.querySelectorAll(".nav-tab"),
  identity: document.querySelector("#studentIdentity"),
  logoutButton: document.querySelector("#logoutButton"),
  sidebarToggle: document.querySelector("#sidebarToggle"),
  studentName: document.querySelector("#studentName"),
  studentId: document.querySelector("#studentId"),
  form: document.querySelector("#recommendForm"),
  recommendButton: document.querySelector("#recommendButton"),
  recommendLimit: document.querySelector("#recommendLimit"),
  recommendStatus: document.querySelector("#recommendStatus"),
  scheduleList: document.querySelector("#scheduleList"),
  recommendationList: document.querySelector("#recommendationList"),
  recommendationCount: document.querySelector("#recommendationCount"),
};

renderIdentity();
renderSchedule();
syncRecommendLimit();
syncActiveNav();

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
elements.form.topK.addEventListener("input", syncRecommendLimit);
elements.navTabs.forEach((tab) => {
  tab.addEventListener("click", () => setActiveNav(tab.getAttribute("href")?.replace("#", "") || "profile"));
});
window.addEventListener("hashchange", syncActiveNav);
window.addEventListener("scroll", syncActiveNav, { passive: true });

async function generateRecommendations() {
  const formData = new FormData(elements.form);
  const interests = splitCsv(formData.get("interests"));
  const topK = Number(formData.get("topK") || 4);
  const includeConflicted = formData.get("includeConflicted") === "on";
  const payload = {
    student: {
      id: studentProfile.id,
      major: studentProfile.major,
      grade: studentProfile.grade,
      completedCourseIds: studentProfile.completedCourseIds,
      interests,
    },
    courses: sampleCourses,
    currentAssignments,
    topK,
    includeConflicted,
  };

  setLoading(true);
  elements.recommendStatus.textContent = "正在生成推荐...";
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
    renderRecommendations(result.recommendations || []);
    elements.recommendStatus.textContent = `已调用后端接口，从 ${result.candidate_count} 门候选课程中生成推荐。`;
  } catch {
    const fallback = localRecommend(payload);
    renderRecommendations(fallback);
    elements.recommendStatus.textContent = "后端接口暂不可用，已使用前端示例规则生成推荐。";
  } finally {
    setLoading(false);
  }
}

function renderIdentity() {
  elements.identity.textContent = `${session.name || "学生用户"} ${session.account}`;
  elements.studentName.textContent = session.name || studentProfile.name;
  elements.studentId.textContent = session.account || studentProfile.id;
}

function renderSchedule() {
  elements.scheduleList.innerHTML = currentAssignments
    .map(
      (item) => `<article class="schedule-item">
        <strong>${escapeHtml(item.courseName)} (${escapeHtml(item.courseId)})</strong>
        <span>${escapeHtml(formatSlot(item.timeSlotId))} · ${escapeHtml(item.courseType)} · ${escapeHtml(item.classroom)}</span>
      </article>`,
    )
    .join("");
}

function renderRecommendations(items) {
  elements.recommendationCount.textContent = `${items.length} 门`;
  if (!items.length) {
    elements.recommendationList.innerHTML = '<div class="empty-state">暂无符合条件的推荐课程</div>';
    return;
  }

  elements.recommendationList.innerHTML = items
    .map((item) => {
      const conflict = Boolean(item.has_time_conflict);
      const missing = item.missing_prerequisite_ids || [];
      const tags = item.matched_interest_tags || [];
      const courseType = item.course_type || item.category || "课程";
      const teacher = item.teacher_name || item.teacherName || "教师待定";
      const classroom = item.classroom || "教室待定";
      const credit = item.credit ?? "-";
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
          <div class="score" aria-label="推荐分数 ${escapeHtml(item.score)}">${escapeHtml(item.score)}</div>
        </div>
        <div class="tag-row">
          <span class="badge ${conflict ? "danger" : "success"}">${conflict ? "时间冲突" : "时间可选"}</span>
          ${tags.map((tag) => `<span class="badge neutral">${escapeHtml(tag)}</span>`).join("")}
          ${missing.length ? `<span class="badge warning">缺少先修：${escapeHtml(missing.join(", "))}</span>` : ""}
        </div>
        <div class="course-reasons">${escapeHtml(summarizeRecommendation(item))}</div>
      </article>`;
    })
    .join("");
}

function localRecommend(payload) {
  const busySlots = new Set(payload.currentAssignments.map((item) => item.timeSlotId || item.time_slot_id));
  return payload.courses
    .map((course) => {
      let score = 50;
      const reasons = [];
      const matchedInterestTags = (course.interestTags || []).filter((tag) =>
        payload.student.interests.some((interest) => interest.toLowerCase() === tag.toLowerCase()),
      );
      const missing = (course.prerequisiteCourseIds || []).filter((id) => !payload.student.completedCourseIds.includes(id));
      const hasConflict = busySlots.has(course.timeSlotId);

      if ((course.majorTags || []).includes(payload.student.major)) {
        score += 20;
        reasons.push("专业匹配");
      }
      if ((course.gradeTags || []).includes(payload.student.grade)) {
        score += 10;
        reasons.push("年级适配");
      }
      if (matchedInterestTags.length) {
        score += matchedInterestTags.length * 10;
        reasons.push(`命中兴趣：${matchedInterestTags.join(", ")}`);
      }
      if (missing.length) {
        score -= 25;
        reasons.push(`缺少先修课程：${missing.join(", ")}`);
      }
      if (hasConflict) {
        score -= 20;
        reasons.push("与当前课表存在时间冲突");
      }

      return {
        course_id: course.id,
        course_name: course.name,
        score: Math.max(score, 0),
        has_time_conflict: hasConflict,
        matched_interest_tags: matchedInterestTags,
        missing_prerequisite_ids: missing,
        reasons,
        time_slot_id: course.timeSlotId,
        category: course.category,
        course_type: course.category,
        credit: course.credit,
        teacher_name: course.teacherName,
        classroom: course.classroom,
        weekday: course.weekday,
        start_section: course.startSection,
        end_section: course.endSection,
      };
    })
    .filter((item) => payload.includeConflicted || !item.has_time_conflict)
    .sort((a, b) => b.score - a.score)
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
  parts.push(item.has_time_conflict ? "当前课表中已有同时间段课程" : "与当前课表不冲突");
  if (item.reasons && item.reasons.every((reason) => !looksMojibake(reason))) {
    parts.push(...item.reasons.slice(0, 2));
  }
  return Array.from(new Set(parts)).join("；");
}

function readSession() {
  try {
    return JSON.parse(localStorage.getItem(AUTH_KEY) || "null");
  } catch {
    localStorage.removeItem(AUTH_KEY);
    return null;
  }
}

function splitCsv(value) {
  return String(value || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function syncRecommendLimit() {
  elements.recommendLimit.textContent = elements.form.topK.value || "4";
}

function setLoading(isLoading) {
  elements.recommendButton.disabled = isLoading;
  elements.recommendButton.textContent = isLoading ? "生成中" : "生成推荐";
}

function syncActiveNav() {
  const sections = ["profile", "settings", "schedule", "recommendations"];
  const currentFromHash = window.location.hash.replace("#", "");
  const visibleSection = sections.find((id) => {
    const section = document.getElementById(id);
    if (!section) return false;
    const rect = section.getBoundingClientRect();
    return rect.top <= 140 && rect.bottom > 140;
  });
  const activeId = sections.includes(currentFromHash) ? currentFromHash : visibleSection || "profile";
  setActiveNav(activeId);
}

function setActiveNav(activeId) {
  elements.navTabs.forEach((tab) => {
    tab.classList.toggle("active", tab.getAttribute("href") === `#${activeId}`);
  });
}

function formatCourseTime(item) {
  if (item.weekday && item.start_section && item.end_section) {
    return `周${"一二三四五六日"[Number(item.weekday) - 1] || item.weekday} 第${item.start_section}-${item.end_section}节`;
  }
  return formatSlot(item.time_slot_id || item.timeSlotId);
}

function formatSlot(slotId) {
  const match = String(slotId || "").match(/^D(\d+)-S(\d+)(?:-(\d+))?$/);
  if (!match) return slotId || "待定";
  const weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"];
  const end = match[3] ? `-${match[3]}` : "";
  return `${weekdays[Number(match[1]) - 1] || `第${match[1]}天`} 第${match[2]}${end}节`;
}

function looksMojibake(value) {
  return /[�]|[鏁绋戠鍦涓浜]/.test(String(value));
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
