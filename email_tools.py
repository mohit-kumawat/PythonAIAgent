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
