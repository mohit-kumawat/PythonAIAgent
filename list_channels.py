import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv

load_dotenv()

def list_channels():
    token = os.environ.get("SLACK_BOT_TOKEN")
    if not token:
        print("Error: SLACK_BOT_TOKEN not found.")
        return

    client = WebClient(token=token)
    try:
        response = client.conversations_list(limit=20, types="public_channel,private_channel")
        channels = response["channels"]
        print(f"Found {len(channels)} channels:")
        for channel in channels:
            print(f"- #{channel['name']} (ID: {channel['id']})")
    except SlackApiError as e:
        print(f"Error listing channels: {e}")

if __name__ == "__main__":
    list_channels()
