# Testing Guide for Channel C08JF2UFCR1

Follow these steps to test your AI agent in the test channel.

---

## Step 1: Check if Bot is in the Channel

First, let's verify the bot can access this channel:

```bash
cd /Users/mohitkumawat/PythonAIAgent
source .venv/bin/activate
python test_mentions.py
```

**What to look for:**
- ✅ If it shows messages: Bot is in the channel
- ❌ If it shows "not_in_channel" error: Bot needs to be invited

**If you get an error:**
1. Go to Slack
2. Open channel `C08JF2UFCR1`
3. Type: `/invite @The Real PM`
4. Press Enter
5. Run the test script again

---

## Step 2: Send a Test Message

Go to Slack channel `C08JF2UFCR1` and send a test message:

### Example Test Message:

```
@The Real PM Remind me to check the deployment status tomorrow at 2pm
```

**OR**

```
@The Real PM Make sure we review the code changes by end of day.
@John is working on the frontend and @Sarah is working on the backend.
```

---

## Step 3: Run the Agent

After sending your test message, run:

```bash
python main.py process-mentions --channels C08JF2UFCR1
```

---

## Step 4: Review the Output

You should see:

```
Processing mentions across channels...
Authorized user: U07FDMFFM5F
Bot user: U0A1J73B8JH

🔍 Checking channel: C08JF2UFCR1

Found X authorized mention(s). Analyzing...

================================================================================
AGENT ANALYSIS
================================================================================
[AI analysis of your message]

Do you approve the proposed actions? [y/n]:
```

---

## Step 5: Approve or Reject

- Type `y` to approve and execute the actions
- Type `n` to cancel

---

## Expected Results:

### If you sent a reminder:
- ✅ Bot will schedule a Slack message for the specified time
- ✅ You'll receive the reminder at that time

### If you assigned tasks:
- ✅ Bot will update the `context.md` file with task assignments
- ✅ You can check the file to see the updates

---

## Troubleshooting:

### "No mentions found"
- Make sure you mentioned `@The Real PM` in your message
- Check that the message is less than 7 days old
- Verify you're the one who sent the message (not someone else)

### "not_in_channel" error
- Run: `/invite @The Real PM` in the Slack channel
- Try again

### "Unauthorized user" message
- Check your User ID in `.env` matches your actual Slack User ID
- Run `python check_slack_setup.py` to verify

---

## Quick Commands Reference:

```bash
# 1. Test if bot can see the channel
python test_mentions.py

# 2. Process mentions and execute commands
python main.py process-mentions --channels C08JF2UFCR1

# 3. Check all settings
python check_slack_setup.py
```

---

## What to Test:

1. **Simple Reminder:**
   ```
   @The Real PM Remind me to call the client tomorrow at 10am
   ```

2. **Task Assignment:**
   ```
   @The Real PM @Alice is working on the login page
   ```

3. **Multiple Actions:**
   ```
   @The Real PM Make sure we deploy by Friday.
   @Bob is handling the backend and @Carol is testing.
   Remind me to check progress tomorrow at 3pm.
   ```

---

## After Testing:

Once everything works in `C08JF2UFCR1`, you can:
- Add more channels: `python main.py process-mentions --channels C08JF2UFCR1 C07FMAQ3485`
- Set up automated runs (cron job)
- Turn off debug mode for cleaner output

---

**Ready to test? Follow the steps above!** 🚀
