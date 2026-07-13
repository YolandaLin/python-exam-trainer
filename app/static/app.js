const state = {
  token: localStorage.getItem("pet_token"),
  user: null,
  lessons: [],
  currentLesson: null,
  projects: [],
  currentProject: null,
  projectAttempts: 0,
  projectCanCheck: true,
  question: null,
  startedAt: null,
  ranCode: false,
  pyodide: null,
  pyodideLoading: null,
  review: {
    active: false,
    size: 20,
    answered: 0,
    correct: 0,
    status: null,
    sessionId: null,
  },
};

const $ = (id) => document.getElementById(id);

const CONCEPT_LABELS = {
  "programming-language": "程式語言",
  "machine-language": "機器語言",
  "compiler-interpreter": "編譯與直譯",
  "python-history": "Python 由來",
  "python-install": "Python 安裝",
  path: "PATH 路徑",
  "python-shell": "Python 互動模式",
  "builtin-functions": "內建函式",
  round: "round() 捨入",
  "object-oriented": "物件導向",
  "data-types": "資料型態",
  operators: "運算子",
  string: "字串",
  ascii: "ASCII",
  unicode: "Unicode",
  containers: "資料容器",
  list: "list 串列",
  tuple: "tuple 元組",
  dict: "dict 字典",
  set: "set 集合",
  "key-value": "key 與 value",
  "sort-sorted": "sort() 與 sorted()",
  "selection-structure": "條件判斷",
  "loop-structure": "迴圈",
  function: "函式",
  "builtin-function": "內建函式",
  "function-call": "函式呼叫",
  parameter: "參數",
  return: "return 回傳",
  scope: "變數作用域",
  class: "class 類別",
  object: "object 物件",
  method: "方法",
  inheritance: "繼承",
  module: "模組",
  package: "套件",
  import: "匯入",
  random: "random 隨機數",
  accumulator: "累加器",
  "append-extend": "append() 與 extend()",
  "args-kwargs": "*args 與 **kwargs",
  attribute: "物件屬性",
  bool: "布林值",
  break: "break 中斷迴圈",
  "class-methods": "類別方法",
  "class-variable": "類別變數",
  comment: "註解",
  "condition-order": "條件順序",
  "conditional-expression": "條件表達式",
  "dict-comprehension": "dict comprehension",
  dir: "dir() 查詢名稱",
  elif: "elif",
  else: "else",
  "error-reason": "錯誤原因",
  "f-string": "f-string 格式化",
  "find-index": "find() 與 index()",
  "floor-division": "整除 //",
  for: "for 迴圈",
  formatting: "字串格式化",
  def: "def 定義函式",
  "default-parameter": "預設參數",
  global: "global 全域變數",
  idle: "IDLE 編輯器",
  if: "if 條件判斷",
  "import-alias": "import 別名",
  indentation: "縮排",
  index: "索引",
  "infinite-loop": "無限迴圈",
  "init-file": "__init__.py",
  input: "input() 輸入",
  "instance-variable": "物件變數",
  iterable: "可迭代物件",
  "list-append": "list.append()",
  "list-comprehension": "list comprehension",
  "list-functions": "list 相關函式",
  "list-methods": "list 方法",
  "list-slice": "list 切片",
  loop: "迴圈",
  "loop-else": "迴圈 else",
  main: "主程式",
  "main-guard": "主程式保護區",
  "method-override": "方法覆寫",
  "method-resolution": "方法解析順序",
  "module-function": "模組函式",
  "multiple-inheritance": "多重繼承",
  "mutable-immutable": "可變與不可變",
  "name-variable": "__name__",
  "nested-if": "巢狀 if",
  "nested-list": "巢狀 list",
  "nested-loop": "巢狀迴圈",
  none: "None",
  ord: "ord()",
  "ord-chr": "ord() 與 chr()",
  pass: "pass",
  pip: "pip 套件工具",
  print: "print() 輸出",
  python: "Python",
  "python-editor": "Python 編輯器",
  "python-extension": ".py 副檔名",
  "python-file": "Python 程式檔",
  range: "range()",
  "return": "return 回傳",
  self: "self 物件本身",
  sep: "sep 分隔符號",
  "set-comprehension": "set comprehension",
  slice: "切片",
  split: "split() 切割",
  "standard-library": "標準函式庫",
  "string-index": "字串索引",
  "string-methods": "字串方法",
  "string-repeat": "字串重複",
  "string-slice": "字串切片",
  "third-party-package": "第三方套件",
  "tuple-list-conversion": "tuple 與 list 轉換",
  "type-conversion": "型態轉換",
  unpacking: "拆包",
  vscode: "VS Code",
  while: "while 迴圈",
  zip: "zip() 配對",
};

function conceptLabel(name) {
  return CONCEPT_LABELS[name] || String(name).replaceAll("-", " ");
}

function sourceLabel(sourceFile) {
  const lesson = state.lessons.find((item) => item.source_file === sourceFile);
  return lesson ? `${lesson.unit}｜${lesson.title}` : String(sourceFile).replace(/\.md$/, "");
}

function formatActivityTime(value) {
  if (!value) return "尚未答題";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString("zh-TW", { hour12: false });
}

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

function configurePythonHighlighting() {
  if (!window.Prism?.languages?.python) return;
  Prism.languages.insertBefore("python", "function", {
    "builtin-method": {
      pattern:
        /(\.)(?:append|capitalize|casefold|center|clear|copy|count|difference|discard|endswith|extend|find|format|fromkeys|get|index|insert|intersection|isalnum|isalpha|isascii|isdecimal|isdigit|isidentifier|islower|isnumeric|isprintable|isspace|istitle|isupper|items|join|keys|ljust|lower|lstrip|maketrans|partition|pop|popitem|remove|removeprefix|removesuffix|replace|reverse|rfind|rindex|rjust|rpartition|rsplit|rstrip|setdefault|sort|split|splitlines|startswith|strip|swapcase|symmetric_difference|title|translate|union|update|upper|values|zfill)(?=\s*\()/,
      lookbehind: true,
      alias: ["builtin", "builtin-method"],
    },
  });
}

function highlightPython(element) {
  if (!window.Prism) return;
  element.classList.add("language-python");
  Prism.highlightElement(element);
  element.querySelectorAll(".token.builtin").forEach((token) => {
    token.title = "Python 內建函式或預設方法";
  });
  element.querySelectorAll(".token.function:not(.builtin)").forEach((token) => {
    token.title = "程式中的函式名稱";
  });
}

function setRichText(element, value) {
  clear(element);
  const parts = String(value).split(
    /(`[^`]+`|\b[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*\([^()\n。；，]*\)|\b(?:def|class|return|if|elif|else|for|while|import|from|in|and|or|not|True|False|None)\b)/g,
  );
  for (const part of parts) {
    const isBackticked = part.startsWith("`") && part.endsWith("`") && part.length > 2;
    const isPythonFragment =
      /^[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*\([^()\n。；，]*\)$/.test(part) ||
      /^(?:def|class|return|if|elif|else|for|while|import|from|in|and|or|not|True|False|None)$/.test(part);
    if (isBackticked || isPythonFragment) {
      const code = document.createElement("code");
      code.className = "inline-code";
      code.textContent = isBackticked ? part.slice(1, -1) : part;
      element.appendChild(code);
      highlightPython(code);
    } else if (part) {
      element.appendChild(document.createTextNode(part));
    }
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
    await Promise.all([loadDashboard(), loadAdmin(), loadReviewStatus()]);
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

async function loadProjects() {
  const body = await api("/api/projects");
  state.projects = body.projects;
  renderProjects();
  return body;
}

function projectStatusLabel(status) {
  return { not_started: "未開始", in_progress: "進行中", completed: "已完成" }[status] || status;
}

function renderProjects() {
  const list = $("project-list");
  clear(list);
  for (const project of state.projects) {
    const card = document.createElement("article");
    card.className = `project-card ${project.status}`;
    const progress = project.tests_total
      ? `${project.tests_passed} / ${project.tests_total} 個測試通過`
      : "尚未測試";
    card.innerHTML = `
      <div class="project-card-meta"><span>Level ${project.level}</span><span>${project.estimated_minutes} 分鐘</span></div>
      <h3>${escapeHtml(project.title)}</h3>
      <p>${escapeHtml(project.description)}</p>
      <p class="project-progress">${escapeHtml(projectStatusLabel(project.status))}｜${escapeHtml(progress)}</p>
      <button type="button" class="project-open">${project.status === "not_started" ? "開始實作" : "繼續實作"}</button>
    `;
    card.querySelector(".project-open").addEventListener("click", () => openProject(project.id));
    list.appendChild(card);
  }
}

async function openProjects() {
  state.review.active = false;
  state.review.returningFromLesson = false;
  $("page-title").textContent = "實作區";
  $("lesson-panel").classList.add("hidden");
  $("question-panel").classList.add("hidden");
  $("review-summary-panel").classList.add("hidden");
  $("projects-panel").classList.remove("hidden");
  $("runner-panel").classList.add("hidden");
  $("projects-nav").classList.add("hidden");
  $("lessons-nav").classList.remove("hidden");
  $("review-nav").classList.add("hidden");
  $("project-list-view").classList.remove("hidden");
  $("project-workspace").classList.add("hidden");
  await loadProjects();
}

async function backToLessons() {
  state.review.returningFromLesson = false;
  $("projects-panel").classList.add("hidden");
  $("runner-panel").classList.remove("hidden");
  $("projects-nav").classList.remove("hidden");
  $("lessons-nav").classList.add("hidden");
  $("review-nav").classList.add("hidden");
  $("page-title").textContent = "今日課程";
  const lessonInfo = await loadLessons();
  if (lessonInfo.next_lesson) await loadLesson(lessonInfo.next_lesson.id);
}

async function openProject(projectId) {
  const body = await api(`/api/projects/${encodeURIComponent(projectId)}/start`, { method: "POST" });
  state.currentProject = body.project;
  state.projectAttempts = 0;
  state.projectCanCheck = false;
  $("project-list-view").classList.add("hidden");
  $("project-workspace").classList.remove("hidden");
  renderProjectWorkspace(state.currentProject);
}

function renderProjectWorkspace(project) {
  const allTestsPassed = project.tests_total > 0 && project.tests_passed >= project.tests_total;
  $("project-level").textContent = `Level ${project.level}`;
  $("project-time").textContent = `預計 ${project.estimated_minutes} 分鐘`;
  $("project-title").textContent = project.title;
  $("project-description").textContent = project.description;
  $("project-example-explanation").textContent = project.example.explanation;
  $("project-example-code").textContent = project.example.code;
  highlightPython($("project-example-code"));
  $("project-example-output").textContent = project.example.output;
  $("project-instructions").textContent = project.instructions;
  $("project-hint").textContent = project.hint;
  $("project-guide-text").textContent = "步驟 1：依照題目，在空白區輸入自己的程式，再按「試跑我的程式」。";
  $("project-code").value = "";
  $("project-code").readOnly = false;
  const needsInput = project.tests.some((test) => test.inputs.length > 0);
  $("project-input-panel").classList.toggle("hidden", !needsInput);
  $("project-input").value = "";
  $("project-output").textContent = "尚未執行";
  $("project-run").textContent = "試跑我的程式";
  $("project-test").textContent = "檢查答案";
  $("project-test").classList.toggle("hidden", !state.projectCanCheck);
  $("project-complete").textContent = project.status === "completed" ? "已完成任務" : "完成任務";
  $("project-complete").classList.toggle("hidden", !allTestsPassed);
  $("project-complete").disabled = project.status === "completed";
  clear($("project-tests"));
}

function projectInputs() {
  return $("project-input").value.split(/\r?\n/).filter((value) => value.length > 0);
}

async function executeProjectCode(code, inputs) {
  const pyodide = await ensurePyodide();
  const encodedInputs = JSON.stringify(inputs);
  pyodide.runPython(`
import sys
import builtins
from io import StringIO
sys.stdout = StringIO()
sys.stderr = StringIO()
_project_inputs = iter(${encodedInputs})
def _project_input(prompt=""):
    try:
        return next(_project_inputs)
    except StopIteration:
        raise EOFError("請在「輸入資料」框填入資料，每行對應一次 input()。")
builtins.input = _project_input
`);
  try {
    await pyodide.runPythonAsync(code);
    const output = pyodide.runPython("sys.stdout.getvalue()");
    const error = pyodide.runPython("sys.stderr.getvalue()");
    return { output: output || "", error: error || "" };
  } catch (error) {
    return { output: "", error: String(error) };
  }
}

function normalizeProjectOutput(value) {
  return String(value || "").replaceAll("\r\n", "\n").trim();
}

function explainPythonError(errorText) {
  const text = String(errorText || "").replace(/^PythonError:\s*/i, "").trim();
  if (!text) return "程式執行時發生錯誤。";
  let hint = "";
  if (/SyntaxError|IndentationError/i.test(text)) {
    hint = "提示：程式語法有問題。要列印文字時，請把文字放在引號裡，例如：print(\"姓名：小明\")。";
  } else if (/NameError/i.test(text)) {
    hint = "提示：Python 找不到這個名稱。請檢查變數名稱是否打對，或確認文字是否有用引號包住。";
  } else if (/TypeError/i.test(text)) {
    hint = "提示：資料的種類不符合這個運算。文字和數字運算前，請先確認型別是否正確。";
  } else if (/ValueError/i.test(text)) {
    hint = "提示：輸入的內容格式不正確。例如 int() 只能把數字文字轉成整數，請檢查輸入資料。";
  } else if (/StopIteration|輸入欄填入資料|EOFError/i.test(text)) {
    hint = "提示：程式需要輸入資料，請在「輸入資料」框每行填入一筆資料，再重新執行。";
  }
  return hint ? `${hint}\n\n錯誤詳細資料：\n${text}` : `錯誤詳細資料：\n${text}`;
}

async function runProjectCode() {
  if (!state.currentProject) return;
  if (!$("project-code").value.trim()) {
    $("project-output").textContent = "請先在程式碼區輸入自己的程式。";
    return;
  }
  if (/\binput\s*\(/.test($("project-code").value) && projectInputs().length === 0) {
    $("project-output").textContent = "提示：這段程式需要輸入資料，請先在「輸入資料」框輸入內容，每行填一筆資料。";
    $("project-input").focus();
    return;
  }
  $("project-run").disabled = true;
  $("project-output").textContent = "載入 Python 執行環境...";
  try {
    const result = await executeProjectCode($("project-code").value, projectInputs());
    $("project-output").textContent = result.output + (result.error ? `\n${explainPythonError(result.error)}` : "") || "程式執行完成，沒有輸出。";
    state.projectAttempts += 1;
    const activity = await api(`/api/projects/${encodeURIComponent(state.currentProject.id)}/activity`, {
      method: "POST",
      body: JSON.stringify({
        attempts: 1,
        tests_passed: state.currentProject.tests_passed,
        tests_total: state.currentProject.tests.length,
      }),
    });
    state.currentProject = activity.project;
    if (!result.error) {
      state.projectCanCheck = true;
      $("project-guide-text").textContent = "步驟 2：試跑成功，現在按「檢查答案」，確認執行結果是否符合題目。";
      $("project-test").classList.remove("hidden");
    }
  } catch (error) {
    $("project-output").textContent = explainPythonError(error.message || String(error));
  } finally {
    $("project-run").disabled = false;
  }
}

async function testProjectCode() {
  if (!state.currentProject) return;
  $("project-test").disabled = true;
  const results = [];
  try {
    for (const test of state.currentProject.tests) {
      const result = await executeProjectCode($("project-code").value, test.inputs);
      const actual = normalizeProjectOutput(result.error ? `錯誤：${result.error}` : result.output);
      results.push({ passed: actual === normalizeProjectOutput(test.expected), actual });
    }
    const passed = results.filter((result) => result.passed).length;
    clear($("project-tests"));
    results.forEach((result, index) => {
      const item = document.createElement("li");
      item.className = result.passed ? "passed" : "failed";
      item.textContent = `測試 ${index + 1}：${result.passed ? "通過" : `未通過（得到：${result.actual || "沒有輸出"}）`}`;
      $("project-tests").appendChild(item);
    });
    $("project-output").textContent = `測試完成：${passed} / ${results.length} 通過`;
    state.projectAttempts += 1;
    const activity = await api(`/api/projects/${encodeURIComponent(state.currentProject.id)}/activity`, {
      method: "POST",
      body: JSON.stringify({ attempts: 1, tests_passed: passed, tests_total: results.length }),
    });
    state.currentProject = activity.project;
    const allTestsPassed = passed === results.length;
    $("project-complete").classList.toggle("hidden", !allTestsPassed);
    $("project-complete").disabled = !allTestsPassed || state.currentProject.status === "completed";
  } catch (error) {
    $("project-output").textContent = error.message || String(error);
  } finally {
    $("project-test").disabled = false;
  }
}

async function completeProject() {
  if (!state.currentProject) return;
  const passed = state.currentProject.tests.length;
  const body = await api(`/api/projects/${encodeURIComponent(state.currentProject.id)}/complete`, {
    method: "POST",
    body: JSON.stringify({ attempts: 0, tests_passed: passed, tests_total: passed }),
  });
  state.currentProject = body.project;
  renderProjectWorkspace(state.currentProject);
  await loadProjects();
  $("project-list-view").classList.remove("hidden");
  $("project-workspace").classList.add("hidden");
}

async function loadLesson(lessonId) {
  const returningFromReview = state.review.active;
  state.review.active = false;
  state.review.returningFromLesson = returningFromReview;
  $("page-title").textContent = "今日課程";
  $("review-summary-panel").classList.add("hidden");
  $("lesson-panel").classList.remove("hidden");
  $("question-panel").classList.add("hidden");
  $("projects-nav").classList.toggle("hidden", returningFromReview);
  $("lessons-nav").classList.add("hidden");
  $("review-nav").classList.toggle("hidden", !returningFromReview);
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
    setRichText(item, value);
    target.appendChild(item);
  }
}

function renderLessonBody(blocks) {
  const container = $("lesson-body");
  clear(container);
  for (const block of blocks) {
    if (block.type === "paragraph") {
      const paragraph = document.createElement("p");
      setRichText(paragraph, block.text);
      container.appendChild(paragraph);
    }
    if (block.type === "list") {
      const list = document.createElement("ul");
      list.className = "content-list";
      for (const value of block.items) {
        const item = document.createElement("li");
        setRichText(item, value);
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
      highlightPython(pre);
      const button = document.createElement("button");
      button.type = "button";
      button.className = "secondary";
      button.textContent = "放到執行區";
      button.addEventListener("click", () => {
        $("code-input").value = block.code;
        syncRunnerInputVisibility();
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
      highlightPython(pre);
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
        <span><strong>${escapeHtml(option.id)}.</strong> <span class="option-text"></span></span>
      `;
      setRichText(label.querySelector(".option-text"), option.text);
      options.appendChild(label);
    }
    wrapper.appendChild(options);
    container.appendChild(wrapper);
  }
}

function renderLesson(lesson) {
  $("lesson-unit").textContent = lesson.unit;
  $("lesson-source").textContent = "";
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
  await Promise.all([loadLessons(), loadDashboard(), loadReviewStatus()]);
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
  $("question-source").textContent = sourceLabel(question.source_file).split("｜")[0];
  $("question-difficulty").textContent = `難度 ${question.difficulty}`;
  $("question-lesson").textContent = state.currentLesson ? state.currentLesson.title : "";
  $("review-progress").classList.toggle("hidden", !state.review.active);
  if (state.review.active) {
    $("review-progress").textContent = `總複習 ${state.review.answered + 1} / ${state.review.size}`;
    $("question-lesson").textContent = "跨章複習";
  }
  $("question-stem").textContent = question.stem;
  $("question-code").textContent = question.code || "";
  $("question-code").classList.toggle("hidden", !question.code);
  if (question.code) highlightPython($("question-code"));
  $("code-input").value = question.code || "print(\"Hello Python\")";
  syncRunnerInputVisibility();
  $("code-output").textContent = "尚未執行";
  $("submit-answer").disabled = false;
  $("next-question").disabled = true;
  $("next-question").textContent = "下一題";

  const form = $("answer-form");
  clear(form);
  const inputType = question.type === "multiple_choice" ? "checkbox" : "radio";
  for (const option of question.options) {
    const label = document.createElement("label");
    label.className = "option";
    label.innerHTML = `
      <input type="${inputType}" name="answer" value="${escapeHtml(option.id)}" />
      <span><strong>${escapeHtml(option.id)}.</strong> <span class="option-text"></span></span>
    `;
    setRichText(label.querySelector(".option-text"), option.text);
    form.appendChild(label);
  }
}

async function loadQuestion(lessonId = state.currentLesson?.id) {
  const suffix = state.review.active
    ? "?mode=review"
    : lessonId
      ? `?lesson_id=${encodeURIComponent(lessonId)}`
      : "";
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
      mode: state.review.active ? "review" : "lesson",
      review_session_id: state.review.active ? state.review.sessionId : null,
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
    <p id="answer-explanation"></p>
    <p><strong>常見錯因：</strong><span id="answer-common-mistake"></span></p>
    <p><strong>熟練度：</strong>${escapeHtml(updates || "尚無更新")}</p>
    ${renderReviewLessons(result.review_lessons)}
  `;
  setRichText($("answer-explanation"), result.explanation);
  setRichText($("answer-common-mistake"), result.common_mistake);
  bindReviewButtons();
  $("submit-answer").disabled = true;
  $("next-question").disabled = false;
  if (state.review.active) {
    state.review.answered += 1;
    if (result.is_correct) state.review.correct += 1;
    if (state.review.answered >= state.review.size) {
      $("next-question").textContent = "查看本輪結果";
    }
  }
  await Promise.all([loadDashboard(), loadReviewStatus()]);
}

async function loadReviewStatus() {
  const body = await api("/api/review/status");
  state.review.status = body;
  const remaining = Math.max(0, body.total_lessons - body.completed_lessons);
  $("start-review").disabled = !body.unlocked;
  $("start-review").textContent = state.review.active ? "重新開始本輪" : "開始總複習";
  const session = body.review_session;
  $("review-status-text").textContent = body.unlocked
    ? session
      ? `已解鎖。本輪已答 ${session.answered_count} / ${state.review.size} 題（答題率 ${session.answer_rate}%）。`
      : `已解鎖。系統會提高 ${body.wrong_questions} 題錯題與薄弱觀念的出現率。`
    : `尚有 ${remaining} 節課程未完成。`;
  return body;
}

async function startReview() {
  if (!state.review.status?.unlocked) return;
  const started = await api("/api/review/start", { method: "POST" });
  state.review.sessionId = started.session.id;
  state.review.active = true;
  state.review.answered = 0;
  state.review.correct = 0;
  state.review.returningFromLesson = false;
  state.currentLesson = null;
  $("page-title").textContent = "總複習";
  $("lesson-panel").classList.add("hidden");
  $("review-summary-panel").classList.add("hidden");
  $("question-panel").classList.remove("hidden");
  $("projects-nav").classList.add("hidden");
  $("lessons-nav").classList.remove("hidden");
  $("review-nav").classList.add("hidden");
  await loadQuestion(null);
  await loadReviewStatus();
}

async function finishReview() {
  const body = await api("/api/review/summary");
  state.review.active = false;
  $("lessons-nav").classList.add("hidden");
  $("question-panel").classList.add("hidden");
  $("review-summary-panel").classList.remove("hidden");
  $("review-progress").classList.add("hidden");
  $("review-round-correct").textContent = `${state.review.correct} / ${state.review.size}`;
  $("review-round-accuracy").textContent = `${Math.round((state.review.correct / state.review.size) * 100)}%`;
  const list = $("review-high-error");
  clear(list);
  if (body.high_error_questions.length === 0) {
    const item = document.createElement("li");
    item.textContent = "目前沒有錯題紀錄";
    list.appendChild(item);
  } else {
    for (const question of body.high_error_questions) {
      const item = document.createElement("li");
      item.textContent = `${sourceLabel(question.source_file)}｜錯誤指標 ${question.error_rate}%｜${question.stem}`;
      list.appendChild(item);
    }
  }
  await loadReviewStatus();
}

async function leaveReview() {
  state.review.active = false;
  state.review.returningFromLesson = false;
  $("projects-nav").classList.remove("hidden");
  $("lessons-nav").classList.add("hidden");
  $("review-nav").classList.add("hidden");
  $("page-title").textContent = "今日課程";
  $("review-summary-panel").classList.add("hidden");
  $("lesson-panel").classList.remove("hidden");
  const lessonInfo = await loadLessons();
  if (lessonInfo.next_lesson) await loadLesson(lessonInfo.next_lesson.id);
}

function returnToReview() {
  if (!state.review.returningFromLesson || !state.question) return;
  state.review.active = true;
  state.review.returningFromLesson = false;
  $("page-title").textContent = "總複習";
  $("lesson-panel").classList.add("hidden");
  $("review-summary-panel").classList.add("hidden");
  $("question-panel").classList.remove("hidden");
  $("projects-nav").classList.add("hidden");
  $("lessons-nav").classList.remove("hidden");
  $("review-nav").classList.add("hidden");
  $("review-progress").classList.remove("hidden");
}

async function nextQuestion() {
  if (state.review.active && state.review.answered >= state.review.size) {
    await finishReview();
    return;
  }
  await loadQuestion();
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
    text.textContent = `${conceptLabel(concept.name)}｜${concept.mastery_score} 分｜連錯 ${concept.wrong_streak}`;
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
      const reviewText = student.review_status === "not_started"
        ? "總複習：尚未開始"
        : student.review_status === "completed"
          ? `總複習：已完成 ${student.review_answered} / 20 題（答題率 ${student.review_answer_rate}%）｜最近 ${formatActivityTime(student.review_last_answered_at)}`
          : `總複習：進行中 ${student.review_answered} / 20 題（答題率 ${student.review_answer_rate}%）｜最近 ${formatActivityTime(student.review_last_answered_at)}`;
      const projectText = `實作：${student.project_completed} / ${student.project_total} 完成`;
      li.textContent = `${student.display_name}｜一般答題 ${student.total_attempts} 題｜正確率 ${student.accuracy}%｜${reviewText}｜${projectText}`;
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

function runnerInputs() {
  return $("code-input-values").value.split(/\r?\n/).filter((value) => value.length > 0);
}

function syncRunnerInputVisibility() {
  $("runner-input-panel").classList.toggle("hidden", !/\binput\s*\(/.test($("code-input").value));
}

async function runCode() {
  const output = $("code-output");
  output.textContent = "載入 Python 執行環境...";
  try {
    const pyodide = await ensurePyodide();
    const code = $("code-input").value;
    syncRunnerInputVisibility();
    if (/\binput\s*\(/.test(code) && runnerInputs().length === 0) {
      output.textContent = "提示：這段程式需要輸入資料，請先在「輸入資料」框輸入內容，每行填一筆資料。";
      $("code-input-values").focus();
      return;
    }
    const encodedInputs = JSON.stringify(runnerInputs());
    pyodide.runPython(`
import sys
import builtins
from io import StringIO
sys.stdout = StringIO()
sys.stderr = StringIO()
_runner_inputs = iter(${encodedInputs})
def _runner_input(prompt=""):
    try:
        return next(_runner_inputs)
    except StopIteration:
        raise EOFError("請在執行輸入欄填入資料，每行對應一次 input()。")
builtins.input = _runner_input
`);
    try {
      await pyodide.runPythonAsync(code);
      const resultText = pyodide.runPython("sys.stdout.getvalue()");
      const errText = pyodide.runPython("sys.stderr.getvalue()");
      output.textContent = (resultText || "") + (errText ? `\n${errText}` : "") || "程式執行完成，沒有輸出。";
    } catch (error) {
      output.textContent = explainPythonError(error);
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
  $("next-question").addEventListener("click", nextQuestion);
  $("start-review").addEventListener("click", startReview);
  $("restart-review").addEventListener("click", startReview);
  $("leave-review").addEventListener("click", leaveReview);
  $("run-code").addEventListener("click", runCode);
  $("code-input").addEventListener("input", syncRunnerInputVisibility);
  $("projects-nav").addEventListener("click", openProjects);
  $("lessons-nav").addEventListener("click", backToLessons);
  $("review-nav").addEventListener("click", returnToReview);
  $("project-back").addEventListener("click", async () => {
    $("project-list-view").classList.remove("hidden");
    $("project-workspace").classList.add("hidden");
    await loadProjects();
  });
  $("project-run").addEventListener("click", runProjectCode);
  $("project-test").addEventListener("click", testProjectCode);
  $("project-complete").addEventListener("click", completeProject);
}

configurePythonHighlighting();
bindEvents();
syncRunnerInputVisibility();
loadMe();
