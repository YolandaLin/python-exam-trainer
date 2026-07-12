from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        os.environ.pop("DATABASE_URL", None)
        os.environ["DB_PATH"] = str(Path(temp_dir) / "test.db")

        from fastapi.testclient import TestClient

        from app.main import app

        questions = []
        for path in sorted((ROOT / "content").glob("questions*.json")):
            questions.extend(json.loads(path.read_text(encoding="utf-8")))
        answers = {question["id"]: question["answer"] for question in questions}

        with TestClient(app) as client:
            login = client.post(
                "/api/login",
                json={"username": "student1", "password": "student123"},
            )
            assert login.status_code == 200, login.text

            headers = {"Authorization": f"Bearer {login.json()['token']}"}

            lessons = client.get("/api/lessons", headers=headers)
            assert lessons.status_code == 200, lessons.text
            assert lessons.json()["lessons"], lessons.text
            lesson_id = lessons.json()["next_lesson"]["id"]

            review_status = client.get("/api/review/status", headers=headers)
            assert review_status.status_code == 200, review_status.text
            assert review_status.json()["unlocked"] is False, review_status.text
            locked_review = client.get("/api/next-question?mode=review", headers=headers)
            assert locked_review.status_code == 403, locked_review.text

            started = client.post(f"/api/lessons/{lesson_id}/start", headers=headers)
            assert started.status_code == 200, started.text
            assert started.json()["lesson"]["status"] == "in_progress", started.text

            completed = client.post(
                f"/api/lessons/{lesson_id}/complete",
                headers=headers,
                json={"checkpoint_correct_count": 1, "checkpoint_total_count": 1},
            )
            assert completed.status_code == 200, completed.text
            assert completed.json()["lesson"]["status"] == "completed", completed.text

            next_question = client.get(f"/api/next-question?lesson_id={lesson_id}", headers=headers)
            assert next_question.status_code == 200, next_question.text

            question = next_question.json()["question"]
            assert "answer" not in question

            attempt = client.post(
                "/api/attempts",
                headers=headers,
                json={
                    "question_id": question["id"],
                    "selected_answer": answers[question["id"]],
                    "used_hint": False,
                    "ran_code": True,
                    "elapsed_seconds": 1,
                },
            )
            assert attempt.status_code == 200, attempt.text
            assert attempt.json()["is_correct"] is True, attempt.text

            dashboard = client.get("/api/dashboard", headers=headers)
            assert dashboard.status_code == 200, dashboard.text
            assert dashboard.json()["total_attempts"] == 1, dashboard.text

            for lesson in lessons.json()["lessons"]:
                completed = client.post(
                    f"/api/lessons/{lesson['id']}/complete",
                    headers=headers,
                    json={"checkpoint_correct_count": 0, "checkpoint_total_count": 0},
                )
                assert completed.status_code == 200, completed.text

            review_status = client.get("/api/review/status", headers=headers)
            assert review_status.status_code == 200, review_status.text
            assert review_status.json()["unlocked"] is True, review_status.text

            review_question = client.get("/api/next-question?mode=review", headers=headers)
            assert review_question.status_code == 200, review_question.text
            assert "answer" not in review_question.json()["question"], review_question.text

            wrong_attempt = client.post(
                "/api/attempts",
                headers=headers,
                json={
                    "question_id": review_question.json()["question"]["id"],
                    "selected_answer": ["not-an-answer"],
                },
            )
            assert wrong_attempt.status_code == 200, wrong_attempt.text
            assert wrong_attempt.json()["is_correct"] is False, wrong_attempt.text

            review_summary = client.get("/api/review/summary", headers=headers)
            assert review_summary.status_code == 200, review_summary.text
            assert review_summary.json()["wrong_questions"] >= 1, review_summary.text
            assert review_summary.json()["high_error_questions"], review_summary.text

    print("OK: login, lessons, lesson progress, review lock/unlock, attempts, dashboard")


if __name__ == "__main__":
    main()
