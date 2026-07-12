from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LESSONS_PATH = ROOT / "content" / "lessons.json"
MISCONCEPTION_QUESTIONS_PATH = ROOT / "content" / "misconception_questions.json"


def load_questions() -> list[dict]:
    questions: list[dict] = []
    for path in sorted((ROOT / "content").glob("questions*.json")):
        questions.extend(json.loads(path.read_text(encoding="utf-8")))
    return questions


def main() -> int:
    lessons = json.loads(LESSONS_PATH.read_text(encoding="utf-8"))
    misconception_mappings = json.loads(MISCONCEPTION_QUESTIONS_PATH.read_text(encoding="utf-8"))
    questions = load_questions()
    question_ids = {question["id"] for question in questions}
    questions_by_id = {question["id"]: question for question in questions}
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

        body_text_parts: list[str] = []
        body_types: set[str] = set()
        for block in lesson["body"]:
            body_types.add(block.get("type", ""))
            if block.get("text"):
                body_text_parts.append(block["text"])
            if block.get("code"):
                body_text_parts.append(block["code"])
            body_text_parts.extend(block.get("items", []))
        body_text = "\n".join(body_text_parts)
        if len(body_text) < 350:
            errors.append(f"{lesson_id}: lesson explanation is too short for beginner teaching")
        if "生活例子" not in body_text:
            errors.append(f"{lesson_id}: lesson must include a life example")
        if "code" not in body_types:
            errors.append(f"{lesson_id}: lesson must include at least one runnable code example")

        missing_questions = sorted(set(lesson["checkpoint_question_ids"]) - question_ids)
        if missing_questions:
            errors.append(f"{lesson_id}: checkpoint ids not found: {', '.join(missing_questions)}")
        if len(lesson["checkpoint_question_ids"]) < 3:
            errors.append(f"{lesson_id}: expected at least 3 checkpoint questions")

        mistake_mappings = misconception_mappings.get(lesson_id)
        if not isinstance(mistake_mappings, list):
            errors.append(f"{lesson_id}: missing misconception question mappings")
        elif len(mistake_mappings) != len(lesson["common_mistakes"]):
            errors.append(
                f"{lesson_id}: expected {len(lesson['common_mistakes'])} misconception mappings, "
                f"found {len(mistake_mappings)}"
            )
        else:
            for mistake_index, mapped_ids in enumerate(mistake_mappings, start=1):
                if not mapped_ids:
                    errors.append(f"{lesson_id}: misconception #{mistake_index} has no questions")
                for question_id in mapped_ids:
                    question = questions_by_id.get(question_id)
                    if not question:
                        errors.append(f"{lesson_id}: misconception question not found: {question_id}")
                    elif question["source_file"] != lesson["source_file"]:
                        errors.append(
                            f"{lesson_id}: misconception question {question_id} belongs to "
                            f"{question['source_file']}"
                        )

    unknown_mapping_lessons = sorted(set(misconception_mappings) - lesson_ids)
    if unknown_mapping_lessons:
        errors.append(f"unknown lessons in misconception mappings: {', '.join(unknown_mapping_lessons)}")

    if errors:
        print("Lesson checks failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    concept_count = len({concept for lesson in lessons for concept in lesson["concepts"]})
    checkpoint_count = sum(len(lesson["checkpoint_question_ids"]) for lesson in lessons)
    misconception_count = sum(len(ids) for mappings in misconception_mappings.values() for ids in mappings)
    print(
        f"OK: {len(lessons)} lessons, {concept_count} concepts, {checkpoint_count} checkpoints, "
        f"{misconception_count} misconception links"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
