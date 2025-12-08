import os
import sys
import argparse
import json
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Import our custom modules
from drift_detector import analyze_drift
from state_manager import update_section, read_context
from slack_tools import (
    read_slack_messages, 
    get_self_todo, 
    send_slack_message,
    schedule_slack_message,
    get_messages_mentions
)
from command_processor import parse_command_from_message, create_reminder_message
from email_tools import read_recent_emails, send_email
from client_manager import ClientManager

# Load environment variables
load_dotenv()

def parse_json_response(text: str) -> list:
    """Parse JSON response from schema-enforced generation."""
    import re
    import json
    
    # Try to find JSON block first (for backward compatibility)
    match = re.search(r"```json\s*\n(.*?)\n\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass
    
    # Try direct JSON parsing
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError as e:
        print(f"Warning: JSON parsing error: {e}")
        return []

def run_sync_mode(manager: ClientManager, channel_ids: list, todo_sync: bool):
    """
    Executes the 'sync' mode: checks for drift and optionally updates context.
    Handles API key rotation on quota errors.
    """
    if not channel_ids and not todo_sync:
        print("Error: At least one --channels or --todo-sync must be provided.")
        return

    print(f"Analyzing drift between Context and Slack...")
    if channel_ids:
        print(f"Channels: {channel_ids}")
    if todo_sync:
        print("Including To-Do Sync")
    
    client = manager.get_client()
    max_retries = len(manager.keys)
    attempts = 0
    
    while attempts < max_retries:
        try:
            result = analyze_drift(client, channel_ids, todo_sync=todo_sync)
            break # Success
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                print(f"Quota exceeded (Attempt {attempts+1}/{max_retries}). Rotating key...")
                client = manager.rotate_client()
                attempts += 1
                time.sleep(1) # Brief pause
            else:
                print(f"Error during drift analysis: {e}")
                return
    else:
        print("Error: All API keys exhausted or failed.")
        return

    print("\n--- Analysis Result ---")
    print(f"Status Change Detected: {result.get('status_change_detected')}")
    print(f"Risk Level: {result.get('risk_level')}")
    print(f"Reason: {result.get('reason')}")
    
    if result.get('status_change_detected'):
        print("\n-----------------------")
        
        # 1. Overall Health & Risk Register Update
        suggested_health = result.get('suggested_update_to_overall_health_and_risk')
        if suggested_health:
            print("\n[Proposed Update for '1. Overall Health & Risk Register']")
            print(suggested_health)
            apply = input("Apply this update? [y/n]: ").strip().lower()
            if apply == 'y':
                try:
                    update_section("1. Overall Health & Risk Register", suggested_health)
                    print("Overall Health & Risk Register updated.")
                except Exception as e:
                    print(f"Failed to update Overall Health & Risk Register: {e}")
            else:
                print("Skipped Overall Health & Risk Register update.")

        # 2. Active Epics & Tasks Update
        suggested_epics = result.get('suggested_update_to_active_epics_and_tasks')
        if suggested_epics:
            print("\n[Proposed Update for '2. Active Epics & Tasks']")
            print(suggested_epics)
            apply = input("Apply this update? [y/n]: ").strip().lower()
            if apply == 'y':
                try:
                    update_section("2. Active Epics & Tasks", suggested_epics)
                    print("Active Epics & Tasks updated.")
                except Exception as e:
                    print(f"Failed to update Active Epics & Tasks: {e}")
            else:
                print("Skipped Active Epics & Tasks update.")

    else:
        print("No status change detected. Context is up to date.")

def create_chat(client):
    """Helper to create a chat session with tools."""
    # Define the tools
    tools = [
        read_slack_messages,
        get_self_todo,
        send_slack_message,
        read_recent_emails,
        send_email
    ]
    
    return client.chats.create(
        model="gemini-flash-latest",
        config=types.GenerateContentConfig(
            tools=tools,
            system_instruction="""You are a helpful personal assistant. 
            Your goal is to help the user manage their tasks and communications.
            
            You have access to the following tools:
            - Slack: Read messages, check 'self-todos' (DMs to self), and send messages.
            - Email: Read recent emails and send emails.
            
            When asked to check tasks or todos, always check the Slack self-DMs first using `get_self_todo`.
            When asked to check messages, check both Slack and Email unless specified.
            
            Always be polite and concise. If you need to send a message or email, confirm the details if they are ambiguous, 
            but if the user gives a clear instruction (e.g. "Tell Alice I'll be late"), just do it.
            
            If the user explicitly asks you to 'send' a message, 'post' an update, or 'ask' someone for status, you must use the `send_slack_message` tool directly. Do NOT ask for confirmation unless the message content or recipient is ambiguous.
            """
        )
    )

def run_chat_mode(manager: ClientManager):
    """
    Executes the 'chat' mode: interactive personal assistant.
    Handles API key rotation on quota errors.
    """
    client = manager.get_client()
    print("Initializing Personal Assistant...")
    
    chat = create_chat(client)
    print("Personal Assistant is ready! (Type 'quit' to exit)")
    
    while True:
        try:
            user_input = input("\nUser: ")
            if user_input.lower() in ["quit", "exit"]:
                break
            
            # Retry logic for chat message
            max_retries = len(manager.keys)
            attempts = 0
            while attempts < max_retries:
                try:
                    response = chat.send_message(user_input)
                    print(f"Assistant: {response.text}")
                    
                    # Check for function calls and print them for debugging/visibility
                    if response.candidates and response.candidates[0].content.parts:
                        for part in response.candidates[0].content.parts:
                            if part.function_call:
                                print(f"[Debug] Tool used: {part.function_call.name}")
                    break # Success
                except Exception as e:
                    error_str = str(e)
                    if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                        print(f"Quota exceeded (Attempt {attempts+1}/{max_retries}). Rotating key...")
                        client = manager.rotate_client()
                        # We need to recreate the chat session with the new client
                        # Note: This loses conversation history in this simple implementation
                        print("Reconnecting session (History may be reset)...")
                        chat = create_chat(client)
                        attempts += 1
                        time.sleep(1)
                    else:
                        raise e
                        
        except Exception as e:
            print(f"An error occurred: {e}")

def run_process_mentions(manager: ClientManager, channel_ids: list):
    """
    Processes messages where the bot is mentioned, user is mentioned, or specific keywords appear.
    Searches for: bot mentions, user mentions, "mohit", "the real pm"
    Only accepts commands from authorized user (Mohit).
    """
    if not channel_ids:
        print("Error: At least one --channels must be provided.")
        return

    bot_user_id = os.environ.get("SLACK_BOT_USER_ID")
    authorized_user_id = os.environ.get("SLACK_USER_ID")  # Mohit's user ID
    
    if not bot_user_id or not authorized_user_id:
        print("Error: SLACK_BOT_USER_ID and SLACK_USER_ID must be set in .env")
        print("  SLACK_USER_ID: Your (Mohit's) Slack user ID")
        print("  SLACK_BOT_USER_ID: The bot's Slack user ID")
        return

    # Load agent instruction
    try:
        with open("agent_instruction.txt", "r") as f:
            agent_instruction = f.read()
    except FileNotFoundError:
        print("Warning: agent_instruction.txt not found. Using default instruction.")
        agent_instruction = "You are a helpful PM assistant."

    print("Processing mentions and keywords across channels...")
    print(f"Authorized user: {authorized_user_id}")
    print(f"Bot user: {bot_user_id}")
    print(f"Searching for: @mentions, 'mohit', 'the real pm' (last 24 hours)")
    
    # Keywords to search for in addition to mentions
    search_keywords = ["mohit", "the real pm"]
    
    # Collect all mentions from all channels (filtered to last 1 day for full conversation context)
    all_mentions = []
    unauthorized_mentions = []
    skipped_channels = []
    
    for channel_id in channel_ids:
        try:
            print(f"\n🔍 Checking channel: {channel_id}")
            
            # Search for bot mentions AND keywords (last 24 hours)
            bot_mentions = get_messages_mentions(
                channel_id, 
                bot_user_id, 
                days=1, 
                debug=False,
                include_keywords=search_keywords
            )
            
            # Also search for user mentions (Mohit's user ID, last 24 hours)
            user_mentions = get_messages_mentions(
                channel_id,
                authorized_user_id,
                days=1,
                debug=False
            )
            
            # Combine and deduplicate by message timestamp
            all_channel_mentions = {msg.get('ts'): msg for msg in (bot_mentions + user_mentions)}
            
            for msg in all_channel_mentions.values():
                msg['channel_id'] = channel_id
                sender_id = msg.get('user')
                
                # Skip messages from the bot itself (e.g., join notifications)
                if sender_id == bot_user_id:
                    print(f"  ℹ️  Skipping bot's own message (e.g., join notification)")
                    continue
                
                # Separate authorized vs unauthorized mentions
                if sender_id == authorized_user_id:
                    all_mentions.append(msg)
                else:
                    unauthorized_mentions.append(msg)
                    
            print(f"  Found {len(all_channel_mentions)} relevant message(s)")
            
        except Exception as e:
            error_str = str(e)
            if 'not_in_channel' in error_str:
                print(f"⚠️  Skipping channel {channel_id}: Bot is not a member of this channel")
                print(f"    To fix: In Slack, type '/invite @The Real PM' in that channel")
                skipped_channels.append(channel_id)
            else:
                print(f"⚠️  Error accessing channel {channel_id}: {e}")
                skipped_channels.append(channel_id)
    
    # Show summary of skipped channels
    if skipped_channels:
        print(f"\n📋 Summary: Skipped {len(skipped_channels)} channel(s) due to access issues")
        print(f"   Successfully checked {len(channel_ids) - len(skipped_channels)} channel(s)")

    
    # Handle unauthorized mentions
    if unauthorized_mentions:
        print(f"\nFound {len(unauthorized_mentions)} mention(s) from unauthorized users.")
        print("Sending refusal messages...")
        
        refusal_message = ("I appreciate the mention, but I only accept commands from my designated "
                          "Project Manager, Mohit. Please reach out to him directly for any requests.")
        
        for msg in unauthorized_mentions:
            try:
                send_slack_message(msg['channel_id'], refusal_message)
                print(f"  ✓ Sent refusal to channel {msg['channel_id']}")
            except Exception as e:
                print(f"  ✗ Failed to send refusal: {e}")
    
    if not all_mentions:
        print("No mentions from authorized user (Mohit) found in the last 24 hours.")
        return
    
    print(f"\nFound {len(all_mentions)} authorized mention(s). Analyzing...")
    
    # Prepare context for AI
    context_text = read_context()
    mentions_text = json.dumps(all_mentions, indent=2, default=str)
    
    # Get current time for the LLM
    from datetime import datetime
    import pytz
    ist = pytz.timezone('Asia/Kolkata')
    current_time = datetime.now(ist).strftime('%Y-%m-%d %H:%M:%S %Z')
    
    # New prompt (replace the original):
    prompt = f"""You are The Real PM agent. Analyze these Slack messages where you were mentioned by Mohit.

CRITICAL RULES:
1. These messages are ONLY from Mohit (authorized user).
2. All messages are from the LAST 24 HOURS to capture full conversation context.
3. Your response MUST contain TWO parts: a readable text analysis, and a structured JSON list of actions enclosed in a ```json code block.
4. CURRENT TIME: {current_time}. DO NOT schedule reminders for times that have already passed.
5. CHECK "3. Reminders (Managed by Agent)" section in the context below. DO NOT schedule reminders that are already listed there.

Current Project Context:
{context_text}

Mohit's Messages (last 24 hours):
{mentions_text}

FIRST, provide a clear, readable summary of intents found (Reminders, Assignments, Tasks) and the proposed actions.

SECOND, at the end of your response, output ONLY the structured actions in a JSON list.

JSON Schema for EACH action object:
{{
  "action_type": "schedule_reminder" | "update_context_task" | "send_message" | "draft_reply",
  "reasoning": "Brief explanation (e.g., 'Remind Umang about beta release')",
  "data": {{
    "target_channel_id": "Channel ID for Slack actions (use original message channel ID)",
    "target_user_ids": "List of Slack IDs mentioned or implied (e.g., ['U123456'])",
    "message_text": "The exact message to send (for send_message or draft_reply action)",
    "reply_to_message_ts": "Timestamp of the message to reply to (for draft_reply action)",
    "time_iso": "ISO 8601 format for reminders (e.g., 2025-12-06T11:30:00). Must be future time.",
    "epic_title": "Epic name from context.md (e.g., Home Page Update)",
    "new_status": "New Status for the task",
    "new_owner": "New Owner for the task",
    "new_markdown_content": "The EXACT full markdown content for Section '2. Active Epics & Tasks' to reflect the update. Maintain existing structure."
  }}
}}

IMPORTANT: 
- Use "send_message" when you need to proactively notify the team.
- Use "draft_reply" when someone asked Mohit a question and you need to draft a response for his approval.
- Check "3. Reminders (Managed by Agent)" to avoid duplicate reminders.

Example JSON Output:
```json
[
  {{
    "action_type": "schedule_reminder",
    "reasoning": "Remind Mohit to take update from Pravin",
    "data": {{
      "target_channel_id": "C08JF2UFCR1",
      "target_user_ids": ["U07FDMFFM5F", "U999888"],
      "time_iso": "2025-12-06T11:30:00"
    }}
  }}
]
```
"""

    client = manager.get_client()
    
    # Retry logic with API key rotation (similar to sync mode)
    max_retries = len(manager.keys)
    attempts = 0
    response = None
    
    while attempts < max_retries:
        try:
            response = client.models.generate_content(
                model="gemini-flash-latest",
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=agent_instruction
                )
            )
            break  # Success
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                print(f"\n⚠️  Quota exceeded (Attempt {attempts+1}/{max_retries}). Rotating to next API key...")
                client = manager.rotate_client()
                attempts += 1
                time.sleep(2)  # Brief pause before retry
            else:
                print(f"Error during analysis: {e}")
                return
    
    if response is None:
        print("\n❌ Error: All API keys exhausted or failed.")
        print("💡 Suggestions:")
        print("   1. Wait for quota to reset (usually 1 minute or 24 hours)")
        print("   2. Add more API keys to your .env file (GOOGLE_API_KEY_2, GOOGLE_API_KEY_3, etc.)")
        print("   3. Upgrade to a paid Gemini API plan")
        print("   4. Check your usage at: https://ai.dev/usage?tab=rate-limit")
        return
    
    try:
        
        print("\n" + "="*80)
        print("AGENT ANALYSIS")
        print("="*80)
        # Print the entire response (text plan + JSON block) for user review
        print(response.text)
        print("="*80 + "\n")
        
        # Extract the structured action plan using the new helper function
        action_plan_json = parse_json_response(response.text)
        
        if not action_plan_json:
            print("Warning: Could not extract structured action plan from response. No actions will be executed.")
            return

        # Display the parsed actions for final check
        print(f"💡 Found {len(action_plan_json)} structured actions ready for execution.")
        
        # Interactive approval loop
        while True:
            approval = input("\nApprove and execute? [y/n/u to update]: ").strip().lower()
            
            if approval == 'y':
                break  # Proceed to execution
            elif approval == 'n':
                print("✗ Actions cancelled by user.")
                return
            elif approval == 'u':
                print("\n📝 Update Mode - You can modify the proposed actions.")
                print("Available commands:")
                print("  - 'delete <number>' - Remove an action")
                print("  - 'edit <number>' - Edit an action's message/reasoning")
                print("  - 'done' - Finish editing and approve")
                print("  - 'cancel' - Cancel all actions\n")
                
                while True:
                    # Display current actions
                    print("\nCurrent Actions:")
                    for i, action in enumerate(action_plan_json, 1):
                        print(f"  {i}. [{action.get('action_type')}] {action.get('reasoning', 'No description')}")
                    
                    edit_cmd = input("\nEdit command: ").strip().lower()
                    
                    if edit_cmd == 'done':
                        print("\n✓ Edits complete. Proceeding to execution...")
                        break
                    elif edit_cmd == 'cancel':
                        print("✗ Actions cancelled by user.")
                        return
                    elif edit_cmd.startswith('delete '):
                        try:
                            idx = int(edit_cmd.split()[1]) - 1
                            if 0 <= idx < len(action_plan_json):
                                removed = action_plan_json.pop(idx)
                                print(f"✓ Removed: {removed.get('reasoning')}")
                            else:
                                print("❌ Invalid action number")
                        except (ValueError, IndexError):
                            print("❌ Invalid command. Use: delete <number>")
                    elif edit_cmd.startswith('edit '):
                        try:
                            idx = int(edit_cmd.split()[1]) - 1
                            if 0 <= idx < len(action_plan_json):
                                action = action_plan_json[idx]
                                print(f"\nEditing: {action.get('reasoning')}")
                                
                                # Allow editing the reasoning
                                new_reasoning = input(f"New reasoning (or press Enter to keep): ").strip()
                                if new_reasoning:
                                    action['reasoning'] = new_reasoning
                                
                                # Allow editing message text if applicable
                                if 'message_text' in action.get('data', {}):
                                    new_message = input(f"New message (or press Enter to keep): ").strip()
                                    if new_message:
                                        action['data']['message_text'] = new_message
                                
                                print("✓ Action updated")
                            else:
                                print("❌ Invalid action number")
                        except (ValueError, IndexError):
                            print("❌ Invalid command. Use: edit <number>")
                    else:
                        print("❌ Unknown command. Try: delete <n>, edit <n>, done, or cancel")
                
                break  # Exit the approval loop and proceed to execution
            else:
                print("❌ Please enter 'y' (yes), 'n' (no), or 'u' (update)")
        
        if approval == 'y' or approval == 'u':  # Execute if approved or after editing
            print("\n✓ Actions approved. Executing...")
            
            executed_actions = []
            
            # Execute all actions from the parsed JSON plan
            for action in action_plan_json:
                action_type = action.get('action_type')
                data = action.get('data', {})
                
                try:
                    if action_type == "schedule_reminder":
                        # We assume the LLM correctly provided the target users and time_iso
                        target_users = data.get('target_user_ids', [])
                        channel_id = data.get('target_channel_id') or all_mentions[0]['channel_id']
                        time_iso = data.get('time_iso')
                        
                        # Validate that the time is in the future
                        from datetime import datetime
                        import pytz
                        
                        try:
                            # Parse the scheduled time
                            if 'T' in time_iso:
                                scheduled_dt = datetime.fromisoformat(time_iso.replace('Z', '+00:00'))
                            else:
                                scheduled_dt = datetime.fromisoformat(time_iso)
                            
                            # Make it timezone-aware if it isn't
                            if scheduled_dt.tzinfo is None:
                                ist = pytz.timezone('Asia/Kolkata')
                                scheduled_dt = ist.localize(scheduled_dt)
                            
                            # Check if it's in the past
                            now = datetime.now(pytz.timezone('Asia/Kolkata'))
                            if scheduled_dt <= now:
                                executed_actions.append(f"⏭️  Skipped past-time reminder: {action.get('reasoning', 'Reminder')} (was scheduled for {time_iso})")
                                continue
                        except Exception as e:
                            # If we can't parse the time, let Slack handle it
                            pass
                        
                        # Use the action's reasoning as the core message content
                        core_action = action.get('reasoning', "A scheduled reminder.")

                        # Create the full reminder message using the existing format
                        from command_processor import create_reminder_message
                        
                        reminder_message = create_reminder_message(
                            {"action": core_action},
                            target_users or [authorized_user_id]
                        )
                        
                        result = schedule_slack_message(
                            channel_id=channel_id,
                            text=reminder_message,
                            scheduled_time=time_iso
                        )
                        
                        if result.get('success'):
                            executed_actions.append(f"✓ Scheduled reminder: {core_action} for {time_iso}")
                            
                            # Add the reminder to the context.md tracking section
                            try:
                                from datetime import datetime
                                dt = datetime.fromisoformat(time_iso.replace('Z', '+00:00'))
                                reminder_entry = f"- [{dt.strftime('%Y-%m-%d %H:%M')}] {core_action}"
                                update_section("3. Reminders (Managed by Agent)", reminder_entry, append=True)
                            except Exception as e:
                                # Don't fail the whole action if tracking fails
                                pass
                        else:
                            executed_actions.append(f"✗ Failed to schedule: {result.get('error')}")
                        
                    elif action_type == "update_context_task":
                        epic_title = data.get('epic_title')
                        new_status = data.get('new_status')
                        new_owner = data.get('new_owner')
                        
                        # Use the new markdown content provided by the LLM
                        if 'new_markdown_content' in data:
                            try:
                                # Update the Active Epics section (Section 2) with the new markdown block
                                update_section("2. Active Epics & Tasks", data['new_markdown_content'])
                                
                                # Build a better success message
                                if epic_title and new_status:
                                    executed_actions.append(f"✓ Context Updated: '{epic_title}' status set to '{new_status}'")
                                elif epic_title and new_owner:
                                    executed_actions.append(f"✓ Context Updated: '{epic_title}' owner set to '{new_owner}'")
                                elif epic_title:
                                    executed_actions.append(f"✓ Context Updated: '{epic_title}' task modified")
                                else:
                                    executed_actions.append(f"✓ Context Updated: Active Epics & Tasks section refreshed")
                            except ValueError as e:
                                executed_actions.append(f"✗ Failed to update context: {e}")
                        else:
                            # Fallback: Log intent if markdown content is missing
                            executed_actions.append(f"✗ Intent captured: Context update for '{epic_title}' but missing 'new_markdown_content' in JSON plan.")
                    
                    elif action_type == "send_message":
                        # Send an immediate message to a channel
                        channel_id = data.get('target_channel_id') or all_mentions[0]['channel_id']
                        message_text = data.get('message_text')
                        
                        if not message_text:
                            executed_actions.append(f"✗ Skipped send_message: Missing message_text")
                            continue
                        
                        try:
                            send_slack_message(channel_id, message_text)
                            executed_actions.append(f"✓ Message sent: {action.get('reasoning', 'Message sent')}")
                        except Exception as e:
                            executed_actions.append(f"✗ Failed to send message: {e}")
                    
                    elif action_type == "draft_reply":
                        # Draft a reply but don't send it automatically - just show it
                        message_text = data.get('message_text')
                        
                        if not message_text:
                            executed_actions.append(f"✗ Skipped draft_reply: Missing message_text")
                            continue
                        
                        print(f"\n{'='*80}")
                        print("📝 DRAFTED REPLY")
                        print(f"{'='*80}")
                        print(message_text)
                        print(f"{'='*80}\n")
                        
                        send_now = input("Send this reply now? [y/n]: ").strip().lower()
                        if send_now == 'y':
                            try:
                                channel_id = data.get('target_channel_id') or all_mentions[0]['channel_id']
                                send_slack_message(channel_id, message_text)
                                executed_actions.append(f"✓ Reply sent: {action.get('reasoning', 'Reply sent')}")
                            except Exception as e:
                                executed_actions.append(f"✗ Failed to send reply: {e}")
                        else:
                            executed_actions.append(f"ℹ️  Draft saved (not sent): {action.get('reasoning', 'Reply draft')}")
                        
                    else:
                        executed_actions.append(f"✗ Unknown action type in plan: {action_type}")
                        
                except Exception as e:
                    executed_actions.append(f"✗ Error during execution of {action_type}: {e}")
            
            if executed_actions:
                print("\nExecution Results:")
                for action in executed_actions:
                    print(f"  {action}")
            else:
                print("\nNo automated actions executed.")
        else:
            print("✗ Actions cancelled by user.")
            
    except Exception as e:
        print(f"Error during analysis: {e}")




def run_post_intro(channel_id: str):
    """
    Posts an introductory message to the specified Slack channel.
    """
    if not channel_id:
        print("Error: --channel argument is required for post-intro mode.")
        return

    intro_message = (
        "Hello team! :wave:\n\n"
        "I'm the *PM Context Agent*. I'll be passively monitoring this channel to keep our project context documentation updated "
        "and help streamline status checks.\n\n"
        "My goal is to reduce manual status reporting and help us catch risks early. "
        "Feel free to ping me or Mohit if you have any questions!"
    )
    
    print(f"Posting intro message to channel {channel_id}...")
    try:
        send_slack_message(channel_id, intro_message)
        print("Message posted successfully.")
    except Exception as e:
        print(f"Failed to post intro message: {e}")

def main():
    parser = argparse.ArgumentParser(description="PM CLI Tool")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Sync command
    sync_parser = subparsers.add_parser("sync", help="Check for drift between Context and Slack")
    sync_parser.add_argument("--channels", nargs='+', help="List of Slack Channel IDs to analyze")
    sync_parser.add_argument("--todo-sync", action="store_true", help="Include Slack Self-To-Dos in analysis")

    # Chat command
    chat_parser = subparsers.add_parser("chat", help="Start the interactive Personal Assistant")

    # Post Intro command
    intro_parser = subparsers.add_parser("post-intro", help="Post an introductory message to a Slack channel")
    intro_parser.add_argument("--channel", help="Slack Channel ID to post to", required=True)
    
    # Process Mentions command (NEW - Intelligent Command Processing)
    mentions_parser = subparsers.add_parser("process-mentions", help="Process bot mentions and execute intelligent commands")
    mentions_parser.add_argument("--channels", nargs='+', help="List of Slack Channel IDs to check for mentions", required=True)

    args = parser.parse_args()
    
    try:
        manager = ClientManager()
    except ValueError as e:
        print(f"Error initializing client: {e}")
        sys.exit(1)

    if args.command == "sync":
        run_sync_mode(manager, args.channels, args.todo_sync)
    elif args.command == "chat":
        run_chat_mode(manager)
    elif args.command == "post-intro":
        run_post_intro(args.channel)
    elif args.command == "process-mentions":
        run_process_mentions(manager, args.channels)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
