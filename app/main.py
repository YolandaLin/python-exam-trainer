from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .db import get_db, init_db, session_expiry, utcnow
from .security import new_token, verify_password


ROOT = Path(__file__).resolve().parents[1]
STATIC_DIR = ROOT / "app" / "static"

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


class LessonCompleteRequest(BaseModel):
    checkpoint_correct_count: int = 0
    checkpoint_total_count: int = 0


def parse_json(value: str) -> Any:
    return json.loads(value)


def public_question(row: Any, include_answer: bool = False) -> dict[str, Any]:
    result = {
        "id": row["id"],
        "source_file": row["source_file"],
        "type": row["type"],
        "difficulty": row["difficulty"],
        "stem": row["stem"],
        "code": row["code"],
        "options": parse_json(row["options_json"]),
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


def checkpoint_questions(db: Any, lesson: dict[str, Any]) -> list[dict[str, Any]]:
    question_ids = lesson.get("checkpoint_question_ids", [])
    if not question_ids:
        return []
    placeholders = ",".join("?" for _ in question_ids)
    rows = db.execute(
        f"""
        SELECT q.*,
               GROUP_CONCAT(qc.concept_id) AS concepts
        FROM questions q
        LEFT JOIN question_concepts qc ON qc.question_id = q.id
        WHERE q.id IN ({placeholders}) AND q.is_active = 1
        GROUP BY q.id
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
    return dict(row)


def require_admin(user: dict[str, Any] = Depends(auth_user)) -> dict[str, Any]:
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    return user


def lesson_row(db: Any, user_id: int, lesson_id: str) -> Any:
    row = db.execute(
        """
        SELECT l.*,
               GROUP_CONCAT(lc.concept_id) AS concepts,
               COALESCE(lp.status, 'not_started') AS status,
               lp.last_viewed_at,
               lp.completed_at,
               COALESCE(lp.checkpoint_correct_count, 0) AS checkpoint_correct_count,
               COALESCE(lp.checkpoint_total_count, 0) AS checkpoint_total_count
        FROM lessons l
        LEFT JOIN lesson_concepts lc ON lc.lesson_id = l.id
        LEFT JOIN lesson_progress lp ON lp.lesson_id = l.id AND lp.user_id = ?
        WHERE l.id = ? AND l.is_active = 1
        GROUP BY l.id
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
def login(payload: LoginRequest) -> dict[str, Any]:
    with get_db() as db:
        user = db.execute("SELECT * FROM users WHERE username = ?", (payload.username,)).fetchone()
        if not user or not verify_password(payload.password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="帳號或密碼錯誤")
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
            """
            SELECT l.*,
                   GROUP_CONCAT(lc.concept_id) AS concepts,
                   COALESCE(lp.status, 'not_started') AS status,
                   lp.last_viewed_at,
                   lp.completed_at,
                   COALESCE(lp.checkpoint_correct_count, 0) AS checkpoint_correct_count,
                   COALESCE(lp.checkpoint_total_count, 0) AS checkpoint_total_count
            FROM lessons l
            LEFT JOIN lesson_concepts lc ON lc.lesson_id = l.id
            LEFT JOIN lesson_progress lp ON lp.lesson_id = l.id AND lp.user_id = ?
            WHERE l.is_active = 1
            GROUP BY l.id
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
        lesson_row(db, user["id"], lesson_id)
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
                max(0, payload.checkpoint_correct_count),
                max(0, payload.checkpoint_total_count),
            ),
        )
        return {"lesson": public_lesson(lesson_row(db, user["id"], lesson_id), include_content=True)}


def question_rows(db: Any) -> list[Any]:
    return db.execute(
        """
        SELECT q.*,
               GROUP_CONCAT(qc.concept_id) AS concepts
        FROM questions q
        LEFT JOIN question_concepts qc ON qc.question_id = q.id
        WHERE q.is_active = 1
        GROUP BY q.id
        ORDER BY q.id
        """
    ).fetchall()


def mastery_map(db: Any, user_id: int) -> dict[str, int]:
    rows = db.execute(
        "SELECT concept_id, mastery_score FROM concept_mastery WHERE user_id = ?",
        (user_id,),
    ).fetchall()
    return {row["concept_id"]: row["mastery_score"] for row in rows}


def recent_question_ids(db: Any, user_id: int) -> set[str]:
    rows = db.execute(
        """
        SELECT question_id
        FROM attempts
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 8
        """,
        (user_id,),
    ).fetchall()
    return {row["question_id"] for row in rows}


def choose_next_question(db: Any, user_id: int, lesson_id: str | None = None) -> Any:
    questions = question_rows(db)
    if not questions:
        raise HTTPException(status_code=404, detail="題庫尚未建立")

    if lesson_id:
        lesson = lesson_row(db, user_id, lesson_id)
        concepts = lesson_concepts(db, lesson_id)
        source_file = lesson["source_file"]
        scoped_questions = [
            question
            for question in questions
            if question["source_file"] == source_file
            or concepts.intersection((question["concepts"] or "").split(","))
        ]
        if scoped_questions:
            questions = scoped_questions

    mastery = mastery_map(db, user_id)
    recent = recent_question_ids(db, user_id)
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

        seen = db.execute(
            "SELECT COUNT(*) AS count FROM attempts WHERE user_id = ? AND question_id = ?",
            (user_id, question["id"]),
        ).fetchone()["count"]
        score = (100 - avg) + (18 if seen == 0 else 0) + gate + random.random() * 12
        if question["id"] in recent:
            score -= 35
        scored.append((score, question))

    scored.sort(key=lambda item: item[0], reverse=True)
    pool = [question for _, question in scored[: min(5, len(scored))]]
    return random.choice(pool)


@app.get("/api/next-question")
def next_question(lesson_id: str | None = None, user: dict[str, Any] = Depends(auth_user)) -> dict[str, Any]:
    with get_db() as db:
        row = choose_next_question(db, user["id"], lesson_id)
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
    with get_db() as db:
        row = db.execute("SELECT * FROM questions WHERE id = ?", (payload.question_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="找不到題目")
        expected = set(parse_json(row["answer_json"]))
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
    return {
        "is_correct": is_correct,
        "answer": list(expected),
        "explanation": row["explanation"],
        "common_mistake": row["common_mistake"],
        "mastery_updates": mastery_updates,
        "review_lessons": review_lessons,
    }


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
                   SUM(CASE WHEN a.is_correct = 1 THEN 1 ELSE 0 END) AS correct_attempts
            FROM users u
            LEFT JOIN attempts a ON a.user_id = u.id
            WHERE u.role = 'student'
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
        students.append(item)
    return {"students": students}


@app.exception_handler(HTTPException)
async def http_exception_handler(_request: Request, exc: HTTPException):
    from fastapi.responses import JSONResponse

    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
