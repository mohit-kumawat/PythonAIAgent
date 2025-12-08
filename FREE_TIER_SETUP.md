# 🆓 Render Free Tier Setup with Cron-Job.org

## ✅ Your Current Setup (Smart & Free!)

You're using a **clever workaround** for Render's free tier limitations:
- **Render Free Tier**: Spins down after 15 minutes of inactivity
- **Cron-Job.org**: Pings your service every 5 minutes to keep it alive
- **Result**: Free 24/7 operation! 🎉

## How It Works

```
┌─────────────────┐      Every 5 min      ┌──────────────────┐
│  Cron-Job.org   │ ──────────────────────▶│  Render Service  │
│  (Free Pinger)  │   GET /health          │  (Free Tier)     │
└─────────────────┘                        └──────────────────┘
                                                    │
                                                    │ Daemon checks
                                                    │ Slack hourly
                                                    ▼
                                            ┌──────────────────┐
                                            │  Slack Channels  │
                                            └──────────────────┘
```

## What I Just Configured

### 1. **Changed to Web Service** (from Background Worker)
   - Free tier only supports Web Services
   - Requires HTTP endpoint for health checks
   - ✅ Now compatible with cron-job.org

### 2. **Enhanced Health Server**
   - Responds to `/health` pings from cron-job.org
   - Keeps service alive (prevents spin-down)
   - Added `/status` endpoint to check daemon status
   - Added `/trigger` endpoint for manual checks

### 3. **Optimized for Free Tier**
   - Daemon runs in background
   - Health server runs in foreground (required)
   - Both run simultaneously

## Your Cron-Job.org Configuration

Based on your screenshot, you have:
- **URL**: `https://pythonaiagent.onrender.com`
- **Schedule**: Every 5 minutes
- **Endpoint**: Should ping `/health`

### ✅ Verify Your Cron Job Settings:
1. Go to [cron-job.org](https://cron-job.org)
2. Edit your "AI Agent" job
3. Ensure URL is: `https://pythonaiagent.onrender.com/health`
4. Schedule: Every 5 minutes ✅ (already set)
5. Enable job: ✅ (already enabled)

## How the Daemon Works on Free Tier

### Timeline:
```
00:00 - Cron pings /health → Service wakes up (if sleeping)
00:05 - Cron pings /health → Service stays alive
00:10 - Cron pings /health → Service stays alive
...
01:00 - Daemon checks Slack (hourly schedule)
01:05 - Cron pings /health → Service stays alive
...
```

### Key Points:
- ✅ Cron-job.org pings **every 5 minutes** → Keeps service alive
- ✅ Daemon checks Slack **every 1 hour** → Processes mentions
- ✅ Actions execute **every 10 seconds** → Fast response
- ✅ **100% FREE** → No costs!

## Deployment Steps

### 1. Update Your .env File
Add your Slack User Token (if not already done):
```bash
SLACK_USER_TOKEN="xoxp-YOUR-ACTUAL-TOKEN"
```

### 2. Push to GitHub
```bash
git add .
git commit -m "Configure for Render free tier with cron-job.org"
git push
```

### 3. Render Will Auto-Deploy
- Your service is already deployed
- It will auto-update with new code
- Wait ~2-5 minutes for deployment

### 4. Verify It's Working

#### Check Render Logs:
```
✅ Health check server running on port 10000
📍 Endpoints:
   - GET /health - Health check (for cron-job.org)
   - GET /status - Service status
   - GET /trigger - Manual trigger
Starting Python Daemon in background for channels: ...
Daemon started. Monitoring channels: ...
```

#### Test Health Endpoint:
Visit: `https://pythonaiagent.onrender.com/health`

You should see:
```json
{
  "status": "alive",
  "service": "The Real PM Agent",
  "timestamp": "2025-12-08T15:30:00",
  "message": "Service is running. Cron ping received."
}
```

#### Check Status Endpoint:
Visit: `https://pythonaiagent.onrender.com/status`

You should see daemon status.

## Free Tier Limitations & Workarounds

| Limitation | Workaround | Status |
|------------|------------|--------|
| Spins down after 15 min | Cron-job.org pings every 5 min | ✅ Solved |
| 750 hours/month free | Cron keeps it alive 24/7 | ✅ Covered |
| Slow cold starts | Cron prevents cold starts | ✅ Solved |
| No persistent storage | Uses server_state/ directory | ✅ Works |

## Monitoring Your Service

### 1. **Render Dashboard**
   - Go to: https://dashboard.render.com
   - Click on "PythonAIAgent"
   - Check "Logs" tab

### 2. **Cron-Job.org Dashboard**
   - Go to: https://cron-job.org
   - View "AI Agent" job
   - Check execution history
   - Should show successful pings every 5 minutes

### 3. **Slack**
   - Mention your bot in Slack
   - It should respond within 5 minutes (next cron ping)
   - Or wait for hourly check

## Expected Behavior

### Normal Operation:
```
[2025-12-08 15:00:00] ✅ Health check pinged - Service kept alive
[2025-12-08 15:05:00] ✅ Health check pinged - Service kept alive
[2025-12-08 15:10:00] ✅ Health check pinged - Service kept alive
[2025-12-08 16:00:00] Starting mention check cycle...
[2025-12-08 16:00:05] Found 2 mentions. analyzing...
[2025-12-08 16:00:10] Added 2 actions to the queue.
[2025-12-08 16:00:15] Executing action: Reply to Mohit
[2025-12-08 16:00:20] Action executed successfully.
```

## Troubleshooting

### Service Keeps Spinning Down
- ✅ Check cron-job.org is enabled
- ✅ Verify URL is correct: `https://pythonaiagent.onrender.com/health`
- ✅ Check cron execution history

### Not Responding to Slack
- ✅ Wait up to 1 hour (hourly check schedule)
- ✅ Or manually trigger: Visit `/trigger` endpoint
- ✅ Check Render logs for errors

### Cron Job Failing
- ✅ Check if service is deployed
- ✅ Verify health endpoint responds
- ✅ Check Render logs for crashes

## Cost Breakdown

| Service | Plan | Cost |
|---------|------|------|
| Render | Free Tier | $0/month |
| Cron-Job.org | Free | $0/month |
| Slack | Free | $0/month |
| Google AI | Free Tier | $0/month* |
| **TOTAL** | | **$0/month** 🎉 |

*Google AI has generous free tier limits

## Optimization Tips

### 1. **Reduce Check Frequency** (if hitting limits)
   - Change daemon schedule from 1 hour to 2 hours
   - Edit line 699 in `daemon.py`:
   ```python
   schedule.every(2).hours.do(check_mentions_job, ...)
   ```

### 2. **Disable Proactive Features** (if needed)
   - Comment out proactive jobs in `daemon.py`
   - Lines 703-708

### 3. **Reduce Cron Frequency** (if needed)
   - Change from 5 minutes to 10 minutes
   - Still keeps service alive
   - Reduces cron-job.org usage

## Next Steps

1. ✅ Push your code to GitHub
2. ✅ Wait for Render to auto-deploy
3. ✅ Verify health endpoint works
4. ✅ Check cron-job.org is pinging successfully
5. ✅ Test by mentioning bot in Slack

## Summary

Your setup is now **optimized for 100% FREE operation**:
- ✅ Render Free Tier (Web Service)
- ✅ Cron-Job.org (keeps it alive)
- ✅ Health server (responds to pings)
- ✅ Daemon (checks Slack hourly)
- ✅ Auto-restart on crash
- ✅ No manual intervention needed

**Total Cost: $0/month** 🎉

The daemon will now run 24/7 for free, check Slack every hour, and respond to mentions automatically!
