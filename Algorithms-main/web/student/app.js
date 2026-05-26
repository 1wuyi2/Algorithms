const API_BASE_URL = "http://127.0.0.1:8000";

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

const sampleCurrentAssignments = [
  { courseId: "C010", timeSlotId: "D1-S1" },
  { courseId: "C011", timeSlotId: "D3-S2" },
];

const form = document.querySelector("#studentForm");
const coursesJson = document.querySelector("#coursesJson");
const scheduleBody = document.querySelector("#scheduleBody");
const recommendationList = document.querySelector("#recommendationList");
const recommendationCount = document.querySelector("#recommendationCount");
const resultSummary = document.querySelector("#resultSummary");

coursesJson.value = JSON.stringify(
  {
    courses: sampleCourses,
    currentAssignments: sampleCurrentAssignments,
  },
  null,
  2,
);
renderSchedule(sampleCurrentAssignments);

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  resultSummary.textContent = "正在调用后端推荐接口……";

  try {
    const payload = buildPayload(new FormData(form));
    const response = await fetch(`${API_BASE_URL}/student/recommend`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.error || "推荐接口返回错误");
    }
    renderSchedule(payload.currentAssignments);
    renderRecommendations(result.recommendations);
    resultSummary.textContent = `已从 ${result.candidate_count} 门候选课程中生成 Top ${result.top_k} 推荐。`;
  } catch (error) {
    recommendationList.innerHTML = `<div class="error-state">${escapeHtml(
      `推荐失败：${error.message}。请确认已运行 python -m src.api.server，且候选课程 JSON 格式正确。`,
    )}</div>`;
    recommendationCount.textContent = "0";
    resultSummary.textContent = "推荐接口暂不可用。";
  }
});

document.querySelector("#resetSampleButton").addEventListener("click", () => {
  coursesJson.value = JSON.stringify(
    {
      courses: sampleCourses,
      currentAssignments: sampleCurrentAssignments,
    },
    null,
    2,
  );
  renderSchedule(sampleCurrentAssignments);
});

document.querySelector("#localPreviewButton").addEventListener("click", () => {
  const parsed = parseCourseInput();
  renderSchedule(parsed.currentAssignments);
});

function buildPayload(formData) {
  const parsed = parseCourseInput();
  return {
    student: {
      id: formData.get("id").trim(),
      major: formData.get("major").trim(),
      grade: formData.get("grade").trim(),
      completedCourseIds: splitCsv(formData.get("completedCourseIds")),
      interests: splitCsv(formData.get("interests")),
    },
    courses: parsed.courses,
    currentAssignments: parsed.currentAssignments,
    topK: Number(formData.get("topK") || 5),
    includeConflicted: formData.get("includeConflicted") === "on",
  };
}

function parseCourseInput() {
  const parsed = JSON.parse(coursesJson.value || "{}");
  return {
    courses: Array.isArray(parsed.courses) ? parsed.courses : [],
    currentAssignments: Array.isArray(parsed.currentAssignments) ? parsed.currentAssignments : [],
  };
}

function renderSchedule(assignments) {
  if (!assignments.length) {
    scheduleBody.innerHTML = '<tr><td colspan="2">暂无当前课表</td></tr>';
    return;
  }
  scheduleBody.innerHTML = assignments
    .map((item) => {
      return `<tr>
        <td>${escapeHtml(item.courseId || item.course_id)}</td>
        <td>${escapeHtml(item.timeSlotId || item.time_slot_id)}</td>
      </tr>`;
    })
    .join("");
}

function renderRecommendations(items) {
  recommendationCount.textContent = items.length;
  if (!items.length) {
    recommendationList.innerHTML = '<div class="empty-state">没有符合过滤条件的推荐课程。</div>';
    return;
  }

  recommendationList.innerHTML = items
    .map((item) => {
      const badgeClass = item.has_time_conflict ? "badge danger" : "badge success";
      const badgeText = item.has_time_conflict ? "时间冲突" : "时间可选";
      return `<article class="recommendation-card">
        <div class="card-main">
          <div>
            <p class="course-id">${escapeHtml(item.course_id)}</p>
            <h3>${escapeHtml(item.course_name)}</h3>
          </div>
          <div class="score">${escapeHtml(item.score)}</div>
        </div>
        <div class="meta-row">
          <span class="${badgeClass}">${badgeText}</span>
          <span>${escapeHtml(item.time_slot_id || "待定时间")}</span>
          ${item.is_completed ? '<span class="badge muted">已修读</span>' : ""}
        </div>
        <ul>
          ${item.reasons.map((reason) => `<li>${escapeHtml(reason)}</li>`).join("")}
        </ul>
      </article>`;
    })
    .join("");
}

function splitCsv(value) {
  return String(value || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
