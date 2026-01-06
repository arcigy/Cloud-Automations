import os
import json
import requests
import datetime
from dotenv import load_dotenv

# Load environment variables from root .env
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Up 3 levels: backend -> Arcigy_website -> cloud_automations -> Agentic Workflows
root_env = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(BASE_DIR))), ".env")
if os.path.exists(root_env):
    load_dotenv(root_env, override=True)
else:
    load_dotenv(override=True)

# Configurations
CAL_API_KEY = os.getenv("CAL_API_KEY") or "cal_live_6101fbb825f9173a4f3e7045d20d5bdc"
CAL_EVENT_TYPE_ID = os.getenv("CAL_EVENT_TYPE_ID") or "3877498"

def get_calendar_availability():
    """
    Fetches bookings from Cal.com and returns a formatted summary for the frontend.
    Replicates the logic from n8n 'HTTP Request1' and 'Code in JavaScript' nodes.
    """
    try:
        # Cal.com v1 API for bookings (as used in n8n)
        url = "https://api.cal.com/v1/bookings"
        params = {
            "apiKey": CAL_API_KEY,
            "eventTypeId": CAL_EVENT_TYPE_ID,
            "dateFrom": datetime.datetime.now().isoformat()
        }
        
        response = requests.get(url, params=params)
        if not response.ok:
            print(f"Cal.com Error: {response.status_code} - {response.text}")
            return []

        data = response.json()
        bookings = data.get("bookings", [])
        
        transformed_bookings = []
        for b in bookings:
            start = b.get("startTime")
            end = b.get("endTime")
            if start and end:
                transformed_bookings.append(f"booking: ({start}), ({end})")
        
        # The frontend expects a list with an object containing bookings_summary
        return [{ "bookings_summary": transformed_bookings }]

    except Exception as e:
        print(f"Error in Calendar Engine (Availability): {e}")
        return []

def confirm_booking(booking_time_iso, email, name, phone, conversation_id=None):
    """
    Creates a real booking in Cal.com.
    """
    try:
        # Sanitize phone number (if it comes from URL, '+' might become ' ')
        if phone and phone.startswith(" ") and not phone.startswith("+"):
            phone = "+" + phone.strip()
        elif phone and not phone.startswith("+") and phone.isdigit():
            # If it's just digits, we might want to keep it as is or add +
            pass 

        url = "https://api.cal.com/v1/bookings"
        payload = {
            "eventTypeId": int(CAL_EVENT_TYPE_ID),
            "start": booking_time_iso,
            "responses": {
                "name": name,
                "email": email,
                "phone": phone,
                "attendeePhoneNumber": phone,
                "title": f"Diagnostika - {name}",
                "location": "Integration Link"
            },
            "timeZone": "Europe/Bratislava",
            "language": "sk",
            "metadata": {"conversation_id": conversation_id}
        }
        
        print(f"DEBUG: Sending to Cal.com: {json.dumps(payload)}")
        
        response = requests.post(
            url, 
            params={"apiKey": CAL_API_KEY}, 
            json=payload
        )
        
        if response.ok:
            return {"status": "success", "message": "Booking confirmed", "data": response.json()}
        else:
            print(f"Booking Error: {response.text}")
            return {"status": "error", "message": response.text}
            
    except Exception as e:
        print(f"Error in Calendar Engine (Confirm): {e}")
        return {"status": "error", "message": str(e)}

def cancel_booking(uid):
    """
    Cancels an existing booking by its UID.
    """
    try:
        url = f"https://api.cal.com/v1/bookings/{uid}/cancel"
        response = requests.delete(url, params={"apiKey": CAL_API_KEY})
        if response.ok:
            return {"status": "success", "message": "Booking canceled"}
        return {"status": "error", "message": response.text}
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    # Local Test
    print("Testing Availability...")
    print(json.dumps(get_calendar_availability(), indent=2))
