from __future__ import annotations

import json
import os
import random
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .db import get_db, init_db, load_misconception_question_ids, session_expiry, string_agg_expr, utcnow
from .security import new_token, verify_password


ROOT = Path(__file__).resolve().parents[1]
STATIC_DIR = ROOT / "app" / "static"
MISCONCEPTION_QUESTION_IDS = load_misconception_question_ids()
REVIEW_SIZE = 20

app = FastAPI(title="python-exam-trainer")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class LoginRequest(BaseModel):
    username: str
    password: str


class AttemptRequest(BaseModel):
    question_id: str
    selected_answer: list[str] = Field(default_factory=list)
    used_hint: bool = False
    ran_code: bool = False
    elapsed_seconds: int = 0
    mode: str = "lesson"
    review_session_id: int | None = None


class LessonCompleteRequest(BaseModel):
    checkpoint_correct_count: int = 0
    checkpoint_total_count: int = 0


class ProjectActivityRequest(BaseModel):
    attempts: int = 0
    tests_passed: int = 0
    tests_total: int = 0


def parse_json(value: str) -> Any:
    return json.loads(value)


def review_session_payload(row: Any) -> dict[str, Any] | None:
    if not row:
        return None
    answered = int(row["answered_count"] or 0)
    return {
        "id": row["id"],
        "started_at": row["started_at"],
        "last_answered_at": row["last_answered_at"],
        "answered_count": answered,
        "correct_count": int(row["correct_count"] or 0),
        "answer_rate": round(answered / REVIEW_SIZE * 100, 1),
        "completed_at": row["completed_at"],
    }


def latest_review_session(db: Any, user_id: int) -> Any:
    return db.execute(
        "SELECT * FROM review_sessions WHERE user_id = ? ORDER BY id DESC LIMIT 1",
        (user_id,),
    ).fetchone()


QUESTION_GROUP_BY = """
    q.id, q.source_file, q.type, q.difficulty, q.stem, q.code,
    q.options_json, q.answer_json, q.explanation, q.common_mistake, q.is_active
"""

LESSON_GROUP_BY = """
    l.id, l.source_file, l.unit, l.title, l.order_index, l.content_json,
    l.goals_json, l.common_mistakes_json, l.checkpoint_question_ids_json, l.is_active
"""

LESSON_PROGRESS_GROUP_BY = """
    lp.status, lp.last_viewed_at, lp.completed_at,
    lp.checkpoint_correct_count, lp.checkpoint_total_count
"""
PRODUCTION_BLOCKED_PASSWORDS = {"admin123", "student123"}
LOGIN_WINDOW_SECONDS = 300
LOGIN_MAX_FAILURES = 8
LOGIN_BLOCK_SECONDS = 900


def public_question(row: Any, include_answer: bool = False) -> dict[str, Any]:
    options = parse_json(row["options_json"])
    random.shuffle(options)
    result = {
        "id": row["id"],
        "source_file": row["source_file"],
        "type": row["type"],
        "difficulty": row["difficulty"],
        "stem": row["stem"],
        "code": row["code"],
        "options": options,
        "concepts": row["concepts"].split(",") if row["concepts"] else [],
    }
    if include_answer:
        result["answer"] = parse_json(row["answer_json"])
        result["explanation"] = row["explanation"]
        result["common_mistake"] = row["common_mistake"]
    return result


def public_lesson(row: Any, include_content: bool = False) -> dict[str, Any]:
    result = {
        "id": row["id"],
        "source_file": row["source_file"],
        "unit": row["unit"],
        "title": row["title"],
        "order": row["order_index"],
        "concepts": row["concepts"].split(",") if row["concepts"] else [],
        "status": row["status"] or "not_started",
        "last_viewed_at": row["last_viewed_at"],
        "completed_at": row["completed_at"],
        "checkpoint_correct_count": row["checkpoint_correct_count"] or 0,
        "checkpoint_total_count": row["checkpoint_total_count"] or 0,
    }
    if include_content:
        result["goals"] = parse_json(row["goals_json"])
        result["body"] = parse_json(row["content_json"])
        result["common_mistakes"] = parse_json(row["common_mistakes_json"])
        result["checkpoint_question_ids"] = parse_json(row["checkpoint_question_ids_json"])
    return result


def public_project(row: Any) -> dict[str, Any]:
    example = parse_json(row["starter_code"])
    return {
        "id": row["id"],
        "title": row["title"],
        "level": row["level"],
        "estimated_minutes": row["estimated_minutes"],
        "concepts": parse_json(row["concepts_json"]),
        "description": row["description"],
        "instructions": row["instructions"],
        "example": example,
        "tests": parse_json(row["tests_json"]),
        "hint": row["hint"],
        "status": row["status"] or "not_started",
        "attempts": row["attempts"] or 0,
        "tests_passed": row["tests_passed"] or 0,
        "tests_total": row["tests_total"] or len(parse_json(row["tests_json"])),
        "started_at": row["started_at"],
        "last_activity_at": row["last_activity_at"],
        "completed_at": row["completed_at"],
    }


def checkpoint_questions(db: Any, lesson: dict[str, Any]) -> list[dict[str, Any]]:
    question_ids = lesson.get("checkpoint_question_ids", [])
    if not question_ids:
        return []
    placeholders = ",".join("?" for _ in question_ids)
    rows = db.execute(
        f"""
        SELECT q.*,
               {string_agg_expr("qc.concept_id")} AS concepts
        FROM questions q
        LEFT JOIN question_concepts qc ON qc.question_id = q.id
        WHERE q.id IN ({placeholders}) AND q.is_active = 1
        GROUP BY {QUESTION_GROUP_BY}
        """,
        tuple(question_ids),
    ).fetchall()
    by_id = {row["id"]: public_question(row) for row in rows}
    return [by_id[question_id] for question_id in question_ids if question_id in by_id]


def auth_user(authorization: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    token = authorization.removeprefix("Bearer ").strip()
    with get_db() as db:
        row = db.execute(
            """
            SELECT users.*
            FROM sessions
            JOIN users ON users.id = sessions.user_id
            WHERE sessions.token = ? AND sessions.expires_at > ?
            """,
            (token, utcnow()),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=401, detail="Invalid token")
    if row["status"] != "approved":
        raise HTTPException(status_code=403, detail="帳號目前尚未核准或已被停用")
    return dict(row)


def require_admin(user: dict[str, Any] = Depends(auth_user)) -> dict[str, Any]:
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    return user


def lesson_row(db: Any, user_id: int, lesson_id: str) -> Any:
    row = db.execute(
        f"""
        SELECT l.*,
               {string_agg_expr("lc.concept_id")} AS concepts,
               COALESCE(lp.status, 'not_started') AS status,
               lp.last_viewed_at,
               lp.completed_at,
               COALESCE(lp.checkpoint_correct_count, 0) AS checkpoint_correct_count,
               COALESCE(lp.checkpoint_total_count, 0) AS checkpoint_total_count
        FROM lessons l
        LEFT JOIN lesson_concepts lc ON lc.lesson_id = l.id
        LEFT JOIN lesson_progress lp ON lp.lesson_id = l.id AND lp.user_id = ?
        WHERE l.id = ? AND l.is_active = 1
        GROUP BY {LESSON_GROUP_BY}, {LESSON_PROGRESS_GROUP_BY}
        """,
        (user_id, lesson_id),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="找不到課程")
    return row


def lesson_concepts(db: Any, lesson_id: str) -> set[str]:
    rows = db.execute(
        "SELECT concept_id FROM lesson_concepts WHERE lesson_id = ?",
        (lesson_id,),
    ).fetchall()
    return {row["concept_id"] for row in rows}


def project_row(db: Any, user_id: int, project_id: str) -> Any:
    row = db.execute(
        """
        SELECT p.*,
               COALESCE(pp.status, 'not_started') AS status,
               COALESCE(pp.attempts, 0) AS attempts,
               COALESCE(pp.tests_passed, 0) AS tests_passed,
               COALESCE(pp.tests_total, 0) AS tests_total,
               pp.started_at, pp.last_activity_at, pp.completed_at
        FROM projects p
        LEFT JOIN project_progress pp
          ON pp.project_id = p.id AND pp.user_id = ?
        WHERE p.id = ? AND p.is_active = 1
        """,
        (user_id, project_id),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="找不到實作任務")
    return row


def suggested_lesson_for_concept(db: Any, user_id: int, concept_id: str) -> dict[str, Any] | None:
    row = db.execute(
        """
        SELECT l.id, l.title, l.unit,
               COALESCE(lp.status, 'not_started') AS status
        FROM lesson_concepts lc
        JOIN lessons l ON l.id = lc.lesson_id
        LEFT JOIN lesson_progress lp ON lp.lesson_id = l.id AND lp.user_id = ?
        WHERE lc.concept_id = ? AND l.is_active = 1
        ORDER BY l.order_index
        LIMIT 1
        """,
        (user_id, concept_id),
    ).fetchone()
    return dict(row) if row else None


def suggested_lessons_for_question(db: Any, user_id: int, question_id: str) -> list[dict[str, Any]]:
    rows = db.execute(
        """
        SELECT DISTINCT l.id, l.title, l.unit,
               COALESCE(lp.status, 'not_started') AS status,
               l.order_index
        FROM question_concepts qc
        JOIN lesson_concepts lc ON lc.concept_id = qc.concept_id
        JOIN lessons l ON l.id = lc.lesson_id
        LEFT JOIN lesson_progress lp ON lp.lesson_id = l.id AND lp.user_id = ?
        WHERE qc.question_id = ? AND l.is_active = 1
        ORDER BY l.order_index
        LIMIT 3
        """,
        (user_id, question_id),
    ).fetchall()
    return [
        {
            "id": row["id"],
            "title": row["title"],
            "unit": row["unit"],
            "status": row["status"],
        }
        for row in rows
    ]


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/login")
def login(payload: LoginRequest, request: Request) -> dict[str, Any]:
    client_key = f"{request.client.host if request.client else 'unknown'}|{payload.username.strip().lower()}"
    now = datetime.now(UTC)
    blocked_default_password = os.environ.get("APP_ENV") == "production" and payload.password in PRODUCTION_BLOCKED_PASSWORDS
    with get_db() as db:
        lock = db.execute("SELECT * FROM login_attempts WHERE key = ?", (client_key,)).fetchone()
        if lock:
            blocked_until = datetime.fromisoformat(lock["blocked_until"]) if lock["blocked_until"] else None
            window_started = datetime.fromisoformat(lock["window_started_at"])
            if blocked_until and blocked_until > now:
                raise HTTPException(status_code=429, detail="登入嘗試過多，請稍後再試")
            if (now - window_started).total_seconds() > LOGIN_WINDOW_SECONDS:
                db.execute("DELETE FROM login_attempts WHERE key = ?", (client_key,))
        user = db.execute(
            "SELECT * FROM users WHERE username = ? OR email = ? LIMIT 1",
            (payload.username, payload.username.strip().lower()),
        ).fetchone()
        if blocked_default_password or not user or not verify_password(payload.password, user["password_hash"]):
            lock = db.execute("SELECT * FROM login_attempts WHERE key = ?", (client_key,)).fetchone()
            if not lock:
                db.execute(
                    "INSERT INTO login_attempts (key, failed_count, window_started_at) VALUES (?, 1, ?)",
                    (client_key, now.isoformat()),
                )
            else:
                failed_count = int(lock["failed_count"]) + 1
                blocked_until = (now + timedelta(seconds=LOGIN_BLOCK_SECONDS)).isoformat() if failed_count >= LOGIN_MAX_FAILURES else None
                db.execute(
                    "UPDATE login_attempts SET failed_count = ?, blocked_until = ? WHERE key = ?",
                    (failed_count, blocked_until, client_key),
                )
            db.commit()
            raise HTTPException(status_code=401, detail="帳號或密碼錯誤")
        if user["status"] != "approved":
            raise HTTPException(status_code=403, detail="帳號目前尚未核准或已被停用")
        db.execute("DELETE FROM login_attempts WHERE key = ?", (client_key,))
        token = new_token()
        db.execute(
            "INSERT INTO sessions (token, user_id, expires_at, created_at) VALUES (?, ?, ?, ?)",
            (token, user["id"], session_expiry(), utcnow()),
        )
    return {
        "token": token,
        "user": {
            "id": user["id"],
            "username": user["username"],
            "role": user["role"],
            "display_name": user["display_name"],
        },
    }


@app.post("/api/logout")
def logout(authorization: Annotated[str | None, Header()] = None) -> dict[str, bool]:
    if authorization and authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ").strip()
        with get_db() as db:
            db.execute("DELETE FROM sessions WHERE token = ?", (token,))
    return {"ok": True}


@app.get("/api/me")
def me(user: dict[str, Any] = Depends(auth_user)) -> dict[str, Any]:
    return {
        "id": user["id"],
        "username": user["username"],
        "role": user["role"],
        "display_name": user["display_name"],
    }


@app.get("/api/lessons")
def lessons(user: dict[str, Any] = Depends(auth_user)) -> dict[str, Any]:
    with get_db() as db:
        rows = db.execute(
            f"""
            SELECT l.*,
                   {string_agg_expr("lc.concept_id")} AS concepts,
                   COALESCE(lp.status, 'not_started') AS status,
                   lp.last_viewed_at,
                   lp.completed_at,
                   COALESCE(lp.checkpoint_correct_count, 0) AS checkpoint_correct_count,
                   COALESCE(lp.checkpoint_total_count, 0) AS checkpoint_total_count
            FROM lessons l
            LEFT JOIN lesson_concepts lc ON lc.lesson_id = l.id
            LEFT JOIN lesson_progress lp ON lp.lesson_id = l.id AND lp.user_id = ?
            WHERE l.is_active = 1
            GROUP BY {LESSON_GROUP_BY}, {LESSON_PROGRESS_GROUP_BY}
            ORDER BY l.order_index
            """,
            (user["id"],),
        ).fetchall()
    items = [public_lesson(row) for row in rows]
    next_lesson = next((lesson for lesson in items if lesson["status"] != "completed"), items[0] if items else None)
    return {"lessons": items, "next_lesson": next_lesson}


@app.get("/api/lessons/{lesson_id}")
def lesson_detail(lesson_id: str, user: dict[str, Any] = Depends(auth_user)) -> dict[str, Any]:
    with get_db() as db:
        lesson = public_lesson(lesson_row(db, user["id"], lesson_id), include_content=True)
        lesson["checkpoint_questions"] = checkpoint_questions(db, lesson)
        return {"lesson": lesson}


@app.post("/api/lessons/{lesson_id}/start")
def start_lesson(lesson_id: str, user: dict[str, Any] = Depends(auth_user)) -> dict[str, Any]:
    with get_db() as db:
        lesson_row(db, user["id"], lesson_id)
        now = utcnow()
        db.execute(
            """
            INSERT INTO lesson_progress (user_id, lesson_id, status, last_viewed_at)
            VALUES (?, ?, 'in_progress', ?)
            ON CONFLICT(user_id, lesson_id) DO UPDATE SET
                status=CASE
                    WHEN lesson_progress.status = 'not_started' THEN 'in_progress'
                    ELSE lesson_progress.status
                END,
                last_viewed_at=excluded.last_viewed_at
            """,
            (user["id"], lesson_id, now),
        )
        lesson = public_lesson(lesson_row(db, user["id"], lesson_id), include_content=True)
        lesson["checkpoint_questions"] = checkpoint_questions(db, lesson)
        return {"lesson": lesson}


@app.post("/api/lessons/{lesson_id}/complete")
def complete_lesson(
    lesson_id: str,
    payload: LessonCompleteRequest,
    user: dict[str, Any] = Depends(auth_user),
) -> dict[str, Any]:
    with get_db() as db:
        lesson = lesson_row(db, user["id"], lesson_id)
        checkpoint_ids = parse_json(lesson["checkpoint_question_ids_json"])
        if checkpoint_ids:
            placeholders = ",".join("?" for _ in checkpoint_ids)
            attempts = db.execute(
                f"""
                SELECT question_id, is_correct
                FROM attempts
                WHERE user_id = ? AND question_id IN ({placeholders})
                ORDER BY id DESC
                """,
                (user["id"], *checkpoint_ids),
            ).fetchall()
            latest = {}
            for attempt in attempts:
                latest.setdefault(attempt["question_id"], bool(attempt["is_correct"]))
            if len(latest) < len(checkpoint_ids):
                raise HTTPException(status_code=400, detail="請先完成所有課後小檢查")
            checkpoint_correct_count = sum(latest.values())
            checkpoint_total_count = len(checkpoint_ids)
        else:
            checkpoint_correct_count = 0
            checkpoint_total_count = 0
        now = utcnow()
        db.execute(
            """
            INSERT INTO lesson_progress (
                user_id, lesson_id, status, last_viewed_at, completed_at,
                checkpoint_correct_count, checkpoint_total_count
            )
            VALUES (?, ?, 'completed', ?, ?, ?, ?)
            ON CONFLICT(user_id, lesson_id) DO UPDATE SET
                status='completed',
                last_viewed_at=excluded.last_viewed_at,
                completed_at=excluded.completed_at,
                checkpoint_correct_count=excluded.checkpoint_correct_count,
                checkpoint_total_count=excluded.checkpoint_total_count
            """,
            (
                user["id"],
                lesson_id,
                now,
                now,
                checkpoint_correct_count,
                checkpoint_total_count,
            ),
        )
        return {"lesson": public_lesson(lesson_row(db, user["id"], lesson_id), include_content=True)}


@app.get("/api/projects")
def projects(user: dict[str, Any] = Depends(auth_user)) -> dict[str, Any]:
    with get_db() as db:
        rows = db.execute(
            """
            SELECT p.*,
                   COALESCE(pp.status, 'not_started') AS status,
                   COALESCE(pp.attempts, 0) AS attempts,
                   COALESCE(pp.tests_passed, 0) AS tests_passed,
                   COALESCE(pp.tests_total, 0) AS tests_total,
                   pp.started_at, pp.last_activity_at, pp.completed_at
            FROM projects p
            LEFT JOIN project_progress pp
              ON pp.project_id = p.id AND pp.user_id = ?
            WHERE p.is_active = 1
            ORDER BY p.level, p.id
            """,
            (user["id"],),
        ).fetchall()
    return {"projects": [public_project(row) for row in rows]}


@app.post("/api/projects/{project_id}/start")
def start_project(project_id: str, user: dict[str, Any] = Depends(auth_user)) -> dict[str, Any]:
    with get_db() as db:
        project_row(db, user["id"], project_id)
        now = utcnow()
        db.execute(
            """
            INSERT INTO project_progress (user_id, project_id, status, started_at, last_activity_at)
            VALUES (?, ?, 'in_progress', ?, ?)
            ON CONFLICT(user_id, project_id) DO UPDATE SET
                status=CASE WHEN project_progress.status = 'completed'
                    THEN project_progress.status ELSE 'in_progress' END,
                started_at=COALESCE(project_progress.started_at, excluded.started_at),
                last_activity_at=excluded.last_activity_at
            """,
            (user["id"], project_id, now, now),
        )
        return {"project": public_project(project_row(db, user["id"], project_id))}


@app.post("/api/projects/{project_id}/activity")
def project_activity(
    project_id: str,
    payload: ProjectActivityRequest,
    user: dict[str, Any] = Depends(auth_user),
) -> dict[str, Any]:
    with get_db() as db:
        project = project_row(db, user["id"], project_id)
        tests_total = len(parse_json(project["tests_json"]))
        if payload.tests_total not in {0, tests_total}:
            raise HTTPException(status_code=400, detail="測試數量不正確")
        now = utcnow()
        db.execute(
            """
            INSERT INTO project_progress (
                user_id, project_id, status, attempts, tests_passed, tests_total,
                started_at, last_activity_at
            )
            VALUES (?, ?, 'in_progress', ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, project_id) DO UPDATE SET
                status=CASE WHEN project_progress.status = 'completed'
                    THEN project_progress.status ELSE 'in_progress' END,
                attempts=project_progress.attempts + excluded.attempts,
                tests_passed=excluded.tests_passed,
                tests_total=excluded.tests_total,
                started_at=COALESCE(project_progress.started_at, excluded.started_at),
                last_activity_at=excluded.last_activity_at
            """,
            (
                user["id"],
                project_id,
                max(0, payload.attempts),
                min(tests_total, max(0, payload.tests_passed)),
                tests_total,
                now,
                now,
            ),
        )
        return {"project": public_project(project_row(db, user["id"], project_id))}


@app.post("/api/projects/{project_id}/complete")
def complete_project(
    project_id: str,
    payload: ProjectActivityRequest,
    user: dict[str, Any] = Depends(auth_user),
) -> dict[str, Any]:
    with get_db() as db:
        project = project_row(db, user["id"], project_id)
        tests_total = len(parse_json(project["tests_json"]))
        if project["status"] == "not_started":
            raise HTTPException(status_code=400, detail="請先開始實作任務")
        if project["tests_passed"] < tests_total:
            raise HTTPException(status_code=400, detail="請先通過所有測試")
        now = utcnow()
        db.execute(
            """
            INSERT INTO project_progress (
                user_id, project_id, status, attempts, tests_passed, tests_total,
                started_at, last_activity_at, completed_at
            )
            VALUES (?, ?, 'completed', ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, project_id) DO UPDATE SET
                status='completed',
                attempts=project_progress.attempts + excluded.attempts,
                tests_passed=excluded.tests_passed,
                tests_total=excluded.tests_total,
                started_at=COALESCE(project_progress.started_at, excluded.started_at),
                last_activity_at=excluded.last_activity_at,
                completed_at=excluded.completed_at
            """,
            (
                user["id"],
                project_id,
                max(0, payload.attempts),
                tests_total,
                tests_total,
                now,
                now,
                now,
            ),
        )
        return {"project": public_project(project_row(db, user["id"], project_id))}


def question_rows(db: Any) -> list[Any]:
    return db.execute(
        f"""
        SELECT q.*,
               {string_agg_expr("qc.concept_id")} AS concepts
        FROM questions q
        LEFT JOIN question_concepts qc ON qc.question_id = q.id
        WHERE q.is_active = 1
        GROUP BY {QUESTION_GROUP_BY}
        ORDER BY q.id
        """
    ).fetchall()


def mastery_map(db: Any, user_id: int) -> dict[str, int]:
    rows = db.execute(
        "SELECT concept_id, mastery_score FROM concept_mastery WHERE user_id = ?",
        (user_id,),
    ).fetchall()
    return {row["concept_id"]: row["mastery_score"] for row in rows}


def recent_question_ids(db: Any, user_id: int, limit: int = 20) -> set[str]:
    rows = db.execute(
        """
        SELECT question_id
        FROM attempts
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (user_id, limit),
    ).fetchall()
    return {row["question_id"] for row in rows}


def last_question_id(db: Any, user_id: int) -> str | None:
    row = db.execute(
        """
        SELECT question_id
        FROM attempts
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (user_id,),
    ).fetchone()
    return row["question_id"] if row else None


def review_unlocked(db: Any, user_id: int) -> tuple[bool, int, int]:
    total = db.execute("SELECT COUNT(*) AS count FROM lessons WHERE is_active = 1").fetchone()["count"]
    completed = db.execute(
        """
        SELECT COUNT(*) AS count
        FROM lesson_progress lp
        JOIN lessons l ON l.id = lp.lesson_id
        WHERE lp.user_id = ? AND lp.status = 'completed' AND l.is_active = 1
        """,
        (user_id,),
    ).fetchone()["count"]
    return total > 0 and completed == total, completed, total


def question_attempt_stats(db: Any, user_id: int) -> dict[str, dict[str, Any]]:
    rows = db.execute(
        """
        SELECT question_id, COUNT(*) AS attempts,
               SUM(CASE WHEN is_correct = 0 THEN 1 ELSE 0 END) AS wrong
        FROM attempts
        WHERE user_id = ?
        GROUP BY question_id
        """,
        (user_id,),
    ).fetchall()
    latest = db.execute(
        """
        SELECT a.question_id, a.is_correct
        FROM attempts a
        JOIN (
            SELECT question_id, MAX(id) AS max_id
            FROM attempts
            WHERE user_id = ?
            GROUP BY question_id
        ) last_attempt ON last_attempt.max_id = a.id
        """,
        (user_id,),
    ).fetchall()
    latest_correct = {row["question_id"]: bool(row["is_correct"]) for row in latest}
    return {
        row["question_id"]: {
            "attempts": row["attempts"],
            "wrong": row["wrong"] or 0,
            "last_correct": latest_correct.get(row["question_id"]),
        }
        for row in rows
    }


def choose_next_question(
    db: Any, user_id: int, lesson_id: str | None = None, review: bool = False
) -> Any:
    questions = question_rows(db)
    if not questions:
        raise HTTPException(status_code=404, detail="題庫尚未建立")

    if lesson_id:
        lesson = lesson_row(db, user_id, lesson_id)
        concepts = lesson_concepts(db, lesson_id)
        source_file = lesson["source_file"]
        scoped_questions = [question for question in questions if question["source_file"] == source_file]
        if not scoped_questions:
            scoped_questions = [
                question
                for question in questions
                if concepts.intersection((question["concepts"] or "").split(","))
            ]
        if scoped_questions:
            questions = scoped_questions

    mastery = mastery_map(db, user_id)
    recent = recent_question_ids(db, user_id, REVIEW_SIZE * 2 if review else 20)
    attempt_stats = question_attempt_stats(db, user_id)

    # Prefer a genuinely different question over repeatedly drilling the same
    # wording. Small lesson pools fall back only after every variant was seen.
    not_recent = [question for question in questions if question["id"] not in recent]
    if not_recent:
        questions = not_recent
    else:
        previous_question_id = last_question_id(db, user_id)
        if previous_question_id and len(questions) > 1:
            questions = [question for question in questions if question["id"] != previous_question_id]

    scored: list[tuple[float, Any]] = []

    for question in questions:
        concepts = [c for c in (question["concepts"] or "").split(",") if c]
        scores = [mastery.get(concept, 45) for concept in concepts] or [45]
        avg = sum(scores) / len(scores)
        difficulty = question["difficulty"]

        if avg < 50 and difficulty > 2:
            gate = -45
        elif avg < 70 and difficulty > 3:
            gate = -30
        else:
            gate = 0

        stats = attempt_stats.get(question["id"])
        seen = stats["attempts"] if stats else 0
        score = (100 - avg) + (30 if seen == 0 else -min(30, seen * 8)) + gate + random.random() * 12
        if review:
            # A 50% prior prevents one early mistake from dominating the review queue.
            wrong_rate = ((stats["wrong"] if stats else 0) + 2) / (seen + 4)
            score += wrong_rate * 70
            if stats and stats["last_correct"] is False:
                score += 24
            if stats and stats["last_correct"] and seen >= 2:
                score -= min(18, seen * 3)
            if question["id"] in MISCONCEPTION_QUESTION_IDS:
                score += 20
        scored.append((score, question))

    scored.sort(key=lambda item: item[0], reverse=True)
    pool = [question for _, question in scored[: min(5, len(scored))]]
    return random.choice(pool)


@app.get("/api/next-question")
def next_question(
    lesson_id: str | None = None,
    mode: str | None = None,
    user: dict[str, Any] = Depends(auth_user),
) -> dict[str, Any]:
    with get_db() as db:
        is_review = mode == "review"
        if is_review:
            unlocked, _, _ = review_unlocked(db, user["id"])
            if user["role"] != "admin" and not unlocked:
                raise HTTPException(status_code=403, detail="完成全部課程後才能開始總複習")
            lesson_id = None
        row = choose_next_question(db, user["id"], lesson_id, review=is_review)
        return {"question": public_question(row)}


def update_mastery(db: Any, user_id: int, question_id: str, correct: bool, used_hint: bool) -> list[dict[str, Any]]:
    concepts = db.execute(
        """
        SELECT concept_id
        FROM question_concepts
        WHERE question_id = ?
        """,
        (question_id,),
    ).fetchall()
    delta = 3 if correct and used_hint else 8 if correct else -12
    updates: list[dict[str, Any]] = []
    for row in concepts:
        concept_id = row["concept_id"]
        current = db.execute(
            """
            SELECT *
            FROM concept_mastery
            WHERE user_id = ? AND concept_id = ?
            """,
            (user_id, concept_id),
        ).fetchone()
        if current:
            new_score = max(0, min(100, current["mastery_score"] + delta))
            wrong_streak = 0 if correct else current["wrong_streak"] + 1
            correct_streak = current["correct_streak"] + 1 if correct else 0
            db.execute(
                """
                UPDATE concept_mastery
                SET mastery_score = ?, last_practiced_at = ?, wrong_streak = ?, correct_streak = ?
                WHERE user_id = ? AND concept_id = ?
                """,
                (new_score, utcnow(), wrong_streak, correct_streak, user_id, concept_id),
            )
        else:
            new_score = max(0, min(100, 50 + delta))
            wrong_streak = 0 if correct else 1
            correct_streak = 1 if correct else 0
            db.execute(
                """
                INSERT INTO concept_mastery (
                    user_id, concept_id, mastery_score, last_practiced_at, wrong_streak, correct_streak
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (user_id, concept_id, new_score, utcnow(), wrong_streak, correct_streak),
            )
        concept = db.execute("SELECT name, unit FROM concepts WHERE id = ?", (concept_id,)).fetchone()
        updates.append(
            {
                "id": concept_id,
                "name": concept["name"] if concept else concept_id,
                "unit": concept["unit"] if concept else "",
                "mastery_score": new_score,
                "wrong_streak": wrong_streak,
                "correct_streak": correct_streak,
                "is_weak": new_score < 70 or wrong_streak >= 2,
            }
        )
    return updates


@app.post("/api/attempts")
def submit_attempt(payload: AttemptRequest, user: dict[str, Any] = Depends(auth_user)) -> dict[str, Any]:
    if payload.mode not in {"lesson", "review"}:
        raise HTTPException(status_code=400, detail="無效的答題模式")
    with get_db() as db:
        row = db.execute("SELECT * FROM questions WHERE id = ?", (payload.question_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="找不到題目")
        expected = set(parse_json(row["answer_json"]))
        option_text_by_id = {
            option["id"]: option["text"] for option in parse_json(row["options_json"])
        }
        selected = set(payload.selected_answer)
        is_correct = selected == expected
        db.execute(
            """
            INSERT INTO attempts (
                user_id, question_id, selected_answer_json, is_correct,
                used_hint, ran_code, elapsed_seconds, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user["id"],
                payload.question_id,
                json.dumps(payload.selected_answer, ensure_ascii=False),
                1 if is_correct else 0,
                1 if payload.used_hint else 0,
                1 if payload.ran_code else 0,
                max(0, payload.elapsed_seconds),
                utcnow(),
            ),
        )
        mastery_updates = update_mastery(db, user["id"], payload.question_id, is_correct, payload.used_hint)
        review_lessons = suggested_lessons_for_question(db, user["id"], payload.question_id)
        if payload.mode == "review":
            session = db.execute(
                "SELECT * FROM review_sessions WHERE id = ? AND user_id = ?",
                (payload.review_session_id, user["id"]),
            ).fetchone() if payload.review_session_id else latest_review_session(db, user["id"])
            if not session:
                raise HTTPException(status_code=400, detail="找不到進行中的總複習紀錄")
            if session["completed_at"]:
                raise HTTPException(status_code=400, detail="這一輪總複習已完成")
            answered = min(REVIEW_SIZE, int(session["answered_count"] or 0) + 1)
            correct = int(session["correct_count"] or 0) + (1 if is_correct else 0)
            now = utcnow()
            db.execute(
                """
                UPDATE review_sessions
                SET answered_count = ?, correct_count = ?, last_answered_at = ?,
                    completed_at = CASE WHEN ? >= ? THEN ? ELSE completed_at END
                WHERE id = ? AND user_id = ?
                """,
                (answered, correct, now, answered, REVIEW_SIZE, now, session["id"], user["id"]),
            )
    return {
        "is_correct": is_correct,
        "answer": list(expected),
        "answer_text": [option_text_by_id[answer] for answer in expected if answer in option_text_by_id],
        "explanation": row["explanation"],
        "common_mistake": row["common_mistake"],
        "mastery_updates": mastery_updates,
        "review_lessons": review_lessons,
    }


def review_summary_data(db: Any, user_id: int, force_unlocked: bool = False) -> dict[str, Any]:
    unlocked, completed, total_lessons = review_unlocked(db, user_id)
    stats = question_attempt_stats(db, user_id)
    practiced = len(stats)
    wrong_questions = sum(1 for item in stats.values() if item["wrong"] > 0)
    high_error_rows = db.execute(
        """
        SELECT q.id, q.stem, q.source_file,
               COUNT(a.id) AS attempts,
               SUM(CASE WHEN a.is_correct = 0 THEN 1 ELSE 0 END) AS wrong
        FROM attempts a
        JOIN questions q ON q.id = a.question_id
        WHERE a.user_id = ?
        GROUP BY q.id, q.stem, q.source_file
        HAVING SUM(CASE WHEN a.is_correct = 0 THEN 1 ELSE 0 END) > 0
        ORDER BY (SUM(CASE WHEN a.is_correct = 0 THEN 1.0 ELSE 0 END) + 2.0)
                 / (COUNT(a.id) + 4.0) DESC,
                 COUNT(a.id) DESC
        LIMIT 5
        """,
        (user_id,),
    ).fetchall()
    high_error_questions = []
    for row in high_error_rows:
        item = dict(row)
        item["error_rate"] = round((item["wrong"] + 2) / (item["attempts"] + 4) * 100, 1)
        high_error_questions.append(item)
    review_session = review_session_payload(latest_review_session(db, user_id))
    return {
        "unlocked": unlocked or force_unlocked,
        "completed_lessons": completed,
        "total_lessons": total_lessons,
        "practiced_questions": practiced,
        "wrong_questions": wrong_questions,
        "high_error_questions": high_error_questions,
        "review_session": review_session,
    }


@app.get("/api/review/status")
def review_status(user: dict[str, Any] = Depends(auth_user)) -> dict[str, Any]:
    with get_db() as db:
        return review_summary_data(db, user["id"], force_unlocked=user["role"] == "admin")


@app.post("/api/review/start")
def start_review(user: dict[str, Any] = Depends(auth_user)) -> dict[str, Any]:
    with get_db() as db:
        unlocked, _, _ = review_unlocked(db, user["id"])
        if user["role"] != "admin" and not unlocked:
            raise HTTPException(status_code=403, detail="請先完成全部課程")
        now = utcnow()
        db.execute(
            "INSERT INTO review_sessions (user_id, started_at) VALUES (?, ?)",
            (user["id"], now),
        )
        session = latest_review_session(db, user["id"])
        return {"session": review_session_payload(session)}


@app.get("/api/review/summary")
def review_summary(user: dict[str, Any] = Depends(auth_user)) -> dict[str, Any]:
    with get_db() as db:
        return review_summary_data(db, user["id"], force_unlocked=user["role"] == "admin")


@app.get("/api/dashboard")
def dashboard(user: dict[str, Any] = Depends(auth_user)) -> dict[str, Any]:
    with get_db() as db:
        total = db.execute(
            "SELECT COUNT(*) AS count FROM attempts WHERE user_id = ?",
            (user["id"],),
        ).fetchone()["count"]
        correct = db.execute(
            "SELECT COUNT(*) AS count FROM attempts WHERE user_id = ? AND is_correct = 1",
            (user["id"],),
        ).fetchone()["count"]
        weak_rows = db.execute(
            """
            SELECT c.id, c.name, c.unit, cm.mastery_score, cm.wrong_streak, cm.correct_streak
            FROM concept_mastery cm
            JOIN concepts c ON c.id = cm.concept_id
            WHERE cm.user_id = ? AND (cm.mastery_score < 70 OR cm.wrong_streak >= 2)
            ORDER BY cm.mastery_score ASC, cm.wrong_streak DESC, c.id
            LIMIT 12
            """,
            (user["id"],),
        ).fetchall()
        recent = db.execute(
            """
            SELECT a.id, a.question_id, q.stem, a.is_correct, a.elapsed_seconds, a.created_at
            FROM attempts a
            JOIN questions q ON q.id = a.question_id
            WHERE a.user_id = ?
            ORDER BY a.id DESC
            LIMIT 10
            """,
            (user["id"],),
        ).fetchall()
        weak_concepts = []
        for row in weak_rows:
            item = dict(row)
            item["review_lesson"] = suggested_lesson_for_concept(db, user["id"], row["id"])
            weak_concepts.append(item)
    return {
        "total_attempts": total,
        "correct_attempts": correct,
        "accuracy": round(correct / total * 100, 1) if total else 0,
        "weak_concepts": weak_concepts,
        "recent_attempts": [dict(row) for row in recent],
    }


@app.get("/api/admin/students")
def admin_students(_admin: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    with get_db() as db:
        rows = db.execute(
            """
            SELECT u.id, u.username, u.display_name,
                   COUNT(a.id) AS total_attempts,
                   SUM(CASE WHEN a.is_correct = 1 THEN 1 ELSE 0 END) AS correct_attempts,
                   (SELECT COUNT(*) FROM review_sessions rs WHERE rs.user_id = u.id) AS review_rounds,
                   (SELECT rs.answered_count FROM review_sessions rs
                    WHERE rs.user_id = u.id ORDER BY rs.id DESC LIMIT 1) AS review_answered,
                   (SELECT rs.correct_count FROM review_sessions rs
                    WHERE rs.user_id = u.id ORDER BY rs.id DESC LIMIT 1) AS review_correct,
                   (SELECT rs.started_at FROM review_sessions rs
                    WHERE rs.user_id = u.id ORDER BY rs.id DESC LIMIT 1) AS review_started_at,
                   (SELECT rs.completed_at FROM review_sessions rs
                    WHERE rs.user_id = u.id ORDER BY rs.id DESC LIMIT 1) AS review_completed_at,
                   (SELECT rs.last_answered_at FROM review_sessions rs
                    WHERE rs.user_id = u.id ORDER BY rs.id DESC LIMIT 1) AS review_last_answered_at,
                   (SELECT COUNT(*) FROM projects p WHERE p.is_active = 1) AS project_total,
                   (SELECT COUNT(*) FROM project_progress pp
                    JOIN projects p ON p.id = pp.project_id
                    WHERE pp.user_id = u.id AND p.is_active = 1 AND pp.status = 'completed') AS project_completed,
                   (SELECT COUNT(*) FROM project_progress pp
                    JOIN projects p ON p.id = pp.project_id
                    WHERE pp.user_id = u.id AND p.is_active = 1 AND pp.status = 'in_progress') AS project_in_progress,
                   (SELECT pp.last_activity_at FROM project_progress pp
                    WHERE pp.user_id = u.id ORDER BY pp.last_activity_at DESC LIMIT 1) AS project_last_activity_at
            FROM users u
            LEFT JOIN attempts a ON a.user_id = u.id
            WHERE u.role IN ('student', 'learner')
            GROUP BY u.id
            ORDER BY u.id
            """
        ).fetchall()
    students = []
    for row in rows:
        total = row["total_attempts"] or 0
        correct = row["correct_attempts"] or 0
        item = dict(row)
        item["accuracy"] = round(correct / total * 100, 1) if total else 0
        answered = int(item["review_answered"] or 0)
        item["review_answered"] = answered
        item["review_correct"] = int(item["review_correct"] or 0)
        item["review_answer_rate"] = round(answered / REVIEW_SIZE * 100, 1)
        if not item["review_rounds"]:
            item["review_status"] = "not_started"
        elif item["review_completed_at"]:
            item["review_status"] = "completed"
        else:
            item["review_status"] = "in_progress"
        item["project_total"] = int(item["project_total"] or 0)
        item["project_completed"] = int(item["project_completed"] or 0)
        item["project_in_progress"] = int(item["project_in_progress"] or 0)
        students.append(item)
    return {"students": students}


@app.exception_handler(HTTPException)
async def http_exception_handler(_request: Request, exc: HTTPException):
    from fastapi.responses import JSONResponse

    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
