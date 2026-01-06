from fastapi import FastAPI, Request
import uvicorn
import json
import os
import sys
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
from enum import Enum
from typing import Optional, Dict, Any

load_dotenv()

# --- CONFIGURATIONS ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
CAL_API_KEY = os.getenv("CAL_API_KEY", "cal_live_6101fbb825f9173a4f3e7045d20d5bdc")
CAL_EVENT_TYPE_ID = os.getenv("CAL_EVENT_TYPE_ID", "3877498")
CAL_BASE_URL = "https://api.cal.com/v1"

# --- SERVICES CONFIGURATION ---
SERVICES_DB: Dict[str, Dict[str, Any]] = {
    "Preventívna prehliadka": {"price": "20 €", "duration_min": 30, "category": "Preventívna"},
    "Dentálne čistenie": {"price": "45–80 €", "duration_min": 60, "category": "Preventívna", "aliases": ["hygiena", "dentálna hygiena", "čistenie zubov"]},
    "Kompozitná výplň": {"price": "60–120 €", "duration_min": 45, "category": "Konzervatívna", "aliases": ["plomba", "kaz", "výplň"]},
    "Koreňové ošetrenie": {"price": "150–300 €", "duration_min": 90, "category": "Endodoncia", "aliases": ["nervy", "koreň"]},
    "Korunka": {"price": "450–800 €", "duration_min": 60, "category": "Protétika"},
    "Implantát": {"price": "800–1 200 €", "duration_min": 60, "category": "Implantológia"},
    "Bielenie zubov": {"price": "250–400 €", "duration_min": 60, "category": "Estetická"},
    "Vstupné vyšetrenie": {"price": "20–50 €", "duration_min": 30, "category": "Vstupné"},
    "Urgentný prípad": {"price": "Podľa výkonu", "duration_min": 30, "category": "Urgent", "aliases": ["bolesť", "opuch"]}
}

def validate_service(service_name: str) -> Optional[str]:
    if not service_name: return None
    s_lower = service_name.lower().strip()
    for canonical in SERVICES_DB.keys():
        if s_lower == canonical.lower(): return canonical
    for canonical, d in SERVICES_DB.items():
        if "aliases" in d:
            for alias in d["aliases"]:
                if alias in s_lower: return canonical
    return None

# --- CALENDAR INTEGRATION ---
def get_available_slots_for_days(days=4):
    now = datetime.now()
    # Explicit format to avoid microsecond issues
    start_iso = (now + timedelta(days=1)).strftime("%Y-%m-%dT08:00:00Z")
    end_iso = (now + timedelta(days=days+1)).strftime("%Y-%m-%dT18:00:00Z")
    
    params = {
        "apiKey": CAL_API_KEY, 
        "eventTypeId": CAL_EVENT_TYPE_ID, 
        "startTime": start_iso, 
        "endTime": end_iso
    }
    print(f"📅 Fetching slots from Cal.com: {start_iso} to {end_iso}")
    
    try:
        resp = requests.get(f"{CAL_BASE_URL}/slots", params=params, timeout=8)
        if not resp.ok:
            print(f"❌ Cal.com API Error: {resp.status_code} - {resp.text}")
            return []
            
        raw_slots = resp.json().get("slots", {})
        formatted = []
        for date_key, day_slots in raw_slots.items():
            for s in day_slots:
                dt_obj = datetime.fromisoformat(s.get("time").replace("Z", "+00:00"))
                formatted.append({
                    "datetime": dt_obj.strftime("%Y-%m-%d %H:%M"), 
                    "iso": s.get("time")
                })
        print(f"✅ Found {len(formatted)} slots.")
        return formatted[:12] # Limit to 12
    except Exception as e: 
        print(f"❌ Exception in slot fetching: {e}")
        return []

def create_booking_cal(name, phone, email, datetime_iso, notes=None):
    payload = {
        "eventTypeId": int(CAL_EVENT_TYPE_ID), 
        "start": datetime_iso, 
        "responses": {
            "name": name or "Unknown Patient", 
            "email": email or "no-email@provided.com", 
            "phone": phone or "Unknown"
        }, 
        "timeZone": "Europe/Bratislava", 
        "language": "sk",
        "metadata": {"source": "retell_ai", "notes": notes}
    }
    print(f"📝 Creating booking at {datetime_iso} for {name}")
    try:
        resp = requests.post(f"{CAL_BASE_URL}/bookings", params={"apiKey": CAL_API_KEY}, json=payload, timeout=8)
        if resp.ok:
            print("✅ Booking successfully created in Cal.com!")
            return {"status": "success", "data": resp.json()}
        else:
            print(f"❌ Booking failed: {resp.status_code} - {resp.text}")
            return {"status": "error", "message": resp.text}
    except Exception as e: 
        print(f"❌ Exception in booking: {e}")
        return {"status": "error", "message": str(e)}

# --- PATIENT LOOKUP ---
def get_patient_by_phone(phone_number: str):
    if not SUPABASE_URL or not SUPABASE_KEY: 
        print("⚠️ Missing Supabase credentials.")
        return None
    clean_phone = phone_number.replace(" ", "").replace("-", "")
    url = f"{SUPABASE_URL}/rest/v1/Patients"
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json"}
    try:
        print(f"🔍 Searching Supabase for: {clean_phone}")
        response = requests.get(url, headers=headers, params={"phone": f"eq.{clean_phone}"}, timeout=3)
        patients = response.json()
        if patients and len(patients) > 0:
            p = patients[0]
            print(f"✅ Found patient: {p.get('forename')} {p.get('surname')}")
            return {"forename": p.get("forename"), "surname": p.get("surname")}
        print("👤 Patient not found in Supabase.")
        return None
    except Exception as e: 
        print(f"❌ Supabase error: {e}")
        return None

# --- FASTAPI APP ---
app = FastAPI()

MOCK_PATIENTS = {"+421919165630": {"forename": "Andrej", "surname": "Repický"}}

@app.get("/")
async def root(): return {"status": "online", "time": datetime.now().isoformat()}

@app.post("/firstWebhook")
async def first_webhook(request: Request):
    print("\n🔔 --- firstWebhook START ---")
    try:
        body = await request.json()
        print(f"📦 Payload: {json.dumps(body, indent=2)}")
        
        call_data = body.get("call", {})
        from_number = call_data.get("from_number") or body.get("from_number") or "UNKNOWN"
        clean_number = str(from_number).replace(" ", "")
        print(f"📞 From Number: {clean_number}")
        
        patient = get_patient_by_phone(clean_number) or MOCK_PATIENTS.get(clean_number)
        
        if patient:
            name = f"{patient.get('forename', '')} {patient.get('surname', '')}"
            greeting = f"Dobrý deň {name}, ako vám dnes môžem pomôcť?"
            res = {"existing_patient_data": patient, "greeting_message": greeting}
        else:
            res = {"existing_patient_data": {"forename": None}, "greeting_message": "Dobrý deň, tu recepcia Dentalis Clinic, ako vám môžem pomôcť?"}
            
        print(f"📤 Result: {res['greeting_message']}")
        return res
    except Exception as e:
        print(f"💥 firstWebhook Error: {e}")
        return {"greeting_message": "Dobrý deň, tu recepcia Dentalis Clinic."}

@app.post("/Get_Appointment")
async def get_appointment(request: Request):
    print("\n📅 --- Get_Appointment START ---")
    try:
        data = await request.json()
        print(f"📦 Payload: {json.dumps(data, indent=2)}")
        s_name = data.get("args", {}).get("service", "General")
        canonical = validate_service(s_name)
        
        slots = get_available_slots_for_days(days=4)
        for s in slots: s["service"] = canonical or "General"
        
        print(f"🍱 Returning {len(slots)} slots for {canonical or 'General'}")
        return {"available_slots": slots}
    except Exception as e:
        print(f"💥 Get_Appointment Error: {e}")
        return {"available_slots": []}

@app.post("/Book_appointment")
async def book_appointment(request: Request):
    print("\n📝 --- Book_appointment START ---")
    try:
        data = await request.json()
        print(f"📦 Payload: {json.dumps(data, indent=2)}")
        args = data.get("args", {})
        
        dt_str = args.get("datetime", "")
        p_name = args.get("patient_name") or "Anonymous"
        p_phone = args.get("patient_phone") or "N/A"
        service = args.get("service")
        
        try:
            dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
            iso = dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        except: 
            iso = dt_str
            
        result = create_booking_cal(name=p_name, phone=p_phone, email="", datetime_iso=iso, notes=f"Service: {service}")
        return result
    except Exception as e:
        print(f"💥 Book_appointment Error: {e}")
        return {"status": "error", "message": str(e)}

# --- STUBS TO AVOID 404 ---
@app.post("/send_form_registration")
async def s1(r: Request): return {"status": "success"}
@app.post("/Change_appointment")
async def s2(r: Request): return {"status": "success"}
@app.post("/cancelAppointment")
async def s3(r: Request): return {"status": "success"}
@app.post("/send_form_cancel")
async def s4(r: Request): return {"status": "success"}
@app.post("/GET_booked_appointment")
async def s5(r: Request): return {"appointment": None}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8002)))
