const API_BASE_URL = window.location.protocol.startsWith("http")
  ? window.location.origin
  : "http://127.0.0.1:8000";
const AUTH_KEY = "nankai-auth-session-v1";

const roleTargets = {
  teacher: "../teacher/index.html",
  student: "../student/index.html",
};

const form = document.querySelector("#loginForm");
const message = document.querySelector("#loginMessage");

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  showMessage("正在登录...", "neutral");

  const formData = new FormData(form);
  const account = String(formData.get("account") || "").trim();
  const password = String(formData.get("password") || "");

  try {
    const result = await apiRequest("/auth/login", {
      method: "POST",
      body: JSON.stringify({ account, password }),
    });
    const payload = result.data || result;
    const user = payload.user || result.user;
    if (!payload.authenticated || !user) {
      showMessage(payload.reason || result.reason || "学工号或密码错误。");
      return;
    }

    const target = roleTargets[user.role];
    if (!target) {
      showMessage("账号身份暂不支持登录。");
      return;
    }

    localStorage.setItem(
      AUTH_KEY,
      JSON.stringify({
        account: user.account || account,
        role: user.role,
        name: user.name || "用户",
        token: payload.token || result.token,
        loginAt: new Date().toISOString(),
      }),
    );
    window.location.href = target;
  } catch (error) {
    showMessage(`登录失败：${error.message}。请确认后端服务已启动。`);
  }
});

function showMessage(text, mode = "error") {
  message.textContent = text;
  message.className = `message ${mode}`;
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
  const rawText = await response.text();
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
