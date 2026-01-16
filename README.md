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
cd ocr-attendance-system/RPA
pip install -r requirements.txt

```

3. 設定環境變數：
在RPA資料夾下建立一個 `.env` 檔案並填入以下資訊：
```env
OpenAPI_KEY=你的OpenAI金鑰
GMAIL_SENDER_EMAIL=你的Gmail帳號
GMAIL_APP_PASSWORD=你的Gmail應用程式密碼

```

4. 啟動後端伺服器：
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000

```



### (二). 前端設定

1. 開啟另一個終端進入前端目錄：
```bash
cd ocr-attendance-system

```

2. 檢查 Node 版本，建議為22.20.0，接著安裝 Node 套件：
```bash
npm install

```

3. 啟動Vite前端開發伺服器：
```bash
npm run dev

```


## 🖥️ 使用說明

1. 在紅框內掃描學號。
2. 輸入當前的心情（例如：累爆了）。
3. 系統將回傳辨識結果、AI 語音回覆，並寄送 Email。

---

## ⚠️ 注意事項

* **OCR 座標**：目前程式碼中，設定了固定的裁剪座標 `ROI_COORDS = [550, 620, 50, 450]`，請根據實際拍照角度調整。
* **裁剪結果**：在 RPA 資料夾下，會輸出當次的掃描結果，方便未來除錯。