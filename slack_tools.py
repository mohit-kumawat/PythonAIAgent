import os
import ssl
import certifi
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from typing import List, Dict, Any
from datetime import datetime, timedelta

def get_slack_client():
    """Initializes and returns a Slack WebClient."""
    token = os.environ.get("SLACK_BOT_TOKEN")
    if not token:
        print("Warning: SLACK_BOT_TOKEN not found in environment variables.")
        return None
    
    # Create SSL context with certifi certificates to fix Mac SSL issues
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    return WebClient(token=token, ssl=ssl_context)

def read_slack_messages(channel_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Reads recent messages from a specific Slack channel.
    
    Args:
        channel_id: The ID of the channel to read from.
        limit: The number of messages to retrieve.
        
    Returns:
        A list of message dictionaries.
    """
    client = get_slack_client()
    if not client:
        return []

    try:
        result = client.conversations_history(channel=channel_id, limit=limit)
        messages = result["messages"]
        return messages
    except SlackApiError as e:
        print(f"Error fetching messages: {e}")
        return []

def get_self_todo(limit: int = 20) -> List[str]:
    """
    Fetches messages sent by the user to themselves (DMs).
    Assumes the bot token has access to read the user's DMs or the user's ID is known.
    
    Note: Reading a user's self-DM usually requires a User Token (xoxp-), not just a Bot Token,
    unless the bot is part of the DM. For a personal assistant, a User Token is often better.
    
    Args:
        limit: Number of messages to check.
        
    Returns:
        A list of message texts found in the self-DM.
    """
    # For a true personal assistant reading "my" messages, we likely need a User Token.
    # If using a Bot Token, the bot can only read DMs it is part of.
    # We will try to find the DM channel with the user.
    
    # This part is tricky without knowing the User's ID. 
    # We'll assume SLACK_USER_ID is provided or we try to find it.
    user_id = os.environ.get("SLACK_USER_ID")
    client = get_slack_client()
    
    if not client or not user_id:
        print("Slack Client or SLACK_USER_ID missing.")
        return []

    try:
        # Open a DM with the user (or get existing one)
        response = client.conversations_open(users=[user_id])
        channel_id = response["channel"]["id"]
        
        history = client.conversations_history(channel=channel_id, limit=limit)
        messages = history["messages"]
        
        # Filter for messages from the user (not the bot itself, if needed)
        todo_list = [msg["text"] for msg in messages if msg.get("user") == user_id]
        return todo_list
        
    except SlackApiError as e:
        print(f"Error fetching self-todos: {e}")
        return []

def send_slack_message(channel_id: str, text: str, thread_ts: str = None):
    """
    Sends a message to a Slack channel.
    
    Args:
        channel_id: The ID of the channel to send to.
        text: The message text.
        thread_ts: Optional timestamp of the thread to reply to.
    """
    client = get_slack_client()
    if not client:
        return

    # CRITICAL: Prevent bot from messaging itself
    bot_user_id = os.environ.get("SLACK_BOT_USER_ID")
    if bot_user_id and channel_id == bot_user_id:
        print(f"[BLOCKED] Attempted to send message to self (Bot ID: {bot_user_id}). Skipping.")
        return

    try:
        client.chat_postMessage(channel=channel_id, text=text, thread_ts=thread_ts)
        print(f"Message sent to {channel_id} (Thread: {thread_ts})")
    except SlackApiError as e:
        print(f"Error sending message: {e}")

def schedule_slack_message(channel_id: str, text: str, scheduled_time: str) -> Dict[str, Any]:
    """
    Schedules a message to be sent to a Slack channel at a specific time.
    
    Args:
        channel_id: The ID of the channel to send to.
        text: The message text.
        scheduled_time: ISO format datetime string (e.g., "2025-12-05T11:30:00")
        
    Returns:
        Dict with scheduled message details or error info.
    """
    client = get_slack_client()
    if not client:
        return {"error": "Slack client not initialized"}

    try:
        # Parse the scheduled time and convert to Unix timestamp
        dt = datetime.fromisoformat(scheduled_time)
        post_at = int(dt.timestamp())
        
        result = client.chat_scheduleMessage(
            channel=channel_id,
            text=text,
            post_at=post_at
        )
        
        print(f"Message scheduled for {scheduled_time} in channel {channel_id}")
        return {
            "success": True,
            "scheduled_message_id": result.get("scheduled_message_id"),
            "post_at": post_at
        }
    except SlackApiError as e:
        print(f"Error scheduling message: {e}")
        return {"error": str(e)}
    except ValueError as e:
        print(f"Invalid datetime format: {e}")
        return {"error": f"Invalid datetime format: {e}"}

def get_messages_mentions(channel_id: str, user_id: str, days: int = 7, debug: bool = False, 
                          include_keywords: List[str] = None) -> List[Dict[str, Any]]:
    """
    Gets messages where a specific user was mentioned or specific keywords appear in the last N days.
    
    Args:
        channel_id: The ID of the channel to search.
        user_id: The user ID to look for mentions.
        days: Number of days to look back.
        debug: If True, print debug information.
        include_keywords: Optional list of keywords/phrases to search for (case-insensitive).
        
    Returns:
        List of messages containing mentions or keywords.
    """
    client = get_slack_client()
    if not client:
        return []

    try:
        # Calculate oldest timestamp (N days ago)
        oldest = (datetime.now() - timedelta(days=days)).timestamp()
        
        result = client.conversations_history(
            channel=channel_id,
            oldest=str(oldest),
            limit=100
        )
        
        messages = result["messages"]
        
        if debug:
            print(f"\n[DEBUG] Found {len(messages)} total messages in channel {channel_id}")
            print(f"[DEBUG] Looking for mentions of user: <@{user_id}>")
            if include_keywords:
                print(f"[DEBUG] Also searching for keywords: {include_keywords}")
            for i, msg in enumerate(messages[:5]):  # Show first 5 messages
                print(f"[DEBUG] Message {i+1}: {msg.get('text', '')[:100]}")
        
        # Filter for messages that mention the user or contain keywords
        mentions = []
        for msg in messages:
            text = msg.get("text", "")
            text_lower = text.lower()
            
            # Check for direct mention
            if f"<@{user_id}>" in text:
                mentions.append(msg)
                continue
            
            # Check for keywords
            if include_keywords:
                for keyword in include_keywords:
                    if keyword.lower() in text_lower:
                        mentions.append(msg)
                        break
        
        if debug:
            print(f"[DEBUG] Filtered to {len(mentions)} messages with mentions/keywords")
        
        return mentions
        
    except SlackApiError as e:
        print(f"Error fetching mentions: {e}")
        return []


def has_bot_replied_in_thread(channel_id: str, thread_ts: str, bot_user_id: str) -> bool:
    """
    Check if the bot has already replied in a specific thread.
    
    Args:
        channel_id: The channel ID
        thread_ts: The thread timestamp
        bot_user_id: The bot's user ID
        
    Returns:
        True if bot has already replied in this thread, False otherwise
    """
    client = get_slack_client()
    if not client or not thread_ts:
        return False
    
    try:
        # Get thread replies
        result = client.conversations_replies(
            channel=channel_id,
            ts=thread_ts,
            limit=100
        )
        
        messages = result.get("messages", [])
        
        # Check if any message is from the bot
        for msg in messages:
            if msg.get("user") == bot_user_id:
                return True
                
        return False
        
    except SlackApiError as e:
        print(f"Error checking thread: {e}")
        return False


def get_thread_context(channel_id: str, thread_ts: str) -> List[Dict[str, Any]]:
    """
    Get all messages in a thread for full context.
    
    Args:
        channel_id: The channel ID
        thread_ts: The thread timestamp (parent message)
        
    Returns:
        List of all messages in the thread (including parent)
    """
    client = get_slack_client()
    if not client or not thread_ts:
        return []
    
    try:
        # Get all thread replies including the parent message
        result = client.conversations_replies(
            channel=channel_id,
            ts=thread_ts,
            limit=100
        )
        
        messages = result.get("messages", [])
        return messages
        
    except SlackApiError as e:
        print(f"Error fetching thread context: {e}")
        return []

