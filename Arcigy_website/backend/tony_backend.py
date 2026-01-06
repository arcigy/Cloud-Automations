import os
import json
import datetime
from openai import OpenAI
from supabase import create_client, Client
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
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Initialize clients
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# Load System Prompt from external file
# Up 3 levels to reach directives
PROMPT_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "..", "directives", "tony_prompt.md")

def load_system_prompt():
    try:
        with open(PROMPT_PATH, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"Error loading prompt: {e}")
        return "You are Tony, a helpful AI assistant."

def persist_conversation(conversation_id, message, output, formatted_history):
    """
    Handles database updates in the background.
    """
    try:
        # 1. Update Memory
        conv_data = {
            "messageID": conversation_id,
            "conversation": formatted_history + f"\nUser: {message}\nBot: {output['response']}"
        }
        try:
            supabase.table("ConversationMemory").upsert(conv_data, on_conflict="messageID").execute()
        except Exception as db_err:
            print(f"Database Warning (Memory): {db_err}")

        # 2. Update Leads (Patients)
        if all(output.get(key) != "null" for key in ["forname", "surname", "email", "phone"]):
            patient_data = {
                "forename": output["forname"],
                "surname": output["surname"],
                "email": output["email"],
                "phone": output["phone"]
            }
            try:
                supabase.table("Patients").upsert(patient_data, on_conflict="phone").execute()
            except Exception as db_err:
                print(f"Database Warning (Patients): {db_err}")
    except Exception as e:
        print(f"Background Persistence Error: {e}")

def get_tony_response(message, conversation_id, history, user_lang=None):
    """
    Handles the AI reasoning using the external prompt.
    """
    try:
        # 1. Format history
        formatted_history = ""
        if isinstance(history, list):
            formatted_history = "\n".join([f"{m.get('type', 'unknown').capitalize()}: {m.get('text', '')}" for m in history])
        
        # 2. Get AI Response
        system_prompt = load_system_prompt()
        if "{now}" in system_prompt:
            system_prompt = system_prompt.replace("{now}", str(datetime.datetime.now()))
        
        # Guide the AI on the required language
        detected_lang = user_lang if user_lang else ('sk' if any(word in message.lower() for word in ['ahoj', 'chcem', 'termin', 'ano', 'dobry']) else 'en')
        lang_instruction = f"IMPORTANT: Respond in {detected_lang.upper()} language." if detected_lang else ""

        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt + f"\n\n{lang_instruction}\nIMPORTANT: Respond ONLY with a raw JSON object. No markdown blocks."},
                {"role": "user", "content": f"HISTÓRIA KONVERZÁCIE:\n{formatted_history}\n\nAKTUÁLNA SPRÁVA OD POUŽÍVATEĽA: {message}"}
            ],
            response_format={"type": "json_object"}
        )
        
        raw_text = response.choices[0].message.content.strip()
        
        # Aggressive cleaning for JSON
        try:
            output = json.loads(raw_text)
        except json.JSONDecodeError:
            # Fallback: Find the first '{' and last '}'
            start = raw_text.find('{')
            end = raw_text.rfind('}')
            if start != -1 and end != -1:
                output = json.loads(raw_text[start:end+1])
            else:
                raise
        
        # Determine language (simple heuristic)
        lang = user_lang if user_lang else ('sk' if any(word in message.lower() for word in ['ahoj', 'chcem', 'termin', 'ano', 'dobry']) else 'en')
        output['lang'] = lang
        
        return output, formatted_history

    except Exception as e:
        import traceback
        print(f"Error in Tony AI: {e}")
        traceback.print_exc()
        return {
            "intention": "question",
            "response": "Prepáč, niečo sa pokazilo. Skús prosím znova.",
            "error": str(e)
        }, ""

if __name__ == "__main__":
    # Local Test
    test_msg = "Ahoj, ja som Branislav Laubert, moj email je branislav@arcigy.com a tel cislo +421912345678. Chcem demo."
    result = get_tony_response(test_msg, "test_conv_123", [])
    print(json.dumps(result, indent=2))
