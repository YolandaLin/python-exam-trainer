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

            project_list = client.get("/api/projects", headers=headers)
            assert project_list.status_code == 200, project_list.text
            assert len(project_list.json()["projects"]) == 5, project_list.text
            project_id = project_list.json()["projects"][0]["id"]
            project_started = client.post(f"/api/projects/{project_id}/start", headers=headers)
            assert project_started.status_code == 200, project_started.text
            assert project_started.json()["project"]["status"] == "in_progress", project_started.text
            project_activity = client.post(
                f"/api/projects/{project_id}/activity",
                headers=headers,
                json={"attempts": 1, "tests_passed": 1, "tests_total": 1},
            )
            assert project_activity.status_code == 200, project_activity.text
            assert project_activity.json()["project"]["tests_passed"] == 1, project_activity.text

            lessons = client.get("/api/lessons", headers=headers)
            assert lessons.status_code == 200, lessons.text
            assert lessons.json()["lessons"], lessons.text
            lesson_id = lessons.json()["next_lesson"]["id"]
            lesson_detail = client.get(f"/api/lessons/{lesson_id}", headers=headers)
            assert lesson_detail.status_code == 200, lesson_detail.text
            checkpoints = lesson_detail.json()["lesson"]["checkpoint_questions"]

            review_status = client.get("/api/review/status", headers=headers)
            assert review_status.status_code == 200, review_status.text
            assert review_status.json()["unlocked"] is False, review_status.text
            locked_review = client.get("/api/next-question?mode=review", headers=headers)
            assert locked_review.status_code == 403, locked_review.text

            admin_login = client.post(
                "/api/login",
                json={"username": "admin", "password": "admin123"},
            )
            assert admin_login.status_code == 200, admin_login.text
            admin_headers = {"Authorization": f"Bearer {admin_login.json()['token']}"}
            admin_review_status = client.get("/api/review/status", headers=admin_headers)
            assert admin_review_status.status_code == 200, admin_review_status.text
            assert admin_review_status.json()["unlocked"] is True, admin_review_status.text
            admin_review_question = client.get("/api/next-question?mode=review", headers=admin_headers)
            assert admin_review_question.status_code == 200, admin_review_question.text
            assert "answer" not in admin_review_question.json()["question"], admin_review_question.text

            started = client.post(f"/api/lessons/{lesson_id}/start", headers=headers)
            assert started.status_code == 200, started.text
            assert started.json()["lesson"]["status"] == "in_progress", started.text

            for checkpoint in checkpoints:
                checkpoint_attempt = client.post(
                    "/api/attempts",
                    headers=headers,
                    json={
                        "question_id": checkpoint["id"],
                        "selected_answer": answers[checkpoint["id"]],
                    },
                )
                assert checkpoint_attempt.status_code == 200, checkpoint_attempt.text

            completed = client.post(
                f"/api/lessons/{lesson_id}/complete",
                headers=headers,
                json={
                    "checkpoint_correct_count": len(checkpoints),
                    "checkpoint_total_count": len(checkpoints),
                },
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
            assert attempt.json()["answer_text"], attempt.text

            following_question = client.get(f"/api/next-question?lesson_id={lesson_id}", headers=headers)
            assert following_question.status_code == 200, following_question.text
            assert following_question.json()["question"]["id"] != question["id"], following_question.text

            dashboard = client.get("/api/dashboard", headers=headers)
            assert dashboard.status_code == 200, dashboard.text
            assert dashboard.json()["total_attempts"] == len(checkpoints) + 1, dashboard.text

            for lesson in lessons.json()["lessons"]:
                detail = client.get(f"/api/lessons/{lesson['id']}", headers=headers)
                assert detail.status_code == 200, detail.text
                lesson_checkpoints = detail.json()["lesson"]["checkpoint_questions"]
                checkpoint_count = len(lesson_checkpoints)
                for checkpoint in lesson_checkpoints:
                    checkpoint_attempt = client.post(
                        "/api/attempts",
                        headers=headers,
                        json={
                            "question_id": checkpoint["id"],
                            "selected_answer": answers[checkpoint["id"]],
                        },
                    )
                    assert checkpoint_attempt.status_code == 200, checkpoint_attempt.text
                completed = client.post(
                    f"/api/lessons/{lesson['id']}/complete",
                    headers=headers,
                    json={
                        "checkpoint_correct_count": checkpoint_count,
                        "checkpoint_total_count": checkpoint_count,
                    },
                )
                assert completed.status_code == 200, completed.text

            review_status = client.get("/api/review/status", headers=headers)
            assert review_status.status_code == 200, review_status.text
            assert review_status.json()["unlocked"] is True, review_status.text

            review_start = client.post("/api/review/start", headers=headers)
            assert review_start.status_code == 200, review_start.text
            review_session_id = review_start.json()["session"]["id"]
            assert review_start.json()["session"]["answer_rate"] == 0, review_start.text

            review_question = client.get("/api/next-question?mode=review", headers=headers)
            assert review_question.status_code == 200, review_question.text
            assert "answer" not in review_question.json()["question"], review_question.text

            wrong_attempt = client.post(
                "/api/attempts",
                headers=headers,
                json={
                    "question_id": review_question.json()["question"]["id"],
                    "selected_answer": ["not-an-answer"],
                    "mode": "review",
                    "review_session_id": review_session_id,
                },
            )
            assert wrong_attempt.status_code == 200, wrong_attempt.text
            assert wrong_attempt.json()["is_correct"] is False, wrong_attempt.text

            first_round_ids = {review_question.json()["question"]["id"]}
            for _ in range(19):
                round_question = client.get("/api/next-question?mode=review", headers=headers)
                assert round_question.status_code == 200, round_question.text
                question_id = round_question.json()["question"]["id"]
                assert question_id not in first_round_ids, round_question.text
                first_round_ids.add(question_id)
                round_attempt = client.post(
                    "/api/attempts",
                    headers=headers,
                    json={
                        "question_id": question_id,
                        "selected_answer": ["not-an-answer"],
                        "mode": "review",
                        "review_session_id": review_session_id,
                    },
                )
                assert round_attempt.status_code == 200, round_attempt.text

            second_start = client.post("/api/review/start", headers=headers)
            assert second_start.status_code == 200, second_start.text
            second_session_id = second_start.json()["session"]["id"]
            second_round_ids = set()
            for _ in range(20):
                round_question = client.get("/api/next-question?mode=review", headers=headers)
                assert round_question.status_code == 200, round_question.text
                question_id = round_question.json()["question"]["id"]
                assert question_id not in first_round_ids, round_question.text
                assert question_id not in second_round_ids, round_question.text
                second_round_ids.add(question_id)
                round_attempt = client.post(
                    "/api/attempts",
                    headers=headers,
                    json={
                        "question_id": question_id,
                        "selected_answer": ["not-an-answer"],
                        "mode": "review",
                        "review_session_id": second_session_id,
                    },
                )
                assert round_attempt.status_code == 200, round_attempt.text

            review_summary = client.get("/api/review/summary", headers=headers)
            assert review_summary.status_code == 200, review_summary.text
            assert review_summary.json()["wrong_questions"] >= 1, review_summary.text
            assert review_summary.json()["high_error_questions"], review_summary.text
            assert review_summary.json()["review_session"]["answered_count"] == 20, review_summary.text

            admin_students = client.get("/api/admin/students", headers=admin_headers)
            assert admin_students.status_code == 200, admin_students.text
            student = next(item for item in admin_students.json()["students"] if item["username"] == "student1")
            assert student["review_status"] == "completed", admin_students.text
            assert student["review_answered"] == 20, admin_students.text
            assert student["project_in_progress"] >= 1, admin_students.text

    print("OK: login, lessons, review lock/unlock, two non-repeating review rounds, dashboard")


if __name__ == "__main__":
    main()
