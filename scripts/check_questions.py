from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
QUESTIONS_PATH = ROOT / "content" / "questions.json"


def main() -> int:
    questions = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
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

        if question["type"] == "single_choice" and len(answers) != 1:
            errors.append(f"{qid}: single_choice must have exactly one answer")

        if not question["concepts"]:
            errors.append(f"{qid}: concepts must not be empty")

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
