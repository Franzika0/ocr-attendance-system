import os
import io
import time
import re
from typing import Optional, Tuple
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# 外部服務/技術導入
# 模組 A: OCR (OpenCV + EasyOCR 替換 PaddleOCR)
import cv2
import numpy as np
import easyocr # ⭐️ 重新導入 EasyOCR ⭐️
# from paddleocr import PaddleOCR # 已移除
# 模組 B: 資料寫入 (SQLite)
import sqlite3
# 模組 C & D: Email & AI 回覆 (OpenAI + LangChain)
from openai import OpenAI
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate

from dotenv import load_dotenv
from starlette.concurrency import run_in_threadpool 

# Email 相關
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# 載入 .env 檔案中的環境變數
load_dotenv()

# --- 設定與初始化 ---

app = FastAPI(
    title="OCR 自動化打卡系統 (EasyOCR)", # 標題更新
    description="整合 EasyOCR、RPA、AI 的自動化解決方案 Demo。",
)

# ⭐️ CORS 中介軟體配置 ⭐️
origins = [
    "http://localhost",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# ------------------------------------

# 替換成您的 OpenAI API Key (從 .env 讀取)
OPENAI_API_KEY = os.getenv("OpenAPI_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

# --- Email 服務設定 (從 .env 讀取敏感資訊) ---
SENDER_EMAIL = os.getenv("GMAIL_SENDER_EMAIL") 
SENDER_PASSWORD = os.getenv("GMAIL_APP_PASSWORD") 
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465
# ---------------------------------------------

# ⭐️ EasyOCR 讀取器初始化 ⭐️
try:
    # 設置為中文和英文，用於辨識學號和可能的中文姓名
    READER = easyocr.Reader(['ch_sim', 'en']) 
except Exception as e:
    print(f"EasyOCR 初始化失敗：{e}")
    READER = None 

# SQLite 資料庫設定
DB_NAME = "attendance.db"
CONN = sqlite3.connect(DB_NAME, check_same_thread=False)

# 初始化資料庫表格
def init_db():
    """創建打卡紀錄表 if not exists"""
    c = CONN.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            name TEXT NOT NULL,
            mood TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    CONN.commit()
init_db()

# --- 輔助函式 ---

def ocr_process_image(image_bytes: bytes) -> Tuple[Optional[str], Optional[str]]:
    """
    模組 A 核心: 圖片前處理與 EasyOCR 辨識 (使用彩色增強與精準 ROI)
    """
    if READER is None: # 變數名稱從 OCR_ENGINE 改為 READER
        print("EasyOCR 引擎未初始化，使用模擬學號。")
        return "A1234567", "模擬學生"

    # 1. 將 bytes 轉為 OpenCV 圖像
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    # ⭐️ 檢查 1: 確認原始圖像讀取成功 ⭐️
    if img is None or img.size == 0:
        print("錯誤：無法解碼圖像或圖像為空。")
        return "A1234567", "模擬學生"

    # 2. OpenCV 圖像前處理 (保留必要的增強和裁剪)
    
    # ⭐️ 步驟 2.1: 轉換為灰階 ⭐️
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # ⭐️ 步驟 2.2: 使用簡單閾值化 ⭐️
    # 這裡可以嘗試 cv2.THRESH_BINARY_INV 或 cv2.ADAPTIVE_THRESH_GAUSSIAN_C
    # 我們先使用簡單的 OYSU 閾值，通常對清晰的文字有效
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    processed_img = thresh # 辨識將使用這個單通道的二值化圖像

    # 對彩色圖像應用直方圖均衡化 (在 YUV 空間操作以保留顏色並增強對比度)
    # 這是您經過驗證有效的圖像增強步驟
    #img_yuv = cv2.cvtColor(img, cv2.COLOR_BGR2YUV)
    #img_yuv[:,:,0] = cv2.equalizeHist(img_yuv[:,:,0])
    #enhanced_img = cv2.cvtColor(img_yuv, cv2.COLOR_YUV2BGR)
    
    # ⭐️ 修正點：使用 1280x720 下鎖定學號區域的裁剪座標 ⭐️
    # 沿用您優化後的座標：[Y_start:Y_end, X_start:X_end]
    ROI_COORDS = [550, 620, 50, 450] 
    
    try:
        # 裁剪操作
        cropped_img = processed_img[ROI_COORDS[0]:ROI_COORDS[1], ROI_COORDS[2]:ROI_COORDS[3]]
        
        # 將裁剪後的圖像儲存下來供檢查 
        temp_img_path = "temp_cropped_for_ocr.png"
        cv2.imwrite(temp_img_path, cropped_img)
        print(f"DEBUG: 裁剪後的圖像已儲存至 {temp_img_path}")

        # 檢查 2: 確認裁剪後的圖像非空 
        if cropped_img.size == 0 or cropped_img.shape[0] == 0 or cropped_img.shape[1] == 0:
            raise ValueError("裁剪操作產生了空圖像。請檢查 ROI 座標是否超出邊界。")
            
    except Exception as e:
        print(f"錯誤：裁剪失敗或座標無效 ({e})。使用完整圖像進行辨識。")
        cropped_img = processed_img
    
    # 3. EasyOCR 辨識 (核心差異)
    # EasyOCR 辨識 (直接在裁剪後的彩色圖像上運行)
    results = READER.readtext(
        cropped_img, 
        allowlist='0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ' # 限制只找數字和大寫字母
    ) 

    # 4. 解析結果
    student_id = None
    student_name = "模擬學生" 
    
    # 假設學號格式為 1 個字母 + 9 個數字 (根據您的圖片範例)
    #id_pattern = re.compile(r'^[A-Z]\d{9}$') 
    id_pattern = re.compile(r'^\d{9}$')

    # 從 EasyOCR 結果中過濾文本 (只取高置信度的結果)
    # EasyOCR 輸出格式：[(bbox, text, prob)]
    all_text = [text.upper().replace(' ', '') for (bbox, text, prob) in results if prob > 0.5]
    
    for text in all_text:
        # 移除所有非字母數字字元
        cleaned_text = re.sub(r'[^A-Z0-9]', '', text) 
        
        if id_pattern.match(cleaned_text):
            student_id = cleaned_text
            break
    
    if student_id is None:
        print(f"OCR 辨識結果 (EasyOCR): {all_text}") # 輸出訊息變更
        print("未找到有效學號，使用模擬學號 'A1234567'")
        student_id = "A1234567"
        
    return student_id, student_name


def generate_ai_response(student_name: str, mood_text: str) -> str:
    """
    模組 D 核心: LangChain + OpenAI 生成幽默回覆 (使用最新 Runnable 寫法)
    """
    if not OPENAI_API_KEY:
        print("警告: OpenAI API Key 未設定，AI 回覆將使用預設文本。")
        return f"AI 系統繁忙，{student_name} 同學今天的心情是 '{mood_text}'，請繼續保持活力！"

    # 設置 LLM 
    llm = ChatOpenAI(model="gpt-3.5-turbo", api_key=OPENAI_API_KEY)
    
    # 設置 Prompt
    prompt = PromptTemplate(
        input_variables=["name", "mood"],
        template="你是一位幽默風趣的校園機器人。學生 {name} 剛打卡，他/她說自己今天的心情是：'{mood}'。請你根據這個心情，給他/她一個簡短、鼓勵且帶點幽默感的客製化回覆（少於 50 字）。",
    )
    
    try:
        # 使用最新的 Runnable 寫法取代 LLMChain 和 .run()
        chain = prompt | llm 
        
        response = chain.invoke({"name": student_name, "mood": mood_text})
        
        # 由於 ChatOpenAI 回傳的是 ChatMessage 物件，我們取其內容
        return response.content.strip()
    except Exception as e:
        print(f"AI 回覆生成失敗: {e}")
        return f"AI 系統繁忙，{student_name} 同學今天的心情是 '{mood_text}'，請繼續保持活力！"
# ----------------------------------------------------


def generate_tts_audio(text_to_speak: str) -> bytes:
    # ... (此函式保持不變) ...
    if not OPENAI_API_KEY:
          print("警告: OpenAI API Key 未設定，跳過 TTS 生成。")
          return b''
    
    try:
        response = client.audio.speech.create(
            model="tts-1",  
            voice="alloy",
            input=text_to_speak,
        )
        return response.content
    except Exception as e:
        print(f"TTS 生成失敗: {e}")
        return b''

def send_email_notification(student_name: str, student_id: str, ai_message: str):
    # ... (此函式保持不變) ...
    if not SENDER_EMAIL or not SENDER_PASSWORD:
        print("--- 郵件通知失敗 (RPA) ---: 錯誤：Gmail 寄件設定未在 .env 檔案中配置。")
        return

    RECEIVER_EMAIL = f"{student_id}@student.edu.tw" 
    
    message = MIMEMultipart("alternative")
    message["Subject"] = f"[打卡成功] {student_name}，你的元氣已登錄！"
    message["From"] = SENDER_EMAIL
    message["To"] = RECEIVER_EMAIL
    
    current_time = time.strftime("%Y-%m-%d %H:%M:%S")

    text = f"""
親愛的 {student_name} 同學，
... (信件內容略) ...
RPA 自動化打卡系統敬上
"""
    
    part1 = MIMEText(text, "plain", "utf-8")
    message.attach(part1)

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=context) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(
                SENDER_EMAIL, RECEIVER_EMAIL, message.as_string()
            )
        print(f"--- 實際郵件發送成功 (RPA) ---: To {RECEIVER_EMAIL}")
    except Exception as e:
        print(f"--- 實際郵件發送失敗 (RPA) ---: 錯誤: {e}")


# --- API 端點 ---
class AttendanceData(BaseModel):
    """資料寫入模組的輸入模型"""
    student_id: str
    name: str
    mood: Optional[str] = None
    
@app.post("/upload")
async def upload_and_process(
    file: UploadFile = File(...),
    mood: str = Form("還不錯"),
):
    """
    ✅ Step 1 & 2: 接收照片，執行 OCR 辨識
    """
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="上傳檔案必須是圖片格式")

    image_bytes = await file.read()
    
    # 執行 OCR 辨識 (現在使用 EasyOCR 函式)
    # ⭐️ 核心修正點：使用 run_in_threadpool ⭐️
    student_id, student_name = await run_in_threadpool(
        ocr_process_image, 
        image_bytes
    )

    if not student_id:
        raise HTTPException(status_code=500, detail="OCR 辨識流程失敗，無法解析學號")

    # --- ✅ Step 3: 自動化流程 (RPA) 開始 ---
    
    # 1. 自動產生個人化 AI 心情回覆 (文字)
    ai_response_text = generate_ai_response(student_name, mood)
    
    # 2. 自動寫入 SQLite
    try:
        c = CONN.cursor()
        c.execute("INSERT INTO attendance (student_id, name, mood) VALUES (?, ?, ?)", 
                  (student_id, student_name, mood))
        CONN.commit()
    except Exception as e:
        print(f"資料庫寫入失敗: {e}")
    
    # 3. 自動寄 Email (RPA 行為)
    send_email_notification(student_name, student_id, ai_response_text)
    
    # 4. 自動生成語音 (mp3)
    #audio_bytes = generate_tts_audio(ai_response_text)
    
    # --- ✅ Step 4: 回傳結果 ---
    
    return JSONResponse(content={
        "status": "success",
        "student_id": student_id,
        "name": student_name,
        "mood_input": mood,
        "ai_message": ai_response_text,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "audio_endpoint": f"/get_audio?text={ai_response_text}" 
    })


@app.get("/get_audio", response_class=FileResponse)
async def get_audio(text: str):
    # ... (此函式保持不變) ...
    audio_bytes = generate_tts_audio(text)
    
    if not audio_bytes:
        raise HTTPException(status_code=404, detail="語音生成失敗或 API Key 未設定")
        
    temp_file_path = f"temp_audio_{time.time()}.mp3"
    try:
        with open(temp_file_path, "wb") as f:
            f.write(audio_bytes)
        
        return FileResponse(
            path=temp_file_path, 
            media_type="audio/mpeg", 
            filename="ai_response.mp3"
        )
    finally:
        pass


@app.get("/attendance_summary")
async def get_summary():
    # ... (此函式保持不變) ...
    c = CONN.cursor()
    c.execute("SELECT COUNT(*) FROM attendance")
    checked_in_count = c.fetchone()[0]
    
    TOTAL_EXPECTED = 50 
    
    return {
        "total_expected": TOTAL_EXPECTED,
        "checked_in": checked_in_count,
        "not_checked_in": TOTAL_EXPECTED - checked_in_count
    }