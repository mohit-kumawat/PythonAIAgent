# Slack Bot Permissions Required for PM Agent

## Required OAuth Scopes

### Bot Token Scopes (for SLACK_BOT_TOKEN)
The following scopes are REQUIRED for the PM Agent to function:

1. **channels:history** - Read messages from public channels
2. **channels:read** - View basic channel information
3. **chat:write** - Send messages as the bot
4. **chat:write.public** - Send messages to channels the bot isn't a member of
5. **users:read** - View people in the workspace
6. **im:history** - Read direct messages (for self-todo feature)
7. **im:read** - View direct message information
8. **im:write** - Send direct messages

### For Scheduled Messages (CRITICAL for Reminders)
9. **chat:write.customize** - Send messages with customized username/icon (optional)

## How to Update Permissions

### Step 1: Go to Slack App Settings
1. Visit: https://api.slack.com/apps
2. Select your app: "The Real PM" (or whatever you named it)

### Step 2: Add OAuth Scopes
1. Click "OAuth & Permissions" in the left sidebar
2. Scroll to "Scopes" section
3. Under "Bot Token Scopes", add the scopes listed above
4. Click "Add an OAuth Scope" for each one

### Step 3: Reinstall the App
1. Scroll to top of "OAuth & Permissions" page
2. Click "Reinstall to Workspace"
3. Review permissions and click "Allow"

### Step 4: Copy New Token
1. After reinstalling, copy the "Bot User OAuth Token"
2. It starts with `xoxb-`
3. Update your `.env` file:
   ```
   SLACK_BOT_TOKEN="xoxb-YOUR-NEW-TOKEN-HERE"
   ```

### Step 5: Get User IDs
You also need to set these in `.env`:

**Your User ID (SLACK_USER_ID):**
1. In Slack, click your profile picture
2. Click "Profile"
3. Click the three dots (More)
4. Click "Copy member ID"
5. Paste in `.env`: `SLACK_USER_ID="U123456789"`

**Bot User ID (SLACK_BOT_USER_ID):**
1. In Slack App settings, go to "Basic Information"
2. Scroll to "App Credentials"
3. Copy the "App ID" or find "Bot User ID" in OAuth settings
4. Paste in `.env`: `SLACK_BOT_USER_ID="U987654321"`

## Testing Permissions

Run this command to test if permissions are working:
```bash
python3 -c "
from slack_sdk import WebClient
import os
from dotenv import load_dotenv

load_dotenv()
client = WebClient(token=os.environ['SLACK_BOT_TOKEN'])

# Test basic auth
auth = client.auth_test()
print(f'✓ Connected as: {auth[\"user\"]}')
print(f'✓ Bot User ID: {auth[\"user_id\"]}')
print(f'✓ Team: {auth[\"team\"]}')

# Test if we can schedule messages
try:
    # This will fail but shows if permission exists
    client.chat_scheduleMessage(channel='test', text='test', post_at=1)
except Exception as e:
    if 'channel_not_found' in str(e):
        print('✓ chat.scheduleMessage permission: OK')
    elif 'missing_scope' in str(e):
        print('✗ Missing scope for scheduling messages!')
        print(f'  Error: {e}')
    else:
        print(f'✓ Scheduling API accessible (error: {e})')
"
```

## Common Issues

### Issue 1: "not_in_channel" error
**Solution:** Invite the bot to the channel:
```
/invite @The Real PM
```

### Issue 2: "missing_scope" error
**Solution:** Add the missing scope in app settings and reinstall

### Issue 3: Token starts with "xoxp-" instead of "xoxb-"
**Problem:** You're using a User Token instead of Bot Token
**Solution:** Use the "Bot User OAuth Token" from OAuth & Permissions page

### Issue 4: Scheduled messages not working
**Requirement:** The `chat:write` scope includes scheduling
**Note:** Scheduled messages require the bot to be in the channel OR have `chat:write.public` scope

## Current Status Check

Run this to see what your current token can do:
```bash
python3 main.py post-intro --channel YOUR_CHANNEL_ID
```

If this works, your basic permissions are OK.
If you get errors, check the error message for which scope is missing.
