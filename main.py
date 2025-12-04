import os
import sys
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Import our custom tools
from slack_tools import read_slack_messages, get_self_todo, send_slack_message
from email_tools import read_recent_emails, send_email

load_dotenv()

def run_personal_assistant():
    """
    Runs the personal assistant agent.
    """
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("Error: GOOGLE_API_KEY not found.")
        return

    client = genai.Client(api_key=api_key)
    model = "gemini-2.0-flash-exp" # Using a capable model

    # Define the tools
    # The SDK allows passing the functions directly
    tools = [
        read_slack_messages,
        get_self_todo,
        send_slack_message,
        read_recent_emails,
        send_email
    ]

    # Create the chat session with tools
    chat = client.chats.create(
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

    print("Personal Assistant is ready! (Type 'quit' to exit)")
    
    while True:
        try:
            user_input = input("\nUser: ")
            if user_input.lower() in ["quit", "exit"]:
                break
            
            response = chat.send_message(user_input)
            print(f"Assistant: {response.text}")
            
            # Check for function calls and print them for debugging/visibility
            if response.candidates and response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if part.function_call:
                        print(f"[Debug] Tool used: {part.function_call.name}")
                        
        except Exception as e:
            print(f"An error occurred: {e}")

if __name__ == "__main__":
    run_personal_assistant()
