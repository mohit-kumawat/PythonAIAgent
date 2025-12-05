# How to Run Your AI Agent - Simple Guide

This guide will help you run your Python AI Agent step by step, even if you're not familiar with tech!

## What This Agent Does

Your AI agent is a smart assistant that:
- 📨 Reads your Slack messages
- ✅ Manages your to-do list
- ⏰ Sets reminders for you
- 🤖 Responds to commands automatically

---

## Step 1: Open Terminal

**On Mac:**
1. Press `Command (⌘) + Space` on your keyboard
2. Type "Terminal"
3. Press `Enter`

You'll see a window with text - this is your Terminal!

---

## Step 2: Go to Your Project Folder

In the Terminal, type this command and press `Enter`:

```bash
cd /Users/mohitkumawat/PythonAIAgent
```

This tells your computer to open the folder where your AI agent lives.

---

## Step 3: Activate the Virtual Environment

A virtual environment is like a special workspace for your project. Type this and press `Enter`:

```bash
source .venv/bin/activate
```

✅ **Success Check:** You should see `(.venv)` appear at the beginning of your Terminal line.

---

## Step 4: Run Your AI Agent

Now you can run your agent! Here are the different ways to use it:

### Option A: Sync Mode (Check Slack Messages)

This reads your Slack channels and checks for updates:

```bash
python main.py sync --channels C08JF2UFCR1 C07FMAQ3485 --todo-sync
```

**OR use the easy shortcut:**

```bash
./run_sync.sh
```

### Option B: Process Mentions (Smart Command Mode)

This looks for messages where you mentioned the bot and executes commands:

```bash
python main.py process-mentions --channels C08JF2UFCR1 C07FMAQ3485
```

### Option C: Chat Mode (Talk to Your Agent)

This lets you chat with your AI agent directly in the Terminal:

```bash
python main.py chat
```

Type your questions or commands, and the agent will respond!

---

## Step 5: Stop the Agent

When you're done:
- Press `Control + C` on your keyboard to stop the agent
- Type `deactivate` and press `Enter` to exit the virtual environment

---

## Common Issues & Solutions

### Problem: "not_in_channel" Warning ⚠️

**Good news!** The bot now handles this gracefully. If you see this warning:

```
⚠️  Skipping channel C08JF2UFCR1: Bot is not a member of this channel
    To fix: In Slack, type '/invite @The Real PM' in that channel
```

This means the bot is working fine, but it can't access that specific channel. The bot will continue checking other channels.

**To fix (optional):**

1. Open Slack
2. Go to the channel mentioned in the warning
3. Type:
   ```
   /invite @The Real PM
   ```
4. Press Enter

The bot will now be able to read that channel on the next run!

---

### Problem: "SSL: CERTIFICATE_VERIFY_FAILED" Error

This is common on Mac with Python 3.13. I've already fixed the code, but you need to install the certificate package:

**Solution:**
```bash
pip install certifi
```

Then try running your command again!

### Problem: "Virtual environment not found"

**Solution:**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Problem: "Permission denied" when running run_sync.sh

**Solution:**
```bash
chmod +x run_sync.sh
./run_sync.sh
```

### Problem: "Module not found" error

**Solution:**
```bash
pip install -r requirements.txt
```

---

## Quick Reference Card

Copy and paste these commands when you need them:

```bash
# 1. Go to project folder
cd /Users/mohitkumawat/PythonAIAgent

# 2. Activate environment
source .venv/bin/activate

# 3. Run the agent (choose one):
./run_sync.sh                                                    # Easy sync
python main.py process-mentions --channels C08JF2UFCR1 C07FMAQ3485  # Smart commands
python main.py chat                                              # Chat mode

# 4. Stop and exit
# Press Control + C, then:
deactivate
```

---

## What Each Command Does

| Command | What It Does |
|---------|-------------|
| `sync` | Checks Slack for new messages and updates your to-do list |
| `process-mentions` | Finds messages where you mentioned the bot and executes commands |
| `chat` | Opens an interactive chat with your AI agent |
| `post-intro` | Introduces the bot to a new Slack channel |

---

## Example: Setting a Reminder

1. In Slack, mention your bot:
   ```
   @The Real PM Remind me to call John tomorrow at 3pm
   ```

2. In Terminal, run:
   ```bash
   python main.py process-mentions --channels C08JF2UFCR1
   ```

3. The agent will ask for approval - type `y` and press `Enter`

4. Tomorrow at 3pm, you'll get a Slack reminder! ⏰

---

## Need Help?

- Check the main `README.md` file for more details
- Look at `SLACK_PERMISSIONS.md` for Slack setup info
- All your settings are in the `.env` file

---

**Pro Tip:** You can schedule this to run automatically using Mac's built-in scheduler (cron), but that's for later! For now, just run it manually when you need it.
