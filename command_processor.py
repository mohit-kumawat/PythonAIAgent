import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Any

def parse_command_from_message(message_text: str, bot_user_id: str, authorized_user_id: str) -> Dict[str, Any]:
    """
    Parses a Slack message to extract actionable commands.
    
    Args:
        message_text: The text of the Slack message
        bot_user_id: The bot's user ID (to detect when it's mentioned)
        authorized_user_id: The user ID of Mohit (only he can give commands)
        
    Returns:
        Dict containing parsed command structure
    """
    result = {
        "is_command": False,
        "authorized": False,
        "tasks": [],
        "reminders": [],
        "assignments": [],
        "mentions": []
    }
    
    # Check if bot is mentioned
    if f"<@{bot_user_id}>" not in message_text:
        return result
    
    result["is_command"] = True
    
    # Extract all user mentions
    mention_pattern = r'<@([A-Z0-9]+)>'
    mentions = re.findall(mention_pattern, message_text)
    result["mentions"] = mentions
    
    # Parse assignments (X is working on Y)
    assignment_pattern = r'<@([A-Z0-9]+)>\s+is working on\s+(.+?)(?:\.|$|\n)'
    assignments = re.findall(assignment_pattern, message_text, re.IGNORECASE)
    for user_id, task in assignments:
        result["assignments"].append({
            "user_id": user_id,
            "task": task.strip()
        })
    
    # Parse reminders (Remind me to X at Y)
    reminder_pattern = r'Remind me to\s+(.+?)\s+(?:at|on)\s+(.+?)(?:\.|$|\n)'
    reminders = re.findall(reminder_pattern, message_text, re.IGNORECASE)
    for action, time_str in reminders:
        result["reminders"].append({
            "action": action.strip(),
            "time_str": time_str.strip(),
            "parsed_time": parse_time_expression(time_str.strip())
        })
    
    # Parse tasks/action items
    task_patterns = [
        r'Make sure\s+(?:we\s+)?(.+?)(?:\.|$|\n)',
        r'(?:Need to|Must|Should)\s+(.+?)(?:\.|$|\n)'
    ]
    
    for pattern in task_patterns:
        tasks = re.findall(pattern, message_text, re.IGNORECASE)
        for task in tasks:
            if task.strip():
                result["tasks"].append(task.strip())
    
    return result

def parse_time_expression(time_str: str) -> str:
    """
    Parses natural language time expressions into ISO format.
    
    Args:
        time_str: Natural language time (e.g., "tomorrow at 11:30", "11:30")
        
    Returns:
        ISO format datetime string
    """
    from datetime import datetime, timedelta
    import pytz
    
    # Use IST timezone for Mohit's context
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)
    
    time_str_lower = time_str.lower().strip()
    
    # Handle "tomorrow"
    if "tomorrow" in time_str_lower:
        target_date = now + timedelta(days=1)
        # Extract time if present
        time_match = re.search(r'(\d{1,2}):(\d{2})', time_str)
        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2))
            target_date = target_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
        else:
            # Default to 9 AM if no time specified
            target_date = target_date.replace(hour=9, minute=0, second=0, microsecond=0)
    
    # Handle "next Monday", "next week", etc.
    elif "next monday" in time_str_lower:
        days_ahead = (7 - now.weekday()) % 7 + 7  # Next Monday
        target_date = now + timedelta(days=days_ahead)
        time_match = re.search(r'(\d{1,2}):(\d{2})', time_str)
        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2))
            target_date = target_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
        else:
            target_date = target_date.replace(hour=9, minute=0, second=0, microsecond=0)
    
    # Handle time today/tomorrow
    else:
        time_match = re.search(r'(\d{1,2}):(\d{2})', time_str)
        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2))
            target_date = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            # If time has passed today, assume tomorrow
            if target_date < now:
                target_date = target_date + timedelta(days=1)
        else:
            # Default to 1 hour from now
            target_date = now + timedelta(hours=1)
    
    return target_date.isoformat()

def create_reminder_message(reminder_data: Dict[str, Any], target_user_ids: List[str], context: str = None) -> str:
    """
    Creates a formatted reminder message.
    
    Args:
        reminder_data: Dict with 'action' and optional context
        target_user_ids: List of user IDs to mention
        context: Optional project context to include
        
    Returns:
        Formatted Slack message
    """
    mentions = " ".join([f"<@{uid}>" for uid in target_user_ids])
    message = f"{mentions} 📋 Reminder from Mohit:\n{reminder_data['action']}"
    
    if context:
        message += f"\n\nContext: {context}"
    
    return message

def is_reminder_command(message_text: str) -> bool:
    """
    Checks if a message contains a reminder command.
    
    Args:
        message_text: The message text to check
        
    Returns:
        True if message contains reminder pattern
    """
    reminder_patterns = [
        r'remind me to',
        r'reminder to',
        r'set a reminder'
    ]
    
    message_lower = message_text.lower()
    return any(re.search(pattern, message_lower) for pattern in reminder_patterns)

def extract_reminder_details(message_text: str) -> Dict[str, Any]:
    """
    Extracts detailed information from a reminder command.
    
    Args:
        message_text: The message containing the reminder
        
    Returns:
        Dict with action, time_str, mentioned_users, and parsed_time
    """
    # Pattern: "Remind me to [action] [time expression]"
    pattern = r'remind me to\s+(.+?)\s+(?:at|on|tomorrow|next|in)\s+(.+?)(?:\.|$|\n)'
    match = re.search(pattern, message_text, re.IGNORECASE)
    
    if not match:
        # Fallback: try to extract action and time separately
        action_match = re.search(r'remind me to\s+(.+?)(?:\.|$|\n)', message_text, re.IGNORECASE)
        action = action_match.group(1).strip() if action_match else "No action specified"
        time_str = "in 1 hour"  # Default
    else:
        action = match.group(1).strip()
        time_str = match.group(2).strip()
    
    # Extract mentioned users
    mention_pattern = r'<@([A-Z0-9]+)>'
    mentioned_users = re.findall(mention_pattern, message_text)
    
    return {
        "action": action,
        "time_str": time_str,
        "mentioned_users": mentioned_users,
        "parsed_time": parse_time_expression(time_str),
        "requires_scheduling": True  # Always true for reminders
    }
