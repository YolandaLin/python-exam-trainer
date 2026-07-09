const state = {
  token: localStorage.getItem("pet_token"),
  user: null,
  lessons: [],
  currentLesson: null,
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

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function clear(node) {
  while (node.firstChild) {
    node.removeChild(node.firstChild);
  }
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
    const lessonInfo = await loadLessons();
    if (lessonInfo.next_lesson) {
      await loadLesson(lessonInfo.next_lesson.id);
    }
    await Promise.all([loadDashboard(), loadAdmin()]);
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
  state.currentLesson = null;
  state.question = null;
  show("login");
}

async function loadLessons() {
  const body = await api("/api/lessons");
  state.lessons = body.lessons;
  renderLessonProgress();
  renderLessonList();
  return body;
}

async function loadLesson(lessonId) {
  $("question-panel").classList.add("hidden");
  const body = await api(`/api/lessons/${lessonId}/start`, { method: "POST" });
  state.currentLesson = body.lesson;
  renderLesson(state.currentLesson);
  await loadLessons();
}

function renderLessonProgress() {
  const completed = state.lessons.filter((lesson) => lesson.status === "completed").length;
  $("lesson-progress").textContent = `${completed} / ${state.lessons.length} 節完成`;
}

function renderLessonList() {
  const list = $("lesson-list");
  clear(list);
  for (const lesson of state.lessons) {
    const item = document.createElement("li");
    const button = document.createElement("button");
    button.type = "button";
    button.className = "lesson-link";
    if (state.currentLesson?.id === lesson.id) button.classList.add("current");
    if (lesson.status === "completed") button.classList.add("completed");
    button.dataset.lessonId = lesson.id;
    button.innerHTML = `<span>${escapeHtml(lesson.unit)}</span><strong>${escapeHtml(lesson.title)}</strong>`;
    button.addEventListener("click", () => loadLesson(lesson.id));
    item.appendChild(button);
    list.appendChild(item);
  }
}

function renderList(target, values) {
  clear(target);
  for (const value of values) {
    const item = document.createElement("li");
    item.textContent = value;
    target.appendChild(item);
  }
}

function renderLessonBody(blocks) {
  const container = $("lesson-body");
  clear(container);
  for (const block of blocks) {
    if (block.type === "paragraph") {
      const paragraph = document.createElement("p");
      paragraph.textContent = block.text;
      container.appendChild(paragraph);
    }
    if (block.type === "list") {
      const list = document.createElement("ul");
      list.className = "content-list";
      for (const value of block.items) {
        const item = document.createElement("li");
        item.textContent = value;
        list.appendChild(item);
      }
      container.appendChild(list);
    }
    if (block.type === "code") {
      const wrapper = document.createElement("div");
      wrapper.className = "lesson-code";
      const pre = document.createElement("pre");
      pre.className = "code-block";
      pre.textContent = block.code;
      const button = document.createElement("button");
      button.type = "button";
      button.className = "secondary";
      button.textContent = "放到執行區";
      button.addEventListener("click", () => {
        $("code-input").value = block.code;
        $("code-output").textContent = "尚未執行";
      });
      wrapper.append(pre, button);
      container.appendChild(wrapper);
    }
  }
}

function renderCheckpoints(questions) {
  const panel = $("checkpoint-panel");
  const container = $("checkpoint-questions");
  clear(container);
  $("checkpoint-result").textContent = "";

  if (!questions || questions.length === 0) {
    panel.classList.add("hidden");
    return;
  }

  panel.classList.remove("hidden");
  for (const question of questions) {
    const wrapper = document.createElement("section");
    wrapper.className = "checkpoint-question";
    wrapper.dataset.questionId = question.id;

    const title = document.createElement("h4");
    title.textContent = question.stem;
    wrapper.appendChild(title);

    if (question.code) {
      const pre = document.createElement("pre");
      pre.className = "code-block";
      pre.textContent = question.code;
      wrapper.appendChild(pre);
    }

    const inputType = question.type === "multiple_choice" ? "checkbox" : "radio";
    const options = document.createElement("div");
    options.className = "options compact";
    for (const option of question.options) {
      const label = document.createElement("label");
      label.className = "option";
      label.innerHTML = `
        <input type="${inputType}" name="checkpoint-${escapeHtml(question.id)}" value="${escapeHtml(option.id)}" />
        <span><strong>${escapeHtml(option.id)}.</strong> ${escapeHtml(option.text)}</span>
      `;
      options.appendChild(label);
    }
    wrapper.appendChild(options);
    container.appendChild(wrapper);
  }
}

function renderLesson(lesson) {
  $("lesson-unit").textContent = lesson.unit;
  $("lesson-source").textContent = lesson.source_file;
  $("lesson-status").textContent = lesson.status === "completed" ? "已完成" : "閱讀中";
  $("lesson-title").textContent = lesson.title;
  renderList($("lesson-goals"), lesson.goals || []);
  renderLessonBody(lesson.body || []);
  renderList($("lesson-mistakes"), lesson.common_mistakes || []);
  renderCheckpoints(lesson.checkpoint_questions || []);
  $("complete-lesson").textContent = lesson.status === "completed" ? "已完成課程" : "送出小檢查並完成";
  $("complete-lesson").disabled = lesson.status === "completed";
  $("practice-lesson").disabled = false;
}

function selectedValues(name) {
  return [...document.querySelectorAll(`input[name="${CSS.escape(name)}"]:checked`)].map((input) => input.value);
}

async function completeCurrentLesson() {
  if (!state.currentLesson) return null;
  const questions = state.currentLesson.checkpoint_questions || [];
  let correct = 0;

  if (state.currentLesson.status !== "completed") {
    for (const question of questions) {
      const selected = selectedValues(`checkpoint-${question.id}`);
      if (selected.length === 0) {
        $("checkpoint-result").textContent = "請先完成所有課後小檢查。";
        return null;
      }
      const result = await api("/api/attempts", {
        method: "POST",
        body: JSON.stringify({
          question_id: question.id,
          selected_answer: selected,
          used_hint: false,
          ran_code: state.ranCode,
          elapsed_seconds: 0,
        }),
      });
      if (result.is_correct) correct += 1;
    }
  } else {
    correct = state.currentLesson.checkpoint_correct_count || 0;
  }

  const body = await api(`/api/lessons/${state.currentLesson.id}/complete`, {
    method: "POST",
    body: JSON.stringify({
      checkpoint_correct_count: correct,
      checkpoint_total_count: questions.length,
    }),
  });
  state.currentLesson = { ...state.currentLesson, ...body.lesson, checkpoint_questions: questions };
  renderLesson(state.currentLesson);
  $("checkpoint-result").textContent = questions.length
    ? `小檢查 ${correct} / ${questions.length} 題答對，已完成本節課。`
    : "已完成本節課。";
  await Promise.all([loadLessons(), loadDashboard()]);
  return state.currentLesson;
}

async function startLessonPractice() {
  if (!state.currentLesson) return;
  const completed = state.currentLesson.status === "completed" ? state.currentLesson : await completeCurrentLesson();
  if (!completed) return;
  await loadQuestion(completed.id);
}

function renderQuestion(question) {
  state.question = question;
  state.startedAt = Date.now();
  state.ranCode = false;
  $("question-panel").classList.remove("hidden");
  $("feedback").className = "feedback hidden";
  $("feedback").textContent = "";
  $("question-source").textContent = question.source_file;
  $("question-difficulty").textContent = `難度 ${question.difficulty}`;
  $("question-lesson").textContent = state.currentLesson ? state.currentLesson.title : "";
  $("question-stem").textContent = question.stem;
  $("question-code").textContent = question.code || "";
  $("question-code").classList.toggle("hidden", !question.code);
  $("code-input").value = question.code || "print(\"Hello Python\")";
  $("code-output").textContent = "尚未執行";

  const form = $("answer-form");
  clear(form);
  const inputType = question.type === "multiple_choice" ? "checkbox" : "radio";
  for (const option of question.options) {
    const label = document.createElement("label");
    label.className = "option";
    label.innerHTML = `
      <input type="${inputType}" name="answer" value="${escapeHtml(option.id)}" />
      <span><strong>${escapeHtml(option.id)}.</strong> ${escapeHtml(option.text)}</span>
    `;
    form.appendChild(label);
  }
}

async function loadQuestion(lessonId = state.currentLesson?.id) {
  const suffix = lessonId ? `?lesson_id=${encodeURIComponent(lessonId)}` : "";
  const body = await api(`/api/next-question${suffix}`);
  renderQuestion(body.question);
}

function selectedAnswers() {
  return [...document.querySelectorAll("input[name='answer']:checked")].map((input) => input.value);
}

function renderReviewLessons(lessons) {
  if (!lessons || lessons.length === 0) return "";
  return `
    <div class="review-lessons">
      <strong>建議重讀：</strong>
      ${lessons
        .map(
          (lesson) =>
            `<button type="button" class="inline-link review-lesson" data-lesson-id="${escapeHtml(lesson.id)}">${escapeHtml(
              lesson.unit,
            )} ${escapeHtml(lesson.title)}</button>`,
        )
        .join("")}
    </div>
  `;
}

function bindReviewButtons() {
  document.querySelectorAll(".review-lesson").forEach((button) => {
    button.addEventListener("click", () => loadLesson(button.dataset.lessonId));
  });
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
    <p>正確答案：${escapeHtml(answerText)}</p>
    <p>${escapeHtml(result.explanation)}</p>
    <p><strong>常見錯因：</strong>${escapeHtml(result.common_mistake)}</p>
    <p><strong>熟練度：</strong>${escapeHtml(updates || "尚無更新")}</p>
    ${renderReviewLessons(result.review_lessons)}
  `;
  bindReviewButtons();
  await loadDashboard();
}

async function loadDashboard() {
  const body = await api("/api/dashboard");
  $("total-attempts").textContent = body.total_attempts;
  $("accuracy").textContent = `${body.accuracy}%`;
  const list = $("weak-concepts");
  clear(list);
  if (body.weak_concepts.length === 0) {
    const item = document.createElement("li");
    item.textContent = "目前尚無弱點資料";
    list.appendChild(item);
    return;
  }
  for (const concept of body.weak_concepts) {
    const li = document.createElement("li");
    const text = document.createElement("span");
    text.textContent = `${concept.name}｜${concept.mastery_score} 分｜連錯 ${concept.wrong_streak}`;
    li.appendChild(text);
    if (concept.review_lesson) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "inline-link";
      button.textContent = `重讀 ${concept.review_lesson.title}`;
      button.addEventListener("click", () => loadLesson(concept.review_lesson.id));
      li.appendChild(button);
    }
    list.appendChild(li);
  }
}

async function loadAdmin() {
  if (!state.user || state.user.role !== "admin") return;
  try {
    const body = await api("/api/admin/students");
    const list = $("students");
    clear(list);
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
    try {
      await pyodide.runPythonAsync(code);
      const resultText = pyodide.runPython("sys.stdout.getvalue()");
      const errText = pyodide.runPython("sys.stderr.getvalue()");
      output.textContent = (resultText || "") + (errText ? `\n${errText}` : "") || "程式執行完成，沒有輸出。";
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
  $("complete-lesson").addEventListener("click", completeCurrentLesson);
  $("practice-lesson").addEventListener("click", startLessonPractice);
  $("submit-answer").addEventListener("click", submitAnswer);
  $("next-question").addEventListener("click", () => loadQuestion());
  $("run-code").addEventListener("click", runCode);
}

bindEvents();
loadMe();
