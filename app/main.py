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


def choose_next_question(db: Any, user_id: int) -> Any:
    questions = question_rows(db)
    if not questions:
        raise HTTPException(status_code=404, detail="題庫尚未建立")

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
def next_question(user: dict[str, Any] = Depends(auth_user)) -> dict[str, Any]:
    with get_db() as db:
        row = choose_next_question(db, user["id"])
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
    return {
        "is_correct": is_correct,
        "answer": list(expected),
        "explanation": row["explanation"],
        "common_mistake": row["common_mistake"],
        "mastery_updates": mastery_updates,
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
    return {
        "total_attempts": total,
        "correct_attempts": correct,
        "accuracy": round(correct / total * 100, 1) if total else 0,
        "weak_concepts": [dict(row) for row in weak_rows],
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
