# Python 複習題網站計畫書

最後更新：2026-07-08

## 1. 專案定位

本網站是給兩位國三升高一學生使用的 Python 複習與診斷系統，目標是精熟雄女電資班初試範圍。

學生起點假設為完全不懂程式，因此網站不能只做成一般題庫列表，而要用「一次一題、由淺入深、答完立即回饋」的方式，引導學生逐步建立語法觀念、輸出判斷能力與除錯能力。

## 2. 使用者與部署範圍

- 使用者：兩位學生。
- 帳號：由管理者預先建立，不開放自行註冊。
- 密碼：不得明文保存，只保存雜湊值。
- 使用方式：部署到公開網站，讓學生在家登入使用。
- 管理者：可匯入題目、檢視兩位學生的學習進度與弱點。

## 3. 題庫來源

第一版題庫來源為：

- `../02-雄女電資班考題整理/videos/01-01-programming-language-intro.md`
- `../02-雄女電資班考題整理/videos/01-02-python-intro.md`
- `../02-雄女電資班考題整理/videos/01-03-install-python-runtime.md`
- `../02-雄女電資班考題整理/videos/01-04-python-shell.md`
- `../02-雄女電資班考題整理/videos/01-05-functions-intro.md`
- `../02-雄女電資班考題整理/videos/01-06-object-oriented-intro.md`
- `../02-雄女電資班考題整理/videos/02-01-basic-data-types.md`
- `../02-雄女電資班考題整理/videos/02-02-operators.md`
- `../02-雄女電資班考題整理/videos/03-01-print.md`
- `../02-雄女電資班考題整理/videos/03-02-input.md`
- `../02-雄女電資班考題整理/videos/03-03-ascii-escape.md`
- `../02-雄女電資班考題整理/videos/03-04-unicode.md`
- `../02-雄女電資班考題整理/videos/03-05-string-basic-ops.md`
- `../02-雄女電資班考題整理/videos/03-06-string-formatting.md`
- `../02-雄女電資班考題整理/videos/03-07-string-search.md`
- `../02-雄女電資班考題整理/videos/03-08-string-case-align-split.md`
- `../02-雄女電資班考題整理/videos/04-01-containers-overview.md`
- `../02-雄女電資班考題整理/videos/04-02-list-ops-1.md`
- `../02-雄女電資班考題整理/videos/04-03-list-add-update-delete.md`
- `../02-雄女電資班考題整理/videos/04-04-list-sort.md`
- `../02-雄女電資班考題整理/videos/04-05-multidimensional-list.md`
- `../02-雄女電資班考題整理/videos/04-06-list-functions-methods.md`
- `../02-雄女電資班考題整理/videos/04-07-tuple.md`
- `../02-雄女電資班考題整理/videos/04-08-tuple-list-builtins.md`
- `../02-雄女電資班考題整理/videos/04-09-dict.md`
- `../02-雄女電資班考題整理/videos/04-10-set.md`

第 5 到第 10 講後續等筆記校對完成後，再逐批補進題庫。

外部題庫只作為形式參考，不直接搬題：

- W3Schools Python Quiz：固定題數、最後計分的基本 quiz 形式。
- PYnative Python Quizzes：分主題、每題解析、用來找出弱點。
- GeeksforGeeks Python MCQ：依變數、運算子、資料型態、list、string、dict、set、function 等主題分類。
- Sanfoundry Python MCQ：大量題庫，適合參考章節化與考試導向編排。

參考連結：

- http://exam.bestdaylong.com/test3359.htm
- https://www.w3schools.com/python/python_quiz.asp
- https://www.geeksforgeeks.org/python/python-multiple-choice-questions/
- https://pynative.com/python/quizzes/
- https://www.sanfoundry.com/1000-python-questions-answers/

## 4. 第一版學習範圍

第一版只做第 1 到第 4 講，目標不是一次做完整網站，而是先讓學生開始練習，並驗證題目分級與弱點追蹤是否有效。

第一版觀念範圍：

| 單元 | 內容 |
|---|---|
| 第 1 講 | 程式語言、Python 由來、安裝、shell、函式、物件導向基本觀念 |
| 第 2 講 | 基本資料型態、型態轉換、運算子 |
| 第 3 講 | `print()`、`input()`、ASCII、Unicode、字串索引切片、格式化、查詢、切割 |
| 第 4 講 | list、tuple、dict、set 與常見方法 |

## 5. 題目設計原則

題目必須符合國三升高一、完全初學者的理解順序。

每個觀念至少規劃三層題目：

1. 定義題：確認學生知道名詞與用途。
2. 判斷題：給一行或短程式，判斷結果。
3. 陷阱題：針對常見錯誤設計選項。

題型：

| 題型 | 用途 |
|---|---|
| 單選題 | 第一版主力題型，適合快速診斷觀念 |
| 多選題 | 適合語法規則、特性比較 |
| 輸出預測題 | 給程式碼，問執行結果 |
| 錯誤判斷題 | 給錯誤程式，問錯誤原因 |
| 程式碼操作題 | 學生可在網頁輸入程式碼並執行 |

每題都必須有：

- 題目文字
- 選項或程式碼輸入區
- 正確答案
- 解析
- 常見錯因
- 觀念標籤
- 難度
- 來源筆記
- 是否可用程式碼執行輔助驗證

## 6. 難度分級

| 難度 | 定義 | 例子 |
|---:|---|---|
| 1 | 名詞與基本規則 | `input()` 回傳什麼型態？ |
| 2 | 單行輸出判斷 | `10 // 3` 的結果 |
| 3 | 2 到 5 行程式追蹤 | 變數重新指定後 `type()` 結果 |
| 4 | 混合觀念 | `input()` + `int()` + 運算子 |
| 5 | 接近考題陷阱 | 字串、list、dict、set 混合判斷 |

初始出題從難度 1、2 開始。學生在同一觀念連續答對後，才逐步提高難度。

## 7. 弱點追蹤與自適應出題

系統要記錄每一次作答：

- 使用者
- 題目
- 作答時間
- 是否答對
- 選擇的答案
- 是否看提示
- 是否執行程式碼
- 作答花費秒數
- 對應觀念標籤

每個觀念維護一個熟練度分數，範圍 0 到 100。

建議規則：

| 行為 | 分數變化 |
|---|---:|
| 答對 | +8 |
| 看提示後答對 | +3 |
| 答錯 | -12 |
| 同一觀念連錯兩次 | 標記為弱點 |
| 同一觀念連對三次 | 降低出題權重 |

出題權重：

- 熟練度低於 50：優先出基礎題。
- 熟練度 50 到 70：提高該觀念出題頻率。
- 熟練度 70 到 90：正常複習。
- 熟練度高於 90：降低頻率，但仍少量回顧。

每次出題比例建議：

- 60%：弱點觀念
- 25%：目前學習進度的新觀念
- 15%：已熟練觀念複習

## 8. 網頁使用流程

學生登入後直接進入練習頁，不做行銷式首頁。

主要流程：

1. 登入。
2. 系統顯示一題。
3. 學生作答。
4. 系統立即顯示對錯、解析、常見錯因。
5. 若題目含程式碼，可開啟程式碼執行區。
6. 系統記錄本題結果並更新觀念熟練度。
7. 學生按下一題。

頁面必備資訊：

- 題目
- 難度
- 所屬觀念
- 作答區
- 送出按鈕
- 解析區
- 下一題按鈕
- 程式碼執行區
- 今日答題數與正確率

## 9. 程式碼執行設計

網站必須讓學生在網頁輸入 Python 程式碼並看到執行結果。

公開部署後，不建議第一版把學生輸入的 Python 程式碼送到後端伺服器執行，因為這會帶來安全風險，例如無限迴圈、檔案存取、系統命令、資源耗盡。

第一版建議採用 Pyodide，在瀏覽器端以 WebAssembly 執行 Python。Pyodide 官方文件說明它是基於 WebAssembly 的 Python distribution，可在瀏覽器中執行 Python。這符合本專案的初學程式碼練習需求，也能降低伺服器執行任意程式碼的風險。

程式碼執行區第一版限制：

- 預設只支援標準輸出。
- 不支援檔案存取題。
- 不支援網路存取。
- 設定執行逾時。
- 若程式無限迴圈，需能中止。
- 只記錄是否執行與最後輸出，不把學生所有草稿視為正式答案。

## 10. 技術架構與部署決策

第一版部署決策：

- 採用 PaaS 部署，不先自架 VPS。
- 優先選 Render 或 Railway 這類支援 Web Service、HTTPS、環境變數與資料庫的服務。
- 正式資料庫採用 PostgreSQL，不用 SQLite 當正式資料庫。
- FastAPI 後端負責登入、題庫、作答紀錄與弱點分析。
- 前端與 Pyodide 負責網頁互動與瀏覽器端 Python 執行。
- 不在後端執行學生輸入的 Python 程式碼。

這個決策的理由：

- 使用者只有兩位，流量很小，不需要一開始自架伺服器。
- 學生會在家使用，公開網站需要 HTTPS 與穩定部署流程。
- 答題紀錄與弱點資料不能因為服務重啟或重新部署而遺失。
- SQLite 對兩位學生的容量足夠，但在 PaaS 上若沒有正確持久化磁碟，檔案可能遺失；第一版直接使用 PostgreSQL 可降低部署風險。
- 後端執行任意 Python 程式碼風險太高，瀏覽器端 Pyodide 比較適合第一版。

第一版採用：

| 層級 | 建議 |
|---|---|
| 前端 | React 或 SvelteKit |
| Python 執行 | Pyodide，瀏覽器端執行 |
| 後端 | FastAPI |
| 資料庫 | PostgreSQL |
| 部署 | Render 或 Railway 類 PaaS |
| 備援方案 | VPS + Docker Compose + PostgreSQL/SQLite volume |

資料庫選擇：

- 第一版正式部署使用 PostgreSQL。
- 若未來改成自架 VPS，兩位學生用 SQLite 也足夠，但必須放在 Docker volume 或固定磁碟，且要每日備份。
- 若部署平台檔案系統是 ephemeral，不得用本機 SQLite 檔案保存正式作答資料。

登入與安全：

- 密碼只存雜湊。
- 使用 HTTPS。
- Session 或 JWT 都可；第一版以簡單、安全、可維護為優先。
- 管理者與學生權限分開。
- 不開放公開註冊。
- 題庫匯入功能只允許管理者使用。

## 11. 資料模型草案

### users

| 欄位 | 說明 |
|---|---|
| id | 使用者 ID |
| username | 帳號 |
| password_hash | 密碼雜湊 |
| role | `student` 或 `admin` |
| display_name | 顯示名稱 |
| created_at | 建立時間 |

### questions

| 欄位 | 說明 |
|---|---|
| id | 題目 ID |
| source_file | 來源筆記 |
| type | 題型 |
| difficulty | 難度 |
| stem | 題幹 |
| code | 題目程式碼，可空 |
| options_json | 選項 |
| answer_json | 答案 |
| explanation | 解析 |
| common_mistake | 常見錯因 |
| is_active | 是否啟用 |

### concepts

| 欄位 | 說明 |
|---|---|
| id | 觀念 ID |
| name | 觀念名稱 |
| unit | 對應講次 |
| description | 觀念說明 |

### question_concepts

| 欄位 | 說明 |
|---|---|
| question_id | 題目 ID |
| concept_id | 觀念 ID |
| weight | 此觀念在本題的重要程度 |

### attempts

| 欄位 | 說明 |
|---|---|
| id | 作答 ID |
| user_id | 使用者 |
| question_id | 題目 |
| selected_answer_json | 學生答案 |
| is_correct | 是否答對 |
| used_hint | 是否看提示 |
| ran_code | 是否執行程式碼 |
| elapsed_seconds | 作答秒數 |
| created_at | 作答時間 |

### concept_mastery

| 欄位 | 說明 |
|---|---|
| user_id | 使用者 |
| concept_id | 觀念 |
| mastery_score | 熟練度 0 到 100 |
| last_practiced_at | 最近練習時間 |
| wrong_streak | 連錯次數 |
| correct_streak | 連對次數 |

## 12. 題目 JSON 草案

```json
{
  "id": "q-03-02-001",
  "source_file": "03-02-input.md",
  "type": "single_choice",
  "difficulty": 1,
  "concepts": ["input", "type-conversion"],
  "stem": "使用者輸入 2，執行 num = input() 後，num 的型態是什麼？",
  "code": "num = input()",
  "options": [
    {"id": "A", "text": "int"},
    {"id": "B", "text": "float"},
    {"id": "C", "text": "str"},
    {"id": "D", "text": "bool"}
  ],
  "answer": ["C"],
  "explanation": "input() 讀到的內容一律先是字串，所以輸入 2 會得到 \"2\"。",
  "common_mistake": "看到 2 就以為它一定是整數。"
}
```

## 13. 第一版 MVP 範圍

第一版必做：

- 學生登入。
- 管理者登入。
- 從第 1 到第 4 講建立第一批題庫。
- 一次只顯示一題。
- 單選題、多選題、輸出預測題。
- 作答後立即顯示解析。
- 記錄作答結果。
- 顯示學生弱點觀念。
- 弱點觀念增加出題頻率。
- 瀏覽器端 Python 執行區。
- 管理者可看兩位學生的正確率、弱點、最近答題紀錄。

第一版暫不做：

- 公開註冊。
- 班級管理。
- 付費或訂閱。
- 排名競賽。
- 複雜社群功能。
- 後端 Python 沙箱執行。
- 大型考試模式。

## 14. 開發階段

### 階段 1：題庫與規格

- 定義觀念標籤。
- 定義題目 JSON 格式。
- 從第 1 到第 4 講建立第一批題目。
- 建立題目檢查腳本，確認每題有答案、解析、來源與觀念標籤。

### 階段 2：網站 MVP

- 建立前端練習頁。
- 建立登入功能。
- 建立後端 API。
- 建立資料庫 schema。
- 匯入第一批題目。
- 實作作答紀錄。

### 階段 3：弱點追蹤

- 實作熟練度計算。
- 實作弱點加權出題。
- 建立學生儀表板。
- 建立管理者儀表板。

### 階段 4：程式碼執行

- 整合 Pyodide。
- 顯示 stdout。
- 顯示錯誤訊息。
- 設定執行逾時與中止。
- 將程式碼執行紀錄納入作答紀錄。

### 階段 5：部署

- Docker 化。
- 選定 PaaS 平台，優先 Render 或 Railway。
- 建立 PostgreSQL 資料庫。
- 設定正式環境變數。
- 設定 HTTPS。
- 建立初始管理者與兩位學生帳號。
- 設定資料庫備份。
- 上線前做登入、作答、弱點更新、程式碼執行測試。

### 階段 6：擴充題庫

- 隨 `02-雄女電資班考題整理` 後續校對，逐批加入第 5 到第 10 講。
- 補模擬考模式。
- 補錯題本。
- 補每日複習排程。

## 15. 風險與決策

| 風險 | 對策 |
|---|---|
| 題目太難，初學者挫折 | 先用難度 1、2 題建立信心，再逐步加難 |
| 題目只考記憶，不會寫程式 | 加入輸出預測題與程式碼操作題 |
| 弱點追蹤不準 | 每題必須有明確觀念標籤，且一題可對應多個觀念 |
| 後端執行學生程式有安全風險 | 第一版用 Pyodide 在瀏覽器執行 |
| 部署平台資料遺失 | 第一版正式資料使用 PostgreSQL，不依賴 ephemeral filesystem |
| 題庫來源還沒全部完成 | 第一版先用第 1 到第 4 講，後續逐批補完 |
| 自架 VPS 維運麻煩 | 第一版不自架，先用 Render 或 Railway 類 PaaS |

## 16. 第一版完成定義

第一版完成時，必須達到：

- 兩位學生可在家登入。
- 可連續練習第 1 到第 4 講題目。
- 每次只出一題。
- 答題後能看到正解與解析。
- 系統能記錄每位學生的弱點觀念。
- 弱點觀念會提高出題頻率。
- 學生能在網頁輸入 Python 程式碼並看到執行結果。
- 管理者能查看兩位學生的進度與弱點。
