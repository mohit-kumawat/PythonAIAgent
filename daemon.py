import os
import sys
import json
import time
import schedule
from datetime import datetime
import pytz
from dotenv import load_dotenv
from google.genai import types

# Import existing modules
from client_manager import ClientManager
from state_manager import read_context, update_section
from slack_tools import get_messages_mentions, send_slack_message, schedule_slack_message
from command_processor import create_reminder_message

# Import new modules
from memory_manager import get_memory_manager
from proactive_engine import ProactiveEngine
from email_tools import send_email_summary
from slack_polls import post_slack_poll
from calendar_tools import add_calendar_event

# Shared State Paths
SERVER_STATE_DIR = "server_state"
PENDING_ACTIONS_FILE = os.path.join(SERVER_STATE_DIR, "pending_actions.json")
STATUS_FILE = os.path.join(SERVER_STATE_DIR, "status.json")
LOG_FILE = os.path.join(SERVER_STATE_DIR, "agent_log.txt")

# Ensure state directory exists
os.makedirs(SERVER_STATE_DIR, exist_ok=True)

load_dotenv()

# Initialize memory manager
memory = get_memory_manager()

def log(message: str):
    """Writes to the shared log file and stdout."""
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted_msg = f"[{timestamp}] {message}"
        print(formatted_msg)
        with open(LOG_FILE, "a") as f:
            f.write(formatted_msg + "\n")
    except Exception as e:
        print(f"Log error: {e}")

def update_status(status: str, detail: str = ""):
    """Updates the agent's current status."""
    try:
        data = {
            "status": status,
            "detail": detail,
            "last_updated": datetime.now().isoformat()
        }
        with open(STATUS_FILE, "w") as f:
            json.dump(data, f)
    except Exception as e:
        log(f"Error updating status: {e}")

def get_pending_actions() -> list:
    try:
        if not os.path.exists(PENDING_ACTIONS_FILE):
            return []
        with open(PENDING_ACTIONS_FILE, "r") as f:
            content = f.read().strip()
            if not content: return []
            return json.loads(content)
    except Exception as e:
        log(f"Error reading pending actions: {e}")
        return []

def save_pending_actions(actions: list):
    try:
        with open(PENDING_ACTIONS_FILE, "w") as f:
            json.dump(actions, f, indent=2)
    except Exception as e:
        log(f"Error saving pending actions: {e}")

# JSON Schema is now enforced at generation time - no extraction needed
def parse_json_response(text: str) -> list:
    """Parse JSON response from schema-enforced generation."""
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError as e:
        log(f"JSON parsing error (should not happen with schema): {e}")
        return []

def check_mentions_job(manager: ClientManager, channel_ids: list):
    """
    Periodic job to check Slack mentions and generate action plans.
    Adds proposed actions to pending_actions.json.
    """
    update_status("THINKING", "Checking Slack mentions...")
    log("Starting mention check cycle...")
    
    bot_user_id = os.environ.get("SLACK_BOT_USER_ID")
    authorized_user_id = os.environ.get("SLACK_USER_ID")
    
    # 1. Collect Mentions
    all_mentions = []
    search_keywords = ["mohit", "the real pm"]
    
    for channel_id in channel_ids:
        try:
            # Check bot mentions
            msgs = get_messages_mentions(channel_id, bot_user_id, days=0.5, include_keywords=search_keywords)
            # Check user mentions
            user_msgs = get_messages_mentions(channel_id, authorized_user_id, days=0.5)
            
            # Combine
            joined = msgs + user_msgs
            for msg in joined:
                msg['channel'] = channel_id
                msg['channel_id'] = channel_id  # Keep both for compatibility
                
                # CRITICAL: Skip bot's own messages FIRST
                if msg.get('user') == bot_user_id:
                    continue
                
                # Filter authorized & valid
                if msg.get('user') == authorized_user_id:
                    all_mentions.append(msg)
        except Exception as e:
            log(f"Error checking channel {channel_id}: {e}")

    # Deduplicate by timestamp
    unique_mentions_map = {m['ts']: m for m in all_mentions} 
    unique_mentions = list(unique_mentions_map.values())
    
    if not unique_mentions:
        log("No new relevant mentions found.")
        update_status("IDLE", "Last check: No mentions")
        return

    log(f"Found {len(unique_mentions)} mentions. analyzing...")
    
    # 2. Analyze with LLM
    try:
        context_text = read_context()
        # mentions_text moved down after filtering
        current_time = datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%Y-%m-%d %H:%M:%S %Z')

        # Filter 1: Exclude already processed messages (Persistent Check)
        # Filter 2: Exclude messages FROM the bot itself
        bot_id = os.environ.get("SLACK_BOT_USER_ID")
        
        new_mentions = []
        for m in unique_mentions:
            # Skip if already processed (Persistent DB Check)
            if memory.is_message_processed(m['ts']):
                continue
            
            # Skip if from the bot itself (prevent infinite loops)
            if bot_id and m.get('user') == bot_id:
                log(f"Skipping own message: {m['ts']}")
                memory.add_processed_message(m['ts'], m.get('channel', '')) 
                continue
                
            new_mentions.append(m)
        
        if not new_mentions:
            log("No new un-processed mentions.")
            update_status("IDLE", "No new mentions")
            return

        # Filter out threads where bot has already replied (unless it's a NEW direct question)
        from slack_tools import has_bot_replied_in_thread
        bot_id = os.environ.get("SLACK_BOT_USER_ID")
        
        final_mentions = []
        for m in new_mentions:
            thread_ts = m.get('thread_ts') or m.get('ts')  # Use message ts if not in a thread
            channel = m.get('channel', '')
            
            # If this is a threaded message and bot already replied, skip it
            if thread_ts and thread_ts != m.get('ts'):  # It's a reply in a thread
                if has_bot_replied_in_thread(channel, thread_ts, bot_id):
                    log(f"Skipping message in thread {thread_ts} - bot already replied")
                    memory.add_processed_message(m['ts'], channel)
                    continue
            
            final_mentions.append(m)
        
        if not final_mentions:
            log("No new mentions requiring response (bot already replied in threads)")
            return

        # Double check: Ensure we haven't already replied to this THREAD in the last few seconds
        # (Race condition prevention for rapid mentions)
        filtered_mentions = []
        for m in final_mentions:  # FIXED: Use final_mentions, not new_mentions
            ts = m['ts']
            if memory.is_message_processed(ts): # Check again right before processing
                 continue
            filtered_mentions.append(m)
            
        if not filtered_mentions:
             return

        # ENHANCEMENT: Fetch full thread context for each mention
        # This allows the AI to see ALL messages in the thread, including resolution messages
        from slack_tools import get_thread_context
        
        enriched_mentions = []
        for m in filtered_mentions:
            thread_ts = m.get('thread_ts') or m.get('ts')
            channel = m.get('channel', '')
            
            # Get full thread context if this is a threaded message
            if thread_ts:
                thread_messages = get_thread_context(channel, thread_ts)
                m['thread_context'] = thread_messages
                log(f"Fetched {len(thread_messages)} messages from thread {thread_ts}")
            else:
                m['thread_context'] = [m]  # Just the single message if not in a thread
            
            enriched_mentions.append(m)

        mentions_text = json.dumps(enriched_mentions, indent=2, default=str)
        
        # Mark as processed immediately to prevent double-processing during long runs
        for m in filtered_mentions:
            memory.add_processed_message(m['ts'], m.get('channel', ''))
        
        # Define JSON Schema for structured output (RELIABILITY UPGRADE)
        action_schema = {
            "type": "OBJECT",
            "properties": {
                "thought_process": {
                    "type": "STRING", 
                    "description": "Analysis of the request, context check, and decision making process."
                },
                "actions": {
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "action_type": {
                                "type": "STRING",
                                "enum": ["schedule_reminder", "send_message", "update_context_task", "draft_reply", 
                                        "send_email_summary", "post_slack_poll", "add_calendar_event"]
                            },
                            "reasoning": {"type": "STRING"},
                            "confidence": {"type": "NUMBER"},
                            "severity": {"type": "STRING", "enum": ["low", "medium", "high"]},
                            "trigger_user_id": {"type": "STRING"},
                            "data": {
                                "type": "OBJECT",
                                "properties": {
                                    "target_channel_id": {"type": "STRING"},
                                    "target_user_ids": {"type": "ARRAY", "items": {"type": "STRING"}},
                                    "message_text": {"type": "STRING"},
                                    "thread_ts": {"type": "STRING"},
                                    "time_iso": {"type": "STRING"},
                                    "epic_title": {"type": "STRING"},
                                    "new_status": {"type": "STRING"},
                                    "new_owner": {"type": "STRING"},
                                    "new_markdown_content": {"type": "STRING"},
                                    "question": {"type": "STRING"},
                                    "options": {"type": "ARRAY", "items": {"type": "STRING"}},
                                    "summary": {"type": "STRING"},
                                    "start_time": {"type": "STRING"},
                                    "end_time": {"type": "STRING"},
                                    "description": {"type": "STRING"},
                                    "attendees": {"type": "ARRAY", "items": {"type": "STRING"}},
                                    "recipient": {"type": "STRING"},
                                    "period": {"type": "STRING"}
                                }
                            }
                        },
                        "required": ["action_type", "reasoning", "data"]
                    }
                }
            },
            "required": ["thought_process", "actions"]
        }
        
        prompt = f"""You are The Real PM agent (Daemon Mode).
        
        Current Time: {current_time}
        Context: {context_text}
        
        TASK:
        1. **ANALYZE**: Read the messages and the full 'thread_context'.
        2. **THINK**: Use the 'thought_process' field to write out your plan.
           - User Intent: What do they want?
           - Context Check: Do I already know the answer in 'Context'?
           - Tool Selection: What tool do I need? (e.g., send_message to ask someone, schedule_reminder to follow up).
        3. **ACT**: Generate the 'actions' array.
        
        Messages: {mentions_text}
        
        USER DIRECTORY:
        - {os.environ.get("SLACK_USER_ID")}: Mohit (Project Manager) - AUTHORIZED for all actions
        - {bot_user_id}: You (The Real PM)
        
        CRITICAL RULES:
        1. **ALWAYS INCLUDE trigger_user_id**: For EVERY action, you MUST set trigger_user_id to the user ID who sent the triggering message. This is REQUIRED for authorization. Extract the 'user' field from the message.
        2. **NEVER ASK QUESTIONS TO THE USER WHO JUST ASKED YOU A QUESTION**: If Mohit asks you something, DO NOT generate a send_message action asking Mohit for clarification. Instead, provide the best answer you can based on available context, or state that you need more information in your reply.
        3. **DO NOT CREATE CIRCULAR CONVERSATIONS**: Never send a message back to the same user/channel that triggered this analysis asking them to clarify their own question.
        4. **Think First**: If you need to "check with" someone OTHER than the person who asked, you MUST generate a `send_message` action to that other person.
        5. **Context First**: Always check the provided Context text before asking users for info.
        6. **No Hallucinations**: Do not make up User IDs. Use <@USER_ID> only if known or parsed from the message.
        7. **Reply in Thread**: When responding to a message, always use the same thread_ts to keep conversations organized.
        
        
        TOOLS AVAILABLE:
        - `send_message`: Send immediate text to a channel or user (use 'draft_reply' for direct responses to the triggering user).
        - `draft_reply`: Generate a direct reply to the user who asked the question (preferred for answering questions).
        - `schedule_reminder`: Schedule a message for the future.
        - `update_context_task`: Update the project status/tasks.
        - `post_slack_poll`: Create a voting poll. DO NOT send a separate confirmation message - the poll itself is the confirmation. Use confidence >= 0.9 for straightforward poll requests.
          Example poll data:
          {{
            "action_type": "post_slack_poll",
            "trigger_user_id": "U07FDMFFM5F",
            "confidence": 0.95,
            "reasoning": "Creating poll as requested",
            "data": {{
              "target_channel_id": "C08JF2UFCR1",
              "question": "Who is ready for writing blog today?",
              "options": ["Option_1", "Option_2", "Option_3"]
            }}
          }}
        - `add_calendar_event`: Schedule a meeting.
        
        IMPORTANT: Every action MUST have trigger_user_id set to the user who sent the message (extract from message 'user' field).
        
        CONFIDENCE GUIDELINES:
        - Simple, clear requests (polls, reminders): confidence >= 0.9
        - Moderate complexity (context updates): confidence >= 0.8
        - Complex or ambiguous: confidence < 0.8
        
        NOTE: When creating polls, reminders, or calendar events, DO NOT generate a separate send_message action to confirm. The action itself is the confirmation.
        """
        
        client = manager.get_client()
        
        # Use native JSON schema enforcement
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=action_schema
            )
        )
        
        # Parse Object Response
        response_data = json.loads(response.text)
        log(f"🧠 AGENT THOUGHTS: {response_data.get('thought_process', 'No thoughts provided')}")
        new_actions = response_data.get('actions', [])
        
        # CRITICAL VALIDATION: Filter out self-questioning actions
        # Identify the triggering user/channel from the messages
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
                    log(f"⚠️ BLOCKED self-questioning action: '{message_text[:50]}...' to {target_channel}")
                    log(f"   Triggering users: {triggering_users}, channels: {triggering_channels}")
                    continue  # Skip this action
                
                # RULE 2: Don't ask Mohit to clarify his own questions
                mohit_id = os.environ.get('SLACK_USER_ID')
                if mohit_id and target_channel == mohit_id and is_question:
                    # Check if Mohit was the one who asked
                    if mohit_id in triggering_users:
                        log(f"⚠️ BLOCKED asking Mohit to clarify his own question: '{message_text[:50]}...'")
                        continue  # Skip this action
                
                # RULE 3: Don't send messages that mention/tag the bot itself with actual Slack tags
                # Only block actual Slack tags like <@U123BOT>, not plain text mentions
                bot_id = os.environ.get('SLACK_BOT_USER_ID')
                if bot_id:
                    # Check if message contains an actual Slack tag of the bot
                    if f'<@{bot_id}>' in message_text:
                        log(f"⚠️ BLOCKED message that tags the bot itself: '{message_text[:50]}...'")
                        continue  # Skip this action
                
                # RULE 4: Ensure thread_ts is preserved for threaded conversations
                # If the original message had a thread_ts, the reply MUST include it
                if not data.get('thread_ts'):
                    # Try to infer from the triggering message
                    for m in filtered_mentions:
                        if m.get('channel') == target_channel:
                            inferred_thread_ts = m.get('thread_ts') or m.get('ts')
                            if inferred_thread_ts:
                                data['thread_ts'] = inferred_thread_ts
                                log(f"📎 Auto-added thread_ts: {inferred_thread_ts}")
                                break
            
            # Action passed validation
            validated_actions.append(action)
        
        new_actions = validated_actions

        
        if new_actions:
            # 3. Append to Pending Queue
            current_queue = get_pending_actions()
            
            for action in new_actions:
                action['id'] = f"{int(time.time()*1000)}_{len(current_queue)}"
                action['created_at'] = datetime.now().isoformat()
                
                # AUTONOMY LOGIC:
                # 1. Replies: Auto-approve if confident (Responsive)
                # 2. Tasks: Auto-approve ONLY if commanded by the Authorized User (Mohit)
                
                confidence = float(action.get('confidence', 0.5))
                severity = action.get('severity', 'medium').lower()
                atype = action.get('action_type')
                
                # Get the triggering user ID (from LLM or data)
                trigger_user = action.get('trigger_user_id') or action.get('data', {}).get('trigger_user_id')
                
                # FALLBACK: If AI didn't include trigger_user_id, extract from triggering messages
                if not trigger_user and filtered_mentions:
                    # Use the first triggering user (most recent mention)
                    trigger_user = filtered_mentions[0].get('user')
                    if trigger_user:
                        action['trigger_user_id'] = trigger_user
                        log(f"🔧 Auto-extracted trigger_user_id: {trigger_user}")
                
                authorized_user = os.environ.get('SLACK_USER_ID')
                is_authorized = (trigger_user == authorized_user) if authorized_user else False
                
                # DEBUG LOGGING
                log(f"📋 Action {action['id']}: type={atype}, confidence={confidence}, trigger_user={trigger_user}, authorized={is_authorized}")

                if atype in ['send_message', 'draft_reply']:
                     # Direct replies are safe if confident
                     if confidence > 0.7:
                         action['status'] = 'APPROVED'
                     else:
                         action['status'] = 'PENDING'
                
                elif atype in ['schedule_reminder', 'update_context_task', 'add_calendar_event', 'send_email_summary']:
                     # Critical tasks: STRICTLY authorized user only
                     if is_authorized and confidence > 0.85:
                         action['status'] = 'APPROVED'
                         log(f"Auto-approving authorized task {action['id']} from {trigger_user}")

                     else:
                         action['status'] = 'PENDING'
                         if not is_authorized:
                             log(f"Held unauthorized task {action['id']} from {trigger_user} (Auth: {authorized_user})")
                
                elif atype == 'post_slack_poll':
                     # Polls are low-risk, lower threshold
                     if is_authorized and confidence > 0.75:
                         action['status'] = 'APPROVED'
                         log(f"Auto-approving poll {action['id']} from {trigger_user}")
                     else:
                         action['status'] = 'PENDING'
                         if not is_authorized:
                             log(f"Held unauthorized poll {action['id']} from {trigger_user} (Auth: {authorized_user})")

                
                else:
                    # Default for unknown types
                    action['status'] = 'PENDING'
                
                current_queue.append(action)
            
            save_pending_actions(current_queue)
            log(f"Added {len(new_actions)} actions to the queue.")
        else:
            log("No actions generated from analysis.")

    except Exception as e:
        log(f"AI Analysis failed: {e}")
    
    update_status("IDLE", f"Waiting. Queue size: {len(get_pending_actions())}")


def run_proactive_check_job(channel_ids: list):
    """
    Periodic job to run proactive checks and add suggestions to queue.
    """
    log("Running proactive check...")
    update_status("THINKING", "Running proactive analysis...")
    
    try:
        context_text = read_context()
        engine = ProactiveEngine(memory)
        
        # Collect recent messages for blocker detection
        all_messages = []
        bot_user_id = os.environ.get("SLACK_BOT_USER_ID")
        for channel_id in channel_ids:
            try:
                msgs = get_messages_mentions(channel_id, bot_user_id, days=1)
                all_messages.extend(msgs)
            except:
                pass
        
        # Get proactive suggestions
        suggestions = engine.get_proactive_suggestions(context_text, all_messages)
        
        if suggestions:
            current_queue = get_pending_actions()
            
            # Check for duplicate proactive suggestions
            existing_ids = {a.get('id', '') for a in current_queue}
            
            new_suggestions = []
            for s in suggestions:
                if s['id'] not in existing_ids:
                    new_suggestions.append(s)
            
            if new_suggestions:
                current_queue.extend(new_suggestions)
                save_pending_actions(current_queue)
                log(f"Added {len(new_suggestions)} proactive suggestions to queue.")
            else:
                log("No new proactive suggestions (already in queue).")
        else:
            log("No proactive suggestions generated.")
    
    except Exception as e:
        log(f"Proactive check failed: {e}")
    
    update_status("IDLE", f"Proactive check complete. Queue: {len(get_pending_actions())}")


def cleanup_queue_job():
    """
    Periodic job to clean up executed/rejected actions from the JSON queue.
    Keep the file size manageable.
    """
    try:
        queue = get_pending_actions()
        if not queue:
            return

        now = datetime.now()
        active_queue = []
        cleaned_count = 0

        for action in queue:
            # Keep PENDING actions unless they are very old (> 3 days)
            if action.get('status') == 'PENDING':
                created_at = datetime.fromisoformat(action.get('created_at'))
                if (now - created_at).days < 3:
                     active_queue.append(action)
                else:
                    cleaned_count += 1
            
            # Keep finished actions for only 1 hour (for UI feedback)
            elif action.get('status') in ['EXECUTED', 'FAILED', 'REJECTED_LOGGED']:
                # If we have an executed_at time, check it
                ts = action.get('executed_at') or action.get('created_at')
                try:
                    action_time = datetime.fromisoformat(ts)
                    # If older than 1 hour, remove (they are already in SQLite history)
                    if (now - action_time).total_seconds() < 3600:
                        active_queue.append(action)
                    else:
                        cleaned_count += 1
                except:
                    cleaned_count += 1
            else:
                active_queue.append(action)
        
        if cleaned_count > 0:
            save_pending_actions(active_queue)
            log(f"Cleaned up {cleaned_count} old/completed actions from queue.")

    except Exception as e:
        log(f"Cleanup job failed: {e}")


def run_weekly_report_job():
    """
    Weekly job to generate and optionally send a status report.
    """
    engine = ProactiveEngine(memory)
    
    if not engine.should_send_weekly_report():
        return
    
    log("Generating weekly report...")
    
    try:
        context_text = read_context()
        report = engine.generate_status_report(context_text, period="weekly")
        report_text = engine.generate_report_text(report)
        
        # Add report as a pending action for approval
        action = {
            "id": f"weekly-report-{int(time.time())}",
            "action_type": "weekly_report",
            "reasoning": "📊 Weekly status report is ready. Approve to send via email.",
            "status": "PENDING",
            "created_at": datetime.now().isoformat(),
            "is_proactive": True,
            "data": {
                "report_text": report_text,
                "report_data": report
            }
        }
        
        current_queue = get_pending_actions()
        current_queue.append(action)
        save_pending_actions(current_queue)
        
        log("Weekly report queued for approval.")
        
        # Log to memory
        memory.log_action_execution(
            action_id=action["id"],
            action_type="weekly_report",
            status="PENDING",
            reasoning=action["reasoning"]
        )
        
    except Exception as e:
        log(f"Weekly report generation failed: {e}")

def run_daily_status_job(type="morning"):
    """
    Generates a daily status update (Morning or Evening).
    Morning (10 AM IST): Focus on plan for the day, blockers, and immediate actions.
    Evening (6 PM IST): Focus on progress made, what's pending, and plan for tomorrow.
    
    Uses persistence to prevent duplicate sends on restart.
    """
    # Check if we already sent this report today
    ist = pytz.timezone('Asia/Kolkata')
    now_ist = datetime.now(ist)
    today_date = now_ist.strftime('%Y-%m-%d')
    report_key = f"daily_{type}_{today_date}"
    
    # Check memory to see if we already sent this report
    if memory.has_sent_report(report_key):
        log(f"Daily {type} report already sent today ({today_date}), skipping.")
        return
    
    log(f"Generating daily {type} report for {today_date}...")
    try:
        context_text = read_context()
        engine = ProactiveEngine(memory)
        
        # Custom prompt based on time of day
        if type == "morning":
            prompt_directive = "Generate a 'Morning Standup' update. Focus on: 1. Key goals for today. 2. Critical blockers to resolve. 3. Call to action for the team."
        else:
            prompt_directive = "Generate an 'End of Day' update. Focus on: 1. Progress made today. 2. What is still pending/blocked. 3. Quick look ahead for tomorrow."
            
        report = engine.generate_status_report(context_text, period="daily", custom_directive=prompt_directive)
        report_text = engine.generate_report_text(report)
        
        # Add as auto-approved action if confident, or pending if complex
        action = {
            "id": f"daily-{type}-{int(time.time())}",
            "action_type": "send_message",
            "reasoning": f"📢 Daily {type.capitalize()} Update",
            "status": "APPROVED", # Auto-approve daily updates
            "created_at": datetime.now().isoformat(),
            "confidence": 0.95,
            "severity": "low",
            "data": {
                "message_text": report_text,
                "target_channel_id": os.environ.get('SLACK_CHANNELS', '').split()[0] # Send to first channel (Main)
            }
        }
        
        current_queue = get_pending_actions()
        current_queue.append(action)
        save_pending_actions(current_queue)
        
        # Mark as sent in memory
        memory.mark_report_sent(report_key)
        log(f"Daily {type} report queued and marked as sent for {today_date}.")

        
    except Exception as e:
        log(f"Daily {type} report generation failed: {e}")

def check_and_send_missed_reports():
    """
    Check if today's reports were missed and send them now.
    This runs on startup to catch up if server was down during scheduled time.
    """
    ist = pytz.timezone('Asia/Kolkata')
    now_ist = datetime.now(ist)
    today_date = now_ist.strftime('%Y-%m-%d')
    current_hour = now_ist.hour
    
    log(f"Checking for missed reports... Current time: {now_ist.strftime('%H:%M IST')}")
    
    # Check morning report (should have been sent by 10 AM)
    if current_hour >= 10:
        morning_key = f"daily_morning_{today_date}"
        if not memory.has_sent_report(morning_key):
            log(f"⚠️ Morning report for {today_date} was missed! Sending now...")
            run_daily_status_job(type="morning")
        else:
            log(f"✅ Morning report for {today_date} already sent.")
    
    # Check evening report (should have been sent by 6 PM)
    if current_hour >= 18:
        evening_key = f"daily_evening_{today_date}"
        if not memory.has_sent_report(evening_key):
            log(f"⚠️ Evening report for {today_date} was missed! Sending now...")
            run_daily_status_job(type="evening")
        else:
            log(f"✅ Evening report for {today_date} already sent.")
    
    if current_hour < 10:
        log(f"ℹ️ Too early for morning report (current: {current_hour}:00, scheduled: 10:00)")
    elif current_hour < 18:
        log(f"ℹ️ Too early for evening report (current: {current_hour}:00, scheduled: 18:00)")


def execute_approved_actions_job():
    """
    Continuous job to execute actions marked as APPROVED/EXECUTING.
    """
    queue = get_pending_actions()
    dirty = False
    
    for action in queue:
        if action.get('status') == 'APPROVED':
            log(f"Executing action: {action.get('reasoning')}")
            update_status("EXECUTING", action.get('reasoning'))
            
            try:
                # Execution Logic (Extended with new action types)
                atype = action.get('action_type')
                data = action.get('data', {})
                result = None
                
                if atype == 'schedule_reminder':
                    msg = create_reminder_message({"action": action['reasoning']}, data.get('target_user_ids', []))
                    
                    target_channel = data.get('target_channel_id') or data.get('channel_id') or data.get('channel')
                    if not target_channel:
                         raise KeyError("target_channel_id/channel_id/channel not found")
                         
                    time_iso = data.get('time_iso') or data.get('reminder_time') or data.get('time')
                    if not time_iso:
                         raise KeyError("time_iso/reminder_time/time not found")

                    result = schedule_slack_message(target_channel, msg, time_iso)
                    
                elif atype == 'send_message' or atype == 'draft_reply':
                    target_channel = (data.get('target_channel_id') or 
                                    data.get('channel_id') or 
                                    data.get('channel') or 
                                    os.environ.get('SLACK_USER_ID')) # Fallback to user DM if channel missing? No, safer to fail if no channel.
                                    
                    msg_text = (data.get('message_text') or 
                              data.get('text') or 
                              data.get('message') or 
                              data.get('reply_text'))
                    
                    if not target_channel:
                         # Fallback: Try to infer from thread_ts? No, need channel.
                         # Last resort: use the channel from the action metadata if available (it isn't currently stored outside data)
                        raise KeyError(f"Missing channel ID. Available keys: {list(data.keys())}")
                    
                    if not msg_text:
                        raise KeyError(f"Missing message text. Available keys: {list(data.keys())}")
                    
                    # POST-PROCESSING: Remove self-tags
                    bot_id = os.environ.get("SLACK_BOT_USER_ID", "")
                    if bot_id:
                        msg_text = msg_text.replace(f"<@{bot_id}>", "")
                    
                    # Remove "The Real PM" text if it appears as a name
                    msg_text = msg_text.replace("@The Real PM", "")

                    # FINAL CHECK: Do not send message if target channel is Self (Bot ID)
                    if bot_id and target_channel == bot_id:
                         log(f"Skipping action {action['id']}: Target channel is self ({bot_id})")
                         result = "Skipped (Self-Target)"
                    else:
                        send_slack_message(target_channel, msg_text, thread_ts=data.get('thread_ts'))
                        result = "Message sent"
                    
                elif atype == 'update_context_task':
                    if 'new_markdown_content' in data:
                        update_section("2. Active Epics & Tasks", data['new_markdown_content'])
                    result = "Context updated"
                
                # New action types
                elif atype == 'send_email_summary':
                    context_text = read_context()
                    result = send_email_summary(
                        recipient=data.get('recipient', os.environ.get('USER_EMAIL', '')),
                        context_md=context_text,
                        period=data.get('period', 'weekly')
                    )
                
                elif atype == 'post_slack_poll':
                    # Get channel ID (support both field names)
                    poll_channel = data.get('channel_id') or data.get('target_channel_id')
                    if not poll_channel:
                        raise KeyError("Missing channel_id or target_channel_id for poll")
                    
                    result = post_slack_poll(
                        channel_id=poll_channel,
                        question=data['question'],
                        options=data.get('options', [])
                    )
                
                elif atype == 'add_calendar_event':
                    result = add_calendar_event(
                        summary=data['summary'],
                        start_time=data['start_time'],
                        end_time=data.get('end_time'),
                        description=data.get('description'),
                        attendees=data.get('attendees')
                    )
                
                elif atype == 'weekly_report':
                    # Send the pre-generated report via email
                    recipient = os.environ.get('USER_EMAIL', '')
                    if recipient:
                        from email_tools import send_email
                        send_email(
                            to=recipient,
                            subject=f"📊 Weekly PM Report - {datetime.now().strftime('%Y-%m-%d')}",
                            body=data.get('report_text', '')
                        )
                        result = f"Report sent to {recipient}"
                    else:
                        result = "No USER_EMAIL configured, report not sent"
                
                elif atype in ['proactive_followup', 'proactive_blocker_alert']:
                    # Proactive actions just get acknowledged
                    result = "Proactive suggestion acknowledged"
                
                action['status'] = 'EXECUTED'
                action['executed_at'] = datetime.now().isoformat()
                action['result'] = str(result) if result else "Success"
                log(f"Action {action['id']} executed successfully.")
                
                # Log to memory
                memory.log_action_execution(
                    action_id=action['id'],
                    action_type=atype,
                    status="SUCCESS",
                    reasoning=action.get('reasoning'),
                    action_data=data,
                    result=str(result)
                )
                memory.log_decision(atype, True, action.get('reasoning'), data)
                
            except Exception as e:
                action['status'] = 'FAILED'
                action['error'] = str(e)
                log(f"Action {action['id']} failed: {e}")
                
                # Log failure to memory
                memory.log_action_execution(
                    action_id=action['id'],
                    action_type=action.get('action_type'),
                    status="FAILED",
                    reasoning=action.get('reasoning'),
                    action_data=data,
                    result=str(e)
                )
            
            dirty = True
        
        elif action.get('status') == 'REJECTED':
            # Log rejected actions to memory for learning
            memory.log_decision(
                action.get('action_type'),
                False,
                action.get('reasoning'),
                action.get('data')
            )
            action['status'] = 'REJECTED_LOGGED'
            dirty = True
            
    if dirty:
        save_pending_actions(queue)
        update_status("IDLE", "Execution cycle complete")

def start_daemon(channel_ids: list):
    """Start the daemon scheduler loop (blocking)"""
    try:
        manager = ClientManager()
    except Exception as e:
        log(f"Failed to init ClientManager: {e}")
        return

    log("Daemon started. Monitoring channels: " + str(channel_ids))
    log(f"Memory database: {memory.db_path}")
    log(f"Current Server Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S %Z')}")
    
    # Schedule jobs
    # USER REQUEST: Run frequently for responsiveness (every 30 seconds)
    schedule.every(30).seconds.do(check_mentions_job, manager=manager, channel_ids=channel_ids)
    schedule.every(10).seconds.do(execute_approved_actions_job)
    
    # Proactive jobs
    schedule.every(1).hour.do(run_proactive_check_job, channel_ids=channel_ids)
    schedule.every().friday.at("17:00").do(run_weekly_report_job)
    
    # Daily Reports (10 AM IST = 04:30 UTC, 6 PM IST = 12:30 UTC)
    # Render servers run on UTC, so we need to convert IST to UTC
    schedule.every().day.at("04:30").do(run_daily_status_job, type="morning")  # 10:00 AM IST
    schedule.every().day.at("12:30").do(run_daily_status_job, type="evening")  # 6:00 PM IST
    
    schedule.every(1).hour.do(cleanup_queue_job)
    
    # Run once immediately
    check_mentions_job(manager, channel_ids)
    cleanup_queue_job()
    
    # Check for missed reports and send them if needed
    check_and_send_missed_reports()
    
    log("📅 Scheduled jobs:")
    log("   - Check mentions: Every 30 seconds")
    log("   - Execute actions: Every 10 seconds")
    log("   - Proactive check: Every 1 hour")
    log("   - Morning report: 04:30 UTC (10:00 AM IST)")
    log("   - Evening report: 12:30 UTC (6:00 PM IST)")
    log("   - Weekly report: Friday 17:00 UTC")
    log("   - Cleanup: Every 1 hour")
    
    while True:
        schedule.run_pending()
        time.sleep(1)

def main():
    if len(sys.argv) < 2:
        print("Usage: python daemon.py <channel_id1> [channel_id2 ...]")
        return

    channel_ids = sys.argv[1:]
    start_daemon(channel_ids)

if __name__ == "__main__":
    main()

