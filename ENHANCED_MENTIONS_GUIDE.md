# Enhanced Mention Detection & Auto-Reply Feature

## Overview

The agent now automatically detects and processes messages that mention you or "The Real PM" in multiple ways:

1. **Direct bot mentions**: `@The Real PM`
2. **Direct user mentions**: `@Mohit` (your Slack user ID)
3. **Keyword "mohit"**: Any message containing the word "mohit" (case-insensitive)
4. **Phrase "the real pm"**: Any message containing "the real pm" (case-insensitive)

## How It Works

### Detection Logic

The system searches across specified Slack channels for messages from the **last 24 hours** (1 day) that match any of the above criteria. This shorter timeframe ensures you get the full context of recent conversations. Messages are:

- **Deduplicated**: If a message matches multiple criteria, it's only processed once
- **Filtered by sender**: Only messages from you (Mohit) are processed for commands
- **Security-aware**: Messages from other users trigger a polite refusal message

### Message Processing Flow

```
1. Scan channels for mentions/keywords
   ↓
2. Separate authorized (Mohit) vs unauthorized users
   ↓
3. Send refusal messages to unauthorized users
   ↓
4. Analyze Mohit's messages with AI
   ↓
5. Generate structured action plan
   ↓
6. Request user approval
   ↓
7. Execute approved actions
```

## Usage

### Running the Enhanced Detection

```bash
# Process mentions across one or more channels
python main.py process-mentions --channels C08JF2UFCR1 C08JF2UFCR2

# Or use the shell script
./run_sync.sh
```

### Testing the Feature

```bash
# Run the test script to verify detection
python test_enhanced_mentions.py
```

The test script will:
- Show you what messages are being detected
- Break down detection by type (bot mentions, user mentions, keywords)
- Display sample messages found
- Help you verify the feature is working correctly

## Configuration

Ensure your `.env` file has these variables set:

```bash
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_BOT_USER_ID=U123456789  # The bot's user ID
SLACK_USER_ID=U987654321      # Your (Mohit's) user ID
```

### Finding Your User IDs

1. **Your User ID**: 
   - Click your profile in Slack
   - Click "More" → "Copy member ID"

2. **Bot User ID**:
   - Run: `python check_slack_setup.py`
   - Look for "Bot User ID" in the output

## Action Types

The AI can generate these action types based on detected messages:

### 1. Schedule Reminder
Schedules a future Slack message as a reminder.

**Example**: "Remind me tomorrow at 2pm to check with Pravin"

```json
{
  "action_type": "schedule_reminder",
  "reasoning": "Remind Mohit to check with Pravin",
  "data": {
    "target_channel_id": "C08JF2UFCR1",
    "target_user_ids": ["U07FDMFFM5F"],
    "time_iso": "2025-12-06T14:00:00"
  }
}
```

### 2. Send Message
Sends an immediate message to a channel.

**Example**: "Tell the team the release is delayed"

```json
{
  "action_type": "send_message",
  "reasoning": "Notify team about release delay",
  "data": {
    "target_channel_id": "C08JF2UFCR1",
    "message_text": "Team, the release is delayed to next week."
  }
}
```

### 3. Draft Reply
Drafts a reply for your approval before sending.

**Example**: Someone asks you a question in a channel

```json
{
  "action_type": "draft_reply",
  "reasoning": "Draft response to Alice's question",
  "data": {
    "target_channel_id": "C08JF2UFCR1",
    "message_text": "Hi Alice, I'll have that ready by EOD."
  }
}
```

### 4. Update Context
Updates the project context (context.md) with task status changes.

**Example**: "Mark the home page update as done"

```json
{
  "action_type": "update_context_task",
  "reasoning": "Update Home Page Update status to Done",
  "data": {
    "epic_title": "Home Page Update",
    "new_status": "Done",
    "new_markdown_content": "..."
  }
}
```

## Interactive Approval

After the AI analyzes messages and proposes actions, you can:

- **`y`** - Approve and execute all actions
- **`n`** - Cancel all actions
- **`u`** - Update mode (edit or delete individual actions)

### Update Mode Commands

- `delete <number>` - Remove an action from the plan
- `edit <number>` - Modify an action's message or reasoning
- `done` - Finish editing and proceed to execution
- `cancel` - Cancel all actions

## Security Features

### Authorized User Only

- Only messages from your Slack user ID are processed for commands
- Messages from other users trigger an automatic refusal message:

> "I appreciate the mention, but I only accept commands from my designated Project Manager, Mohit. Please reach out to him directly for any requests."

### Bot Self-Filtering

- The bot ignores its own messages (e.g., join notifications)
- Prevents infinite loops and unnecessary processing

### Time Validation

- Reminders scheduled for past times are automatically skipped
- Duplicate reminders (already in context.md) are avoided
- Only messages from the last 24 hours are processed

## Examples

### Example 1: Someone mentions "mohit" in a channel

**Message**: "Hey team, mohit asked us to prioritize the login bug"

**Result**: 
- Message is detected (contains "mohit")
- If from you: Processed for potential actions
- If from someone else: Refusal message sent

### Example 2: Direct mention of the bot

**Message**: "@The Real PM remind me to follow up with design team tomorrow at 10am"

**Result**:
- Message detected (bot mention)
- AI analyzes and proposes: `schedule_reminder` action
- You approve → Reminder scheduled

### Example 3: Mixed detection

**Message**: "@Mohit can you ask the real pm to schedule a sync?"

**Result**:
- Detected via: user mention (@Mohit) AND keyword ("the real pm")
- Counted once (deduplicated)
- Processed if from you

## Troubleshooting

### No messages detected

1. Verify bot is in the channel: `/invite @The Real PM`
2. Check user IDs are correct in `.env`
3. Run test script: `python test_enhanced_mentions.py`
4. Enable debug mode in the code (set `debug=True`)

### Messages from wrong users

- Verify `SLACK_USER_ID` in `.env` matches your actual Slack user ID
- Check the output shows correct "Authorized user" ID

### Bot not responding

1. Check bot token is valid: `python check_slack_setup.py`
2. Verify bot has `chat:write` and `channels:history` permissions
3. Ensure bot is a member of the target channels

## Advanced Configuration

### Customizing Keywords

Edit `main.py` line ~238 to add/modify keywords:

```python
search_keywords = ["mohit", "the real pm", "your-custom-keyword"]
```

### Changing Time Window

Modify the `days` parameter (default: 1 day for full conversation context):

```python
bot_mentions = get_messages_mentions(
    channel_id, 
    bot_user_id, 
    days=2,  # Look back 2 days instead of 1
    debug=False,
    include_keywords=search_keywords
)
```

### Customizing Refusal Message

Edit `main.py` line ~281:

```python
refusal_message = "Your custom refusal message here"
```

## Best Practices

1. **Run regularly**: Set up a cron job to check for mentions periodically
2. **Review before approving**: Always review the AI's proposed actions
3. **Use update mode**: Edit actions if the AI misunderstood intent
4. **Monitor context.md**: Keep your project context up to date
5. **Test in private channels first**: Verify behavior before using in public channels

## Integration with Existing Features

This feature works alongside:

- **Sync mode**: `python main.py sync --channels ...`
- **Chat mode**: `python main.py chat`
- **Post intro**: `python main.py post-intro --channel ...`

All modes share the same configuration and security model.
