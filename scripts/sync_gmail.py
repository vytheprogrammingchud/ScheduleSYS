import os
import json
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCHEDULE_FILE = "schedule.json"

def get_services():
    """Initializes and returns Gmail API instances for all configured accounts."""
    services = []
    # Looks for GMAIL_CREDENTIALS, GMAIL_CREDENTIALS_2, GMAIL_CREDENTIALS_3, etc.
    env_keys = [k for k in os.environ.keys() if k.startswith("GMAIL_CREDENTIALS")]
    
    for key in sorted(env_keys):
        creds_json = os.environ.get(key)
        if creds_json:
            try:
                creds_info = json.loads(creds_json)
                creds = Credentials.from_authorized_user_info(creds_info)
                service = build("gmail", "v1", credentials=creds)
                services.append(service)
                print(f"Successfully connected account via {key}")
            except Exception as e:
                print(f"Error initializing credentials for {key}: {e}")
                
    return services

def fetch_emails_from_service(service):
    query = "label:UNREAD (flight OR exam OR makeup OR schedule OR padrón OR booking)"
    results = service.users().messages().list(userId="me", q=query, maxResults=5).execute()
    messages = results.get("messages", [])
    
    parsed_items = []
    for msg_info in messages:
        msg = service.users().messages().get(userId="me", id=msg_info["id"], format="full").execute()
        headers = msg["payload"].get("headers", [])
        
        subject = ""
        for header in headers:
            if header["name"].lower() == "subject":
                subject = header["value"]
                break
                
        snippet = msg.get("snippet", "No details available.")
        
        item_type = "note"
        badge = "To do"
        subj_lower = subject.lower()
        if "flight" in subj_lower or "vueling" in subj_lower or "air europa" in subj_lower or "ryanair" in subj_lower:
            item_type = "flight"
            badge = "Paid"
        elif "exam" in subj_lower or "paper" in subj_lower:
            item_type = "exam"
            badge = "Exam"
        elif "class" in subj_lower or "makeup" in subj_lower:
            item_type = "class"
            badge = "Class"
        elif "padrón" in subj_lower or "cita" in subj_lower:
            item_type = "admin"
            badge = "Booked"

        parsed_items.append({
            "date": "New Sync",
            "time": "TBD",
            "title": subject,
            "desc": snippet,
            "type": item_type,
            "badge": badge
        })

    return parsed_items

def update_schedule_json(new_items):
    if not os.path.exists(SCHEDULE_FILE):
        data = {"alerts": [], "upcoming": [], "archive": []}
    else:
        with open(SCHEDULE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

    if not new_items:
        return False

    for item in new_items:
        data["upcoming"].insert(0, item)
        print(f"Added item: {item['title']}")

    with open(SCHEDULE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    return True

if __name__ == "__main__":
    services = get_services()
    if not services:
        print("No Gmail credentials found in environment.")
        exit(1)

    all_new_events = []
    for srv in services:
        try:
            events = fetch_emails_from_service(srv)
            all_new_events.extend(events)
        except Exception as e:
            print(f"Error fetching from an email account: {e}")

    if update_schedule_json(all_new_events):
        print("schedule.json updated successfully across accounts.")
    else:
        print("No new schedule emails found across connected accounts.")
