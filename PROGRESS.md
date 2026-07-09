# 計畫進度

最後更新：2026-07-09

## 狀態摘要

- 狀態：本機課程 + 練習 MVP 已完成；26 節課程已重寫成國三升高一可讀的上課講解版，學生可先上課、完成小檢查，再進入對應練習題。
- 主要資料來源：`../02-雄女電資班考題整理/`。
- 目標：把第 1 到第 4 講考題整理先轉成可練習、可追蹤弱點、可在網頁執行 Python 的公開網站，供兩位學生在家登入使用。

## 對應表

| 項目 | 位置 | 狀態 | 備註 |
|---|---|---|---|
| 專案說明 | [README.md](README.md) | 已建立 | 說明用途、資料來源與第一版範圍。 |
| 計畫書 | [PLAN.md](PLAN.md) | 已建立 | 已定義部署範圍、MVP、題庫來源、弱點追蹤、技術架構與部署決策。 |
| 網頁程式 | `app/` | 進行中 | 已建立 FastAPI API、靜態前端、課程頁、練習頁與進度紀錄。 |
| 課程資料 | `content/lessons.json` | 已重寫 | 已從 `../02-雄女電資班考題整理/videos/` 整理第 1 到第 4 講 26 節課程；每節補生活例子、可執行範例與常見誤解。 |
| 題目資料 | `content/questions.json` | 進行中 | 已建立第 1 到第 4 講第一批 23 題。 |
| 檢查工具 | `scripts/check_questions.py` / `scripts/check_lessons.py` / `scripts/check_app_flow.py` | 已建立 | 可檢查題目、課程資料與 API 主流程。 |
| 本機資料庫 | `data/app.db` | 開發用 | 啟動時自動建立，已由 `.gitignore` 排除。 |
| 部署設定 | `render.yaml` / [DEPLOYMENT.md](DEPLOYMENT.md) | 已建立 | Render Blueprint：FastAPI Web Service + PostgreSQL。 |

## 下一步

1. 擴充第 1 到第 4 講題庫，讓每個主要觀念至少有 3 題，並補齊目前沒有小檢查題的課程。
2. 補更完整的管理者弱點檢視，加入課程完成率與最近課程進度。
3. 補更完整的密碼初始化/重設流程，避免正式環境帳號建立後只能靠資料庫處理。
4. 實際建立 Render Blueprint，取得公開網址。
5. 部署後測試登入、課程、作答、Python 執行區與弱點追蹤。

## 已驗證

- `python scripts/check_questions.py`：通過，23 題、32 個觀念。
- `python scripts/check_lessons.py`：通過，26 節課程、39 個觀念、23 個小檢查連結；檢查每節課需有生活例子、可執行範例與足夠解說長度。
- `python scripts/check_app_flow.py`：通過，登入、課程列表、課程進度、依課程取下一題、送出正解、dashboard 查詢皆正常。
- `node --check app/static/app.js`：通過。
- `python -m compileall app scripts`：通過。

## 上線前置

- 已登記上線前置 3 項到 `D:/AI/handoffs/pending/deploy-prerequisites.md`：`ADMIN_PASSWORD`、`STUDENT1_PASSWORD`、`STUDENT2_PASSWORD`。
- 2026-07-09 上線後檢查發現公開站仍可使用開發預設密碼登入；已補 production 安全門檻，正式環境三組密碼未設定或仍是預設值時會拒絕啟動。
