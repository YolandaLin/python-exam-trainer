from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Iterator

from .security import hash_password


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = Path(os.environ.get("DB_PATH", ROOT / "data" / "app.db"))
QUESTIONS_PATH = ROOT / "content" / "questions.json"


def utcnow() -> str:
    return datetime.now(UTC).isoformat()


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def get_db() -> Iterator[sqlite3.Connection]:
    conn = connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with get_db() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('student', 'admin')),
                display_name TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS questions (
                id TEXT PRIMARY KEY,
                source_file TEXT NOT NULL,
                type TEXT NOT NULL,
                difficulty INTEGER NOT NULL,
                stem TEXT NOT NULL,
                code TEXT NOT NULL DEFAULT '',
                options_json TEXT NOT NULL,
                answer_json TEXT NOT NULL,
                explanation TEXT NOT NULL,
                common_mistake TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS concepts (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                unit TEXT NOT NULL DEFAULT '',
                description TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS question_concepts (
                question_id TEXT NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
                concept_id TEXT NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
                weight REAL NOT NULL DEFAULT 1.0,
                PRIMARY KEY (question_id, concept_id)
            );

            CREATE TABLE IF NOT EXISTS attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                question_id TEXT NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
                selected_answer_json TEXT NOT NULL,
                is_correct INTEGER NOT NULL,
                used_hint INTEGER NOT NULL DEFAULT 0,
                ran_code INTEGER NOT NULL DEFAULT 0,
                elapsed_seconds INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS concept_mastery (
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                concept_id TEXT NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
                mastery_score INTEGER NOT NULL DEFAULT 50,
                last_practiced_at TEXT,
                wrong_streak INTEGER NOT NULL DEFAULT 0,
                correct_streak INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (user_id, concept_id)
            );
            """
        )

    seed_questions()
    seed_users()


def concept_name(concept_id: str) -> str:
    return concept_id.replace("-", " ")


def unit_from_source(source_file: str) -> str:
    if source_file.startswith("01-"):
        return "第 1 講"
    if source_file.startswith("02-"):
        return "第 2 講"
    if source_file.startswith("03-"):
        return "第 3 講"
    if source_file.startswith("04-"):
        return "第 4 講"
    return ""


def seed_questions() -> None:
    questions = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    with get_db() as db:
        for question in questions:
            db.execute(
                """
                INSERT INTO questions (
                    id, source_file, type, difficulty, stem, code, options_json,
                    answer_json, explanation, common_mistake, is_active
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                ON CONFLICT(id) DO UPDATE SET
                    source_file=excluded.source_file,
                    type=excluded.type,
                    difficulty=excluded.difficulty,
                    stem=excluded.stem,
                    code=excluded.code,
                    options_json=excluded.options_json,
                    answer_json=excluded.answer_json,
                    explanation=excluded.explanation,
                    common_mistake=excluded.common_mistake,
                    is_active=1
                """,
                (
                    question["id"],
                    question["source_file"],
                    question["type"],
                    question["difficulty"],
                    question["stem"],
                    question.get("code", ""),
                    json.dumps(question["options"], ensure_ascii=False),
                    json.dumps(question["answer"], ensure_ascii=False),
                    question["explanation"],
                    question["common_mistake"],
                ),
            )
            db.execute("DELETE FROM question_concepts WHERE question_id = ?", (question["id"],))
            for concept_id in question["concepts"]:
                db.execute(
                    """
                    INSERT INTO concepts (id, name, unit, description)
                    VALUES (?, ?, ?, '')
                    ON CONFLICT(id) DO UPDATE SET
                        name=excluded.name,
                        unit=CASE WHEN concepts.unit = '' THEN excluded.unit ELSE concepts.unit END
                    """,
                    (concept_id, concept_name(concept_id), unit_from_source(question["source_file"])),
                )
                db.execute(
                    "INSERT INTO question_concepts (question_id, concept_id, weight) VALUES (?, ?, 1.0)",
                    (question["id"], concept_id),
                )


def seed_users() -> None:
    defaults = [
        (
            os.environ.get("ADMIN_USERNAME", "admin"),
            os.environ.get("ADMIN_PASSWORD", "admin123"),
            "admin",
            "管理者",
        ),
        (
            os.environ.get("STUDENT1_USERNAME", "student1"),
            os.environ.get("STUDENT1_PASSWORD", "student123"),
            "student",
            "學生一",
        ),
        (
            os.environ.get("STUDENT2_USERNAME", "student2"),
            os.environ.get("STUDENT2_PASSWORD", "student123"),
            "student",
            "學生二",
        ),
    ]
    with get_db() as db:
        for username, password, role, display_name in defaults:
            exists = db.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
            if exists:
                continue
            db.execute(
                """
                INSERT INTO users (username, password_hash, role, display_name, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (username, hash_password(password), role, display_name, utcnow()),
            )


def session_expiry() -> str:
    return (datetime.now(UTC) + timedelta(days=7)).isoformat()
