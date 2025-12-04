#!/usr/bin/env python3
"""
Test script for command processing
Tests the parsing of "Reming @Umang Kedia today 10 am to release the app for testing on beta"
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from command_processor import is_reminder_command, extract_reminder_details, parse_time_expression

def test_reminder_parsing():
    """Test parsing of the user's message"""
    
    # Simulate the actual message
    test_message = "Reming <@U123456> today 10 am to release the app for testing on beta."
    
    print("="*80)
    print("TESTING COMMAND PROCESSOR")
    print("="*80)
    print(f"\nTest Message: {test_message}\n")
    
    # Test 1: Is it recognized as a reminder?
    is_reminder = is_reminder_command(test_message)
    print(f"✓ Is Reminder Command: {is_reminder}")
    
    if not is_reminder:
        print("✗ FAILED: Message not recognized as reminder!")
        return False
    
    # Test 2: Extract details
    details = extract_reminder_details(test_message)
    print(f"\n✓ Extracted Details:")
    print(f"  - Action: {details['action']}")
    print(f"  - Time String: {details['time_str']}")
    print(f"  - Mentioned Users: {details['mentioned_users']}")
    print(f"  - Parsed Time (ISO): {details['parsed_time']}")
    print(f"  - Remind Others: {details.get('remind_others', False)}")
    
    # Test 3: Verify correctness
    expected_action = "release the app for testing on beta"
    expected_time_str = "today 10 am"
    expected_users = ["U123456"]
    
    success = True
    
    if expected_action not in details['action']:
        print(f"\n✗ Action mismatch! Expected '{expected_action}', got '{details['action']}'")
        success = False
    else:
        print(f"\n✓ Action correctly extracted")
    
    if details['mentioned_users'] != expected_users:
        print(f"✗ Users mismatch! Expected {expected_users}, got {details['mentioned_users']}")
        success = False
    else:
        print(f"✓ Mentioned users correctly extracted")
    
    if details.get('remind_others') != True:
        print(f"✗ Should be 'remind_others'=True")
        success = False
    else:
        print(f"✓ Correctly identified as reminding others")
    
    # Test 4: Time parsing
    print(f"\n✓ Time Parsing Test:")
    print(f"  Input: '{expected_time_str}'")
    print(f"  Output: {details['parsed_time']}")
    
    # Verify it's today at 10:00
    from datetime import datetime
    import pytz
    ist = pytz.timezone('Asia/Kolkata')
    parsed_dt = datetime.fromisoformat(details['parsed_time'])
    
    if parsed_dt.hour == 10 and parsed_dt.minute == 0:
        print(f"  ✓ Correctly parsed to 10:00 AM")
    else:
        print(f"  ✗ Time parsing error! Got {parsed_dt.hour}:{parsed_dt.minute}")
        success = False
    
    print("\n" + "="*80)
    if success:
        print("✅ ALL TESTS PASSED")
    else:
        print("❌ SOME TESTS FAILED")
    print("="*80)
    
    return success

if __name__ == "__main__":
    success = test_reminder_parsing()
    sys.exit(0 if success else 1)
