import json
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

# Official course code filters
COURSE_CODES = ["SP101", "GEB1350", "EN113", "CS110"]

# Academic notification triggers
PRIORITY_KEYWORDS = [
    "assignment", "project", "exam", "midterm", "final", 
    "cancelled", "cancellation", "rescheduled", "room change", 
    "make-up", "deadline", "submission", "due date"
]

def process_gmail_updates():
    # 1. Load existing static schedule
    with open('schedule.json', 'r') as f:
        schedule = json.load(f)

    # 2. Connect to Gmail API (using stored token.json)
    creds = Credentials.from_authorized_user_file('token.json')
    service = build('gmail', 'v1', credentials=creds)

    # Query unread emails from the past day
    results = service.users().messages().list(userId='me', q='is:unread newer_than:1d').execute()
    messages = results.get('messages', [])

    alerts_added = False

    for msg in messages:
        detail = service.users().messages().get(userId='me', id=msg['id']).execute()
        headers = detail['payload']['headers']
        
        subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), '')
        snippet = detail.get('snippet', '')

        full_text = (subject + " " + snippet).upper()

        # Check if the email mentions any of your specific course codes AND an academic keyword
        has_course_code = any(code in full_text for code in COURSE_CODES)
        has_keyword = any(kw.upper() in full_text for kw in PRIORITY_KEYWORDS)

        if has_course_code and has_keyword:
            new_alert = f"<b>{subject}:</b> {snippet[:120]}..."
            if new_alert not in schedule.get('alerts', []):
                schedule.setdefault('alerts', []).append(new_alert)
                alerts_added = True

    # 3. Save back to schedule.json if relevant notices were found
    if alerts_added:
        with open('schedule.json', 'w') as f:
            json.dump(schedule, f, indent=2)
        print("Updated schedule.json with targeted course notification.")
    else:
        print("No relevant course updates found.")

if __name__ == '__main__':
    process_gmail_updates()
