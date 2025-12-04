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
        
        # 1. Critical Status Update
        suggested_status = result.get('suggested_update_to_critical_status')
        if suggested_status:
            print("\n[Proposed Update for '1. Critical Status']")
            print(suggested_status)
            apply = input("Apply this update? [y/n]: ").strip().lower()
            if apply == 'y':
                try:
                    update_section("1. Critical Status", suggested_status)
                    print("Critical Status updated.")
                except Exception as e:
                    print(f"Failed to update Critical Status: {e}")
            else:
                print("Skipped Critical Status update.")

        # 2. Action Items Update
        suggested_actions = result.get('suggested_update_to_action_items')
        if suggested_actions:
            print("\n[Proposed Update for '3. Action Items']")
            print(suggested_actions)
            apply = input("Apply this update? [y/n]: ").strip().lower()
            if apply == 'y':
                try:
                    update_section("3. Action Items", suggested_actions)
                    print("Action Items updated.")
                except Exception as e:
                    print(f"Failed to update Action Items: {e}")
            else:
                print("Skipped Action Items update.")

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
        model="gemini-2.0-flash",
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
    Processes messages where the bot is mentioned and executes intelligent commands.
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

    print("Processing mentions across channels...")
    print(f"Authorized user: {authorized_user_id}")
    print(f"Bot user: {bot_user_id}")
    
    # Collect all mentions from all channels (already filtered to 7 days in get_messages_mentions)
    all_mentions = []
    unauthorized_mentions = []
    
    for channel_id in channel_ids:
        mentions = get_messages_mentions(channel_id, bot_user_id, days=7)
        for msg in mentions:
            msg['channel_id'] = channel_id
            
            # Separate authorized vs unauthorized mentions
            if msg.get('user') == authorized_user_id:
                all_mentions.append(msg)
            else:
                unauthorized_mentions.append(msg)
    
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
        print("No mentions from authorized user (Mohit) found in the last 7 days.")
        return
    
    print(f"\nFound {len(all_mentions)} authorized mention(s). Analyzing...")
    
    # Prepare context for AI
    context_text = read_context()
    mentions_text = json.dumps(all_mentions, indent=2, default=str)
    
    prompt = f"""You are The Real PM agent. Analyze these Slack messages where you were mentioned by Mohit.

CRITICAL RULES:
1. These messages are ONLY from Mohit (authorized user)
2. All messages are already filtered to last 7 days
3. For ANY reminder ("Remind me to..."), you MUST use schedule_slack_message tool
4. Present a clear action plan before executing

Current Project Context:
{context_text}

Mohit's Messages (last 7 days):
{mentions_text}

Identify and propose actions for:
1. **Reminders** (HIGHEST PRIORITY - use schedule_slack_message)
   - Extract: action, time, mentioned users
   - Format time as ISO datetime
   
2. **Task Assignments** ("@User is working on X")
   - Extract: user, task
   - Propose context.md update
   
3. **Direct Tasks** ("Make sure we...")
   - Extract: task, deadline
   - Propose context.md update
   
4. **Status Requests**
   - Check context.md and propose response

Present your analysis in this format:
```
ANALYSIS COMPLETE

Found Items:
1. [Type]: [Description]
   - Details: ...
   - Proposed Tool: ...
   
Proposed Actions:
✓ [Action 1]
✓ [Action 2]

Do you approve? (yes/no)
```
"""

    client = manager.get_client()
    
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=agent_instruction
            )
        )
        
        print("\n" + "="*80)
        print("AGENT ANALYSIS")
        print("="*80)
        print(response.text)
        print("="*80 + "\n")
        
        # Ask for approval
        approval = input("Do you approve the proposed actions? [y/n]: ").strip().lower()
        
        if approval == 'y':
            print("\n✓ Actions approved. Executing...")
            
            # Parse response and execute actions
            # For now, we'll use the command processor to help
            from command_processor import is_reminder_command, extract_reminder_details
            
            executed_actions = []
            for msg in all_mentions:
                msg_text = msg.get('text', '')
                
                # Check if it's a reminder
                if is_reminder_command(msg_text):
                    reminder_details = extract_reminder_details(msg_text)
                    
                    # Schedule the reminder
                    try:
                        result = schedule_slack_message(
                            channel_id=msg['channel_id'],
                            text=create_reminder_message(
                                reminder_details,
                                reminder_details['mentioned_users'] or [authorized_user_id]
                            ),
                            scheduled_time=reminder_details['parsed_time']
                        )
                        
                        if result.get('success'):
                            executed_actions.append(f"✓ Scheduled reminder for {reminder_details['time_str']}")
                        else:
                            executed_actions.append(f"✗ Failed to schedule: {result.get('error')}")
                    except Exception as e:
                        executed_actions.append(f"✗ Error scheduling reminder: {e}")
            
            if executed_actions:
                print("\nExecution Results:")
                for action in executed_actions:
                    print(f"  {action}")
            else:
                print("\nNo automated actions executed. Manual review may be needed.")
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
