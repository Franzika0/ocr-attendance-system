# OCR 自動化打卡系統 (EasyOCR + FastAPI)

這是一個整合了 EasyOCR 辨識、OpenAI 語義生成、RPA 自動化郵件通知與 SQL 紀錄的簡易打卡系統。

## 🚀 功能特點

* AI 辨識：使用 EasyOCR 自動提取學生證學號。
* 智慧互動：基於 OpenAI GPT 模型，根據學生心情生成幽默回覆。
* 自動化 RPA：自動寫入資料庫並發送 Gmail 通知。
* 語音合成：將 AI 回覆轉換為語音輸出。

---

## 📂 安裝與設定

### (一). 後端設定

1. 建立並啟動虛擬環境
```bash
conda create --name myenv python=3.12.7
conda activate myenv

```

2. 安裝 Python 依賴：
```bash
cd RPA
pip install -r requirements.txt

```


3. 設定環境變數：
建立一個 `.env` 檔案並填入以下資訊：
```env
OpenAPI_KEY=你的OpenAI金鑰
GMAIL_SENDER_EMAIL=你的Gmail帳號
GMAIL_APP_PASSWORD=你的Gmail應用程式密碼

```


4. 啟動後端伺服器：
```bash
uvicorn main:app --reload

```

5. 



### 2. 前端設定 (Web Interface)

這是你提到的 `npm install` 部分：

1. 進入前端目錄：
```bash
cd frontend

```


2. **安裝 Node 套件**：
```bash
npm install

```


3. 啟動前端開發伺服器：
```bash
npm run dev  # 或是 npm start，視你的框架而定

```



---

## 🖥️ 使用說明

1. 開啟瀏覽器至 `http://localhost:8080`。
2. 上傳一張包含學號的圖片。
3. 輸入當前的心情（例如：累爆了）。
4. 系統將自動回傳辨識結果、AI 語音回覆，並寄送 Email。

---

## ⚠️ 注意事項

* **隱私安全性**：請確保 `.env` 與 `attendance.db` 已加入 `.gitignore`。
* **OCR 座標**：目前代碼中硬編碼了裁剪座標 `ROI_COORDS = [550, 620, 50, 450]`，請根據實際拍照角度調整。