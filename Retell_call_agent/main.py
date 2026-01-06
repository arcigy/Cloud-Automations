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

@app.post("/firstWebhook")
async def first_webhook(request: Request):
    """
    Triggered when Retell starts the call.
    Expects from_number to lookup patient data.
    """
    print("\n" + "🚀" * 30)
    print("🔔 RETELL: FIRST WEBHOOK RECEIVED")
    print(f"Time: {datetime.now().strftime('%H:%M:%S')}")
    
    # Log headers for debugging
    headers = dict(request.headers)
    print(f"Headers: {json.dumps(headers, indent=2)}")
    
    try:
        # Check if there is a body
        body = await request.body()
        if not body:
            print("⚠️ Empty body received")
            data = {}
        else:
            try:
                data = json.loads(body)
                print(f"Payload: {json.dumps(data, indent=2)}")
            except json.JSONDecodeError:
                print(f"⚠️ Could not parse JSON body: {body.decode(errors='ignore')}")
                data = {}
        
        # Look for from_number in various places
        from_number = data.get("from_number") or data.get("caller_id") or "unknown"
        
        if from_number == "unknown":
            # Check headers (Retell often passes info there)
            from_number = headers.get("x-retell-from-number") or "unknown"
        
        # Cleanup number
        clean_number = str(from_number).replace(" ", "")
        
        # Lookup patient
        patient = MOCK_PATIENTS.get(clean_number)
        
        if patient:
            print(f"✅ Patient FOUND in database: {patient['forename']} {patient['surname']}")
            response = {"existing_patient_data": patient}
        else:
            print(f"👤 Patient NOT FOUND (New User: {from_number})")
            response = {
                "existing_patient_data": {
                    "forename": None,
                    "surname": None,
                    "email": None,
                    "last_visit_date": None,
                    "other_relevant_info": "Neznámy volajúci."
                }
            }
        
        print(f"Returning to Retell: {json.dumps(response)}")
        print("🚀" * 30 + "\n")
        return response
    except Exception as e:
        print(f"❌ Error in firstWebhook: {e}")
        return {
            "existing_patient_data": {
                "forename": None,
                "surname": None,
                "email": None,
                "last_visit_date": None,
                "other_relevant_info": f"Internal Error: {str(e)}"
            }
        }

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
