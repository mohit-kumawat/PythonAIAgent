#!/usr/bin/env python3
"""
Test script to verify the enhanced mention detection functionality.
This script tests the ability to find messages containing:
1. Direct bot mentions (@The Real PM)
2. Direct user mentions (@Mohit)
3. Keyword "mohit"
4. Phrase "the real pm"
"""

import os
from dotenv import load_dotenv
from slack_tools import get_messages_mentions

# Load environment variables
load_dotenv()

def test_mention_detection():
    """Test the enhanced mention detection with keywords."""
    
    bot_user_id = os.environ.get("SLACK_BOT_USER_ID")
    user_id = os.environ.get("SLACK_USER_ID")
    
    if not bot_user_id or not user_id:
        print("❌ Error: SLACK_BOT_USER_ID and SLACK_USER_ID must be set in .env")
        return
    
    # Test channel - replace with your actual test channel ID
    test_channel = input("Enter a Slack channel ID to test (or press Enter to skip): ").strip()
    
    if not test_channel:
        print("No channel provided. Exiting.")
        return
    
    print("\n" + "="*80)
    print("TESTING ENHANCED MENTION DETECTION")
    print("="*80)
    
    print(f"\n📋 Configuration:")
    print(f"   Bot User ID: {bot_user_id}")
    print(f"   User ID: {user_id}")
    print(f"   Test Channel: {test_channel}")
    
    # Test 1: Bot mentions only
    print(f"\n\n🔍 Test 1: Bot mentions only")
    print("-" * 80)
    try:
        bot_only = get_messages_mentions(test_channel, bot_user_id, days=1, debug=True)
        print(f"\n✓ Found {len(bot_only)} messages with bot mentions")
        for i, msg in enumerate(bot_only[:3], 1):
            print(f"   {i}. {msg.get('text', '')[:100]}...")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 2: Bot mentions + keywords
    print(f"\n\n🔍 Test 2: Bot mentions + keywords ('mohit', 'the real pm')")
    print("-" * 80)
    try:
        bot_with_keywords = get_messages_mentions(
            test_channel, 
            bot_user_id, 
            days=1, 
            debug=True,
            include_keywords=["mohit", "the real pm"]
        )
        print(f"\n✓ Found {len(bot_with_keywords)} messages with bot mentions or keywords")
        for i, msg in enumerate(bot_with_keywords[:5], 1):
            text = msg.get('text', '')
            sender = msg.get('user', 'unknown')
            print(f"   {i}. [{sender}] {text[:100]}...")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 3: User mentions
    print(f"\n\n🔍 Test 3: User mentions (Mohit)")
    print("-" * 80)
    try:
        user_mentions = get_messages_mentions(test_channel, user_id, days=1, debug=True)
        print(f"\n✓ Found {len(user_mentions)} messages with user mentions")
        for i, msg in enumerate(user_mentions[:3], 1):
            print(f"   {i}. {msg.get('text', '')[:100]}...")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 4: Combined (simulating what process-mentions does)
    print(f"\n\n🔍 Test 4: Combined detection (bot mentions + keywords + user mentions)")
    print("-" * 80)
    try:
        bot_with_keywords = get_messages_mentions(
            test_channel, 
            bot_user_id, 
            days=1, 
            debug=False,
            include_keywords=["mohit", "the real pm"]
        )
        
        user_mentions = get_messages_mentions(
            test_channel,
            user_id,
            days=1,
            debug=False
        )
        
        # Combine and deduplicate
        all_mentions = {msg.get('ts'): msg for msg in (bot_with_keywords + user_mentions)}
        
        print(f"\n✓ Total unique messages found: {len(all_mentions)}")
        print(f"   - Bot mentions + keywords: {len(bot_with_keywords)}")
        print(f"   - User mentions: {len(user_mentions)}")
        print(f"   - Combined (deduplicated): {len(all_mentions)}")
        
        print("\n📝 Sample messages:")
        for i, msg in enumerate(list(all_mentions.values())[:5], 1):
            text = msg.get('text', '')
            sender = msg.get('user', 'unknown')
            print(f"   {i}. [{sender}] {text[:100]}...")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n" + "="*80)
    print("✅ Testing complete!")
    print("="*80)

if __name__ == "__main__":
    test_mention_detection()
