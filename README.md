# PM Agent - Intelligent Project Management Assistant

## Overview
This is an intelligent PM agent that can:
- Monitor Slack channels for project updates
- Detect drift between documented context and reality
- Process natural language commands from authorized users
- Schedule reminders and manage tasks autonomously
- Update project documentation automatically

## New Features: Intelligent Command Processing

### The `process-mentions` Command
The agent can now intelligently interpret your Slack messages and execute complex commands.

**Example Message:**
```
@The Real PM Make sure we test and release the new home page of the app tomorrow 
along with the new changes which were required to launch the proactive Question flow.

@Umang Kedia is working on the home page and @Badal is working on the proactive Question flow.

Remind me to take update from @Pravin Kumar Tomorrow at 11:30 on the same.
```

**What the Agent Does:**
1. **Parses** the message to extract:
   - Tasks: "test and release new home page tomorrow"
   - Assignments: Umang → home page, Badal → proactive flow
   - Reminders: Update from Pravin at 11:30 tomorrow

2. **Proposes Actions:**
   - Schedule reminder message to @Pravin Kumar for tomorrow 11:30
   - Update context.md with new action items
   - Track assignments for status monitoring

3. **Asks for Approval** before executing anything

### Usage

```bash
# Process mentions from the last 7 days
python main.py process-mentions --channels C08JF2UFCR1 C07FMAQ3485

# The agent will:
# 1. Find all messages where it was mentioned
# 2. Analyze them for commands (only from authorized user)
# 3. Present a plan
# 4. Execute upon approval
```

### Setup Requirements

Add to your `.env` file:
```bash
SLACK_USER_ID=U123456789          # Your Slack user ID (Mohit)
SLACK_BOT_USER_ID=U987654321      # The bot's user ID
```

**How to find these IDs:**
1. Your User ID: Click your profile → "Copy member ID"
2. Bot User ID: Go to bot app settings → "App ID" section

### Security
- **Authorization**: Only commands from `SLACK_USER_ID` (Mohit) are executed
- **Approval Required**: Agent always asks before taking action
- **Time Filter**: Only processes messages from last 7 days

### Available Commands

```bash
# 1. Sync - Check drift between context and Slack
python main.py sync --channels C123 C456 --todo-sync

# 2. Chat - Interactive assistant mode
python main.py chat

# 3. Post Intro - Introduce the bot to a channel
python main.py post-intro --channel C123

# 4. Process Mentions - Intelligent command processing (NEW!)
python main.py process-mentions --channels C123 C456
```

### How It Works

1. **Message Analysis**: Uses Gemini AI with custom system instruction
2. **Command Parsing**: Regex-based extraction of tasks, assignments, reminders
3. **Time Parsing**: Natural language → ISO datetime (e.g., "tomorrow at 11:30")
4. **Scheduling**: Uses Slack's `chat.scheduleMessage` API
5. **Context Updates**: Modular section updates to context.md

### Agent Capabilities

The agent understands:
- ✅ Task assignments ("X is working on Y")
- ✅ Direct tasks ("Make sure we...")
- ✅ Reminders ("Remind me to...")
- ✅ Status requests ("What's the status of...")
- ✅ Time expressions ("tomorrow at 11:30", "next Monday")

### Example Workflow

1. **You mention the bot in Slack:**
   ```
   @The Real PM Remind me to review the PR tomorrow at 2pm
   ```

2. **Run the command:**
   ```bash
   python main.py process-mentions --channels C07FMAQ3485
   ```

3. **Agent responds:**
   ```
   Found 1 mention(s). Analyzing...
   
   --- Agent Analysis ---
   I found the following:
   1. Reminder: Review the PR
      - Scheduled for: 2025-12-06 14:00:00
   
   Proposed Actions:
   ✓ Schedule reminder message for tomorrow 2pm
   
   Do you approve? [y/n]:
   ```

4. **You approve:**
   ```
   y
   ```

5. **Tomorrow at 2pm**, you receive a Slack message:
   ```
   📋 Reminder: Review the PR
   ```

## Installation

```bash
pip install -r requirements.txt
```

## Testing

```bash
# Run all tests
python -m pytest tests/

# Run specific test
python tests/test_drift_detector.py
```