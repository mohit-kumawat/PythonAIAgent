import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from typing import List, Dict, Any

def get_slack_client():
    """Initializes and returns a Slack WebClient."""
    token = os.environ.get("SLACK_BOT_TOKEN")
    if not token:
        print("Warning: SLACK_BOT_TOKEN not found in environment variables.")
        return None
    return WebClient(token=token)

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

def send_slack_message(channel_id: str, text: str):
    """
    Sends a message to a Slack channel.
    
    Args:
        channel_id: The ID of the channel to send to.
        text: The message text.
    """
    client = get_slack_client()
    if not client:
        return

    try:
        client.chat_postMessage(channel=channel_id, text=text)
        print(f"Message sent to {channel_id}")
    except SlackApiError as e:
        print(f"Error sending message: {e}")
