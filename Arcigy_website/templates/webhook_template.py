import os
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def handle_webhook(payload):
    """
    Standard entry point for webhook triggers.
    """
    try:
        print(f"Received payload: {json.dumps(payload, indent=2)}")
        
        # 1. Validate Payload
        # 2. Logic (e.g., call execution layer scripts)
        # 3. Return result
        
        return {"status": "success", "data": "Processed successfully"}
        
    except Exception as e:
        print(f"Error processing webhook: {e}")
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    # Local testing example
    test_payload = {"test": "data"}
    print(handle_webhook(test_payload))
