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
from state_manager import update_section
from slack_tools import read_slack_messages, get_self_todo, send_slack_message
from email_tools import read_recent_emails, send_email
from client_manager import ClientManager

# Load environment variables
load_dotenv()

def run_sync_mode(manager: ClientManager, channel_id: str):
    """
    Executes the 'sync' mode: checks for drift and optionally updates context.
    Handles API key rotation on quota errors.
    """
    if not channel_id:
        print("Error: --channel argument is required for sync mode.")
        return

    print(f"Analyzing drift between Context and Slack (Channel: {channel_id})...")
    
    client = manager.get_client()
    max_retries = len(manager.keys)
    attempts = 0
    
    while attempts < max_retries:
        try:
            result = analyze_drift(client, channel_id)
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
    
    suggested_update = result.get('suggested_update_to_doc')
    if suggested_update:
        print(f"Suggested Update:\n{suggested_update}")

    if result.get('status_change_detected'):
        print("\n-----------------------")
        apply = input("Do you want to apply this update to context.md? [y/n]: ").strip().lower()
        
        if apply == 'y':
            print("\nWhich section should this go into?")
            print("1. Critical Status")
            print("2. Release Plan")
            print("3. Action Items")
            
            section_choice = input("Enter section number (1, 2, or 3): ").strip()
            
            section_map = {
                "1": "1. Critical Status",
                "2": "2. Release Plan",
                "3": "3. Action Items"
            }
            
            section_title = section_map.get(section_choice)
            
            if section_title:
                try:
                    update_section(section_title, suggested_update)
                    print(f"Context updated successfully in section '{section_title}'.")
                except Exception as e:
                    print(f"Failed to update context: {e}")
            else:
                print("Invalid section choice. Update aborted.")
        else:
            print("Update skipped.")
    else:
        print("No status change detected. Context is up to date.")

def run_chat_mode(manager: ClientManager):
    """
    Executes the 'chat' mode: interactive assistant loop.
    """
    model = "gemini-2.0-flash"
    
    # Define the tools
    tools = [
        read_slack_messages,
        get_self_todo,
        send_slack_message,
        read_recent_emails,
        send_email
    ]

    client = manager.get_client()

    def create_chat(cli):
        return cli.chats.create(
            model=model,
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
                """
            )
        )

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

def main():
    parser = argparse.ArgumentParser(description="PM CLI Tool")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Sync command
    sync_parser = subparsers.add_parser("sync", help="Check for drift between Context and Slack")
    sync_parser.add_argument("--channel", help="Slack Channel ID to analyze", required=True)

    # Chat command
    chat_parser = subparsers.add_parser("chat", help="Start the interactive Personal Assistant")

    args = parser.parse_args()
    
    try:
        manager = ClientManager()
    except ValueError as e:
        print(f"Error initializing client: {e}")
        sys.exit(1)

    if args.command == "sync":
        run_sync_mode(manager, args.channel)
    elif args.command == "chat":
        run_chat_mode(manager)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
