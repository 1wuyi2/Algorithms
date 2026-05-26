const API_BASE_URL = "http://127.0.0.1:8000";
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
  },
];

const currentAssignments = [
  { courseId: "C010", courseName: "大学英语", timeSlotId: "D1-S1" },
  { courseId: "C011", courseName: "线性代数", timeSlotId: "D3-S2" },
];

const elements = {
  identity: document.querySelector("#studentIdentity"),
  logoutButton: document.querySelector("#logoutButton"),
  studentName: document.querySelector("#studentName"),
  studentId: document.querySelector("#studentId"),
  form: document.querySelector("#recommendForm"),
  recommendButton: document.querySelector("#recommendButton"),
  recommendStatus: document.querySelector("#recommendStatus"),
  scheduleList: document.querySelector("#scheduleList"),
  recommendationList: document.querySelector("#recommendationList"),
  recommendationCount: document.querySelector("#recommendationCount"),
};

renderIdentity();
renderSchedule();

elements.logoutButton.addEventListener("click", () => {
  localStorage.removeItem(AUTH_KEY);
  window.location.href = "../login/index.html";
});

elements.recommendButton.addEventListener("click", generateRecommendations);

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
  }
}

function renderIdentity() {
  elements.identity.textContent = `${session.name || "学生用户"} ${session.account}`;
  elements.studentName.textContent = session.name || studentProfile.name;
  elements.studentId.textContent = session.account || studentProfile.id;
}

function renderSchedule() {
  elements.scheduleList.innerHTML = currentAssignments
    .map((item) => `<article class="schedule-item">
      <strong>${escapeHtml(item.courseName)} (${escapeHtml(item.courseId)})</strong>
      <span>${escapeHtml(formatSlot(item.timeSlotId))}</span>
    </article>`)
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
      return `<article class="course-card">
        <div class="course-head">
          <div>
            <strong>${escapeHtml(item.course_name)} (${escapeHtml(item.course_id)})</strong>
            <div class="course-meta">${escapeHtml(item.category || "课程")} · ${escapeHtml(item.credit || "-")} 学分 · ${escapeHtml(formatSlot(item.time_slot_id))}</div>
          </div>
          <div class="score">${escapeHtml(item.score)}</div>
        </div>
        <div class="tag-row">
          <span class="badge ${conflict ? "danger" : "success"}">${conflict ? "时间冲突" : "时间可选"}</span>
          ${tags.map((tag) => `<span class="badge neutral">${escapeHtml(tag)}</span>`).join("")}
          ${missing.length ? `<span class="badge warning">缺少先修：${escapeHtml(missing.join(", "))}</span>` : ""}
        </div>
        <div class="course-reasons">${(item.reasons || []).map(escapeHtml).join("；")}</div>
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
        reasons.push("年级匹配");
      }
      if (matchedInterestTags.length) {
        score += matchedInterestTags.length * 10;
        reasons.push(`兴趣命中：${matchedInterestTags.join(", ")}`);
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
        credit: course.credit,
      };
    })
    .filter((item) => payload.includeConflicted || !item.has_time_conflict)
    .sort((a, b) => b.score - a.score)
    .slice(0, payload.topK);
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

function formatSlot(slotId) {
  const match = String(slotId || "").match(/^D(\d+)-S(\d+)$/);
  if (!match) return slotId || "待定";
  const weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"];
  return `${weekdays[Number(match[1]) - 1] || `第${match[1]}天`} 第 ${match[2]} 节`;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
