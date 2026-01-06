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
    url = f"{SUPABASE_URL}/rest/v1/Patients"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    params = {"phone": f"eq.{clean_phone}"}
    
    start_time = datetime.now()
    try:
        response = requests.get(url, headers=headers, params=params, timeout=2)
        response.raise_for_status()
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        print(f"⏱️ Supabase query took: {duration:.2f}s")
        
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
    },
    "+421919165630": {
        "forename": "Andrej",
        "surname": "Repický",
        "email": "repicky@example.com",
        "last_visit_date": "2024-01-01",
        "other_relevant_info": "VIP klient, preferuje poobedné termíny."
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

from services_config import validate_service, SERVICES_DB
from calendar_integration import get_available_slots_for_days, create_booking_cal

@app.post("/Get_Appointment")
async def get_appointment(request: Request):
    print("📅 Tool Call: Get_Appointment")
    
    try:
        body = await request.json()
        args = body.get("args", {})
        requested_service = args.get("service") or args.get("service_type") or "General"
    except:
        requested_service = "General"
        
    print(f"🔍 Requested Service: {requested_service}")
    
    canonical_service = validate_service(requested_service)
    
    if not canonical_service and requested_service != "General":
        print(f"❌ Service '{requested_service}' NOT FOUND.")
        valid_services_str = ", ".join(SERVICES_DB.keys())
        return {
            "error": f"Služba '{requested_service}' nie je v ponuke. Dostupné služby: {valid_services_str}."
        }
        
    print(f"✅ Validated Service: {canonical_service}")
    
    # FETCH REAL SLOTS
    slots = get_available_slots_for_days(days=4)
    
    # Filter or add service info
    # We return the list directly. Agent will pick one.
    # We add the 'service' field to each slot just to be consistent with what we promised the agent
    for s in slots:
        s["service"] = canonical_service or "General"
        
    if not slots:
        return {"message": "Momentálne nie sú voľné žiadne termíny na najbližšie 4 dni. Skúste neskôr."}

    return {"available_slots": slots}

@app.post("/GET_booked_appointment")
async def get_booked_appointment(request: Request):
    print("🔍 Tool Call: GET_booked_appointment")
    return {"appointment": None}

@app.post("/Book_appointment")
async def book_appointment(request: Request):
    print(f"📝 Tool Call: Book_appointment")
    
    try:
        body = await request.json()
        args = body.get("args", {})
        
        service_to_book = args.get("service") or "Unknown"
        datetime_str = args.get("datetime")
        patient_name = args.get("patient_name") or "Neznámy"
        patient_phone = args.get("patient_phone") or "0000"
        
    except:
        return {"status": "error", "message": "Invalid request body"}

    # Validation
    canonical = validate_service(service_to_book)
    if not canonical:
        return {
            "status": "error",
            "message": "Nemožno rezervovať túto službu."
        }
        
    if not datetime_str:
         return {"status": "error", "message": "Chýba čas termínu."}

    # Convert readable datetime back to ISO if needed, or find the ISO from slots
    # But simpler: Construct ISO from "YYYY-MM-DD HH:MM"
    try:
        # Expected input: "2024-01-09 09:30"
        # We need to add T and :00.000Z or similar for Cal.com
        # Or parse it.
        # Let's try to parse
        dt = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M")
        iso_start = dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    except ValueError:
        # Maybe it came as ISO already?
        iso_start = datetime_str
        
    # CREATE BOOKING
    result = create_booking_cal(
        name=patient_name,
        phone=patient_phone,
        email="", # No email context usually
        datetime_iso=iso_start,
        notes=f"Service: {canonical}"
    )

    if result["status"] == "success":
        print(f"✅ Booking Confirmed for: {canonical} at {iso_start}")
        return {"status": "success", "message": f"Rezervácia potvrdená: {canonical} na {datetime_str}", "details": result}
    else:
        print(f"❌ Booking Failed: {result['message']}")
        return {"status": "error", "message": "Nepodarilo sa rezervovať termín. Skúste iný čas."}

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
