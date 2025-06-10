import re
from fastapi import FastAPI
from pydantic import BaseModel
import aiosmtplib
from email.message import EmailMessage
import os
from dotenv import load_dotenv
import boto3
from datetime import datetime
from starlette.concurrency import run_in_threadpool
import traceback
import openai
import uuid
import time

# Load environment variables first
load_dotenv()

# Initialize DynamoDB resource and table
dynamodb = boto3.resource(
    'dynamodb',
    region_name=os.getenv("AWS_REGION"),
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
)
table = dynamodb.Table("AyobotConversations")

async def save_to_dynamodb(user_message, bot_reply):
    conversation_id = str(uuid.uuid4())  # or your logic to get conversation/session id
    timestamp = str(int(time.time() * 1000))  # e.g., milliseconds since epoch

    item = {
        "conversation_id": conversation_id,
        "timestamp": timestamp,
        "user_message": user_message,
        "bot_reply": bot_reply
    }

    table = dynamodb.Table("AyobotConversations")
    await run_in_threadpool(table.put_item, Item=item)

# Initialize OpenAI client
openai.api_key = os.getenv("OPEN_AI_API_KEY")


class Message(BaseModel):
    message: str

app = FastAPI()

def is_send_email_intent(message: str) -> bool:
    patterns = [
        r"\bsend an email\b",
        r"\bemail to\b",
        r"\bsend mail\b",
        r"\bsend message to\b",
        r"\bmail to\b"
    ]
    return any(re.search(pattern, message, re.I) for pattern in patterns)

@app.post("/chat")
async def chat(msg: Message):
    print("🔹 Received message:", msg.message)

    try:
        # 1. Detect email intent
        intent_prompt = (
            "Does this message involve sending an email? Reply only with 'yes' or 'no'."
        )
        intent_response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": intent_prompt},
                {"role": "user", "content": msg.message}
            ]
        )
        intent_raw = intent_response.choices[0].message.content.strip()
        print("🔍 Intent detection result:", intent_raw)
        send_email_intent = intent_raw.lower() == "yes"

        # 2. Unified assistant prompt
        system_prompt = (
            "You are Ayobot, a helpful assistant. If the user asks to send an email, "
            "acknowledge that it was sent and summarize the content. Otherwise, reply conversationally. do not include any heading in your response.Just reply like a normal human."
        )

        gpt_response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": msg.message}
            ]
        )
        reply = gpt_response.choices[0].message.content.strip()
        print("💬 AI reply (main response):", reply)

        if send_email_intent:
            # 3. Extract recipient email
            email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", msg.message)
            if not email_match:
                print("⚠️ No valid email found in message.")
                return {"reply": "No valid email address found in message.", "email_sent": False}
            recipient_email = email_match.group(0)
            print("📧 Email detected:", recipient_email)

            # 4. Extract email body
            body_extraction_prompt = (
                "Extract the message body the user wants to send via email. "
                "Exclude the email address. Keep it professional and concise."
            )
            body_response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": body_extraction_prompt},
                    {"role": "user", "content": msg.message}
                ]
            )
            body_content = body_response.choices[0].message.content.strip()
            print("✉️ Extracted email body:", body_content)

            # 5. Send the email
            subject_line = "Email from Ayobot"
            msg_obj = EmailMessage()
            msg_obj["From"] = os.getenv("EMAIL_USERNAME")
            msg_obj["To"] = recipient_email
            msg_obj["Subject"] = subject_line
            msg_obj.set_content(body_content)

            await aiosmtplib.send(
                msg_obj,
                hostname=os.getenv("EMAIL_HOST"),
                port=int(os.getenv("EMAIL_PORT")),
                start_tls=True,
                username=os.getenv("EMAIL_USERNAME"),
                password=os.getenv("EMAIL_PASSWORD"),
            )

            await save_to_dynamodb(msg.message, reply)

            snippet = (body_content[:100] + "...") if len(body_content) > 100 else body_content
            confirmation = f"Email sent successfully to {recipient_email}. Here's a brief summary: {snippet}"
            print("✅ Email sent confirmation:", confirmation)
            return {"reply": confirmation, "email_sent": True}

        else:
            await save_to_dynamodb(msg.message, reply)
            return {"reply": reply, "email_sent": False}

    except Exception as e:
        print("❌ Exception occurred:")
        traceback.print_exc()
        return {"error": str(e)}