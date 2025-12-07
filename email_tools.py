import os.path
import base64
from email.message import EmailMessage
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from typing import List, Dict, Any

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly', 'https://www.googleapis.com/auth/gmail.send']

def get_gmail_service():
    """Shows basic usage of the Gmail API.
    Lists the user's Gmail labels.
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"Error refreshing token: {e}")
                return None
        else:
            if os.path.exists('credentials.json'):
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
                # This will open a browser for auth, which might be tricky in headless env.
                # But for a local assistant, it's fine.
                creds = flow.run_local_server(port=0)
            else:
                print("credentials.json not found. Please provide Gmail credentials.")
                return None
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    try:
        service = build('gmail', 'v1', credentials=creds)
        return service
    except HttpError as error:
        print(f'An error occurred: {error}')
        return None

def read_recent_emails(limit: int = 5) -> List[Dict[str, Any]]:
    """
    Reads recent emails from the user's inbox.
    
    Args:
        limit: Number of emails to retrieve.
        
    Returns:
        List of email dictionaries with 'subject', 'sender', 'snippet'.
    """
    service = get_gmail_service()
    if not service:
        return []

    try:
        # Call the Gmail API
        results = service.users().messages().list(userId='me', labelIds=['INBOX'], maxResults=limit).execute()
        messages = results.get('messages', [])

        email_data = []
        if not messages:
            print('No new messages.')
            return []
        
        for message in messages:
            msg = service.users().messages().get(userId='me', id=message['id']).execute()
            payload = msg['payload']
            headers = payload.get('headers')
            
            subject = "No Subject"
            sender = "Unknown"
            
            if headers:
                for header in headers:
                    if header['name'] == 'Subject':
                        subject = header['value']
                    if header['name'] == 'From':
                        sender = header['value']
            
            email_data.append({
                "id": message['id'],
                "subject": subject,
                "sender": sender,
                "snippet": msg.get('snippet', '')
            })
            
        return email_data

    except HttpError as error:
        print(f'An error occurred: {error}')
        return []

def send_email(to: str, subject: str, body: str):
    """
    Sends an email.
    
    Args:
        to: Recipient email address.
        subject: Email subject.
        body: Email body text.
    """
    service = get_gmail_service()
    if not service:
        return

    try:
        message = EmailMessage()
        message.set_content(body)
        message['To'] = to
        message['From'] = 'me'
        message['Subject'] = subject

        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

        create_message = {
            'raw': encoded_message
        }

        send_message = (service.users().messages().send(userId="me", body=create_message).execute())
        print(f'Message Id: {send_message["id"]}')
    except HttpError as error:
        print(f'An error occurred: {error}')
        return None


def send_email_summary(
    recipient: str,
    context_md: str,
    period: str = "weekly",
    custom_subject: str = None
) -> Dict[str, Any]:
    """
    Generate and send a project summary email based on context.md.
    
    Uses the project context to generate a professional status update email.
    
    Args:
        recipient: Email address to send to
        context_md: Current project context (from context.md)
        period: "daily" or "weekly" for summary type
        custom_subject: Optional custom email subject
        
    Returns:
        Dict with success status and details
        
    Example:
        send_email_summary(
            recipient="team@example.com",
            context_md=read_context(),
            period="weekly"
        )
    """
    from datetime import datetime
    
    # Parse context to extract key information
    lines = context_md.split('\n')
    
    # Extract sections
    health_section = []
    epics_section = []
    reminders_section = []
    notes_section = []
    
    current_section = None
    for line in lines:
        if '## 1. Overall Health' in line:
            current_section = 'health'
        elif '## 2. Active Epics' in line:
            current_section = 'epics'
        elif '## 3. Reminders' in line:
            current_section = 'reminders'
        elif '## 4. Raw Notes' in line:
            current_section = 'notes'
        elif line.strip() and current_section:
            if current_section == 'health':
                health_section.append(line)
            elif current_section == 'epics':
                epics_section.append(line)
            elif current_section == 'reminders':
                reminders_section.append(line)
            elif current_section == 'notes':
                notes_section.append(line)
    
    # Generate email subject
    today = datetime.now().strftime("%B %d, %Y")
    if custom_subject:
        subject = custom_subject
    elif period == "daily":
        subject = f"📋 Daily Project Update - {today}"
    else:
        subject = f"📊 Weekly Project Summary - {today}"
    
    # Build email body
    body_parts = [
        f"{'Daily' if period == 'daily' else 'Weekly'} Project Status Update",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} IST",
        "",
        "=" * 50,
        "",
    ]
    
    # Health Status
    body_parts.append("🏥 PROJECT HEALTH")
    body_parts.append("-" * 30)
    if health_section:
        body_parts.extend(health_section)
    else:
        body_parts.append("No health information available.")
    body_parts.append("")
    
    # Active Work
    body_parts.append("📋 ACTIVE EPICS & TASKS")
    body_parts.append("-" * 30)
    if epics_section:
        body_parts.extend(epics_section)
    else:
        body_parts.append("No active epics documented.")
    body_parts.append("")
    
    # Upcoming Reminders
    body_parts.append("⏰ UPCOMING REMINDERS")
    body_parts.append("-" * 30)
    if reminders_section:
        body_parts.extend(reminders_section)
    else:
        body_parts.append("No reminders scheduled.")
    body_parts.append("")
    
    # Footer
    body_parts.extend([
        "=" * 50,
        "",
        "This summary was auto-generated by The Real PM Agent.",
        "For questions, reply to this email or message in Slack."
    ])
    
    email_body = '\n'.join(body_parts)
    
    # Send the email
    try:
        send_email(recipient, subject, email_body)
        return {
            "success": True,
            "recipient": recipient,
            "subject": subject,
            "period": period
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

