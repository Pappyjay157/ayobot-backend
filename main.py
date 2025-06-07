<<<<<<< HEAD
import re
from fastapi import FastAPI
from pydantic import BaseModel
from openai import OpenAI
import aiosmtplib
from email.message import EmailMessage
import os
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPEN_AI_API_KEY"))

class Message(BaseModel):
    message: str

app = FastAPI()

@app.post("/chat")
async def chat(msg: Message):
    print("Received:", msg.message)

    try:
        # Check for email instruction
        send_email_intent = "send an email" in msg.message.lower()

        # Let GPT generate a subject + body from user input
        gpt_response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are Ayobot. When asked to send an email, respond only with the subject and body, formatted like this:\n\nSubject: <subject line>\n\n<body of the email>"},
                {"role": "user", "content": msg.message}
            ]
        )
        reply = gpt_response.choices[0].message.content.strip()
        print("Reply:\n", reply)

        # If it's a send email request, extract the email and send it
        if send_email_intent:
            email_match = re.search(r"to\s+(\S+@\S+)", msg.message, re.IGNORECASE)
            if not email_match:
                return {"reply": reply, "email_sent": False, "error": "No valid email address found in message."}

            recipient_email = email_match.group(1)

            # Parse subject and body from GPT reply
            parts = re.split(r"\n\s*\n", reply, maxsplit=1)
            subject_line = ""
            body_content = ""

            for part in parts:
                if part.lower().startswith("subject:"):
                    subject_line = part[len("Subject:"):].strip()
                else:
                    body_content = part.strip()

            if not subject_line or not body_content:
                return {"reply": reply, "email_sent": False, "error": "Could not extract subject or body from reply."}

            # Send the email
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

            return {"reply": reply, "email_sent": True}

        return {"reply": reply, "email_sent": False}

    except Exception as e:
        print("❌ Error:", e)
        return {"error": str(e)}
=======
import re
from fastapi import FastAPI
from pydantic import BaseModel
from openai import OpenAI
import aiosmtplib
from email.message import EmailMessage
import os
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPEN_AI_API_KEY"))

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
    print("Received:", msg.message)

    try:
        send_email_intent = is_send_email_intent(msg.message)

        if send_email_intent:
            system_prompt = "You are Ayobot. When asked to send an email, respond only with the subject and body, formatted like this:\n\nSubject: <subject line>\n\n<body of the email>"
        else:
            system_prompt = "You are Ayobot, a helpful assistant. Respond conversationally and helpfully."

        gpt_response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": msg.message}
            ]
        )
        reply = gpt_response.choices[0].message.content.strip()
        print("Reply:\n", reply)

        if send_email_intent:
            email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", msg.message)
            if not email_match:
                return {"reply": "No valid email address found in message.", "email_sent": False}

            recipient_email = email_match.group(0)

            subject_line = ""
            body_lines = []
            for line in reply.splitlines():
                if line.lower().startswith("subject:"):
                    subject_line = line[len("Subject:"):].strip()
                else:
                    body_lines.append(line)
            body_content = "\n".join(body_lines).strip()

            if not subject_line or not body_content:
                return {"reply": "Could not extract subject or body from reply.", "email_sent": False}

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

            # Return confirmation and brief snippet of body (e.g. first 100 chars)
            snippet = (body_content[:100] + "...") if len(body_content) > 100 else body_content
            confirmation = f"Email sent successfully. Here's a brief summary: {snippet}"

            return {"reply": confirmation, "email_sent": True}

        # For normal chat just return the reply
        return {"reply": reply, "email_sent": False}

    except Exception as e:
        print("❌ Error:", e)
        return {"error": str(e)}

>>>>>>> feature/fix-ai-agent
