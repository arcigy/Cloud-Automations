import os
import requests
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

def get_patient_by_phone(phone_number: str):
    """
    Search for a patient in Supabase by phone number.
    Returns patient data if found, None otherwise.
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("⚠️ Supabase credentials not configured")
        return None
    
    # Clean phone number (remove spaces, dashes)
    clean_phone = phone_number.replace(" ", "").replace("-", "")
    
    url = f"{SUPABASE_URL}/rest/v1/patient"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    
    # Search by phone number - try multiple possible column names
    params = {
        "or": f"(phone.eq.{clean_phone},phone_number.eq.{clean_phone},tel.eq.{clean_phone})"
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=5)
        response.raise_for_status()
        
        patients = response.json()
        
        if patients and len(patients) > 0:
            patient = patients[0]  # Take first match
            print(f"✅ Found patient in Supabase: {patient.get('forename', 'N/A')} {patient.get('surname', 'N/A')}")
            return {
                "forename": patient.get("forename") or patient.get("first_name"),
                "surname": patient.get("surname") or patient.get("last_name"),
                "email": patient.get("email"),
                "last_visit_date": patient.get("last_visit_date") or patient.get("last_visit"),
                "other_relevant_info": patient.get("notes") or patient.get("other_relevant_info") or ""
            }
        else:
            print(f"👤 No patient found for phone: {clean_phone}")
            return None
            
    except Exception as e:
        print(f"❌ Supabase error: {e}")
        return None

if __name__ == "__main__":
    # Test
    result = get_patient_by_phone("+421919165630")
    print(result)
