from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LESSONS_PATH = ROOT / "content" / "lessons.json"
QUESTIONS_PATH = ROOT / "content" / "questions.json"


def main() -> int:
    lessons = json.loads(LESSONS_PATH.read_text(encoding="utf-8"))
    questions = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    question_ids = {question["id"] for question in questions}
    lesson_ids: set[str] = set()
    errors: list[str] = []

    required = {
        "id",
        "source_file",
        "unit",
        "title",
        "order",
        "concepts",
        "goals",
        "body",
        "common_mistakes",
        "checkpoint_question_ids",
    }

    for index, lesson in enumerate(lessons, start=1):
        missing = sorted(required - lesson.keys())
        if missing:
            errors.append(f"lesson #{index}: missing {', '.join(missing)}")
            continue

        lesson_id = lesson["id"]
        if lesson_id in lesson_ids:
            errors.append(f"{lesson_id}: duplicate id")
        lesson_ids.add(lesson_id)

        if not isinstance(lesson["order"], int):
            errors.append(f"{lesson_id}: order must be an integer")

        for key in ("concepts", "goals", "body", "common_mistakes", "checkpoint_question_ids"):
            if not isinstance(lesson[key], list):
                errors.append(f"{lesson_id}: {key} must be a list")

        if not lesson["concepts"]:
            errors.append(f"{lesson_id}: concepts must not be empty")

        if not lesson["goals"]:
            errors.append(f"{lesson_id}: goals must not be empty")

        if not lesson["body"]:
            errors.append(f"{lesson_id}: body must not be empty")

        for block_index, block in enumerate(lesson["body"], start=1):
            block_type = block.get("type")
            if block_type not in {"paragraph", "list", "code"}:
                errors.append(f"{lesson_id}: body block #{block_index} has unsupported type {block_type}")
            if block_type in {"paragraph", "code"} and not block.get("text") and not block.get("code"):
                errors.append(f"{lesson_id}: body block #{block_index} is missing text/code")
            if block_type == "list" and not block.get("items"):
                errors.append(f"{lesson_id}: body block #{block_index} list must have items")

        missing_questions = sorted(set(lesson["checkpoint_question_ids"]) - question_ids)
        if missing_questions:
            errors.append(f"{lesson_id}: checkpoint ids not found: {', '.join(missing_questions)}")

    if errors:
        print("Lesson checks failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    concept_count = len({concept for lesson in lessons for concept in lesson["concepts"]})
    checkpoint_count = sum(len(lesson["checkpoint_question_ids"]) for lesson in lessons)
    print(f"OK: {len(lessons)} lessons, {concept_count} concepts, {checkpoint_count} checkpoints")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
