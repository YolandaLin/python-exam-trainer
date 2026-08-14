from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.db import BLOCKED_PRODUCTION_PASSWORDS, get_db  # noqa: E402
from app.security import hash_password  # noqa: E402


MIN_PASSWORD_LENGTH = 12


def validate_new_password(password: str) -> None:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"新密碼至少需要 {MIN_PASSWORD_LENGTH} 個字元")
    if password in BLOCKED_PRODUCTION_PASSWORDS:
        raise ValueError("不可使用開發環境預設密碼")


def reset_user_password(username: str, password: str) -> int:
    normalized_username = username.strip()
    if not normalized_username:
        raise ValueError("帳號不可空白")
    validate_new_password(password)

    with get_db() as db:
        user = db.execute(
            "SELECT id FROM users WHERE username = ?",
            (normalized_username,),
        ).fetchone()
        if not user:
            raise LookupError(f"找不到帳號：{normalized_username}")
        db.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (hash_password(password), user["id"]),
        )
        return int(user["id"])


def main() -> None:
    parser = argparse.ArgumentParser(description="安全地重設既有帳號密碼")
    parser.add_argument("--username", required=True, help="要重設的帳號")
    args = parser.parse_args()

    password = getpass.getpass("新密碼：")
    confirmation = getpass.getpass("再次輸入新密碼：")
    if password != confirmation:
        parser.exit(1, "錯誤：兩次輸入的密碼不一致\n")
    try:
        reset_user_password(args.username, password)
    except (LookupError, ValueError) as error:
        parser.exit(1, f"錯誤：{error}\n")
    print(f"已更新帳號 {args.username.strip()} 的密碼。")


if __name__ == "__main__":
    main()
