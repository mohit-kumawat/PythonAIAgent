"""
Test poll approval logic to ensure polls are auto-approved correctly.
"""

import os
from dotenv import load_dotenv

load_dotenv()

def test_poll_approval():
    """Test that polls with confidence > 0.75 are auto-approved"""
    
    # Mock action data
    action = {
        'id': 'test_poll_123',
        'action_type': 'post_slack_poll',
        'confidence': 0.9,  # High confidence
        'trigger_user_id': os.environ.get('SLACK_USER_ID'),  # Mohit's ID
        'data': {
            'channel_id': 'C08JF2UFCR1',
            'question': 'Who is ready for writing blog today?',
            'options': ['Yes', 'No', 'Maybe']
        }
    }
    
    # Simulate approval logic
    atype = action.get('action_type')
    confidence = float(action.get('confidence', 0.5))
    trigger_user = action.get('trigger_user_id')
    authorized_user = os.environ.get('SLACK_USER_ID')
    is_authorized = (trigger_user == authorized_user) if authorized_user else False
    
    print(f"📋 Action {action['id']}:")
    print(f"   Type: {atype}")
    print(f"   Confidence: {confidence}")
    print(f"   Trigger User: {trigger_user}")
    print(f"   Authorized User: {authorized_user}")
    print(f"   Is Authorized: {is_authorized}")
    print()
    
    # Test approval logic
    if atype == 'post_slack_poll':
        if is_authorized and confidence > 0.75:
            action['status'] = 'APPROVED'
            print(f"✅ Auto-approving poll {action['id']} from {trigger_user}")
            return True
        else:
            action['status'] = 'PENDING'
            if not is_authorized:
                print(f"❌ Held unauthorized poll {action['id']} from {trigger_user}")
            else:
                print(f"❌ Held poll {action['id']} - confidence too low ({confidence})")
            return False
    
    return False

def test_low_confidence_poll():
    """Test that polls with low confidence are held"""
    
    action = {
        'id': 'test_poll_456',
        'action_type': 'post_slack_poll',
        'confidence': 0.6,  # Low confidence
        'trigger_user_id': os.environ.get('SLACK_USER_ID'),
        'data': {
            'channel_id': 'C08JF2UFCR1',
            'question': 'Test poll',
            'options': ['A', 'B']
        }
    }
    
    atype = action.get('action_type')
    confidence = float(action.get('confidence', 0.5))
    trigger_user = action.get('trigger_user_id')
    authorized_user = os.environ.get('SLACK_USER_ID')
    is_authorized = (trigger_user == authorized_user) if authorized_user else False
    
    print(f"📋 Action {action['id']}:")
    print(f"   Type: {atype}")
    print(f"   Confidence: {confidence}")
    print(f"   Is Authorized: {is_authorized}")
    print()
    
    if atype == 'post_slack_poll':
        if is_authorized and confidence > 0.75:
            action['status'] = 'APPROVED'
            print(f"✅ Auto-approving poll {action['id']}")
            return False  # Should NOT approve
        else:
            action['status'] = 'PENDING'
            print(f"❌ Held poll {action['id']} - confidence too low ({confidence})")
            return True  # Should hold
    
    return False

def test_unauthorized_poll():
    """Test that polls from unauthorized users are held"""
    
    action = {
        'id': 'test_poll_789',
        'action_type': 'post_slack_poll',
        'confidence': 0.95,  # High confidence
        'trigger_user_id': 'U999UNAUTHORIZED',  # Not Mohit
        'data': {
            'channel_id': 'C08JF2UFCR1',
            'question': 'Test poll',
            'options': ['A', 'B']
        }
    }
    
    atype = action.get('action_type')
    confidence = float(action.get('confidence', 0.5))
    trigger_user = action.get('trigger_user_id')
    authorized_user = os.environ.get('SLACK_USER_ID')
    is_authorized = (trigger_user == authorized_user) if authorized_user else False
    
    print(f"📋 Action {action['id']}:")
    print(f"   Type: {atype}")
    print(f"   Confidence: {confidence}")
    print(f"   Trigger User: {trigger_user}")
    print(f"   Authorized User: {authorized_user}")
    print(f"   Is Authorized: {is_authorized}")
    print()
    
    if atype == 'post_slack_poll':
        if is_authorized and confidence > 0.75:
            action['status'] = 'APPROVED'
            print(f"✅ Auto-approving poll {action['id']}")
            return False  # Should NOT approve
        else:
            action['status'] = 'PENDING'
            print(f"❌ Held unauthorized poll {action['id']} from {trigger_user}")
            return True  # Should hold
    
    return False

if __name__ == "__main__":
    print("=" * 60)
    print("Testing Poll Approval Logic")
    print("=" * 60)
    print()
    
    print("TEST 1: High confidence poll from authorized user")
    print("-" * 60)
    test1 = test_poll_approval()
    print()
    
    print("TEST 2: Low confidence poll from authorized user")
    print("-" * 60)
    test2 = test_low_confidence_poll()
    print()
    
    print("TEST 3: High confidence poll from unauthorized user")
    print("-" * 60)
    test3 = test_unauthorized_poll()
    print()
    
    print("=" * 60)
    print("RESULTS:")
    print("=" * 60)
    print(f"Test 1 (Should approve): {'✅ PASS' if test1 else '❌ FAIL'}")
    print(f"Test 2 (Should hold): {'✅ PASS' if test2 else '❌ FAIL'}")
    print(f"Test 3 (Should hold): {'✅ PASS' if test3 else '❌ FAIL'}")
    print()
    
    if test1 and test2 and test3:
        print("🎉 ALL TESTS PASSED!")
    else:
        print("❌ SOME TESTS FAILED!")
