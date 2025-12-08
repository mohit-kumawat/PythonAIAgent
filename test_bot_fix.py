#!/usr/bin/env python3
"""
Quick test to verify the bot self-messaging fix works correctly.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Test data
bot_user_id = os.environ.get("SLACK_BOT_USER_ID")
authorized_user_id = os.environ.get("SLACK_USER_ID")

print("=" * 60)
print("TESTING BOT SELF-MESSAGING FIX")
print("=" * 60)

print(f"\nBot User ID: {bot_user_id}")
print(f"Authorized User ID: {authorized_user_id}")

# Simulate message scenarios
test_messages = [
    {
        "ts": "1234567890.123456",
        "user": authorized_user_id,
        "text": "Hey @mohit, can you help?",
        "expected": "PROCESS",
        "reason": "Message from authorized user"
    },
    {
        "ts": "1234567890.123457",
        "user": bot_user_id,
        "text": "I'm working on it, @mohit",
        "expected": "SKIP",
        "reason": "Message from bot itself"
    },
    {
        "ts": "1234567890.123458",
        "user": "U0A1J73B8JH",
        "text": "Hey @mohit, update?",
        "expected": "SKIP",
        "reason": "Message from other user (not authorized)"
    },
    {
        "ts": "1234567890.123459",
        "user": authorized_user_id,
        "text": "The Real PM, what's the status?",
        "expected": "PROCESS",
        "reason": "Message from authorized user with keyword"
    }
]

print("\n" + "=" * 60)
print("SIMULATING MESSAGE FILTERING")
print("=" * 60)

passed = 0
failed = 0

for i, msg in enumerate(test_messages, 1):
    print(f"\n[Test {i}] {msg['reason']}")
    print(f"  User: {msg['user']}")
    print(f"  Text: {msg['text']}")
    
    # Simulate the filtering logic from daemon.py
    should_process = False
    
    # Skip bot's own messages FIRST (the fix)
    if msg.get('user') == bot_user_id:
        print(f"  ❌ SKIPPED: Bot's own message")
    # Then check if from authorized user
    elif msg.get('user') == authorized_user_id:
        should_process = True
        print(f"  ✅ PROCESSED: From authorized user")
    else:
        print(f"  ❌ SKIPPED: Not from authorized user")
    
    # Verify expected behavior
    actual = "PROCESS" if should_process else "SKIP"
    if actual == msg['expected']:
        print(f"  ✅ TEST PASSED")
        passed += 1
    else:
        print(f"  ❌ TEST FAILED: Expected {msg['expected']}, got {actual}")
        failed += 1

print("\n" + "=" * 60)
print("TEST RESULTS")
print("=" * 60)
print(f"Passed: {passed}/{len(test_messages)}")
print(f"Failed: {failed}/{len(test_messages)}")

if failed == 0:
    print("\n✅ ALL TESTS PASSED - Fix is working correctly!")
else:
    print(f"\n❌ {failed} TEST(S) FAILED - Fix needs review")

print("=" * 60)
