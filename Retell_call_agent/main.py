from fastapi import FastAPI, Request
import uvicorn
import json
import os
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

def get_patient_by_phone(phone_number: str):
    """Search for patient in Supabase by phone number."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None
    
    clean_phone = phone_number.replace(" ", "").replace("-", "")
    url = f"{SUPABASE_URL}/rest/v1/patient"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    params = {"or": f"(phone.eq.{clean_phone},phone_number.eq.{clean_phone},tel.eq.{clean_phone})"}
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=5)
        response.raise_for_status()
        patients = response.json()
        
        if patients and len(patients) > 0:
            patient = patients[0]
            print(f"✅ Found patient in Supabase: {patient.get('forename', 'N/A')} {patient.get('surname', 'N/A')}")
            return {
                "forename": patient.get("forename") or patient.get("first_name"),
                "surname": patient.get("surname") or patient.get("last_name"),
                "email": patient.get("email"),
                "last_visit_date": patient.get("last_visit_date") or patient.get("last_visit"),
                "other_relevant_info": patient.get("notes") or patient.get("other_relevant_info") or ""
            }
        return None
    except Exception as e:
        print(f"❌ Supabase error: {e}")
        return None

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
    print("\n" + "="*80)
    print("🔔 FIRSTWEBHOOK CALLED")
    print("="*80)
    
    # 1. Log all headers
    headers = dict(request.headers)
    print("\n📋 HEADERS:")
    for key, value in headers.items():
        print(f"  {key}: {value}")
    
    # 2. Log query parameters
    print("\n🔗 QUERY PARAMETERS:")
    for key, value in request.query_params.items():
        print(f"  {key}: {value}")
    
    # 3. Log raw body
    raw_body = await request.body()
    print(f"\n📦 RAW BODY ({len(raw_body)} bytes):")
    print(raw_body.decode(errors='ignore'))
    
    try:
        if raw_body:
            data = json.loads(raw_body)
            print("\n📊 PARSED JSON:")
            print(json.dumps(data, indent=2))
        else:
            data = {}
        
        # Try to extract phone number from ALL possible locations
        query_number = request.query_params.get("number")
        args = data.get("args", {})
        call_data = data.get("call", {})
        
        # PRIORITY: call.from_number is where Retell actually sends it!
        from_number = (
            call_data.get("from_number") or  # THIS IS THE REAL ONE
            query_number or 
            args.get("caller_number") or 
            data.get("from_number") or 
            data.get("caller_id") or 
            headers.get("x-retell-from-number") or 
            headers.get("x-retell-call-from") or
            "UNKNOWN"
        )
        
        print(f"\n📞 IDENTIFIED CALLER NUMBER: {from_number}")
        print(f"🔍 Source: call.from_number = {call_data.get('from_number')}")
        print("="*80 + "\n")
        
        # Cleanup
        clean_number = str(from_number).replace(" ", "")
        
        # Try Supabase first, fallback to mock data
        patient = get_patient_by_phone(clean_number)
        
        # Fallback to mock data if Supabase fails or returns nothing
        if not patient:
            patient = MOCK_PATIENTS.get(clean_number)
        
        if patient:
            print(f"✅ Found Patient: {patient.get('forename')} {patient.get('surname')}")
            res = {"existing_patient_data": patient}
        else:
            print(f"👤 New Patient (number: {clean_number})")
            res = {
                "existing_patient_data": {
                    "forename": None,
                    "surname": None,
                    "email": None,
                    "last_visit_date": None,
                    "other_relevant_info": "Neznámy."
                }
            }
        
        print(f"📤 RESPONSE: {json.dumps(res)}")
        return res
        
    except Exception as e:
        print(f"💥 ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
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
