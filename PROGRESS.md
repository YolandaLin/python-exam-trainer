# 計畫進度

最後更新：2026-07-09

## 狀態摘要

- 狀態：本機 MVP 已完成，已具備第一版練習流程；下一階段是擴題與部署設定。
- 主要資料來源：`../02-雄女電資班考題整理/`。
- 目標：把第 1 到第 4 講考題整理先轉成可練習、可追蹤弱點、可在網頁執行 Python 的公開網站，供兩位學生在家登入使用。

## 對應表

| 項目 | 位置 | 狀態 | 備註 |
|---|---|---|---|
| 專案說明 | [README.md](README.md) | 已建立 | 說明用途、資料來源與第一版範圍。 |
| 計畫書 | [PLAN.md](PLAN.md) | 已建立 | 已定義部署範圍、MVP、題庫來源、弱點追蹤、技術架構與部署決策。 |
| 網頁程式 | `app/` | 進行中 | 已建立 FastAPI API 與靜態前端頁面。 |
| 題目資料 | `content/questions.json` | 進行中 | 已建立第 1 到第 4 講第一批 23 題。 |
| 檢查工具 | `scripts/check_questions.py` / `scripts/check_app_flow.py` | 已建立 | 可檢查題目格式、答案、觀念標籤與 API 主流程。 |
| 本機資料庫 | `data/app.db` | 開發用 | 啟動時自動建立，已由 `.gitignore` 排除。 |

## 下一步

1. 擴充第 1 到第 4 講題庫，讓每個主要觀念至少有 3 題。
2. 補更完整的學生儀表板與管理者弱點檢視。
3. 將本機 SQLite 抽象化，為部署 PostgreSQL 做準備。
4. 補登入密碼初始化/重設流程，避免正式環境使用開發密碼。
5. 部署採 PaaS + PostgreSQL，優先 Render 或 Railway，不先自架 VPS。

## 已驗證

- `python scripts/check_questions.py`：通過，23 題、32 個觀念。
- `python scripts/check_app_flow.py`：通過，登入、取下一題、送出正解、dashboard 查詢皆正常。
- `python -m compileall app scripts`：通過。
