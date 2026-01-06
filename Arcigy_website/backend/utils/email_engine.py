import os
import smtplib
import json
import imaplib
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# SMTP Config
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.hostinger.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 465))

email_acc = os.getenv("EMAIL_ACCOUNT_BRANISLAV")
if email_acc and ":" in email_acc:
    email_acc = email_acc.strip('"\'')
    parts = email_acc.split(":", 1)
    SMTP_USER = parts[0].strip()
    SMTP_PASS = parts[1].strip()
else:
    SMTP_USER = os.getenv("SMTP_USER", "branislav@arcigy.com")
    SMTP_PASS = os.getenv("SMTP_PASS")

def get_paths():
    """Helper to get correct paths relative to Arcigy_website root."""
    
    # 1. Try file-relative path first (most reliable if file structure is intact)
    # email_engine.py is in .../Arcigy_website/backend/utils/
    # We want .../Arcigy_website/
    try:
        current_file = os.path.abspath(__file__)
        # Up 3 levels: utils -> backend -> Arcigy_website
        base_dir_rel = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
        if os.path.exists(os.path.join(base_dir_rel, "assets")):
             base_dir = base_dir_rel
        else:
             raise Exception("Relative path check failed")
    except:
        # 2. Fallback to CWD construction
        cwd = os.getcwd()
        if "Agentic Workflows" in cwd:
             base_dir = os.path.join(cwd, "cloud_automations", "Arcigy_website")
        else:
             # Last resort fallback if run from weird place
             base_dir = cwd

    template_path = os.path.join(base_dir, "templates", "premium_email.html")
    asset_path = os.path.join(base_dir, "assets", "cyber_socials_layout.jpg")
    
    print(f"DEBUG PATHS:")
    print(f"  Base Dir: {base_dir}")
    print(f"  Template Target: {template_path}")
    print(f"  Asset Target: {asset_path}")

    return template_path, asset_path

def get_template():
    """Loads the premium HTML template from the fixed location."""
    template_path, _ = get_paths()
    
    # Try reading directly
    try:
        if os.path.exists(template_path):
            with open(template_path, 'r', encoding='utf-8') as f:
                return f.read()
    except Exception as e:
        print(f"Error reading template: {e}")
            
    print(f"CRITICAL: Template file missing at {template_path}")
    return "<html><body><h2>Error: Template not found</h2><p>{greeting}</p><p>{details}</p><br><a href='{confirm_url}'>Potvrdiť</a></body></html>"

def format_datetime(iso_string, lang='sk'):
    """Converts ISO 8601 to a pretty readable format."""
    try:
        from datetime import datetime
        if not iso_string or iso_string == "null":
            return "---"
        # Handle Zulu or offsets
        clean_iso = iso_string.replace('Z', '+00:00')
        dt = datetime.fromisoformat(clean_iso)
        
        if lang == 'sk':
            months = ["", "január", "február", "marec", "apríl", "máj", "jún", "júl", "august", "september", "október", "november", "december"]
            return f"{dt.day}. {months[dt.month]} {dt.year} o {dt.strftime('%H:%M')}"
        else:
            return dt.strftime("%B %d, %Y at %H:%M")
    except:
        return iso_string

def send_confirmation_email(to_email, name, action_type, details, confirm_url, lang='sk'):
    """Sends a premium confirmation email with CID embedded images."""
    try:
        print(f"\n🔧 EMAIL ENGINE DEBUG:")
        template_path, asset_path = get_paths()
        
        html = get_template()
        print(f"   Template loaded: {len(html)} chars")
        
        if not os.path.exists(asset_path):
             # Try absolute fallback
             print(f"   ❌ WARNING: Image asset not found at {asset_path}")
        else:
            print(f"   ✅ Image asset found at {asset_path}")

        pretty_date = format_datetime(details, lang)
        
        if lang == 'sk':
            subjects = {
                "book": "Potvrdenie termínu | ArciGy",
                "cancel": "Zrušenie termínu | ArciGy",
                "reschedule": "Presun termínu | ArciGy"
            }
            greetings = f"Dobrý deň,<br class='m-br' style='display:none;'> {name}!"
            descriptions = {
                "book": f"Váš nový termín na diagnostiku je:<br><b>{pretty_date}</b>.",
                "cancel": f"Dostali sme požiadavku na zrušenie termínu:<br><b>{pretty_date}</b>.",
                "reschedule": f"Váš termín bol presunutý na:<br><b>{pretty_date}</b>."
            }
        else:
            subjects = {
                "book": "Booking Confirmation | ArciGy",
                "cancel": "Cancellation | ArciGy",
                "reschedule": "Rescheduling | ArciGy"
            }
            greetings = f"Hello,<br class='m-br' style='display:none;'> {name}!"
            descriptions = {
                "book": f"Your new diagnostic appointment is set for: <b>{pretty_date}</b>.",
                "cancel": f"We received a request to cancel your appointment: <b>{pretty_date}</b>.",
                "reschedule": f"Your appointment has been rescheduled to: <b>{pretty_date}</b>."
            }

        email_id = str(int(time.time()))
        
        # Inject variables into HTML
        html_content = html.replace("{greeting}", greetings).replace("{details}", descriptions.get(action_type, "")).replace("{confirm_url}", confirm_url).replace("{email_id}", email_id)
        
        # Create plain text version
        desc_text = descriptions.get(action_type, "").replace('<b>', '').replace('</b>', '').replace('<br>', '\n')
        text_content = f"{greetings.replace('<br>', ' ')}\n\n{desc_text}\n\nPotvrdiť termín: {confirm_url}"
        
        # Create message
        msg = MIMEMultipart('related')
        msg['From'] = f"ArciGy Automation <{SMTP_USER}>"
        msg['To'] = to_email
        msg['Subject'] = subjects.get(action_type, "Potvrdenie terminu")

        msg_alt = MIMEMultipart('alternative')
        msg_alt.attach(MIMEText(text_content, 'plain'))
        msg_alt.attach(MIMEText(html_content, 'html'))
        msg.attach(msg_alt)

        # Attach Images (CID)
        if os.path.exists(asset_path):
            try:
                with open(asset_path, 'rb') as f:
                    img = MIMEImage(f.read())
                    img.add_header('Content-ID', '<cyber_socials_layout>')
                    msg.attach(img)
                print("   ✅ Image attached to email successfully.")
            except Exception as img_err:
                 print(f"   ❌ Failed to attach image: {img_err}")
        else:
            print("   ❌ Image NOT attached (file missing).")

        # SMTP SEND
        try:
            with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
                server.login(SMTP_USER, SMTP_PASS)
                server.send_message(msg)
            
            # Save to Sent
            try:
                imap_host = os.getenv("EMAIL_HOST_IMAP", "imap.hostinger.com")
                imap_port = int(os.getenv("EMAIL_PORT_IMAP", 993))
                mail = imaplib.IMAP4_SSL(imap_host, imap_port)
                mail.login(SMTP_USER, SMTP_PASS)
                mail.append("INBOX.Sent", '\\Seen', imaplib.Time2Internaldate(time.time()), msg.as_bytes())
                mail.logout()
            except: pass

            print("   ✅ Email sent successfully via SMTP.")
            return True
        except Exception as e:
            print(f"CRITICAL Email Error: {e}")
            return False
            
    except Exception as e:
        print(f"CRITICAL Template Error: {e}")
        return False
