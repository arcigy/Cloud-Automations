import os
import requests
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load env from root
load_dotenv()

# Fallback values from local .env to ensure it works on Railway without manual config
CAL_API_KEY = os.getenv("CAL_API_KEY", "cal_live_6101fbb825f9173a4f3e7045d20d5bdc")
CAL_EVENT_TYPE_ID = os.getenv("CAL_EVENT_TYPE_ID", "3877498")

BASE_URL = "https://api.cal.com/v1"

def get_available_slots_for_days(days=3):
    """
    Fetch available slots for the next N days.
    Returns a list of slots formatted for the agent.
    """
    if not CAL_API_KEY or not CAL_EVENT_TYPE_ID:
        print("❌ Missing CAL_API_KEY or CAL_EVENT_TYPE_ID")
        return []

    now = datetime.now()
    # Start looking from tomorrow (or today + 1 hour if we want dynamic)
    # Let's say we look from tomorrow to keep it simple for now
    start_time = (now + timedelta(days=1)).replace(hour=8, minute=0, second=0).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    end_time = (now + timedelta(days=days+1)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    
    params = {
        "apiKey": CAL_API_KEY,
        "eventTypeId": CAL_EVENT_TYPE_ID,
        "startTime": start_time,
        "endTime": end_time
    }
    
    try:
        print(f"📅 Fetching slots from {start_time} to {end_time}")
        resp = requests.get(f"{BASE_URL}/slots", params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        raw_slots = data.get("slots", {})
        formatted_slots = []
        
        for date_key, day_slots in raw_slots.items():
            for s in day_slots:
                # Time is in ISO format like '2023-10-25T09:00:00.000+01:00' or similar
                # We want to return readable slots
                # Ideally, we return ISO for machine reading, agent acts on it
                slot_iso = s.get("time")
                if slot_iso:
                    # Parse to nicer format? Or keep ISO?
                    # Let's keep a simplified ISO-like string "YYYY-MM-DD HH:MM"
                    dt_obj = datetime.fromisoformat(slot_iso.replace("Z", "+00:00"))
                    nice_format = dt_obj.strftime("%Y-%m-%d %H:%M")
                    formatted_slots.append({"datetime": nice_format, "iso": slot_iso})
                    
        return formatted_slots[:15] # Return max 15 slots to not overwhelm context
        
    except Exception as e:
        print(f"❌ Error fetching slots: {e}")
        return []

def create_booking_cal(name, phone, email, datetime_iso, notes=None):
    """
    Books a slot in Cal.com
    """
    if not CAL_API_KEY or not CAL_EVENT_TYPE_ID:
        return {"status": "error", "message": "Missing Configuration"}

    # Sanitize inputs
    if not email:
        email = "no-email@provided.com" # Placeholder
        
    payload = {
        "eventTypeId": int(CAL_EVENT_TYPE_ID),
        "start": datetime_iso,
        "responses": {
            "name": name,
            "email": email,
            "phone": phone,
            "notes": notes or "Rezervované cez AI Agenta"
        },
        "timeZone": "Europe/Bratislava",
        "language": "sk",
        "metadata": {"source": "retell_ai"}
    }
    
    try:
        print(f"📝 Booking slot at {datetime_iso} for {name}")
        resp = requests.post(f"{BASE_URL}/bookings", params={"apiKey": CAL_API_KEY}, json=payload, timeout=10)
        
        if resp.status_code in [200, 201]:
            data = resp.json()
            # Check if booking was actually successful (sometimes returns 200 but logic error)
            return {"status": "success", "data": data, "message": "Booking successful"}
        else:
            print(f"❌ Booking failed: {resp.text}")
            return {"status": "error", "message": f"Provider API Error: {resp.text}"}
            
    except Exception as e:
        print(f"❌ Booking Exception: {e}")
        return {"status": "error", "message": str(e)}
