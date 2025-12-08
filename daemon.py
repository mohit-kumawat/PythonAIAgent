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

def extract_json_block(text: str) -> list:
    import re
    match = re.search(r"```json\s*\n(.*?)\n\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except:
            return []
    try:
        return json.loads(text.strip())
    except:
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
                msg['channel_id'] = channel_id
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

        # Double check: Ensure we haven't already replied to this THREAD in the last few seconds
        # (Race condition prevention for rapid mentions)
        filtered_mentions = []
        for m in new_mentions:
            ts = m['ts']
            if memory.is_message_processed(ts): # Check again right before processing
                 continue
            filtered_mentions.append(m)
            
        if not filtered_mentions:
             return

        mentions_text = json.dumps(filtered_mentions, indent=2, default=str)
        
        # Mark as processed immediately to prevent double-processing during long runs
        for m in filtered_mentions:
            memory.add_processed_message(m['ts'], m.get('channel', ''))
        
        prompt = f"""You are The Real PM agent (Daemon Mode). Analyze these Slack messages.
        
        Current Time: {current_time}
        Context: {context_text}
        Messages: {mentions_text}
        
        USER DIRECTORY (Map these IDs to names):
        - {os.environ.get("SLACK_USER_ID")}: Mohit (Project Manager/User)
        - {bot_user_id}: You (The Real PM Agent) - NEVER tag yourself in messages.
        - U0A1J73B8JH: Pravin
        - U07NJKB5HA7: Umang
        - U07FDMFFM5F: Mohit
        
        Generate a structured JSON plan of actions.
        For replies, MUST include "thread_ts" in the "data" object matching the message's "ts".
        
        CRITICAL INSTRUCTION: Include a 'confidence' score (0-1) and 'severity' (low, medium, high) for each action.
        Also include 'trigger_user_id' in the JSON (the ID of the user who caused this action).
        
        CONTEXT UPDATES:
        If the user says "I am back", "I am good", or provides a status update that contradicts the current Context (e.g. Health: Red), 
        generate an 'update_context_task' action to fix the context.
        
        If you are >0.8 confident and severity is not 'critical', the action will be auto-executed.
        
        JSON format: [{{ 
            "action_type": "...", 
            "reasoning": "...", 
            "confidence": 0.9,
            "severity": "low",
            "trigger_user_id": "U12345",
            "data": {{...}} 
        }}]
        Types: schedule_reminder, update_context_task, send_message, draft_reply, 
               send_email_summary, post_slack_poll, add_calendar_event
        
        WRITING & FORMATTING RULES:
        1. Speak naturally in first-person ("I", "We"). DO NOT refer to yourself as "The Real PM" or tag yourself.
        2. When mentioning users, ALWAYS use the <@USER_ID> format. if you only have a name, look it up in context or output plain text name.
        3. Do NOT use raw User IDs (e.g., U12345) in text without <@...> wrappers.
        4. For Reminders: Simplify the text. Instead of "Remind Mohit to check X", just use "Check X".
        """
        
        client = manager.get_client()
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        
        new_actions = extract_json_block(response.text)
        
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
                authorized_user = os.environ.get('SLACK_USER_ID')
                is_authorized = (trigger_user == authorized_user) if authorized_user else False

                if atype in ['send_message', 'draft_reply']:
                     # Direct replies are safe if confident
                     if confidence > 0.7:
                         action['status'] = 'APPROVED'
                     else:
                         action['status'] = 'PENDING'
                
                elif atype in ['schedule_reminder', 'update_context_task', 'add_calendar_event', 'post_slack_poll', 'send_email_summary']:
                     # Critical tasks: STRICTLY authorized user only
                     if is_authorized and confidence > 0.85:
                         action['status'] = 'APPROVED'
                         log(f"Auto-approving authorized task {action['id']} from {trigger_user}")
                     else:
                         action['status'] = 'PENDING'
                         if not is_authorized:
                             log(f"Held unauthorized task {action['id']} from {trigger_user} (Auth: {authorized_user})")
                
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
    Morning (10 AM): Focus on plan for the day, blockers, and immediate actions.
    Evening (6 PM): Focus on progress made, what's pending, and plan for tomorrow.
    """
    log(f"Generating daily {type} report...")
    try:
        context_text = read_context()
        
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
        log(f"Daily {type} report queued.")
        
    except Exception as e:
        log(f"Daily {type} report generation failed: {e}")


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
                    result = post_slack_poll(
                        channel_id=data['channel_id'],
                        question=data['question'],
                        options=data['options']
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

def main():
    if len(sys.argv) < 2:
        print("Usage: python daemon.py <channel_id1> [channel_id2 ...]")
        return

    channel_ids = sys.argv[1:]
    
    try:
        manager = ClientManager()
    except Exception as e:
        log(f"Failed to init ClientManager: {e}")
        return

    log("Daemon started. Monitoring channels: " + str(channel_ids))
    log(f"Memory database: {memory.db_path}")
    
    # Schedule jobs
    # Schedule jobs
    # USER REQUEST: Run hourly to prevent spam on the server
    schedule.every(1).hour.do(check_mentions_job, manager=manager, channel_ids=channel_ids)
    schedule.every(10).seconds.do(execute_approved_actions_job)
    
    # Proactive jobs
    schedule.every(1).hour.do(run_proactive_check_job, channel_ids=channel_ids)
    schedule.every().friday.at("17:00").do(run_weekly_report_job)
    
    # Daily Reports (10 AM & 6 PM)
    schedule.every().day.at("10:00").do(run_daily_status_job, type="morning")
    schedule.every().day.at("18:00").do(run_daily_status_job, type="evening")
    
    schedule.every(1).hour.do(cleanup_queue_job)
    
    # Run once immediately
    check_mentions_job(manager, channel_ids)
    cleanup_queue_job()
    
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    main()

