from fastapi import FastAPI, Request
import uvicorn
import json
import os
from datetime import datetime, timedelta

# Create the FastAPI app
app = FastAPI(title="Retell AI Receptionist Backend")

# In-memory storage or mock data for demonstration
MOCK_PATIENTS = {
    "+421903123456": {
        "forename": "Milan",
        "surname": "Majtán",
        "email": "milan@example.com",
        "last_visit_date": "2023-10-15",
        "other_relevant_info": "Pacient má strach z ihiel."
    }
}

@app.get("/")
async def root():
    return {"status": "online", "service": "Retell AI Backend"}

@app.post("/")
async def root_post(request: Request):
    """
    Handle generic POST requests to the root, often used by Retell for status updates.
    """
    body = await request.body()
    print(f"🔔 ROOT POST RECEIVED: {body.decode(errors='ignore')}")
    return {"status": "ok"}

@app.post("/firstWebhook")
async def first_webhook(request: Request):
    """
    Ultra-permissive endpoint to debug Retell calls.
    """
    print("\n" + "🚨" * 20)
    print("DEBUG: firstWebhook HIT")
    
    # 1. Log all headers
    headers = dict(request.headers)
    print(f"DEBUG Headers: {json.dumps(headers, indent=2)}")
    
    # 2. Log raw body
    raw_body = await request.body()
    print(f"DEBUG Raw Body: {raw_body.decode(errors='ignore')}")
    
    try:
        if raw_body:
            data = json.loads(raw_body)
        else:
            data = {}
        
        from_number = data.get("from_number") or data.get("caller_id") or headers.get("x-retell-from-number") or "unknown"
        print(f"DEBUG Detected Number: {from_number}")
        
        # Cleanup
        clean_number = str(from_number).replace(" ", "")
        patient = MOCK_PATIENTS.get(clean_number)
        
        if patient:
            print(f"✅ Found Patient: {patient['forename']}")
            res = {"existing_patient_data": patient}
        else:
            print("👤 New Patient")
            res = {
                "existing_patient_data": {
                    "forename": None,
                    "surname": None,
                    "email": None,
                    "last_visit_date": None,
                    "other_relevant_info": "Neznámy."
                }
            }
        
        print(f"DEBUG Response: {json.dumps(res)}")
        return res
        
    except Exception as e:
        print(f"💥 ERROR: {str(e)}")
        # Fallback to empty but valid response
        return {"existing_patient_data": {"forename": None}}

# --- STUBS FOR OTHER ENDPOINTS ---

@app.post("/Get_Appointment")
async def get_appointment(request: Request):
    print("📅 Tool Call: Get_Appointment")
    now = datetime.now()
    slots = []
    for i in range(1, 4):
        date = (now + timedelta(days=i)).strftime("%Y-%m-%d")
        slots.append({"datetime": f"{date} 09:00"})
        slots.append({"datetime": f"{date} 14:30"})
    return {"available_slots": slots}

@app.post("/GET_booked_appointment")
async def get_booked_appointment(request: Request):
    print("🔍 Tool Call: GET_booked_appointment")
    return {"appointment": None}

@app.post("/Book_appointment")
async def book_appointment(request: Request):
    print(f"📝 Tool Call: Book_appointment")
    return {"status": "success", "message": "Booking confirmed"}

@app.post("/send_form_registration")
async def send_form_registration(request: Request):
    print(f"📩 Tool Call: send_form_registration")
    return {"status": "success", "message": "Registration form sent"}

@app.post("/Change_appointment")
async def change_appointment(request: Request):
    print(f"🔄 Tool Call: Change_appointment")
    return {"status": "success", "message": "Rescheduled"}

@app.post("/cancelAppointment")
async def cancel_appointment(request: Request):
    print("❌ Tool Call: cancelAppointment")
    return {"status": "success", "message": "Cancelled"}

@app.post("/send_form_cancel")
async def send_form_cancel(request: Request):
    print("📩 Tool Call: send_form_cancel")
    return {"status": "success", "message": "Cancel form sent"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8002)))
