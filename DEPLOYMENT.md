# 部署說明

目前部署目標：Render Blueprint。

## Render 部署流程

1. 確認最新程式已推到 GitHub：
   `https://github.com/YolandaLin/python-exam-trainer`
2. 登入 Render。
3. 選擇 Blueprint，連到此 GitHub repo。
4. Render 會讀取 repo 根目錄的 `render.yaml`，建立：
   - Web Service：`python-exam-trainer`
   - PostgreSQL：`python-exam-trainer-db`
5. 初次建立 Blueprint 時，Render 會要求輸入下列 secret：
   - `ADMIN_PASSWORD`
   - `STUDENT1_PASSWORD`
   - `STUDENT2_PASSWORD`
6. 部署完成後，打開 Render 提供的 `https://*.onrender.com` 網址。

## 正式環境資料庫

正式環境使用 PostgreSQL：

- `DATABASE_URL` 由 `render.yaml` 自動從 Render Postgres 連線字串帶入。
- 本機開發仍可用 SQLite 的 `DB_PATH=data/app.db`。
- 網站啟動時會自動建立資料表，並匯入課程與題庫。

## 注意事項

- 不要在正式環境使用 `admin123` 或 `student123`。
- Pyodide 由瀏覽器從 CDN 載入，學生端瀏覽器需要能連網。
- Render 免費 Web Service 可能會休眠，第一次開啟可能較慢。
