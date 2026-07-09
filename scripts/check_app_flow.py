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
        os.environ["DB_PATH"] = str(Path(temp_dir) / "test.db")

        from fastapi.testclient import TestClient

        from app.main import app

        questions = json.loads((ROOT / "content" / "questions.json").read_text(encoding="utf-8"))
        answers = {question["id"]: question["answer"] for question in questions}

        with TestClient(app) as client:
            login = client.post(
                "/api/login",
                json={"username": "student1", "password": "student123"},
            )
            assert login.status_code == 200, login.text

            headers = {"Authorization": f"Bearer {login.json()['token']}"}
            next_question = client.get("/api/next-question", headers=headers)
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

    print("OK: login, next question, attempt, dashboard")


if __name__ == "__main__":
    main()
