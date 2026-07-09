const state = {
  token: localStorage.getItem("pet_token"),
  user: null,
  question: null,
  startedAt: null,
  ranCode: false,
  pyodide: null,
  pyodideLoading: null,
};

const $ = (id) => document.getElementById(id);

async function api(path, options = {}) {
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };
  if (state.token) {
    headers.Authorization = `Bearer ${state.token}`;
  }
  const response = await fetch(path, { ...options, headers });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(body.detail || "Request failed");
  }
  return body;
}

function show(view) {
  $("login-view").classList.toggle("hidden", view !== "login");
  $("app-view").classList.toggle("hidden", view !== "app");
}

function setLoginError(message) {
  $("login-error").textContent = message || "";
}

async function loadMe() {
  if (!state.token) {
    show("login");
    return;
  }
  try {
    state.user = await api("/api/me");
    $("user-name").textContent = `${state.user.display_name} (${state.user.username})`;
    $("admin-panel").classList.toggle("hidden", state.user.role !== "admin");
    show("app");
    await Promise.all([loadDashboard(), loadQuestion(), loadAdmin()]);
  } catch (_error) {
    localStorage.removeItem("pet_token");
    state.token = null;
    show("login");
  }
}

async function login(event) {
  event.preventDefault();
  setLoginError("");
  try {
    const body = await api("/api/login", {
      method: "POST",
      body: JSON.stringify({
        username: $("username").value.trim(),
        password: $("password").value,
      }),
    });
    state.token = body.token;
    state.user = body.user;
    localStorage.setItem("pet_token", state.token);
    await loadMe();
  } catch (error) {
    setLoginError(error.message);
  }
}

async function logout() {
  try {
    await api("/api/logout", { method: "POST" });
  } catch (_error) {
    // Local logout should still happen even if the session is already gone.
  }
  localStorage.removeItem("pet_token");
  state.token = null;
  state.user = null;
  show("login");
}

function renderQuestion(question) {
  state.question = question;
  state.startedAt = Date.now();
  state.ranCode = false;
  $("feedback").className = "feedback hidden";
  $("feedback").textContent = "";
  $("question-source").textContent = question.source_file;
  $("question-difficulty").textContent = `難度 ${question.difficulty}`;
  $("question-stem").textContent = question.stem;
  $("question-code").textContent = question.code || "";
  $("question-code").classList.toggle("hidden", !question.code);
  $("code-input").value = question.code || "print(\"Hello Python\")";
  $("code-output").textContent = "尚未執行";

  const form = $("answer-form");
  form.innerHTML = "";
  const inputType = question.type === "multiple_choice" ? "checkbox" : "radio";
  for (const option of question.options) {
    const label = document.createElement("label");
    label.className = "option";
    label.innerHTML = `
      <input type="${inputType}" name="answer" value="${option.id}" />
      <span><strong>${option.id}.</strong> ${option.text}</span>
    `;
    form.appendChild(label);
  }
}

async function loadQuestion() {
  const body = await api("/api/next-question");
  renderQuestion(body.question);
}

function selectedAnswers() {
  return [...document.querySelectorAll("input[name='answer']:checked")].map((input) => input.value);
}

async function submitAnswer() {
  if (!state.question) return;
  const selected = selectedAnswers();
  if (selected.length === 0) {
    $("feedback").className = "feedback wrong";
    $("feedback").textContent = "請先選一個答案。";
    return;
  }
  const elapsed = Math.round((Date.now() - state.startedAt) / 1000);
  const result = await api("/api/attempts", {
    method: "POST",
    body: JSON.stringify({
      question_id: state.question.id,
      selected_answer: selected,
      used_hint: false,
      ran_code: state.ranCode,
      elapsed_seconds: elapsed,
    }),
  });
  const answerText = result.answer.join(", ");
  const updates = result.mastery_updates
    .map((item) => `${item.name}: ${item.mastery_score}`)
    .join("；");
  $("feedback").className = `feedback ${result.is_correct ? "correct" : "wrong"}`;
  $("feedback").innerHTML = `
    <strong>${result.is_correct ? "答對" : "答錯"}</strong>
    <p>正確答案：${answerText}</p>
    <p>${result.explanation}</p>
    <p><strong>常見錯因：</strong>${result.common_mistake}</p>
    <p><strong>熟練度：</strong>${updates || "尚無更新"}</p>
  `;
  await loadDashboard();
}

async function loadDashboard() {
  const body = await api("/api/dashboard");
  $("total-attempts").textContent = body.total_attempts;
  $("accuracy").textContent = `${body.accuracy}%`;
  const list = $("weak-concepts");
  list.innerHTML = "";
  if (body.weak_concepts.length === 0) {
    list.innerHTML = "<li>目前尚無弱點資料</li>";
    return;
  }
  for (const concept of body.weak_concepts) {
    const li = document.createElement("li");
    li.textContent = `${concept.name}｜${concept.mastery_score} 分｜連錯 ${concept.wrong_streak}`;
    list.appendChild(li);
  }
}

async function loadAdmin() {
  if (!state.user || state.user.role !== "admin") return;
  try {
    const body = await api("/api/admin/students");
    const list = $("students");
    list.innerHTML = "";
    for (const student of body.students) {
      const li = document.createElement("li");
      li.textContent = `${student.display_name}｜${student.total_attempts} 題｜${student.accuracy}%`;
      list.appendChild(li);
    }
  } catch (_error) {
    // The student view does not need this section.
  }
}

async function ensurePyodide() {
  if (state.pyodide) return state.pyodide;
  if (state.pyodideLoading) return state.pyodideLoading;

  state.pyodideLoading = new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = "https://cdn.jsdelivr.net/pyodide/v0.26.4/full/pyodide.js";
    script.onload = async () => {
      try {
        const pyodide = await window.loadPyodide();
        state.pyodide = pyodide;
        resolve(pyodide);
      } catch (error) {
        reject(error);
      }
    };
    script.onerror = () => reject(new Error("Pyodide 載入失敗，請確認網路連線。"));
    document.head.appendChild(script);
  });
  return state.pyodideLoading;
}

async function runCode() {
  const output = $("code-output");
  output.textContent = "載入 Python 執行環境...";
  try {
    const pyodide = await ensurePyodide();
    const code = $("code-input").value;
    pyodide.runPython(`
import sys
from io import StringIO
sys.stdout = StringIO()
sys.stderr = StringIO()
`);
    let resultText = "";
    try {
      await pyodide.runPythonAsync(code);
      resultText = pyodide.runPython("sys.stdout.getvalue()");
      const errText = pyodide.runPython("sys.stderr.getvalue()");
      output.textContent = (resultText || "") + (errText ? `\\n${errText}` : "") || "程式執行完成，沒有輸出。";
    } catch (error) {
      output.textContent = String(error);
    }
    state.ranCode = true;
  } catch (error) {
    output.textContent = error.message || String(error);
  }
}

function bindEvents() {
  $("login-form").addEventListener("submit", login);
  $("logout-button").addEventListener("click", logout);
  $("submit-answer").addEventListener("click", submitAnswer);
  $("next-question").addEventListener("click", loadQuestion);
  $("run-code").addEventListener("click", runCode);
}

bindEvents();
loadMe();
