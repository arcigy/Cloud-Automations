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
class ServiceType(str, Enum):
    PREVENTIVNA_PREHLIADKA = "Preventívna prehliadka"
    DENTALNE_CISTENIE = "Dentálne čistenie"
    KOMPOZITNA_VYPLN = "Kompozitná výplň"
    KORENOVE_OSETRENIE = "Koreňové ošetrenie"
    KORUNKA = "Korunka"
    IMPLANTAT = "Implantát"
    BIELENIE_ZUBOV = "Bielenie zubov"
    VSTUPNE_VYSETRENIE = "Vstupné vyšetrenie"
    KONZULTACIA = "Konzultácia"
    URGENTNY_PRIKAZ = "Urgentný prípad"

SERVICES_DB: Dict[str, Dict[str, Any]] = {
    "Preventívna prehliadka": {
        "price": "20 €",
        "duration_min": 30,
        "category": "Preventívna stomatológia"
    },
    "Dentálne čistenie": {
        "price": "45–80 €",
        "duration_min": 60,
        "category": "Preventívna stomatológia",
        "aliases": ["hygiena", "dentálna hygiena", "čistenie zubov", "scaling"]
    },
    "Kompozitná výplň": {
        "price": "60–120 €",
        "duration_min": 45,
        "category": "Konzervatívna stomatológia",
        "aliases": ["plomba", "kaz", "výplň"]
    },
    "Koreňové ošetrenie": {
        "price": "150–300 €",
        "duration_min": 90,
        "category": "Konzervatívna stomatológia",
        "aliases": ["endodoncia", "koreň", "nervy"]
    },
    "Korunka": {
        "price": "450–800 €",
        "duration_min": 60,
        "category": "Protétika"
    },
    "Implantát": {
        "price": "800–1 200 €",
        "duration_min": 60,
        "category": "Implantológia"
    },
    "Bielenie zubov": {
        "price": "250–400 €",
        "duration_min": 60,
        "category": "Estetická stomatológia"
    },
    "Vstupné vyšetrenie": {
        "price": "20–50 €",
        "duration_min": 30,
        "category": "Preventívna stomatológia",
        "aliases": ["vstupná prehliadka", "prvé vyšetrenie"]
    },
    "Urgentný prípad": {
        "price": "Podľa výkonu",
        "duration_min": 30,
        "category": "Urgentné služby",
        "aliases": ["bolesť", "opuch", "akútne"]
    }
}

def validate_service(service_name: str) -> Optional[str]:
    if not service_name: return None
    s_lower = service_name.lower().strip()
    for canonical in SERVICES_DB.keys():
        if s_lower == canonical.lower(): return canonical
    for canonical, details in SERVICES_DB.items():
        if "aliases" in details:
            for alias in details["aliases"]:
                if alias in s_lower: return canonical
    return None

# --- CALENDAR INTEGRATION ---
def get_available_slots_for_days(days=3):
    if not CAL_API_KEY or not CAL_EVENT_TYPE_ID: return []
    now = datetime.now()
    start_time = (now + timedelta(days=1)).replace(hour=8, minute=0, second=0).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    end_time = (now + timedelta(days=days+1)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    params = {"apiKey": CAL_API_KEY, "eventTypeId": CAL_EVENT_TYPE_ID, "startTime": start_time, "endTime": end_time}
    try:
        resp = requests.get(f"{CAL_BASE_URL}/slots", params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        raw_slots = data.get("slots", {})
        formatted_slots = []
        for date_key, day_slots in raw_slots.items():
            for s in day_slots:
                slot_iso = s.get("time")
                if slot_iso:
                    dt_obj = datetime.fromisoformat(slot_iso.replace("Z", "+00:00"))
                    formatted_slots.append({"datetime": dt_obj.strftime("%Y-%m-%d %H:%M"), "iso": slot_iso})
        return formatted_slots[:15]
    except Exception as e:
        print(f"❌ Error fetching slots: {e}")
        return []

def create_booking_cal(name, phone, email, datetime_iso, notes=None):
    if not CAL_API_KEY or not CAL_EVENT_TYPE_ID: return {"status": "error", "message": "Missing Config"}
    payload = {
        "eventTypeId": int(CAL_EVENT_TYPE_ID),
        "start": datetime_iso,
        "responses": {"name": name, "email": email or "no-email@provided.com", "phone": phone},
        "timeZone": "Europe/Bratislava",
        "language": "sk",
        "metadata": {"source": "retell_ai", "notes": notes}
    }
    try:
        resp = requests.post(f"{CAL_BASE_URL}/bookings", params={"apiKey": CAL_API_KEY}, json=payload, timeout=10)
        if resp.status_code in [200, 201]: return {"status": "success", "data": resp.json()}
        return {"status": "error", "message": resp.text}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# --- PATIENT LOOKUP ---
def get_patient_by_phone(phone_number: str):
    if not SUPABASE_URL or not SUPABASE_KEY: return None
    clean_phone = phone_number.replace(" ", "").replace("-", "")
    url = f"{SUPABASE_URL}/rest/v1/Patients"
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json"}
    params = {"phone": f"eq.{clean_phone}"}
    try:
        response = requests.get(url, headers=headers, params=params, timeout=2)
        response.raise_for_status()
        patients = response.json()
        if patients:
            p = patients[0]
            return {
                "forename": p.get("forename") or p.get("first_name"),
                "surname": p.get("surname") or p.get("last_name"),
                "email": p.get("email"),
                "last_visit_date": p.get("last_visit_date"),
                "other_relevant_info": p.get("notes") or ""
            }
        return None
    except Exception as e:
        print(f"❌ Supabase error: {e}")
        return None

# --- FASTAPI APP ---
app = FastAPI(title="Retell AI Receptionist Backend")

MOCK_PATIENTS = {
    "+421919165630": {
        "forename": "Andrej",
        "surname": "Repický",
        "email": "repicky@example.com",
        "last_visit_date": "2024-01-01",
        "other_relevant_info": "VIP klient"
    }
}

@app.get("/")
async def root(): return {"status": "online"}

@app.post("/firstWebhook")
async def first_webhook(request: Request):
    print("🔔 firstWebhook CALLED")
    data = await request.json()
    call_data = data.get("call", {})
    from_number = call_data.get("from_number") or "UNKNOWN"
    clean_number = str(from_number).replace(" ", "")
    
    patient = get_patient_by_phone(clean_number) or MOCK_PATIENTS.get(clean_number)
    
    if patient:
        name = f"{patient.get('forename', '')} {patient.get('surname', '')}"
        greeting = f"Dobrý deň {name}, ako vám dnes môžem pomôcť?"
        res = {"existing_patient_data": patient, "greeting_message": greeting}
    else:
        res = {
            "existing_patient_data": {"forename": None},
            "greeting_message": "Dobrý deň, tu recepcia Dentalis Clinic, ako vám môžem pomôcť?"
        }
    return res

@app.post("/Get_Appointment")
async def get_appointment(request: Request):
    data = await request.json()
    service = data.get("args", {}).get("service", "General")
    canonical = validate_service(service)
    if not canonical and service != "General":
        return {"error": f"Služba '{service}' nie je v ponuke."}
    
    slots = get_available_slots_for_days(days=4)
    for s in slots: s["service"] = canonical or "General"
    return {"available_slots": slots}

@app.post("/Book_appointment")
async def book_appointment(request: Request):
    data = await request.json()
    args = data.get("args", {})
    service = args.get("service")
    dt_str = args.get("datetime")
    canonical = validate_service(service)
    if not canonical or not dt_str: return {"status": "error", "message": "Chýba služba alebo čas."}
    
    try:
        dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
        iso = dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    except: iso = dt_str
        
    result = create_booking_cal(name=args.get("patient_name"), phone=args.get("patient_phone"), email="", datetime_iso=iso, notes=f"Service: {canonical}")
    return result

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8002)))
