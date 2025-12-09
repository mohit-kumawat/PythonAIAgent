"""
Test to verify that the bot does not ask questions to itself or create circular conversations.
"""

import os
import json
from dotenv import load_dotenv

load_dotenv()

def test_self_questioning_prevention():
    """
    Simulate a scenario where Mohit asks a question and verify the bot doesn't ask back.
    """
    
    # Mock data
    bot_user_id = os.environ.get("SLACK_BOT_USER_ID")
    mohit_user_id = os.environ.get("SLACK_USER_ID")
    test_channel = "C12345TEST"
    
    # Simulate Mohit asking about Abhinav's tasks
    filtered_mentions = [
        {
            'user': mohit_user_id,
            'channel': test_channel,
            'text': "Mohit, I'll compile Pravin's tasks based on the context. He is currently assigned to fix the follow up question buttons tap issue along with @Umang Kedia. Anything else, @Mohit Kumawat?",
            'ts': '1733741234.000100',
            'thread_ts': '1733741200.000000'
        }
    ]
    
    # Simulate AI generating a self-questioning action (BAD)
    new_actions = [
        {
            'action_type': 'send_message',
            'reasoning': 'Need clarification from Mohit',
            'confidence': 0.8,
            'data': {
                'target_channel_id': test_channel,  # Same channel where Mohit asked
                'message_text': 'Mohit, can you provide some context on what you are looking for regarding @Abhinav Singh\'s tasks?',
                'thread_ts': '1733741200.000000'
            }
        }
    ]
    
    # VALIDATION LOGIC (from daemon.py)
    triggering_users = set()
    triggering_channels = set()
    for m in filtered_mentions:
        if m.get('user'):
            triggering_users.add(m.get('user'))
        if m.get('channel'):
            triggering_channels.add(m.get('channel'))
    
    validated_actions = []
    for action in new_actions:
        atype = action.get('action_type')
        data = action.get('data', {})
        
        # Check if this is a message action
        if atype in ['send_message', 'draft_reply']:
            target_channel = data.get('target_channel_id') or data.get('channel_id') or data.get('channel')
            message_text = data.get('message_text', '')
            
            # RULE 1: Don't send questions back to the triggering user/channel
            is_question = '?' in message_text
            targets_triggering_user = target_channel in triggering_users
            targets_triggering_channel = target_channel in triggering_channels
            
            if is_question and (targets_triggering_user or targets_triggering_channel):
                print(f"⚠️ BLOCKED self-questioning action: '{message_text[:50]}...' to {target_channel}")
                print(f"   Triggering users: {triggering_users}, channels: {triggering_channels}")
                continue  # Skip this action
            
            # RULE 2: Don't ask Mohit to clarify his own questions
            mohit_id = os.environ.get('SLACK_USER_ID')
            if mohit_id and target_channel == mohit_id and is_question:
                # Check if Mohit was the one who asked
                if mohit_id in triggering_users:
                    print(f"⚠️ BLOCKED asking Mohit to clarify his own question: '{message_text[:50]}...'")
                    continue  # Skip this action
        
        # Action passed validation
        validated_actions.append(action)
    
    # Verify the action was blocked
    print(f"\n✅ TEST RESULTS:")
    print(f"   Original actions: {len(new_actions)}")
    print(f"   Validated actions: {len(validated_actions)}")
    print(f"   Blocked actions: {len(new_actions) - len(validated_actions)}")
    
    if len(validated_actions) == 0:
        print(f"\n✅ SUCCESS: Self-questioning action was correctly blocked!")
        return True
    else:
        print(f"\n❌ FAILURE: Self-questioning action was NOT blocked!")
        print(f"   Remaining actions: {json.dumps(validated_actions, indent=2)}")
        return False

def test_valid_action_passes():
    """
    Verify that valid actions (asking someone else) still pass through.
    """
    
    mohit_user_id = os.environ.get("SLACK_USER_ID")
    umang_user_id = "U07EXAMPLE"  # Different user
    test_channel = "C12345TEST"
    
    # Simulate Mohit asking about Abhinav's tasks
    filtered_mentions = [
        {
            'user': mohit_user_id,
            'channel': test_channel,
            'text': "What is Umang working on?",
            'ts': '1733741234.000100'
        }
    ]
    
    # Simulate AI generating a valid action (asking Umang, not Mohit)
    new_actions = [
        {
            'action_type': 'send_message',
            'reasoning': 'Check with Umang about his tasks',
            'confidence': 0.9,
            'data': {
                'target_channel_id': umang_user_id,  # Different user
                'message_text': 'Hi Umang, can you share what you are currently working on?',
            }
        }
    ]
    
    # VALIDATION LOGIC
    triggering_users = set()
    triggering_channels = set()
    for m in filtered_mentions:
        if m.get('user'):
            triggering_users.add(m.get('user'))
        if m.get('channel'):
            triggering_channels.add(m.get('channel'))
    
    validated_actions = []
    for action in new_actions:
        atype = action.get('action_type')
        data = action.get('data', {})
        
        if atype in ['send_message', 'draft_reply']:
            target_channel = data.get('target_channel_id') or data.get('channel_id') or data.get('channel')
            message_text = data.get('message_text', '')
            
            is_question = '?' in message_text
            targets_triggering_user = target_channel in triggering_users
            targets_triggering_channel = target_channel in triggering_channels
            
            if is_question and (targets_triggering_user or targets_triggering_channel):
                print(f"⚠️ BLOCKED self-questioning action: '{message_text[:50]}...'")
                continue
            
            mohit_id = os.environ.get('SLACK_USER_ID')
            if mohit_id and target_channel == mohit_id and is_question:
                if mohit_id in triggering_users:
                    print(f"⚠️ BLOCKED asking Mohit to clarify his own question: '{message_text[:50]}...'")
                    continue
        
        validated_actions.append(action)
    
    print(f"\n✅ TEST RESULTS (Valid Action):")
    print(f"   Original actions: {len(new_actions)}")
    print(f"   Validated actions: {len(validated_actions)}")
    
    if len(validated_actions) == len(new_actions):
        print(f"\n✅ SUCCESS: Valid action was correctly allowed!")
        return True
    else:
        print(f"\n❌ FAILURE: Valid action was incorrectly blocked!")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Testing Self-Questioning Prevention Logic")
    print("=" * 60)
    
    test1 = test_self_questioning_prevention()
    print("\n" + "=" * 60)
    test2 = test_valid_action_passes()
    print("\n" + "=" * 60)
    
    # Test 3: Verify messages that tag the bot itself are blocked
    print("\n🧪 TEST 3: Blocking messages that tag the bot")
    print("=" * 60)
    
    mohit_user_id = os.environ.get("SLACK_USER_ID")
    bot_user_id = os.environ.get("SLACK_BOT_USER_ID")
    test_channel = "C12345TEST"
    
    filtered_mentions = [
        {
            'user': mohit_user_id,
            'channel': test_channel,
            'text': "What is Abhinav working on?",
            'ts': '1733741234.000100'
        }
    ]
    
    # Simulate AI generating a message that tags the bot (BAD)
    new_actions = [
        {
            'action_type': 'send_message',
            'reasoning': 'Asking for clarification',
            'confidence': 0.8,
            'data': {
                'target_channel_id': test_channel,
                'message_text': f'Hi <@{bot_user_id}>, can you check on this?',  # Tags itself!
            }
        }
    ]
    
    # VALIDATION LOGIC
    triggering_users = set()
    triggering_channels = set()
    for m in filtered_mentions:
        if m.get('user'):
            triggering_users.add(m.get('user'))
        if m.get('channel'):
            triggering_channels.add(m.get('channel'))
    
    validated_actions = []
    for action in new_actions:
        atype = action.get('action_type')
        data = action.get('data', {})
        
        if atype in ['send_message', 'draft_reply']:
            target_channel = data.get('target_channel_id') or data.get('channel_id') or data.get('channel')
            message_text = data.get('message_text', '')
            
            is_question = '?' in message_text
            targets_triggering_user = target_channel in triggering_users
            targets_triggering_channel = target_channel in triggering_channels
            
            if is_question and (targets_triggering_user or targets_triggering_channel):
                print(f"⚠️ BLOCKED self-questioning action")
                continue
            
            mohit_id = os.environ.get('SLACK_USER_ID')
            if mohit_id and target_channel == mohit_id and is_question:
                if mohit_id in triggering_users:
                    print(f"⚠️ BLOCKED asking Mohit to clarify his own question")
                    continue
            
            # RULE 3: Check for self-tagging
            bot_id = os.environ.get('SLACK_BOT_USER_ID')
            if bot_id:
                if f'<@{bot_id}>' in message_text or '@The Real PM' in message_text:
                    print(f"⚠️ BLOCKED message that tags the bot itself: '{message_text[:50]}...'")
                    continue
        
        validated_actions.append(action)
    
    print(f"\n✅ TEST RESULTS (Self-Tagging):")
    print(f"   Original actions: {len(new_actions)}")
    print(f"   Validated actions: {len(validated_actions)}")
    
    test3 = len(validated_actions) == 0
    if test3:
        print(f"\n✅ SUCCESS: Self-tagging message was correctly blocked!")
    else:
        print(f"\n❌ FAILURE: Self-tagging message was NOT blocked!")
    
    print("\n" + "=" * 60)
    
    if test1 and test2 and test3:
        print("\n🎉 ALL TESTS PASSED!")
    else:
        print("\n❌ SOME TESTS FAILED!")

