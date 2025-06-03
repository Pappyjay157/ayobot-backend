from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import openai
import os
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPEN_AI_API_KEY")

app = FastAPI()

# Allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # you can restrict this later
    allow_methods=["*"],
    allow_headers=["*"],
)

class Message(BaseModel):
    message: str

@app.post("/chat")
async def chat(msg: Message):
    print("Received:", msg.message)
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are Ayobot, a helpful assistant for programmers."},
                {"role": "user", "content": msg.message}
            ]
        )
        reply = response['choices'][0]['message']['content']
        print("Reply:", reply)
        return {"reply": reply}
    except Exception as e:
        print("❌ Error:", e)
        return {"error": str(e)}
