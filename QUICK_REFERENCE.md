# Quick Reference Guide: The Real PM Agent

## 🚀 Quick Start

### Run the Agent

```bash
# Process mentions (intelligent command execution)
python main.py process-mentions --channels C08JF2UFCR1

# Sync mode (drift detection)
python main.py sync --channels C08JF2UFCR1

# Chat mode (interactive assistant)
python main.py chat

# Post intro message
python main.py post-intro --channel C08JF2UFCR1
```

---

## 📝 Slack Commands

### Reminders
```
@The Real PM remind me tomorrow at 2pm to review PR
@The Real PM remind @umang on Friday to submit report
@The Real PM set a reminder for next Monday at 10am to check deployment
```

### Task Updates
```
@The Real PM Umang finished the Home Page Update
@The Real PM assign Proactive Question Flow to Badal
@The Real PM mark Home Page Update as Ready for Testing
```

### Status Queries
```
@The Real PM what's the status of Home Page Update?
@The Real PM what are the current blockers?
@The Real PM show me all high-risk items
```

---

## 🔧 Configuration

### Required Environment Variables (.env)
```bash
# Gemini API Keys (comma-separated for rotation)
GOOGLE_API_KEY=key1,key2,key3

# Slack Configuration
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_USER_ID=U07FDMFFM5F  # Mohit's user ID (authorized user)
SLACK_BOT_USER_ID=U123456   # Bot's user ID

# Email Configuration (optional)
GMAIL_ADDRESS=your-email@gmail.com
GMAIL_APP_PASSWORD=your-app-password
```

### Channel IDs
Find your Slack channel ID:
1. Right-click channel → View channel details
2. Scroll to bottom → Copy channel ID
3. Example: `C08JF2UFCR1`

---

## 📂 File Structure

```
PythonAIAgent/
├── main.py                    # Main entry point
├── drift_detector.py          # Drift detection logic
├── state_manager.py           # Context.md management
├── slack_tools.py             # Slack API integration
├── command_processor.py       # Legacy regex parser (fallback)
├── email_tools.py             # Email integration
├── client_manager.py          # API key rotation
├── agent_instruction.txt      # System instruction for LLM
├── context.md                 # Project context (DO NOT EDIT HEADER)
├── .env                       # Environment variables
├── requirements.txt           # Python dependencies
├── ARCHITECTURE.md            # Architecture diagram
├── REFACTORING_SUMMARY.md     # Detailed refactoring notes
└── IMPLEMENTATION_COMPLETE.md # Implementation summary
```

---

## 🎯 Key Functions

### extract_json_block(text: str) → list
Extracts JSON from LLM response.
```python
# Usage
actions = extract_json_block(response.text)
# Returns: [{"action_type": "...", "data": {...}}, ...]
```

### update_section(section_title, new_content, append=False)
Updates context.md sections.
```python
# Replace section
update_section("1. Overall Health & Risk Register", new_content)

# Append to section
update_section("4. Raw Notes (Append Only)", note, append=True)
```

### schedule_slack_message(channel_id, text, scheduled_time)
Schedules a Slack message.
```python
result = schedule_slack_message(
    channel_id="C08JF2UFCR1",
    text="⏰ Reminder: Review PR",
    scheduled_time="2025-12-06T14:00:00"
)
```

---

## 🧪 Testing Checklist

### ✅ Pre-Deployment
- [ ] Environment variables set in `.env`
- [ ] Bot added to Slack channels
- [ ] `SLACK_USER_ID` is Mohit's ID
- [ ] `SLACK_BOT_USER_ID` is bot's ID
- [ ] API keys valid and working

### ✅ Functional Tests
- [ ] Reminder scheduling works
- [ ] Context updates append to Raw Notes
- [ ] Drift detection uses new sections
- [ ] JSON extraction handles various formats
- [ ] Unauthorized users get refusal message

### ✅ Edge Cases
- [ ] No mentions found → graceful message
- [ ] Invalid JSON → warning + no execution
- [ ] Missing channel_id → fallback to first mention
- [ ] API quota exceeded → key rotation

---

## 🐛 Troubleshooting

### "Could not extract structured action plan"
**Cause:** LLM didn't output JSON in expected format  
**Fix:** Check LLM response, ensure prompt includes example JSON

### "Skipped reminder: Missing channel_id or time_iso"
**Cause:** LLM didn't extract required fields  
**Fix:** Improve prompt clarity, provide more context

### "not_in_channel" error
**Cause:** Bot not added to channel  
**Fix:** In Slack, type `/invite @The Real PM` in that channel

### "RESOURCE_EXHAUSTED" error
**Cause:** API quota exceeded  
**Fix:** Add more API keys to `.env` (comma-separated)

---

## 📊 Action Types

### schedule_reminder
Schedules a Slack message for future delivery.

**Required Fields:**
- `target_channel_id` (string)
- `time_iso` (ISO 8601 datetime)

**Optional Fields:**
- `target_user_ids` (list of user IDs)

**Example:**
```json
{
  "action_type": "schedule_reminder",
  "reasoning": "Remind Mohit to take update from Pravin",
  "data": {
    "target_channel_id": "C08JF2UFCR1",
    "target_user_ids": ["U07FDMFFM5F"],
    "time_iso": "2025-12-06T11:30:00"
  }
}
```

### update_context_task
Updates context.md with task information.

**Required Fields:**
- `epic_title` (string, must match epic in context.md)

**Optional Fields:**
- `new_status` (string)
- `new_owner` (string)

**Example:**
```json
{
  "action_type": "update_context_task",
  "reasoning": "Mark Home Page Update as complete",
  "data": {
    "epic_title": "Home Page Update",
    "new_status": "Completed",
    "new_owner": "Umang"
  }
}
```

---

## 🔐 Security

### Authorization
- **Only Mohit** (`SLACK_USER_ID`) can issue commands
- Unauthorized users receive polite refusal message
- Bot's own messages (join notifications) are ignored

### Message Filtering
- Only last **7 days** of messages processed
- Prevents processing old/stale commands
- Reduces API costs and noise

### API Key Rotation
- Multiple keys supported (comma-separated)
- Automatic rotation on quota errors
- Graceful degradation if all keys exhausted

---

## 📈 Monitoring

### Success Indicators
- ✅ "💡 Found N structured actions ready for execution"
- ✅ "✓ Scheduled reminder: ... for [time]"
- ✅ "✓ Updated context: ..."

### Warning Indicators
- ⚠️ "Warning: Could not extract structured action plan"
- ⚠️ "Skipping channel: Bot is not a member"
- ⚠️ "Quota exceeded. Rotating key..."

### Error Indicators
- ✗ "Failed to schedule: [error]"
- ✗ "Error executing [action_type]: [error]"
- ✗ "Unknown action type: [type]"

---

## 🎓 Best Practices

### 1. Clear Commands
❌ Bad: "remind me about that thing"  
✅ Good: "remind me tomorrow at 2pm to review PR #42"

### 2. Specific Times
❌ Bad: "remind me later"  
✅ Good: "remind me on Friday at 10am"

### 3. Explicit Mentions
❌ Bad: "tell him to finish it"  
✅ Good: "@umang please finish the Home Page Update"

### 4. Context References
❌ Bad: "update the status"  
✅ Good: "mark Home Page Update as Ready for Testing"

---

## 📞 Support

### Documentation
- **Architecture:** `ARCHITECTURE.md`
- **Refactoring:** `REFACTORING_SUMMARY.md`
- **Implementation:** `IMPLEMENTATION_COMPLETE.md`

### Common Issues
1. Check `.env` configuration
2. Verify bot is in channel
3. Confirm user IDs are correct
4. Review LLM response format

### Debug Mode
Add `debug=True` to function calls:
```python
mentions = get_messages_mentions(channel_id, bot_user_id, days=7, debug=True)
```

---

**Version:** 1.0.0  
**Last Updated:** 2025-12-05 11:00 IST  
**Status:** ✅ Production Ready
