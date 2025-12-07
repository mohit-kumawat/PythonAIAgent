# Quick Reference: Enhanced Mention Detection

## What Gets Detected? 🔍

✅ Direct bot mentions: `@The Real PM`  
✅ Direct user mentions: `@Mohit`  
✅ Keyword: `mohit` (case-insensitive)  
✅ Phrase: `the real pm` (case-insensitive)  

**Time Window**: Last 24 hours (1 day) for full conversation context  

## Quick Commands

```bash
# Process mentions across channels
python main.py process-mentions --channels C08JF2UFCR1

# Test the detection
python test_enhanced_mentions.py

# Check your setup
python check_slack_setup.py
```

## Approval Options

When the AI proposes actions:

- **`y`** → Execute all actions
- **`n`** → Cancel everything  
- **`u`** → Edit mode (delete/modify individual actions)

## Update Mode Commands

- `delete 2` → Remove action #2
- `edit 1` → Modify action #1
- `done` → Finish editing, execute
- `cancel` → Abort everything

## Example Triggers

| Message | Detected? | Why |
|---------|-----------|-----|
| "@The Real PM schedule a meeting" | ✅ Yes | Bot mention |
| "@Mohit can you help?" | ✅ Yes | User mention |
| "Hey mohit, quick question" | ✅ Yes | Keyword "mohit" |
| "Ask the real pm about this" | ✅ Yes | Phrase "the real pm" |
| "The project is on track" | ❌ No | No triggers |

## Security

- ✅ Only **your messages** are processed for commands
- ✅ Other users get a polite refusal message
- ✅ Bot ignores its own messages
- ✅ Past-time reminders are skipped

## Required .env Variables

```bash
SLACK_BOT_TOKEN=xoxb-...
SLACK_BOT_USER_ID=U123456789
SLACK_USER_ID=U987654321
```

## Common Issues

**No messages found?**
→ Run `/invite @The Real PM` in the channel

**Wrong user ID?**
→ Check with `python check_slack_setup.py`

**Bot not responding?**
→ Verify bot permissions: `channels:history`, `chat:write`
