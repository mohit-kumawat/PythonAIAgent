# Deploying to Render - Background Worker Setup

## Overview
This Python AI Agent runs as a **Background Worker** on Render, which means:
- ✅ Runs continuously 24/7
- ✅ Auto-restarts if it crashes
- ✅ Auto-restarts after server reboots
- ✅ Auto-checks Slack every hour
- ✅ Auto-executes scheduled tasks
- ✅ Cheaper than Web Service (can use free tier)

## Deployment Steps

### Option 1: Using render.yaml (Recommended)

1. **Push your code to GitHub** (if not already done)
   ```bash
   git add .
   git commit -m "Configure for Render Background Worker"
   git push
   ```

2. **Create New Service on Render**
   - Go to [Render Dashboard](https://dashboard.render.com/)
   - Click "New +" → "Blueprint"
   - Connect your GitHub repository
   - Render will automatically detect `render.yaml` and configure everything

3. **Set Environment Variables** (in Render Dashboard)
   - `SLACK_BOT_TOKEN` - Your Slack bot token
   - `SLACK_USER_TOKEN` - Your Slack user token
   - `SLACK_BOT_USER_ID` - Your bot's user ID
   - `SLACK_USER_ID` - Your user ID (Mohit)
   - `GOOGLE_API_KEY` - Your Google AI API key
   - `USER_EMAIL` - Your email (for reports)
   - `SMTP_USER` - Your SMTP email
   - `SMTP_PASSWORD` - Your SMTP password

4. **Deploy**
   - Click "Apply" and Render will deploy your service
   - It will auto-deploy on every git push

### Option 2: Manual Setup

1. **Create New Service**
   - Go to Render Dashboard
   - Click "New +" → "Background Worker"
   - Connect your GitHub repository
   - Select "Docker" as runtime

2. **Configure Service**
   - **Name**: `python-ai-agent`
   - **Runtime**: Docker
   - **Docker Command**: Leave empty (uses Dockerfile CMD)
   - **Plan**: Starter (or Free if available)

3. **Add Environment Variables** (same as above)

4. **Deploy**

## What Happens After Deployment

### Automatic Operations
- **Every 1 hour**: Checks Slack for mentions
- **Every 10 seconds**: Executes approved actions
- **Every 1 hour**: Runs proactive checks
- **Daily at 10:00 AM**: Sends morning report
- **Daily at 6:00 PM**: Sends evening report
- **Every Friday at 5:00 PM**: Sends weekly report

### Auto-Restart Behavior
- ✅ If daemon crashes → Render auto-restarts it
- ✅ If server reboots → Render auto-restarts it
- ✅ If you deploy new code → Render auto-restarts with new version
- ❌ If you manually stop the service → Stays stopped until you start it

## Monitoring Your Service

### View Logs
1. Go to Render Dashboard
2. Click on your service
3. Click "Logs" tab
4. You'll see:
   - `[timestamp] Daemon started. Monitoring channels: ...`
   - `[timestamp] Starting mention check cycle...`
   - `[timestamp] Found X mentions. analyzing...`
   - `[timestamp] Action executed successfully.`

### Check Status
- **Running**: Green indicator in Render dashboard
- **Deploying**: Yellow indicator
- **Failed**: Red indicator (check logs)

## Troubleshooting

### Service Keeps Crashing
1. Check logs for error messages
2. Verify all environment variables are set correctly
3. Check if API keys are valid

### Not Responding to Slack Messages
1. Verify `SLACK_BOT_USER_ID` and `SLACK_USER_ID` are correct
2. Check if bot has permissions in the channels
3. Look for "Skipping own message" in logs (means it's working correctly)

### Actions Not Executing
1. Check `server_state/pending_actions.json` (if accessible)
2. Look for "Executing action" in logs
3. Verify confidence scores are > 0.7 for auto-approval

## Cost Estimate

### Background Worker Pricing (Render)
- **Free Tier**: Limited hours per month
- **Starter**: $7/month - 0.5 GB RAM, always on
- **Standard**: $25/month - 2 GB RAM, always on

**Recommendation**: Start with Starter plan ($7/month) for reliable 24/7 operation.

## Updating Your Service

### Deploy New Code
```bash
git add .
git commit -m "Your update message"
git push
```
Render will automatically detect the push and redeploy (takes ~2-5 minutes).

### Manual Redeploy
1. Go to Render Dashboard
2. Click on your service
3. Click "Manual Deploy" → "Deploy latest commit"

## Differences from Web Service

| Feature | Web Service | Background Worker |
|---------|-------------|-------------------|
| HTTP Server | Required | Not needed |
| Health Checks | Required | Optional |
| Port Exposure | Required | Not needed |
| Cost | Higher | Lower |
| Use Case | APIs, websites | Daemons, workers |

Your daemon is now correctly configured as a **Background Worker** ✅

## Next Steps

1. Push your code to GitHub
2. Deploy to Render using Option 1 or 2 above
3. Monitor logs to ensure it's running
4. Test by mentioning the bot in Slack

The daemon will now run continuously and automatically handle all tasks!
