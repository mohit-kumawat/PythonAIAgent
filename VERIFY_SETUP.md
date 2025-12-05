# Slack Bot Setup Verification Guide

This guide will help you verify all your Slack IDs are correct.

---

## Step 1: Find Your User ID (Mohit's ID)

### Method 1: From Slack Desktop/Web
1. Click on your **profile picture** (top right)
2. Click **"Profile"**
3. Click the **three dots** (More)
4. Click **"Copy member ID"**
5. Paste it somewhere - it should look like: `U07FDMFFM5F`

### Method 2: From Any Message You Sent
1. Right-click on any message you sent
2. Click **"Copy link"**
3. The link will look like: `https://yourworkspace.slack.com/archives/C123/p1234567890?thread_ts=1234567890&cid=C123`
4. Your User ID is NOT in the link - use Method 1 instead

### Method 3: Using Python (Easiest!)
Run this command in your terminal:

```bash
cd /Users/mohitkumawat/PythonAIAgent
source .venv/bin/activate
python check_slack_setup.py
```

This will show you all the IDs!

---

## Step 2: Find The Bot's User ID

### Method 1: From Slack
1. In Slack, click on **"The Real PM"** bot name
2. Click **"View full profile"**
3. Look for **"Member ID"** or click the three dots → **"Copy member ID"**
4. It should look like: `U0A1J73B8JH` (starts with **U**, not A)

### Method 2: From a Message Where You Mentioned the Bot
1. In Slack, find a message where you mentioned `@The Real PM`
2. Right-click on the message
3. Click **"Copy link"**
4. Open the link in a browser
5. In the browser, right-click on the page → **"Inspect"** (or press F12)
6. Press `Ctrl+F` (or `Cmd+F` on Mac) and search for: `<@U`
7. You'll see something like: `<@U0A1J73B8JH>`
8. That's your bot's User ID!

### Method 3: Check the Raw Message (Advanced)
When you mention the bot, Slack stores it as `<@U0A1J73B8JH>` in the message text.

---

## Step 3: Verify Your Current Settings

Check your `.env` file:

```bash
cat /Users/mohitkumawat/PythonAIAgent/.env
```

You should see:
```
SLACK_USER_ID="U07FDMFFM5F"        ← Your (Mohit's) User ID
SLACK_BOT_USER_ID="U0A1J73B8JH"    ← The bot's User ID (starts with U)
```

---

## Step 4: Run the Verification Script

I've created a script to check everything. Run:

```bash
cd /Users/mohitkumawat/PythonAIAgent
source .venv/bin/activate
python check_slack_setup.py
```

This will show:
- ✅ Your Slack connection status
- ✅ Your User ID
- ✅ The Bot's User ID
- ✅ Available channels
- ✅ Whether the bot can access them

---

## Step 5: Test with Debug Mode

Run this command to see exactly what's happening:

```bash
python main.py process-mentions --channels C07FMAQ3485
```

Look for these lines in the output:
```
Authorized user: U07FDMFFM5F    ← Should match YOUR User ID
Bot user: U0A1J73B8JH           ← Should match the BOT's User ID

[DEBUG] Message 1: <@U0A1J73B8JH> ...  ← This shows the bot was mentioned
```

---

## Common Issues & Solutions

### Issue 1: Bot Sends Refusal Message

**Symptom:** Bot says "I only accept commands from my designated Project Manager, Mohit"

**Cause:** The message was sent by someone else, OR your `SLACK_USER_ID` is wrong

**Solution:**
1. Verify your User ID using Step 1 above
2. Update `.env` file with the correct ID
3. Make sure YOU are the one sending the message (not someone else)

### Issue 2: "No mentions found"

**Symptom:** Bot says "No mentions from authorized user (Mohit) found"

**Cause:** The `SLACK_BOT_USER_ID` is wrong

**Solution:**
1. Verify the bot's User ID using Step 2 above
2. Update `.env` file with the correct ID
3. Make sure it starts with `U`, not `A`

### Issue 3: "not_in_channel" error

**Symptom:** Bot says it can't access the channel

**Solution:**
1. Go to the Slack channel
2. Type: `/invite @The Real PM`
3. Press Enter

---

## Quick Verification Checklist

- [ ] My User ID starts with `U` (e.g., `U07FDMFFM5F`)
- [ ] Bot User ID starts with `U` (e.g., `U0A1J73B8JH`)
- [ ] Both IDs are in the `.env` file
- [ ] The bot is invited to the channel (type `/invite @The Real PM`)
- [ ] I am the one sending the message (not someone else)
- [ ] The message mentions `@The Real PM`

---

## Expected Output (Success)

When everything is correct, you should see:

```
Processing mentions across channels...
Authorized user: U07FDMFFM5F
Bot user: U0A1J73B8JH

🔍 Checking channel: C07FMAQ3485

[DEBUG] Found 7 total messages in channel C07FMAQ3485
[DEBUG] Looking for mentions of user: <@U0A1J73B8JH>
[DEBUG] Found 2 messages with mentions

Found 2 authorized mention(s). Analyzing...

================================================================================
AGENT ANALYSIS
================================================================================
[AI analysis of your messages]
```

---

## Need Help?

If you're still having issues, run:

```bash
python check_slack_setup.py
```

And share the output with me!
