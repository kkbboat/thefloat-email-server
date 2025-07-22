import re
import os
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional
from datetime import datetime
import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr

# Pydantic models for request/response
class CustomerDetails(BaseModel):
    name: str
    email: EmailStr
    phone: str

class BookingDetails(BaseModel):
    room: str
    dates: str

class EmailSettings(BaseModel):
    SMTP_SERVER: str
    SMTP_PORT: str
    SMTP_USERNAME: str
    SMTP_PASSWORD: str
    SMTP_FROM_NAME: str

class SendEmailRequest(BaseModel):
    recipients: List[EmailStr]
    payment_id: int
    timestamp: int
    customer_details: CustomerDetails
    booking_details: BookingDetails
    HTML_PAGE: str
    email_settings: EmailSettings

class EmailResponse(BaseModel):
    message: str
    sent_to: List[str]
    timestamp: str

# FastAPI app setup
app = FastAPI(
    title="SMTP Email Sender",
    description="Sends SMTP emails for booking confirmations",
    version="2.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def send_email_smtp(to_emails: List[str], subject: str, html_content: str, email_settings: EmailSettings) -> bool:
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f"{email_settings.SMTP_FROM_NAME} <{email_settings.SMTP_USERNAME}>"
        msg['To'] = "undisclosed-recipients:;"  # Hides actual recipients

        html_part = MIMEText(html_content, 'html')
        msg.attach(html_part)

        with smtplib.SMTP(email_settings.SMTP_SERVER, int(email_settings.SMTP_PORT)) as server:
            server.starttls()
            server.login(email_settings.SMTP_USERNAME, email_settings.SMTP_PASSWORD)
            server.sendmail(
                from_addr=email_settings.SMTP_USERNAME,
                to_addrs=to_emails,  # Recipients go here, not in headers
                msg=msg.as_string()
            )
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False


@app.post("/send-email", response_model=EmailResponse)
async def send_email(request: SendEmailRequest):
    try:
        if not request.recipients:
            raise HTTPException(status_code=400, detail="At least one recipient is required")
        if not all([request.email_settings.SMTP_SERVER,request.email_settings.SMTP_PORT,request.email_settings.SMTP_USERNAME,request.email_settings.SMTP_PASSWORD,request.email_settings.SMTP_FROM_NAME]):
            raise HTTPException(status_code=400, detail="All email settings are required")
        subject = f"Order Confirmed - Payment ID: {request.payment_id}"
        html_content = request.HTML_PAGE
        success = send_email_smtp(request.recipients, subject, html_content, request.email_settings)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to send email")
        return EmailResponse(message="Email sent successfully",sent_to=request.recipients,timestamp=datetime.now().isoformat())
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error sending email: {str(e)}")

@app.get("/")
async def hello():
    return {"message": "Hello! Email sender API is running."}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
