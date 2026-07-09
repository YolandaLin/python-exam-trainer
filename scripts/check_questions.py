from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_questions() -> list[dict]:
    questions: list[dict] = []
    for path in sorted((ROOT / "content").glob("questions*.json")):
        questions.extend(json.loads(path.read_text(encoding="utf-8")))
    return questions


def run_output(code: str) -> str:
    stream = io.StringIO()
    with contextlib.redirect_stdout(stream):
        exec(code, {})
    output = stream.getvalue()
    if output.endswith("\n"):
        output = output[:-1]
    return output


def main() -> int:
    questions = load_questions()
    ids: set[str] = set()
    errors: list[str] = []

    required = {
        "id",
        "source_file",
        "type",
        "difficulty",
        "concepts",
        "stem",
        "options",
        "answer",
        "explanation",
        "common_mistake",
    }

    for index, question in enumerate(questions, start=1):
        missing = sorted(required - question.keys())
        if missing:
            errors.append(f"question #{index}: missing {', '.join(missing)}")
            continue

        qid = question["id"]
        if qid in ids:
            errors.append(f"{qid}: duplicate id")
        ids.add(qid)

        if question["type"] not in {"single_choice", "multiple_choice", "output_prediction", "error_reason"}:
            errors.append(f"{qid}: unsupported type {question['type']}")

        if not isinstance(question["difficulty"], int) or not 1 <= question["difficulty"] <= 5:
            errors.append(f"{qid}: difficulty must be an integer from 1 to 5")

        options = question["options"]
        if not isinstance(options, list) or len(options) < 2:
            errors.append(f"{qid}: options must contain at least two choices")
            continue

        option_ids = {option.get("id") for option in options}
        answers = set(question["answer"])
        if not answers <= option_ids:
            errors.append(f"{qid}: answer contains ids not present in options")

        if question["type"] == "output_prediction" and question.get("code") and "input(" not in question["code"]:
            option_text = {option["id"]: option["text"] for option in options}
            expected_outputs = [option_text[answer] for answer in question["answer"]]
            try:
                actual_output = run_output(question["code"])
            except Exception as exc:  # noqa: BLE001 - invalid quiz snippets should be reported.
                errors.append(f"{qid}: output_prediction code raised {type(exc).__name__}: {exc}")
            else:
                if actual_output not in expected_outputs:
                    errors.append(
                        f"{qid}: output {actual_output!r} does not match answer option(s) {expected_outputs!r}"
                    )

        if question["type"] == "single_choice" and len(answers) != 1:
            errors.append(f"{qid}: single_choice must have exactly one answer")

        if not question["concepts"]:
            errors.append(f"{qid}: concepts must not be empty")

    by_source: dict[str, int] = {}
    for question in questions:
        source_file = question.get("source_file")
        if source_file and source_file[:2] in {"01", "02", "03", "04"}:
            by_source[source_file] = by_source.get(source_file, 0) + 1

    sparse_sources = {source: count for source, count in by_source.items() if count < 3}
    for source, count in sorted(sparse_sources.items()):
        errors.append(f"{source}: expected at least 3 questions, found {count}")

    if errors:
        print("Question checks failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    concept_count = len({concept for question in questions for concept in question["concepts"]})
    print(f"OK: {len(questions)} questions, {concept_count} concepts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
