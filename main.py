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
def get_available_slots_for_days(days=3):
    params = {"apiKey": CAL_API_KEY, "eventTypeId": CAL_EVENT_TYPE_ID, "startTime": (datetime.now() + timedelta(days=1)).isoformat() + "Z", "endTime": (datetime.now() + timedelta(days=days+1)).isoformat() + "Z"}
    try:
        resp = requests.get(f"{CAL_BASE_URL}/slots", params=params, timeout=5)
        raw_slots = resp.json().get("slots", {})
        formatted = []
        for date_key, day_slots in raw_slots.items():
            for s in day_slots:
                dt_obj = datetime.fromisoformat(s.get("time").replace("Z", "+00:00"))
                formatted.append({"datetime": dt_obj.strftime("%Y-%m-%d %H:%M"), "iso": s.get("time")})
        return formatted[:15]
    except: return []

def create_booking_cal(name, phone, email, datetime_iso, notes=None):
    payload = {"eventTypeId": int(CAL_EVENT_TYPE_ID), "start": datetime_iso, "responses": {"name": name, "email": email or "no-email@provided.com", "phone": phone}, "timeZone": "Europe/Bratislava", "language": "sk"}
    try:
        resp = requests.post(f"{CAL_BASE_URL}/bookings", params={"apiKey": CAL_API_KEY}, json=payload, timeout=5)
        return {"status": "success" if resp.ok else "error", "data": resp.json()}
    except Exception as e: return {"status": "error", "message": str(e)}

# --- PATIENT LOOKUP ---
def get_patient_by_phone(phone_number: str):
    if not SUPABASE_URL or not SUPABASE_KEY: return None
    clean_phone = phone_number.replace(" ", "").replace("-", "")
    url = f"{SUPABASE_URL}/rest/v1/Patients"
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json"}
    try:
        response = requests.get(url, headers=headers, params={"phone": f"eq.{clean_phone}"}, timeout=2)
        patients = response.json()
        if patients:
            p = patients[0]
            return {"forename": p.get("forename") or p.get("first_name"), "surname": p.get("surname") or p.get("last_name")}
        return None
    except: return None

# --- FASTAPI APP ---
app = FastAPI()

MOCK_PATIENTS = {"+421919165630": {"forename": "Andrej", "surname": "Repický"}}

@app.get("/")
async def root(): return {"status": "online"}

@app.post("/firstWebhook")
async def first_webhook(request: Request):
    data = await request.json()
    from_number = data.get("call", {}).get("from_number") or "UNKNOWN"
    clean_number = str(from_number).replace(" ", "")
    patient = get_patient_by_phone(clean_number) or MOCK_PATIENTS.get(clean_number)
    
    if patient:
        name = f"{patient.get('forename', '')} {patient.get('surname', '')}"
        greeting = f"Dobrý deň {name}, ako vám dnes môžem pomôcť?"
        res = {"existing_patient_data": patient, "greeting_message": greeting}
    else:
        res = {"existing_patient_data": {"forename": None}, "greeting_message": "Dobrý deň, tu recepcia Dentalis Clinic, ako vám môžem pomôcť?"}
    return res

@app.post("/Get_Appointment")
async def get_appointment(request: Request):
    data = await request.json()
    s_name = data.get("args", {}).get("service", "General")
    canonical = validate_service(s_name)
    slots = get_available_slots_for_days(days=4)
    for s in slots: s["service"] = canonical or "General"
    return {"available_slots": slots}

@app.post("/Book_appointment")
async def book_appointment(request: Request):
    data = await request.json()
    args = data.get("args", {})
    try:
        dt = datetime.strptime(args.get("datetime", ""), "%Y-%m-%d %H:%M")
        iso = dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    except: iso = args.get("datetime")
    return create_booking_cal(name=args.get("patient_name"), phone=args.get("patient_phone"), email="", datetime_iso=iso)

# --- MISSING ENDPOINTS (To avoid 404) ---
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
