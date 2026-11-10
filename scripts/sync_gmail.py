import os
import json
import base64
from email.utils import parseaddr
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

def get_gmail_service(token_json):
    creds_info = json.loads(token_json)
    creds = Credentials.from_authorized_user_info(creds_info)
    return build('gmail', 'v1', credentials=creds)

def fetch_emails():
    events = []
    
    # List of trusted or expected terms / senders
    # Any email containing these exclusion words will be completely ignored to stop junk
    exclusion_keywords = ['unsubscribe', 'promo', 'offer', 'sale', 'newsletter', 'discount', 'free trial', 'marketing']

    token_1 = os.environ.get('GMAIL_CREDENTIALS')
    token_2 = os.environ.get('GMAIL_CREDENTIALS_2')
    
    tokens = [t for t in [token_1, token_2] if t]
    
    for token in tokens:
        try:
            service = get_gmail_service(token)
            # Search recent inbox messages
            results = service.users().messages().list(userId='me', q='in:inbox newer_than:7d', maxResults=20).execute()
            messages = results.get('messages', [])
            
            for msg in messages:
                m_data = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
                headers = m_data['payload']['headers']
                
                subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), '')
                sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), '')
                snippet = m_data.get('snippet', '')
                
                combined_text = (subject + ' ' + snippet).lower()
                
                # Skip if it contains junk keywords
                if any(bad in combined_text for bad in exclusion_keywords):
                    continue
                
                # Only pull in items relevant to your schedule/exams/travel/admin
                relevant_keywords = ['exam', 'physics', 'flight', 'train', 'booking', 'payment', 'enrollment', 'deadline', 'university']
                if any(kw in combined_text for kw in relevant_keywords):
                    events.append({
                        "title": subject[:60],
                        "desc": snippet[:100],
                        "date": "Upcoming",
                        "time": "Synced via Email",
                        "badge": "To Do"
                    })
        except Exception as e:
            print(f"Error fetching Gmail account: {e}")
            
    return events

def update_schedule_json():
    filename = 'schedule.json'
    
    # Load existing schedule
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
    else:
        data = {"alerts": [], "upcoming": [], "archive": []}
        
    # Fetch filtered new events from Gmail
    new_events = fetch_emails()
    
    # Avoid duplicate entries
    existing_titles = {item['title'] for item in data.get('upcoming', [])}
    for event in new_events:
        if event['title'] not in existing_titles:
            data['upcoming'].append(event)
            
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

if __name__ == '__main__':
    update_schedule_json()
