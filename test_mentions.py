#!/usr/bin/env python3
"""
Simple script to show all messages that mention the bot and who sent them
"""

import os
from dotenv import load_dotenv
from slack_tools import get_messages_mentions

load_dotenv()

# Get IDs from environment
bot_user_id = os.environ.get("SLACK_BOT_USER_ID")
authorized_user_id = os.environ.get("SLACK_USER_ID")
channel_id = "C08JF2UFCR1"  # Test channel

print("="*80)
print("MENTION DETECTION TEST")
print("="*80)
print(f"\nBot User ID: {bot_user_id}")
print(f"Authorized User ID (Mohit): {authorized_user_id}")
print(f"Channel: {channel_id}\n")

# Get all mentions
try:
    mentions = get_messages_mentions(channel_id, bot_user_id, days=7, debug=False)
    
    print(f"Found {len(mentions)} message(s) that mention the bot:\n")
    
    for i, msg in enumerate(mentions, 1):
        sender_id = msg.get('user', 'UNKNOWN')
        text = msg.get('text', '')[:150]  # First 150 chars
        timestamp = msg.get('ts', '')
        
        # Check if authorized
        is_authorized = (sender_id == authorized_user_id)
        status = "✅ AUTHORIZED" if is_authorized else "❌ UNAUTHORIZED"
        
        print(f"Message {i}: {status}")
        print(f"  Sender ID: {sender_id}")
        print(f"  Timestamp: {timestamp}")
        print(f"  Text: {text}")
        print()
    
    # Summary
    authorized_count = sum(1 for msg in mentions if msg.get('user') == authorized_user_id)
    unauthorized_count = len(mentions) - authorized_count
    
    print("="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Total mentions: {len(mentions)}")
    print(f"Authorized (from Mohit): {authorized_count}")
    print(f"Unauthorized (from others): {unauthorized_count}")
    print()
    
    if unauthorized_count > 0:
        print("⚠️  ISSUE DETECTED:")
        print("   The bot is receiving mentions from unauthorized users.")
        print("   The bot will send refusal messages to them.")
        print()
    
    if authorized_count > 0:
        print("✅ GOOD NEWS:")
        print(f"   Found {authorized_count} authorized mention(s) from you!")
        print("   The bot should process these.")
        print()

except Exception as e:
    print(f"❌ Error: {e}")
    print("\nMake sure:")
    print("1. The bot is invited to the channel: /invite @The Real PM")
    print("2. Your .env file has the correct IDs")

print("="*80)
