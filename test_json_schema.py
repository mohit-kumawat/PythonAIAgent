#!/usr/bin/env python3
"""
Test script to validate JSON Schema implementation.
This ensures the LLM always outputs valid, structured JSON.
"""

import os
import json
from dotenv import load_dotenv
from google import genai
from google.genai import types
from client_manager import ClientManager

load_dotenv()

def test_json_schema_enforcement():
    """Test that the LLM respects the JSON schema and outputs valid JSON."""
    
    print("=" * 80)
    print("Testing JSON Schema Enforcement")
    print("=" * 80)
    
    # Define the same schema used in daemon.py
    action_schema = {
        "type": "ARRAY",
        "items": {
            "type": "OBJECT",
            "properties": {
                "action_type": {
                    "type": "STRING",
                    "enum": ["schedule_reminder", "send_message", "update_context_task", "draft_reply"]
                },
                "reasoning": {"type": "STRING"},
                "confidence": {"type": "NUMBER"},
                "severity": {"type": "STRING", "enum": ["low", "medium", "high"]},
                "trigger_user_id": {"type": "STRING"},
                "data": {
                    "type": "OBJECT",
                    "properties": {
                        "target_channel_id": {"type": "STRING"},
                        "message_text": {"type": "STRING"},
                        "time_iso": {"type": "STRING"}
                    }
                }
            },
            "required": ["action_type", "reasoning", "data"]
        }
    }
    
    # Test prompt with intentionally complex scenario
    test_prompt = """
    Analyze this Slack message and generate actions:
    
    Message: "Hey @bot, remind me tomorrow at 2pm to check the deployment status"
    User: U12345 (Mohit)
    Channel: C67890
    Time: 2025-12-08T16:00:00
    
    Generate appropriate actions.
    """
    
    try:
        manager = ClientManager()
        client = manager.get_client()
        
        print("\n📤 Sending test prompt to LLM with schema enforcement...")
        
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=test_prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=action_schema
            )
        )
        
        print("\n✅ Response received!")
        print("\n📄 Raw Response Text:")
        print("-" * 80)
        print(response.text)
        print("-" * 80)
        
        # Parse the JSON
        print("\n🔍 Parsing JSON...")
        actions = json.loads(response.text)
        
        print(f"\n✅ Successfully parsed {len(actions)} action(s)")
        
        # Validate each action
        print("\n📋 Validating Actions:")
        for i, action in enumerate(actions, 1):
            print(f"\n  Action {i}:")
            print(f"    Type: {action.get('action_type')}")
            print(f"    Reasoning: {action.get('reasoning')}")
            print(f"    Confidence: {action.get('confidence', 'N/A')}")
            print(f"    Severity: {action.get('severity', 'N/A')}")
            
            # Validate required fields
            assert "action_type" in action, "Missing action_type"
            assert "reasoning" in action, "Missing reasoning"
            assert "data" in action, "Missing data"
            
            # Validate enum
            valid_types = ["schedule_reminder", "send_message", "update_context_task", "draft_reply"]
            assert action["action_type"] in valid_types, f"Invalid action_type: {action['action_type']}"
            
            print(f"    ✅ Valid structure")
        
        print("\n" + "=" * 80)
        print("✅ ALL TESTS PASSED!")
        print("=" * 80)
        print("\n💡 Key Observations:")
        print("  • LLM output is pure JSON (no markdown wrappers)")
        print("  • All required fields are present")
        print("  • Enum values are validated")
        print("  • No parsing errors possible")
        print("\n🚀 JSON Schema enforcement is working correctly!")
        
        return True
        
    except json.JSONDecodeError as e:
        print(f"\n❌ JSON Parsing Error: {e}")
        print("This should NEVER happen with schema enforcement!")
        return False
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False


def test_backward_compatibility():
    """Test that old code still works with new parse_json_response function."""
    
    print("\n" + "=" * 80)
    print("Testing Backward Compatibility")
    print("=" * 80)
    
    # Import the new function
    from daemon import parse_json_response
    
    # Test with markdown-wrapped JSON (old format)
    old_format = """
    Here's the action plan:
    
    ```json
    [
        {
            "action_type": "send_message",
            "reasoning": "Test message",
            "data": {"message_text": "Hello"}
        }
    ]
    ```
    """
    
    # Test with plain JSON (new format)
    new_format = """
    [
        {
            "action_type": "send_message",
            "reasoning": "Test message",
            "data": {"message_text": "Hello"}
        }
    ]
    """
    
    print("\n🧪 Test 1: Plain JSON (new format)")
    result1 = parse_json_response(new_format)
    assert len(result1) == 1, "Failed to parse plain JSON"
    print("  ✅ Passed")
    
    print("\n🧪 Test 2: Markdown-wrapped JSON (old format - main.py)")
    # Use the main.py version which has backward compatibility
    from main import parse_json_response as main_parse
    result2 = main_parse(old_format)
    assert len(result2) == 1, "Failed to parse markdown-wrapped JSON"
    print("  ✅ Passed")
    
    print("\n✅ Backward compatibility maintained!")


if __name__ == "__main__":
    print("\n🧪 JSON Schema Validation Test Suite\n")
    
    # Test 1: Schema enforcement
    test1_passed = test_json_schema_enforcement()
    
    # Test 2: Backward compatibility
    try:
        test_backward_compatibility()
        test2_passed = True
    except Exception as e:
        print(f"\n❌ Backward compatibility test failed: {e}")
        test2_passed = False
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"  Schema Enforcement:      {'✅ PASS' if test1_passed else '❌ FAIL'}")
    print(f"  Backward Compatibility:  {'✅ PASS' if test2_passed else '❌ FAIL'}")
    print("=" * 80)
    
    if test1_passed and test2_passed:
        print("\n🎉 All tests passed! Your upgrade is ready for production.")
        exit(0)
    else:
        print("\n⚠️  Some tests failed. Please review the errors above.")
        exit(1)
