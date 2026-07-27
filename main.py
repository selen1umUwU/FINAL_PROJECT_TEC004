from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
import os
import requests
from google import genai
from google.genai import types
from dotenv import load_dotenv
import json
import models
from database import engine, get_db

load_dotenv()

# Auto-create the Postgres tables on Neon
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# Mount your frontend files
#app.mount("/static", StaticFiles(directory="static"), name="static")

class ChatRequest(BaseModel):
    question: str
    session_id: str

# Load scraped data
try:
    with open("scraped_data.json", "r", encoding="utf-8") as f:
        json_data = json.load(f)
        # Extract only the "content" from each dictionary and merge it into plain text for the AI
        KNOWLEDGE_BASE = "\n".join([item["content"] for item in json_data])
except FileNotFoundError:
    KNOWLEDGE_BASE = "Swinburne University Vietnam admission information."

# ---------- AI CLIENTS ----------
# API 1 (chính): gọi thẳng Gemini qua google-genai SDK
gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
GEMINI_MODEL = "gemini-2.5-flash"

# API 2 (dự phòng): Beeknoee — dùng khi API 1 lỗi/hết quota
BEEKNOEE_API_KEY = os.getenv("BEEKNOEE_API_KEY")
BEEKNOEE_URL = "https://platform.beeknoee.com/v1/chat/completions"
BEEKNOEE_MODEL = "gemini-2.5-flash"  # Beeknoee cũng proxy được model Gemini

# ---------- SYSTEM PROMPT ----------
# Tách riêng system instruction khỏi câu hỏi của user (đúng chuẩn Gemini API),
# thay vì nhét chung vào 1 chuỗi string như trước.
SYSTEM_PROMPT = f"""Bạn là trợ lý tư vấn tuyển sinh AI của Swinburne Việt Nam.

DỮ LIỆU THAM KHẢO (chỉ dùng thông tin này để trả lời, không tự bịa thêm):
---
{KNOWLEDGE_BASE}
---

QUY TẮC BẮT BUỘC:
1. PHẠM VI: Chỉ trả lời các câu hỏi liên quan đến tuyển sinh Swinburne Việt Nam
   (ngành học, học phí, học bổng, điều kiện nhập học, thủ tục đăng ký, cơ sở, sự kiện,
   đời sống sinh viên). Nếu câu hỏi KHÔNG liên quan (toán, lập trình, thời sự, chuyện
   phiếm, các trường khác, v.v.), hãy TỪ CHỐI lịch sự bằng đúng dạng câu:
   "Xin lỗi, mình chỉ hỗ trợ các câu hỏi về tuyển sinh Swinburne Việt Nam thôi. Bạn có
   câu hỏi nào về ngành học, học phí hay học bổng không?" — không trả lời nội dung
   ngoài phạm vi dù người dùng có yêu cầu thêm.
2. NGẮN GỌN: Trả lời tối đa 3-4 câu hoặc vài gạch đầu dòng ngắn. Đi thẳng vào thông tin
   quan trọng nhất, không lặp lại câu hỏi, không rào đón dài dòng.
3. ĐẦY ĐỦ: Dù ngắn gọn, câu trả lời phải chứa đúng và đủ thông tin cốt lõi người hỏi cần
   (ví dụ: tên học bổng + giá trị, không chỉ nói "có nhiều học bổng").
4. TRUNG THỰC: Nếu dữ liệu tham khảo không có thông tin cụ thể (ví dụ số tiền học phí
   chính xác), đừng bịa số liệu — hãy nói rõ và hướng dẫn liên hệ hotline
   0773 313 319 hoặc trang tuyensinh.swin.edu.vn để biết chi tiết mới nhất.
5. NGÔN NGỮ: Trả lời bằng tiếng Việt, giọng thân thiện, chuyên nghiệp như một nhân viên
   tư vấn tuyển sinh thật.
"""


def ask_gemini(question: str) -> str:
    """API 1 (chính): gọi thẳng Gemini qua google-genai SDK."""
    response = gemini_client.models.generate_content(
        model=GEMINI_MODEL,
        contents=question,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.3,
            max_output_tokens=220,
        ),
    )
    text = (response.text or "").strip()
    if not text:
        # Gemini đôi khi trả về rỗng (bị chặn safety, hết token giữa chừng...)
        raise ValueError("Gemini trả về nội dung rỗng")
    return text


def ask_beeknoee(question: str) -> str:
    """API 2 (dự phòng): gọi qua Beeknoee khi API 1 lỗi/hết quota."""
    if not BEEKNOEE_API_KEY:
        raise RuntimeError("Chưa cấu hình BEEKNOEE_API_KEY trong .env")

    resp = requests.post(
        BEEKNOEE_URL,
        headers={
            "Authorization": f"Bearer {BEEKNOEE_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": BEEKNOEE_MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": question},
            ],
            "temperature": 0.3,
            "max_tokens": 220,
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"].strip()


@app.post("/chat")
def chat_endpoint(req: ChatRequest, db: Session = Depends(get_db)):
    # 1. Thử API 1 (Gemini) trước. Nếu lỗi (hết quota, rate limit, timeout...)
    #    thì tự động fallback sang API 2 (Beeknoee) để chatbot không bị gián đoạn.
    used_provider = "gemini"
    try:
        bot_reply = ask_gemini(req.question)
    except Exception as gemini_err:
        print(f"[WARN] Gemini API lỗi, fallback sang Beeknoee: {gemini_err}")
        used_provider = "beeknoee"
        try:
            bot_reply = ask_beeknoee(req.question)
        except Exception as beeknoee_err:
            print(f"[ERROR] Beeknoee API cũng lỗi: {beeknoee_err}")
            bot_reply = (
                "Xin lỗi, hệ thống tư vấn AI đang tạm gián đoạn. "
                "Vui lòng thử lại sau ít phút hoặc liên hệ hotline 0939 403 555."
            )
            used_provider = "none"

    # 2. Save to Neon PostgreSQL
    new_chat = models.ChatHistory(
        session_id=req.session_id,
        user_message=req.question,
        bot_response=bot_reply
    )
    db.add(new_chat)
    db.commit()

    return {"answer": bot_reply, "provider": used_provider}

app.mount("/", StaticFiles(directory="static", html=True), name="static")