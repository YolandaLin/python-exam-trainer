from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def check_removed_content_is_deactivated(get_db, seed_questions, seed_lessons, seed_projects) -> None:
    removed_ids = {
        "questions": "removed-question-regression",
        "lessons": "removed-lesson-regression",
        "projects": "removed-project-regression",
    }
    with get_db() as db:
        db.execute(
            """
            INSERT INTO questions (
                id, source_file, type, difficulty, stem, code, options_json,
                answer_json, explanation, common_mistake, is_active
            ) VALUES (?, 'removed.md', 'single_choice', 1, 'removed', '', '[]', '[]', '', '', 1)
            """,
            (removed_ids["questions"],),
        )
        db.execute(
            """
            INSERT INTO lessons (
                id, source_file, unit, title, order_index, content_json,
                goals_json, common_mistakes_json, checkpoint_question_ids_json, is_active
            ) VALUES (?, 'removed.md', 'removed', 'removed', 9999, '[]', '[]', '[]', '[]', 1)
            """,
            (removed_ids["lessons"],),
        )
        db.execute(
            """
            INSERT INTO projects (
                id, title, level, estimated_minutes, concepts_json, description,
                instructions, starter_code, tests_json, hint, is_active
            ) VALUES (?, 'removed', 1, 1, '[]', '', '', '{}', '[]', '', 1)
            """,
            (removed_ids["projects"],),
        )

    seed_questions()
    seed_lessons()
    seed_projects()

    with get_db() as db:
        for table, content_id in removed_ids.items():
            row = db.execute(
                f"SELECT is_active FROM {table} WHERE id = ?",
                (content_id,),
            ).fetchone()
            assert row is not None, (table, content_id)
            assert row["is_active"] == 0, (table, content_id, row["is_active"])


def check_production_startup_rejects_unsafe_passwords(app, test_client_class) -> None:
    safe_passwords = {
        "ADMIN_PASSWORD": "safe-admin-password",
        "STUDENT1_PASSWORD": "safe-student-one-password",
        "STUDENT2_PASSWORD": "safe-student-two-password",
    }
    cases = (
        ("missing", "ADMIN_PASSWORD", None),
        ("empty", "STUDENT1_PASSWORD", ""),
        ("blocked default", "STUDENT2_PASSWORD", "student123"),
    )

    for label, key, unsafe_value in cases:
        with patch.dict(os.environ, {"APP_ENV": "production", **safe_passwords}, clear=False):
            if unsafe_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = unsafe_value

            try:
                with test_client_class(app):
                    pass
            except RuntimeError as error:
                assert key in str(error), (label, str(error))
            else:
                raise AssertionError(f"production startup accepted {label} {key}")


def main() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        os.environ.pop("DATABASE_URL", None)
        os.environ["APP_ENV"] = "test"
        os.environ["DB_PATH"] = str(Path(temp_dir) / "test.db")

        from fastapi.testclient import TestClient

        from app.db import get_db, seed_lessons, seed_projects, seed_questions
        from app.main import app
        from app.security import verify_password
        from scripts.reset_password import reset_user_password

        questions = []
        for path in sorted((ROOT / "content").glob("questions*.json")):
            questions.extend(json.loads(path.read_text(encoding="utf-8")))
        answers = {question["id"]: question["answer"] for question in questions}

        with TestClient(app) as client:
            for _ in range(8):
                failed_login = client.post(
                    "/api/login",
                    json={"username": "rate-limit-check", "password": "wrong"},
                )
                assert failed_login.status_code == 401, failed_login.text
            blocked_login = client.post(
                "/api/login",
                json={"username": "rate-limit-check", "password": "wrong"},
            )
            assert blocked_login.status_code == 429, blocked_login.text

            login = client.post(
                "/api/login",
                json={"username": "student1", "password": "student123"},
            )
            assert login.status_code == 200, login.text

            headers = {"Authorization": f"Bearer {login.json()['token']}"}

            project_list = client.get("/api/projects", headers=headers)
            assert project_list.status_code == 200, project_list.text
            assert len(project_list.json()["projects"]) == 5, project_list.text
            project = project_list.json()["projects"][0]
            project_id = project["id"]
            project_test_count = len(project["tests"])
            assert project_test_count > 0, project
            project_started = client.post(f"/api/projects/{project_id}/start", headers=headers)
            assert project_started.status_code == 200, project_started.text
            assert project_started.json()["project"]["status"] == "in_progress", project_started.text
            premature_complete = client.post(
                f"/api/projects/{project_id}/complete",
                headers=headers,
                json={"attempts": 0, "tests_passed": 1, "tests_total": 1},
            )
            assert premature_complete.status_code == 400, premature_complete.text
            invalid_activities = (
                ("zero tests_total", {"attempts": 1, "tests_passed": 0, "tests_total": 0}),
                (
                    "tests_passed above total",
                    {
                        "attempts": 1,
                        "tests_passed": project_test_count + 1,
                        "tests_total": project_test_count,
                    },
                ),
                (
                    "negative attempts",
                    {"attempts": -1, "tests_passed": project_test_count, "tests_total": project_test_count},
                ),
                (
                    "multiple attempts",
                    {"attempts": 2, "tests_passed": project_test_count, "tests_total": project_test_count},
                ),
            )
            for label, payload in invalid_activities:
                rejected_activity = client.post(
                    f"/api/projects/{project_id}/activity",
                    headers=headers,
                    json=payload,
                )
                assert rejected_activity.status_code == 400, (label, rejected_activity.text)
            project_activity = client.post(
                f"/api/projects/{project_id}/activity",
                headers=headers,
                json={
                    "attempts": 1,
                    "tests_passed": project_test_count,
                    "tests_total": project_test_count,
                },
            )
            assert project_activity.status_code == 200, project_activity.text
            assert project_activity.json()["project"]["attempts"] == 1, project_activity.text
            assert project_activity.json()["project"]["tests_passed"] == project_test_count, project_activity.text
            project_completed = client.post(
                f"/api/projects/{project_id}/complete",
                headers=headers,
                json={
                    "attempts": 0,
                    "tests_passed": project_test_count,
                    "tests_total": project_test_count,
                },
            )
            assert project_completed.status_code == 200, project_completed.text
            assert project_completed.json()["project"]["status"] == "completed", project_completed.text

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
                assert checkpoint["options"], checkpoint
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
                    assert checkpoint["options"], checkpoint
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

            with get_db() as db:
                review_session_count = db.execute(
                    "SELECT COUNT(*) AS count FROM review_sessions WHERE user_id = ?",
                    (login.json()["user"]["id"],),
                ).fetchone()["count"]

            resumed_review = client.post("/api/review/start", headers=headers)
            assert resumed_review.status_code == 200, resumed_review.text
            assert resumed_review.json()["session"]["id"] == review_session_id, resumed_review.text
            assert resumed_review.json()["session"]["answered_count"] == 1, resumed_review.text
            assert resumed_review.json()["session"]["correct_count"] == 0, resumed_review.text

            with get_db() as db:
                resumed_session_count = db.execute(
                    "SELECT COUNT(*) AS count FROM review_sessions WHERE user_id = ?",
                    (login.json()["user"]["id"],),
                ).fetchone()["count"]
            assert resumed_session_count == review_session_count

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
            assert second_session_id != review_session_id, second_start.text
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
            assert student["project_completed"] + student["project_in_progress"] >= 1, admin_students.text

            rotated_password = "rotated-student2-password"
            reset_user_password("student2", rotated_password)
            old_password_login = client.post(
                "/api/login",
                json={"username": "student2", "password": "student123"},
            )
            assert old_password_login.status_code == 401, old_password_login.text
            rotated_password_login = client.post(
                "/api/login",
                json={"username": "student2", "password": rotated_password},
            )
            assert rotated_password_login.status_code == 200, rotated_password_login.text

        check_removed_content_is_deactivated(get_db, seed_questions, seed_lessons, seed_projects)
        check_production_startup_rejects_unsafe_passwords(app, TestClient)
        with get_db() as db:
            rotated_user = db.execute(
                "SELECT password_hash FROM users WHERE username = ?",
                ("student2",),
            ).fetchone()
        assert verify_password("rotated-student2-password", rotated_user["password_hash"])

    print(
        "OK: login, lessons, project validation, seed sync, production passwords and rotation, "
        "review resume, two non-repeating review rounds, attempts, dashboard"
    )


if __name__ == "__main__":
    main()
