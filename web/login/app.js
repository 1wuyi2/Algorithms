const API_BASE_URL = "http://127.0.0.1:8000";
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
    const response = await fetch(`${API_BASE_URL}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ account, password }),
    });
    const result = await response.json();
    if (!response.ok || result.success === false) {
      throw new Error(result.error || `HTTP ${response.status}`);
    }
    if (!result.authenticated || !result.user) {
      showMessage(result.reason || "学工号或密码错误。");
      return;
    }

    const target = roleTargets[result.user.role];
    if (!target) {
      showMessage("账号身份暂不支持登录。");
      return;
    }

    localStorage.setItem(
      AUTH_KEY,
      JSON.stringify({
        account: result.user.account,
        role: result.user.role,
        name: result.user.name,
        token: result.token,
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
