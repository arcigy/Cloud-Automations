from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
import uvicorn

# Import our custom engines
from tony_backend import get_tony_response, persist_conversation
from calendar_engine import get_calendar_availability, confirm_booking, cancel_booking
try:
    from utils.email_engine import send_confirmation_email
except ImportError:
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
    from utils.email_engine import send_confirmation_email
from fastapi import BackgroundTasks, Query
from fastapi.responses import RedirectResponse
import urllib.parse

app = FastAPI(title="Tony AI Cloud Backend")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class ChatMessage(BaseModel):
    message: str
    conversationID: str
    history: List[dict]
    lang: Optional[str] = None

class BookingConfirm(BaseModel):
    bookingTime: str
    email: str
    name: str
    phone: str = "null"
    lang: str = "sk"
    conversationID: Optional[str] = None

# Routes
@app.get("/")
def read_root():
    return {"status": "online", "agent": "Tony", "version": "2.0.0"}

@app.post("/webhook/chat")
async def chat_endpoint(data: ChatMessage, background_tasks: BackgroundTasks):
    """
    Main chat endpoint with V2 logic.
    """
    response_json, formatted_history = get_tony_response(data.message, data.conversationID, data.history, data.lang)
    
    # Background persistence
    background_tasks.add_task(persist_conversation, data.conversationID, data.message, response_json, formatted_history)
    
    return response_json

@app.post("/webhook/calendar-availability-check")
async def availability_endpoint():
    return get_calendar_availability()

@app.post("/webhook/calendar-initiate-book")
async def initiate_booking(data: BookingConfirm, background_tasks: BackgroundTasks):
    """
    Sends a verification email instead of booking immediately.
    """
    print(f"📧 BOOKING REQUEST RECEIVED:")
    print(f"   Email: {data.email}")
    print(f"   Name: {data.name}")
    print(f"   Time: {data.bookingTime}")
    print(f"   Phone: {data.phone}")
    print(f"   Lang: {data.lang}")
    
    # Use environment variable for BASE_URL to support localhost/ngrok/production
    base_url = os.getenv("WEB_BASE_URL", "http://127.0.0.1:8001")
    
    # Generate confirmation URL
    confirm_params = {
        "action": "book",
        "time": data.bookingTime,
        "email": data.email,
        "name": data.name,
        "phone": data.phone,
        "lang": data.lang,
        "cid": data.conversationID
    }
    confirm_url = f"{base_url}/webhook/confirm?{urllib.parse.urlencode(confirm_params)}"
    
    print(f"📨 Sending email to {data.email}...")
    # We send it directly here to catch errors and notify the frontend if email fails
    success = send_confirmation_email(
        data.email, 
        data.name, 
        "book", 
        data.bookingTime, 
        confirm_url, 
        data.lang
    )
    
    if not success:
        print(f"❌ Email FAILED to send!")
        return {"status": "error", "message": "Failed to send confirmation email. Please check server logs."}

    print(f"✅ Email sent successfully!")
    return {"status": "verification_sent", "message": "Check your email to confirm."}

@app.get("/webhook/confirm")
async def confirm_action_webhook(
    action: str, 
    time: str, 
    email: str, 
    name: str, 
    phone: str = "null",
    lang: str = "sk", 
    cid: Optional[str] = None
):
    """
    Triggered by the email button. Performs the action and redirects to the landing page.
    """
    # Use environment variable for Frontend URL
    frontend_url = os.getenv("FRONTEND_BASE_URL", "http://127.0.0.1:5500")

    print(f"DEBUG: Processing Action={action}, Name={name}, Email={email}, Phone={phone}, Time={time}")
    if action == "book":
        if not phone or phone == "null":
            return {"status": "error", "message": "Missing phone number. Please retry the booking through the chat."}
            
        res = confirm_booking(time, email, name, phone, cid)
        print(f"DEBUG: Cal.com Response Status={res['status']}, Message={res.get('message')}")
        
        if res["status"] == "success":
            # Redirect to beautiful landing page
            target = f"{frontend_url}/.tmp/public_html/confirmation.html?lang={lang}&name={urllib.parse.quote(name)}"
            return RedirectResponse(url=target)
        else:
            # Show actual error from Cal.com
            return {"status": "error", "message": res.get("message", "Booking failed"), "details": res}
    
    return {"status": "error", "message": "Invalid action or expired link"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
