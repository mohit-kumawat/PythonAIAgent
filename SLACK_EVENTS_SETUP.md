# Slack Events API Setup Guide

## Overview
This guide will help you configure Slack Events API webhooks to enable **instant responses** instead of hourly polling. This transforms your agent from a "background cron job" to a "live assistant."

## Benefits
- ⚡ **Instant Response**: Bot responds within seconds instead of waiting up to 1 hour
- 🔋 **Lower Resource Usage**: No constant polling needed
- 💬 **Better UX**: Feels like chatting with a real person

---

## Setup Steps

### 1. Deploy Your Service (if not already deployed)

Your health server must be publicly accessible. If using Render:

```bash
# Your service should already be running at:
https://your-app-name.onrender.com
```

### 2. Configure Slack App Event Subscriptions

1. Go to **https://api.slack.com/apps**
2. Select your app (e.g., "The Real PM")
3. Navigate to **Event Subscriptions** in the left sidebar
4. **Enable Events** (toggle ON)

### 3. Set Request URL

In the "Request URL" field, enter:

```
https://your-app-name.onrender.com/slack/events
```

**Important**: Slack will immediately send a verification challenge. Your server will automatically respond with the challenge token. You should see:
- ✅ "Verified" checkmark in Slack
- In your server logs: `✅ Slack URL verification successful`

### 4. Subscribe to Bot Events

Scroll down to **Subscribe to bot events** and add:

- `app_mention` - When someone mentions your bot with @The Real PM
- `message.channels` (optional) - All public channel messages
- `message.groups` (optional) - All private channel messages
- `message.im` (optional) - Direct messages to the bot

**Recommended**: Start with just `app_mention` for focused, instant responses.

### 5. Save Changes

Click **Save Changes** at the bottom of the page.

### 6. Reinstall App (if prompted)

If Slack prompts you to reinstall the app to your workspace:
1. Click **Reinstall App**
2. Authorize the new permissions

---

## Testing

### Test 1: Mention the Bot in Slack

In any channel where the bot is a member:

```
@The Real PM what's the status of the login bug?
```

**Expected behavior**:
- Your server logs show: `🔔 Slack event received: app_mention`
- Within 3-5 seconds, the bot analyzes and responds
- No waiting for the hourly cron job!

### Test 2: Check Server Logs

You should see output like:

```
[2025-12-08 15:54:26] 🔔 Slack event received: app_mention
   📨 Mention from user U07FDMFFM5F in channel C08JF2UFCR1
   💬 Message: @The Real PM what's the status...
   ⚡ Triggered immediate analysis for channel C08JF2UFCR1
```

---

## Architecture

### Before (Polling)
```
Slack Message → Wait up to 1 hour → Daemon checks → Bot responds
```

### After (Events)
```
Slack Message → Instant webhook → Daemon checks immediately → Bot responds (3-5s)
```

---

## Troubleshooting

### Issue: "URL verification failed"

**Cause**: Your server is not responding to the challenge correctly.

**Fix**:
1. Check that your server is running and publicly accessible
2. Test the health endpoint: `curl https://your-app.onrender.com/health`
3. Check server logs for errors
4. Ensure the `/slack/events` endpoint is accessible

### Issue: "Events not triggering"

**Cause**: Bot is not subscribed to the right events or not in the channel.

**Fix**:
1. Verify `app_mention` is in your subscribed events list
2. Invite the bot to the channel: `/invite @The Real PM`
3. Check that the bot has the `app_mentions:read` scope

### Issue: "Duplicate responses"

**Cause**: Both polling and events are triggering simultaneously.

**Fix**:
- The daemon's deduplication logic (via `memory.is_message_processed()`) should prevent this
- If it persists, consider reducing the polling frequency or disabling it entirely

---

## Advanced Configuration

### Disable Polling (Optional)

If you want **only** event-driven responses, edit `daemon.py`:

```python
# Comment out the hourly polling job
# schedule.every(1).hour.do(check_mentions_job, manager=manager, channel_ids=channel_ids)

# Keep the execution job (processes approved actions)
schedule.every(10).seconds.do(execute_approved_actions_job)
```

This makes your agent 100% event-driven and even more efficient.

### Add More Event Types

To respond to all messages (not just mentions):

1. In Slack App settings → Event Subscriptions
2. Add `message.channels` to bot events
3. Update `health_server.py` to handle `message` event type:

```python
if event_type in ["app_mention", "message"]:
    # Existing logic...
```

**Warning**: This will trigger on EVERY message, which may be noisy. Use filters in `daemon.py` to ignore non-command messages.

---

## Summary

| Feature | Before | After |
|---------|--------|-------|
| **Response Time** | Up to 1 hour | 3-5 seconds |
| **Trigger Method** | Cron polling | Slack webhooks |
| **Resource Usage** | Constant polling | Event-driven |
| **User Experience** | Slow, batch-like | Instant, chat-like |

✅ **You've successfully upgraded to instant, event-driven responses!**
