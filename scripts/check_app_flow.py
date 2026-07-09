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

    print("OK: login, lessons, lesson progress, next question, attempt, dashboard")


if __name__ == "__main__":
    main()
