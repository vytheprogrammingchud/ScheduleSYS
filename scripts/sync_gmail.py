import os
import json
import base64
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCHEDULE_FILE = "schedule.json"

def get_gmail_service():
    """Initializes and returns the Gmail API service using GitHub Actions secrets."""
    creds_json = os.environ.get("GMAIL_CREDENTIALS")
    if not creds_json:
        raise ValueError("GMAIL_CREDENTIALS environment variable not found.")
    
    creds_info = json.loads(creds_json)
    creds = Credentials.from_authorized_user_info(creds_info)
    return build("gmail", "v1", credentials=creds)

def fetch_relevant_emails(service):
    """Searches inbox for recent unread or important schedule emails."""
    # Query can be customized to look for specific keywords, senders, or labels
    query = "label:UNREAD (flight OR exam OR makeup OR schedule OR padrón)"
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
                
        # Extract snippet or body snippet as description
        snippet = msg.get("snippet", "No description available.")
        
        # Simple heuristic mapping (you can customize this pattern matching)
        item_type = "note"
        badge = "To do"
        if "flight" in subject.lower() or "vueling" in subject.lower() or "air europa" in subject.lower():
            item_type = "flight"
            badge = "Paid"
        elif "exam" in subject.lower():
            item_type = "exam"
            badge = "Exam"
        elif "class" in subject.lower() or "makeup" in subject.lower():
            item_type = "class"
            badge = "Class"

        parsed_items.append({
            "date": "Auto-Synced",
            "time": "TBD",
            "title": subject,
            "desc": snippet,
            "type": item_type,
            "badge": badge
        })
        
        # Optionally mark message as read so it doesn't duplicate next run
        service.users().messages().batchModify(
            userId="me",
            body={'ids': [msg_info["id"]], 'removeLabelIds': ['UNREAD']}
        ).execute()
        
    return parsed_items

def update_schedule_json(new_items):
    """Loads schedule.json, appends new items to upcoming events, and saves it back."""
    if not os.path.exists(SCHEDULE_FILE):
        print("schedule.json not found. Creating a new one.")
        data = {"alerts": [], "upcoming": [], "archive": []}
    else:
        with open(SCHEDULE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

    if not new_items:
        print("No new schedule emails found.")
        return False

    # Prepend or append new items to upcoming list
    for item in new_items:
        data["upcoming"].insert(0, item)
        print(f"Added item from email: {item['title']}")

    with open(SCHEDULE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    return True

if __name__ == "__main__":
    try:
        service = get_gmail_service()
        new_events = fetch_relevant_emails(service)
        updated = update_schedule_json(new_events)
        if updated:
            print("schedule.json successfully updated.")
        else:
            print("No changes made to schedule.json.")
    except Exception as e:
        print(f"Error syncing Gmail: {e}")
        exit(1)
