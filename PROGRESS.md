# 計畫進度

最後更新：2026-07-09

## 狀態摘要

- 狀態：已部署到 Render；第 1 到第 4 講課程 + 練習 MVP 可用。26 節課程已重寫成國三升高一可讀的上課講解版，並補到每節課至少 3 題小檢查/練習題，學生可先上課、完成小檢查，再進入對應練習題。
- 主要資料來源：`../02-雄女電資班考題整理/`。
- 目標：把第 1 到第 4 講考題整理先轉成可練習、可追蹤弱點、可在網頁執行 Python 的公開網站，供兩位學生在家登入使用。
- 公開網址：`https://python-exam-trainer.onrender.com/`。
- GitHub：`https://github.com/YolandaLin/python-exam-trainer`。

## 對應表

| 項目 | 位置 | 狀態 | 備註 |
|---|---|---|---|
| 專案說明 | [README.md](README.md) | 已建立 | 說明用途、資料來源與第一版範圍。 |
| 計畫書 | [PLAN.md](PLAN.md) | 已建立 | 已定義部署範圍、MVP、題庫來源、弱點追蹤、技術架構與部署決策。 |
| 網頁程式 | `app/` | 進行中 | 已建立 FastAPI API、靜態前端、課程頁、練習頁與進度紀錄。 |
| 課程資料 | `content/lessons.json` | 已重寫 | 已從 `../02-雄女電資班考題整理/videos/` 整理第 1 到第 4 講 26 節課程；每節補生活例子、可執行範例與常見誤解。 |
| 題目資料 | `content/questions.json` / `content/questions_1_4_extra.json` | 已補密度 | 第 1 到第 4 講共 78 題；26 節課每節至少 3 題。 |
| 檢查工具 | `scripts/check_questions.py` / `scripts/check_lessons.py` / `scripts/check_app_flow.py` | 已建立 | 可檢查題目、課程資料與 API 主流程；輸出預測題會實際執行程式片段比對答案。 |
| 本機資料庫 | `data/app.db` | 開發用 | 啟動時自動建立，已由 `.gitignore` 排除。 |
| 部署設定 | `render.yaml` / [DEPLOYMENT.md](DEPLOYMENT.md) | 已上線 | Render Blueprint：FastAPI Web Service + PostgreSQL；正式密碼已由使用者於 Render Environment 設定，不寫入 Git。 |
| README 帳密處理 | [README.md](README.md) | 已完成 | 已移除密碼欄位，只保留帳號名稱；密碼只放 Render Environment，不寫入 Git。 |

## 下一步

1. 補更完整的管理者弱點檢視，加入課程完成率與最近課程進度。
2. 補更完整的密碼初始化/重設流程，避免正式環境帳號建立後只能靠資料庫處理。
3. 觀察 Render 免費方案休眠狀況；若學生使用體驗不佳，再評估升級或改部署方案。
4. 等 `../02-雄女電資班考題整理/` 後續講次整理穩定後，逐批補第 5 講以後課程與題庫。

## 已驗證

- `python scripts/check_questions.py`：通過，78 題、39 個觀念；會檢查第 1 到第 4 講每個來源小節至少 3 題，並實際執行輸出預測題比對答案。
- `python scripts/check_lessons.py`：通過，26 節課程、39 個觀念、78 個小檢查連結；檢查每節課需有生活例子、可執行範例、足夠解說長度與至少 3 題小檢查。
- `python scripts/check_app_flow.py`：通過，登入、課程列表、課程進度、依課程取下一題、送出正解、dashboard 查詢皆正常。
- `node --check app/static/app.js`：通過。
- `python -m compileall app scripts`：通過。
- 正式密碼字串掃描：通過，未寫入 Git 工作區。
- Render 公開站：`/health`、首頁、`/static/app.js` 皆回 200。
- Render 公開站：`admin/admin123`、`student1/student123` 已被 production 登入門檻拒絕。
- 正式帳號：使用者已確認可正常登入使用。

## 上線前置

- 已登記上線前置 3 項到 `D:/AI/handoffs/pending/deploy-prerequisites.md`：`ADMIN_PASSWORD`、`STUDENT1_PASSWORD`、`STUDENT2_PASSWORD`。
- 2026-07-09 上線後檢查發現公開站仍可使用開發預設密碼登入；已補 production 安全門檻，正式環境會拒絕 `admin123` / `student123` 登入，並可用 Render env vars 更新既有帳號密碼。
- 使用者已表示正式環境密碼已更換；密碼不落檔、不提交 Git。

## 今日交接重點

- Git 狀態：03 專案進度已推上 `main`，下一次接手以 `git log -1` 為準。
- 正式網址：`https://python-exam-trainer.onrender.com/`。
- 已完成：課程優先流程、26 節初學者版課程、78 題第 1 到第 4 講題庫、每節 3 題小檢查、Render 部署、PostgreSQL 支援、production 預設密碼阻擋、README 移除密碼欄。
- 下次接手先做：補管理者弱點檢視與課程完成率；之後再做密碼初始化/重設流程，或等第 5 講以後教材穩定後續補題庫。
