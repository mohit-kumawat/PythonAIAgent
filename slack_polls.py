"""
Slack Polls - Create interactive polls in Slack channels.
Uses emoji reactions for voting.
"""

import os
import ssl
import certifi
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from typing import List, Dict, Any


def get_slack_client():
    """Initializes and returns a Slack WebClient."""
    token = os.environ.get("SLACK_BOT_TOKEN")
    if not token:
        print("Warning: SLACK_BOT_TOKEN not found in environment variables.")
        return None
    
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    return WebClient(token=token, ssl=ssl_context)


# Emoji numbers for poll options
POLL_EMOJIS = ["one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "keycap_ten"]


def post_slack_poll(
    channel_id: str, 
    question: str, 
    options: List[str],
    anonymous: bool = False
) -> Dict[str, Any]:
    """
    Posts an interactive poll to a Slack channel using emoji reactions.
    
    Args:
        channel_id: The Slack channel ID to post to
        question: The poll question
        options: List of poll options (max 10)
        anonymous: If True, includes note about anonymous voting
        
    Returns:
        Dict with success status and message details
        
    Example:
        post_slack_poll(
            channel_id="C123ABC",
            question="Which day works for the standup?",
            options=["Monday", "Wednesday", "Friday"]
        )
        
        Result in Slack:
        📊 *Poll: Which day works for the standup?*
        
        :one: Monday
        :two: Wednesday  
        :three: Friday
        
        _React with the corresponding emoji to vote!_
    """
    client = get_slack_client()
    if not client:
        return {"error": "Slack client not initialized"}
    
    if len(options) > 10:
        return {"error": "Maximum 10 options allowed"}
    
    if len(options) < 2:
        return {"error": "At least 2 options required"}
    
    # Build the poll message
    poll_lines = [f"📊 *Poll: {question}*", ""]
    
    for i, option in enumerate(options):
        emoji = POLL_EMOJIS[i]
        poll_lines.append(f":{emoji}: {option}")
    
    poll_lines.append("")
    
    if anonymous:
        poll_lines.append("_React with the corresponding emoji to vote! (Anonymous poll)_")
    else:
        poll_lines.append("_React with the corresponding emoji to vote!_")
    
    message_text = "\n".join(poll_lines)
    
    try:
        # Post the message
        result = client.chat_postMessage(
            channel=channel_id,
            text=message_text,
            mrkdwn=True
        )
        
        message_ts = result["ts"]
        
        # Add reaction emojis as vote buttons
        for i in range(len(options)):
            emoji = POLL_EMOJIS[i]
            try:
                client.reactions_add(
                    channel=channel_id,
                    timestamp=message_ts,
                    name=emoji
                )
            except SlackApiError as e:
                # Ignore if reaction already exists
                if "already_reacted" not in str(e):
                    print(f"Warning: Could not add reaction {emoji}: {e}")
        
        return {
            "success": True,
            "message_ts": message_ts,
            "channel": channel_id,
            "question": question,
            "options_count": len(options)
        }
        
    except SlackApiError as e:
        print(f"Error posting poll: {e}")
        return {"error": str(e)}


def get_poll_results(channel_id: str, message_ts: str) -> Dict[str, Any]:
    """
    Get the current results of a poll.
    
    Args:
        channel_id: The channel where the poll was posted
        message_ts: The timestamp of the poll message
        
    Returns:
        Dict with reaction counts per option
    """
    client = get_slack_client()
    if not client:
        return {"error": "Slack client not initialized"}
    
    try:
        result = client.reactions_get(
            channel=channel_id,
            timestamp=message_ts
        )
        
        message = result["message"]
        reactions = message.get("reactions", [])
        
        # Parse results
        results = {}
        for reaction in reactions:
            name = reaction["name"]
            if name in POLL_EMOJIS:
                # Subtract 1 for the bot's initial reaction
                count = reaction["count"] - 1
                option_index = POLL_EMOJIS.index(name)
                results[f"option_{option_index + 1}"] = {
                    "emoji": name,
                    "votes": max(0, count)
                }
        
        return {
            "success": True,
            "results": results,
            "total_votes": sum(r["votes"] for r in results.values())
        }
        
    except SlackApiError as e:
        print(f"Error getting poll results: {e}")
        return {"error": str(e)}


def create_quick_poll(channel_id: str, question: str) -> Dict[str, Any]:
    """
    Create a simple yes/no poll.
    
    Args:
        channel_id: The Slack channel ID
        question: The question to ask
        
    Returns:
        Poll creation result
    """
    return post_slack_poll(channel_id, question, ["Yes", "No"])
