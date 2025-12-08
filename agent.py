#!/usr/bin/env python3
"""
Interactive AI Agent CLI
Just tell the agent what you want to do in natural language!
"""

import os
import sys
import json
from dotenv import load_dotenv
from google import genai
from google.genai import types
from client_manager import ClientManager
from slack_tools import send_slack_message, schedule_slack_message, read_slack_messages
import subprocess

# Load environment
load_dotenv()

# Channel mappings for easy reference
CHANNELS = {
    "test": "C08JF2UFCR1",
    "test channel": "C08JF2UFCR1",
    "devteam": "C07FMAQ3485",
    "dev": "C07FMAQ3485",
}

def get_channel_id(channel_name):
    """Convert channel name to ID"""
    channel_lower = channel_name.lower().strip()
    return CHANNELS.get(channel_lower, channel_name)

def create_planning_agent(client):
    """Create an agent that plans actions without executing"""
    
    # Get user info from environment
    user_name = os.environ.get("USER_NAME", "Mohit")
    user_role = os.environ.get("USER_ROLE", "Project Manager")
    
    system_instruction = f"""You are an intelligent PM Agent assistant for {user_name}, a {user_role}.

IMPORTANT CONTEXT:
- Your user is: {user_name}
- When {user_name} asks you to send messages to others, craft them in THIRD PERSON
- Example: If {user_name} says "I'm not feeling well", the message should say "{user_name} is not feeling well"
- Be professional and clear in all communications

Your job is to UNDERSTAND what the user wants and CREATE A PLAN, but NOT execute it yet.

You can help with:
1. **Send Slack messages** - Send messages to any channel
2. **Schedule messages** - Schedule messages for later  
3. **Read messages** - Read recent messages from channels
4. **Process mentions** - Check for bot mentions
5. **Verify setup** - Check Slack configuration

Channel Mappings:
- "test" or "test channel" → C08JF2UFCR1
- "devteam" or "dev" → C07FMAQ3485

MESSAGE CRAFTING RULES:
1. When {user_name} says "I am..." or "I'm...", convert to "{user_name} is..."
2. When {user_name} says "I will...", convert to "{user_name} will..."
3. Keep the message professional and clear
4. Preserve the core meaning and tone

IMPORTANT: When the user asks you to do something, respond in this EXACT format:

```
I understand you want to: [brief description]

Here's what I'll do:
ACTION: [action type - send_message/schedule_message/read_messages/run_command]
DETAILS:
  - Channel: [channel name and ID]
  - Message: [exact message text - in THIRD PERSON if notifying others]
  OR
  - Command: [exact command to run]

Is this correct? I'll execute after you approve.
```

Examples:

User: "I'm not feeling well today, tell the team in test channel"
You respond:
```
I understand you want to: Notify the team in test channel about your health

Here's what I'll do:
ACTION: send_message
DETAILS:
  - Channel: test (C08JF2UFCR1)
  - Message: "{user_name} is not feeling well today and will be working from home."

Is this correct? I'll execute after you approve.
```

User: "I am working from home, let devteam know"
You respond:
```
I understand you want to: Inform devteam about working from home

Here's what I'll do:
ACTION: send_message
DETAILS:
  - Channel: devteam (C07FMAQ3485)
  - Message: "{user_name} is working from home today."

Is this correct? I'll execute after you approve.
```

User: "Check my mentions in devteam"
You respond:
```
I understand you want to: Check for bot mentions in devteam channel

Here's what I'll do:
ACTION: run_command
DETAILS:
  - Command: python main.py process-mentions --channels C07FMAQ3485

Is this correct? I'll execute after you approve.
```

Always be clear about what you'll do before executing.
Always craft messages in third person when notifying others about {user_name}.
"""
    
    return client.chats.create(
        model="gemini-flash-latest",
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.3  # Lower temperature for more consistent formatting
        )
    )

def parse_action_plan(response_text):
    """Parse the action plan from agent response"""
    if "ACTION:" not in response_text:
        return None
    
    plan = {
        "action": None,
        "channel": None,
        "message": None,
        "command": None
    }
    
    lines = response_text.split("\n")
    for i, line in enumerate(lines):
        line = line.strip()
        
        if line.startswith("ACTION:"):
            action = line.replace("ACTION:", "").strip()
            plan["action"] = action
        
        if "Channel:" in line:
            # Extract channel ID
            if "C08JF2UFCR1" in line or "test" in line.lower():
                plan["channel"] = "C08JF2UFCR1"
            elif "C07FMAQ3485" in line or "dev" in line.lower():
                plan["channel"] = "C07FMAQ3485"
        
        if "Message:" in line:
            # Extract message (might be in quotes)
            msg = line.split("Message:", 1)[1].strip()
            msg = msg.strip('"').strip("'")
            plan["message"] = msg
        
        if "Command:" in line:
            cmd = line.split("Command:", 1)[1].strip()
            cmd = cmd.replace("`", "").strip()
            plan["command"] = cmd
    
    return plan if plan["action"] else None

def execute_action(plan):
    """Execute the planned action"""
    action = plan["action"]
    
    print(f"\n{'='*80}")
    print("EXECUTING ACTION")
    print(f"{'='*80}\n")
    
    try:
        if action == "send_message":
            channel = plan["channel"]
            message = plan["message"]
            
            if not channel or not message:
                print("❌ Missing channel or message")
                return
            
            print(f"📤 Sending message to channel {channel}...")
            print(f"💬 Message: {message}\n")
            
            send_slack_message(channel, message)
            
            print(f"\n✅ Message sent successfully!")
            
        elif action == "schedule_message":
            # TODO: Implement scheduling
            print("⚠️  Scheduling not yet implemented in this flow")
            
        elif action == "read_messages":
            channel = plan["channel"]
            if not channel:
                print("❌ Missing channel")
                return
            
            print(f"📖 Reading messages from channel {channel}...\n")
            messages = read_slack_messages(channel, limit=10)
            
            for i, msg in enumerate(messages, 1):
                print(f"{i}. {msg.get('text', '')[:100]}")
            
            print(f"\n✅ Retrieved {len(messages)} messages")
            
        elif action == "run_command":
            command = plan["command"]
            if not command:
                print("❌ Missing command")
                return
            
            print(f"🔧 Running command: {command}\n")
            
            result = subprocess.run(
                command,
                shell=True,
                cwd="/Users/mohitkumawat/PythonAIAgent",
                text=True,
                capture_output=False
            )
            
            if result.returncode == 0:
                print(f"\n✅ Command completed successfully")
            else:
                print(f"\n⚠️  Command exited with code: {result.returncode}")
        
        else:
            print(f"❌ Unknown action: {action}")
    
    except Exception as e:
        print(f"\n❌ Error executing action: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\n{'='*80}\n")

def main():
    """Main interactive loop"""
    
    print("\n" + "="*80)
    print("🤖  INTERACTIVE PM AGENT CLI")
    print("="*80)
    print("\nJust tell me what you want to do!")
    print("I'll show you my plan and ask for approval before executing.\n")
    print("Type 'quit' or 'exit' to stop.\n")
    print("Examples:")
    print("  - 'Send a message to test channel saying I'm working from home'")
    print("  - 'Check my Slack mentions in the test channel'")
    print("  - 'Read recent messages from devteam'")
    print("  - 'Verify my setup'")
    print("="*80 + "\n")
    
    # Initialize client
    try:
        manager = ClientManager()
        client = manager.get_client()
    except Exception as e:
        print(f"❌ Error initializing client: {e}")
        sys.exit(1)
    
    # Create planning agent
    agent = create_planning_agent(client)
    
    # Interactive loop
    while True:
        try:
            user_input = input("You: ").strip()
            
            if not user_input:
                continue
                
            if user_input.lower() in ["quit", "exit", "bye"]:
                print("\n👋 Goodbye!\n")
                break
            
            # Get agent's plan
            response = agent.send_message(user_input)
            response_text = response.text
            
            print(f"\nAgent:\n{response_text}\n")
            
            # Parse the action plan
            plan = parse_action_plan(response_text)
            
            if plan:
                # Ask for approval
                confirm = input("Approve and execute? (yes/no): ").strip().lower()
                
                if confirm in ["yes", "y"]:
                    execute_action(plan)
                else:
                    print("\n❌ Action cancelled.\n")
            else:
                # No action to execute, just conversation
                pass
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!\n")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}\n")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()

