const PYODIDE_INDEX_URL = "https://cdn.jsdelivr.net/pyodide/v0.26.4/full/";

let pyodideRuntime = null;

self.addEventListener("message", async (event) => {
  const message = event.data || {};
  if (message.type !== "run" || !pyodideRuntime) return;

  const globals = pyodideRuntime.globals.get("dict")();
  let pythonError = "";
  try {
    const inputs = Array.isArray(message.inputs) ? message.inputs.map(String) : [];
    globals.set("__pet_inputs_json", JSON.stringify(inputs));
    await pyodideRuntime.runPythonAsync(`
import json
import sys
from io import StringIO

sys.stdout = StringIO()
sys.stderr = StringIO()
_pet_inputs = iter(json.loads(__pet_inputs_json))

def _pet_input(prompt=""):
    try:
        return next(_pet_inputs)
    except StopIteration:
        raise EOFError("請在輸入資料欄每行填入一筆資料，每行對應一次 input()。")

input = _pet_input
`, { globals });
    const evaluation = await pyodideRuntime.runPythonAsync(String(message.code || ""), {
      globals,
      filename: "student.py",
    });
    if (evaluation && typeof evaluation.destroy === "function") evaluation.destroy();
  } catch (error) {
    pythonError = String(error);
  }

  let output = "";
  let stderr = "";
  try {
    output = String(
      pyodideRuntime.runPython("import sys\nsys.stdout.getvalue()", { globals }) || "",
    );
    stderr = String(
      pyodideRuntime.runPython("import sys\nsys.stderr.getvalue()", { globals }) || "",
    );
  } catch (error) {
    pythonError = [pythonError, String(error)].filter(Boolean).join("\n");
  }
  globals.destroy();
  self.postMessage({
    type: "result",
    runId: message.runId,
    output,
    error: [stderr, pythonError].filter(Boolean).join("\n"),
  });
});

(async () => {
  try {
    self.importScripts(`${PYODIDE_INDEX_URL}pyodide.js`);
    pyodideRuntime = await self.loadPyodide({ indexURL: PYODIDE_INDEX_URL });
    self.postMessage({ type: "ready" });
  } catch (error) {
    self.postMessage({ type: "load-error", error: String(error) });
  }
})();
