# python-exam-trainer

暫時 FOR 雄女電資班考題練習。

這裡是 Python 複習題網站專案，和課程教材、考題整理分開維護。

計畫書見 [PLAN.md](PLAN.md)，計畫進度見 [PROGRESS.md](PROGRESS.md)。

## 目錄

- `app/`：網頁程式碼。
- `content/`：題目、解析與可匯入資料。
- `scripts/`：資料轉換、檢查與產生工具。

## 資料來源

初期課程與題目資料可從 `../02-雄女電資班考題整理/` 的筆記整理轉出。

第一版先使用第 1 到第 4 講課程與題庫，部署成公開網站供兩位學生在家登入使用。

## 本機啟動

```bash
pip install -r requirements.txt
python scripts/check_questions.py
python scripts/check_lessons.py
python scripts/check_app_flow.py
python -m uvicorn app.main:app --reload
```

開啟：

```text
http://127.0.0.1:8000
```

## 開發用預設帳號

若沒有設定環境變數，系統會建立下列開發用帳號：

| 角色 | 帳號 | 密碼 |
|---|---|---|
| 管理者 | `admin` | `admin123` |
| 學生 | `student1` | `student123` |
| 學生 | `student2` | `student123` |

正式部署前必須用環境變數覆蓋密碼，參考 [.env.example](.env.example)。

## 第一版功能

- 登入 / 登出。
- 登入後先看到下一堂課。
- 第 1 到第 4 講共 26 節短課程。
- 課程內可把範例程式放到 Python 執行區試跑。
- 課後小檢查會記錄答題結果。
- 完成課程後進入對應練習題。
- 一次出一題。
- 作答後立即顯示正解、解析與常見錯因。
- 答錯後可連回建議重讀課程。
- 依觀念更新熟練度與弱點。
- 儀表板顯示答題數、正確率、薄弱觀念。
- 管理者可看兩位學生簡表。
- 網頁 Python 執行區使用 Pyodide，在瀏覽器端執行。
