#!/usr/bin/env python3
"""
Diagnostic script to check Slack bot permissions and configuration
"""

import os
import sys
from dotenv import load_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

def check_env_vars():
    """Check if required environment variables are set"""
    print("="*80)
    print("CHECKING ENVIRONMENT VARIABLES")
    print("="*80)
    
    load_dotenv()
    
    required_vars = {
        'SLACK_BOT_TOKEN': 'Bot token for Slack API',
        'SLACK_USER_ID': 'Your (Mohit\'s) Slack user ID',
        'SLACK_BOT_USER_ID': 'The bot\'s Slack user ID'
    }
    
    missing = []
    for var, description in required_vars.items():
        value = os.environ.get(var)
        if value and value != f"YOUR_{var}_HERE":
            print(f"✓ {var}: Set ({description})")
        else:
            print(f"✗ {var}: MISSING ({description})")
            missing.append(var)
    
    return len(missing) == 0

def check_bot_connection():
    """Test bot connection and get bot info"""
    print("\n" + "="*80)
    print("CHECKING BOT CONNECTION")
    print("="*80)
    
    token = os.environ.get('SLACK_BOT_TOKEN')
    if not token:
        print("✗ Cannot test - SLACK_BOT_TOKEN not set")
        return False
    
    client = WebClient(token=token)
    
    try:
        auth = client.auth_test()
        print(f"✓ Connected successfully!")
        print(f"  Bot User: {auth['user']}")
        print(f"  Bot User ID: {auth['user_id']}")
        print(f"  Team: {auth['team']}")
        print(f"  Team ID: {auth['team_id']}")
        
        # Save bot user ID if not set
        if not os.environ.get('SLACK_BOT_USER_ID'):
            print(f"\n💡 TIP: Add this to your .env file:")
            print(f"   SLACK_BOT_USER_ID=\"{auth['user_id']}\"")
        
        return True
    except SlackApiError as e:
        print(f"✗ Connection failed: {e.response['error']}")
        return False

def check_permissions():
    """Check if bot has required permissions"""
    print("\n" + "="*80)
    print("CHECKING PERMISSIONS")
    print("="*80)
    
    token = os.environ.get('SLACK_BOT_TOKEN')
    if not token:
        print("✗ Cannot test - SLACK_BOT_TOKEN not set")
        return False
    
    client = WebClient(token=token)
    
    # Test 1: Can we read conversations?
    print("\n1. Testing channels:history (read messages)...")
    try:
        # Try to get conversations list
        result = client.conversations_list(limit=1)
        print("   ✓ Can list conversations")
    except SlackApiError as e:
        print(f"   ✗ Failed: {e.response['error']}")
    
    # Test 2: Can we schedule messages?
    print("\n2. Testing chat:write (send/schedule messages)...")
    try:
        # This will fail with channel_not_found but shows permission exists
        client.chat_scheduleMessage(
            channel='INVALID_CHANNEL',
            text='test',
            post_at=1234567890
        )
    except SlackApiError as e:
        error = e.response['error']
        if 'channel_not_found' in error or 'invalid_channel' in error:
            print("   ✓ Can schedule messages (permission exists)")
        elif 'missing_scope' in error:
            print(f"   ✗ Missing scope: {e.response.get('needed')}")
        else:
            print(f"   ? Unexpected error: {error}")
    
    # Test 3: Can we read user info?
    print("\n3. Testing users:read (read user information)...")
    try:
        user_id = os.environ.get('SLACK_USER_ID', 'U000000')
        client.users_info(user=user_id)
        print("   ✓ Can read user information")
    except SlackApiError as e:
        error = e.response['error']
        if 'user_not_found' in error:
            print("   ✓ Permission exists (user ID may be wrong)")
        elif 'missing_scope' in error:
            print(f"   ✗ Missing scope: {e.response.get('needed')}")
        else:
            print(f"   ? Error: {error}")
    
    return True

def main():
    print("\n")
    print("╔" + "="*78 + "╗")
    print("║" + " "*20 + "PM AGENT DIAGNOSTIC TOOL" + " "*34 + "║")
    print("╚" + "="*78 + "╝")
    print()
    
    # Run checks
    env_ok = check_env_vars()
    
    if env_ok:
        conn_ok = check_bot_connection()
        if conn_ok:
            check_permissions()
    
    print("\n" + "="*80)
    print("RECOMMENDATIONS")
    print("="*80)
    
    if not env_ok:
        print("1. Update your .env file with the required variables")
        print("2. See SLACK_PERMISSIONS.md for detailed instructions")
    else:
        print("✓ Environment variables are set")
        print("\nNext steps:")
        print("1. Make sure the bot is invited to your channels:")
        print("   /invite @The Real PM")
        print("\n2. Test the process-mentions command:")
        print("   python3 main.py process-mentions --channels YOUR_CHANNEL_ID")
        print("\n3. If you get permission errors, see SLACK_PERMISSIONS.md")
    
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
