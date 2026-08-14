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
   - 此 PostgreSQL 同時提供 04 英文單字學習網站使用；04 的 Blueprint 只引用，不會再建立第二個資料庫。
5. 初次建立 Blueprint 時，Render 會要求輸入下列 secret：
- `ADMIN_PASSWORD`
- `STUDENT1_PASSWORD`
- `STUDENT2_PASSWORD`

若要讓兩個網站登入同一批帳號，03 的 `ADMIN_EMAIL`／`STUDENT1_EMAIL`／`STUDENT2_EMAIL` 與 04 的帳號 Email 要填相同值。密碼環境變數只在帳號不存在時建立初始密碼，不會在每次啟動時覆寫共用帳號的既有密碼。
6. 部署完成後，打開 Render 提供的 `https://*.onrender.com` 網址。

## 正式環境資料庫

正式環境使用 PostgreSQL：

- `DATABASE_URL` 由 `render.yaml` 自動從 Render Postgres 連線字串帶入。
- 04 專案使用相同的 `DATABASE_URL`；兩個網站的帳號資料共用，03 的題庫資料與 04 的單字資料則使用各自的資料表。
- 本機開發仍可用 SQLite 的 `DB_PATH=data/app.db`。
- 網站啟動時會自動建立資料表，並匯入課程與題庫。

## 注意事項

- 不要在正式環境使用 `admin123` 或 `student123`。
- `APP_ENV=production` 時，三組密碼環境變數都必須存在、不得空白，也不得使用 `admin123` / `student123`；不符合時服務會拒絕啟動。
- 三組密碼環境變數是建立帳號時的初始值。既有帳號的密碼雜湊不會因重新部署或其他共用資料庫服務啟動而被改寫。
- 若 Blueprint 已經建立過，`sync: false` 的密碼值不會靠 Git push 自動更新。請到 Render Web Service 的 Environment 手動設定三組密碼後，重新部署。
- 若要輪替既有帳號密碼，先連到目標資料庫，再執行 `python scripts/reset_password.py --username 帳號`，依提示輸入兩次新密碼。密碼由互動提示讀取，不會出現在命令列參數中。
- 輪替後也應把對應的 Render 密碼 secret 更新成相同值，供未來重建空資料庫時建立初始帳號；重新部署本身不會重設既有密碼。
- Pyodide 由瀏覽器從 CDN 載入，學生端瀏覽器需要能連網。
- Render 免費 Web Service 可能會休眠，第一次開啟可能較慢。
