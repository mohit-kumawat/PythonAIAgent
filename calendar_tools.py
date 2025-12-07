"""
Google Calendar Tools - Add events to Google Calendar.
Uses OAuth2 for authentication (similar to Gmail setup).
"""

import os
import os.path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


# Calendar API scopes
SCOPES = ['https://www.googleapis.com/auth/calendar.events']


def get_calendar_service():
    """
    Initialize and return the Google Calendar API service.
    
    On first run, will open browser for OAuth consent.
    Subsequent runs use stored credentials.
    """
    creds = None
    token_file = 'calendar_token.json'
    credentials_file = 'calendar_credentials.json'
    
    # Load existing credentials
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)
    
    # Refresh or get new credentials
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"Error refreshing calendar token: {e}")
                creds = None
        
        if not creds:
            if os.path.exists(credentials_file):
                flow = InstalledAppFlow.from_client_secrets_file(
                    credentials_file, SCOPES
                )
                creds = flow.run_local_server(port=0)
            else:
                print(f"Error: {credentials_file} not found.")
                print("Please set up Google Calendar API credentials:")
                print("1. Go to https://console.cloud.google.com/apis/credentials")
                print("2. Create OAuth 2.0 credentials for Desktop app")
                print("3. Download and save as 'calendar_credentials.json'")
                return None
        
        # Save credentials for next run
        with open(token_file, 'w') as token:
            token.write(creds.to_json())
    
    try:
        service = build('calendar', 'v3', credentials=creds)
        return service
    except HttpError as error:
        print(f'Calendar API error: {error}')
        return None


def add_calendar_event(
    summary: str,
    start_time: str,
    end_time: str = None,
    description: str = None,
    attendees: List[str] = None,
    location: str = None,
    reminder_minutes: int = 30
) -> Dict[str, Any]:
    """
    Add an event to Google Calendar.
    
    Args:
        summary: Event title
        start_time: Start time in ISO format (e.g., "2025-12-08T14:00:00")
        end_time: End time in ISO format (defaults to start + 1 hour)
        description: Optional event description
        attendees: Optional list of email addresses to invite
        location: Optional location string
        reminder_minutes: Minutes before event to send reminder (default 30)
        
    Returns:
        Dict with event details or error message
        
    Example:
        add_calendar_event(
            summary="Code Review with Team",
            start_time="2025-12-08T14:00:00",
            description="Review PR #123 before release",
            attendees=["pravin@example.com", "umang@example.com"]
        )
    """
    service = get_calendar_service()
    if not service:
        return {"error": "Calendar service not initialized. Check credentials."}
    
    try:
        # Parse start time
        start_dt = datetime.fromisoformat(start_time)
        
        # Default end time: 1 hour after start
        if end_time:
            end_dt = datetime.fromisoformat(end_time)
        else:
            end_dt = start_dt + timedelta(hours=1)
        
        # Build event object
        event = {
            'summary': summary,
            'start': {
                'dateTime': start_dt.isoformat(),
                'timeZone': 'Asia/Kolkata',  # IST
            },
            'end': {
                'dateTime': end_dt.isoformat(),
                'timeZone': 'Asia/Kolkata',
            },
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'popup', 'minutes': reminder_minutes},
                ],
            },
        }
        
        if description:
            event['description'] = description
        
        if location:
            event['location'] = location
        
        if attendees:
            event['attendees'] = [{'email': email} for email in attendees]
        
        # Create the event
        created_event = service.events().insert(
            calendarId='primary',
            body=event,
            sendUpdates='all' if attendees else 'none'
        ).execute()
        
        return {
            "success": True,
            "event_id": created_event.get('id'),
            "html_link": created_event.get('htmlLink'),
            "summary": summary,
            "start": start_dt.isoformat(),
            "end": end_dt.isoformat()
        }
        
    except ValueError as e:
        return {"error": f"Invalid datetime format: {e}"}
    except HttpError as e:
        return {"error": f"Calendar API error: {e}"}


def get_upcoming_events(max_results: int = 10) -> List[Dict[str, Any]]:
    """
    Get upcoming calendar events.
    
    Args:
        max_results: Maximum number of events to return
        
    Returns:
        List of upcoming events
    """
    service = get_calendar_service()
    if not service:
        return []
    
    try:
        now = datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
        
        events_result = service.events().list(
            calendarId='primary',
            timeMin=now,
            maxResults=max_results,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        return [
            {
                'id': event['id'],
                'summary': event.get('summary', 'No title'),
                'start': event['start'].get('dateTime', event['start'].get('date')),
                'end': event['end'].get('dateTime', event['end'].get('date')),
                'location': event.get('location'),
                'description': event.get('description')
            }
            for event in events
        ]
        
    except HttpError as e:
        print(f"Error fetching events: {e}")
        return []


def find_free_slots(
    date: str,
    duration_minutes: int = 60,
    working_hours: tuple = (9, 18)
) -> List[Dict[str, str]]:
    """
    Find free time slots on a given date.
    
    Args:
        date: Date to check (YYYY-MM-DD format)
        duration_minutes: Required slot duration
        working_hours: Tuple of (start_hour, end_hour)
        
    Returns:
        List of available time slots
    """
    service = get_calendar_service()
    if not service:
        return []
    
    try:
        # Parse the date
        check_date = datetime.strptime(date, "%Y-%m-%d")
        day_start = check_date.replace(hour=working_hours[0], minute=0)
        day_end = check_date.replace(hour=working_hours[1], minute=0)
        
        # Get events for that day
        events_result = service.events().list(
            calendarId='primary',
            timeMin=day_start.isoformat() + 'Z',
            timeMax=day_end.isoformat() + 'Z',
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        # Find gaps
        free_slots = []
        current_time = day_start
        
        for event in events:
            event_start = datetime.fromisoformat(
                event['start'].get('dateTime', event['start'].get('date')).replace('Z', '')
            )
            
            # Check if there's a gap before this event
            gap_minutes = (event_start - current_time).total_seconds() / 60
            if gap_minutes >= duration_minutes:
                free_slots.append({
                    'start': current_time.isoformat(),
                    'end': event_start.isoformat(),
                    'duration_minutes': int(gap_minutes)
                })
            
            event_end = datetime.fromisoformat(
                event['end'].get('dateTime', event['end'].get('date')).replace('Z', '')
            )
            current_time = max(current_time, event_end)
        
        # Check remaining time until end of day
        gap_minutes = (day_end - current_time).total_seconds() / 60
        if gap_minutes >= duration_minutes:
            free_slots.append({
                'start': current_time.isoformat(),
                'end': day_end.isoformat(),
                'duration_minutes': int(gap_minutes)
            })
        
        return free_slots
        
    except Exception as e:
        print(f"Error finding free slots: {e}")
        return []


def quick_block_time(
    summary: str,
    start_time: str,
    duration_minutes: int = 60
) -> Dict[str, Any]:
    """
    Quick helper to block time on calendar.
    
    Args:
        summary: What you're blocking time for
        start_time: Start time in ISO format
        duration_minutes: Duration in minutes
        
    Returns:
        Event creation result
    """
    start_dt = datetime.fromisoformat(start_time)
    end_dt = start_dt + timedelta(minutes=duration_minutes)
    
    return add_calendar_event(
        summary=f"🔒 {summary}",
        start_time=start_time,
        end_time=end_dt.isoformat(),
        description="Time blocked by PM Agent"
    )
