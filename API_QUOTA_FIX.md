# API Quota Management & Auto-Retry Fix

**Date**: December 7, 2025  
**Issue**: Gemini API quota exhaustion (429 RESOURCE_EXHAUSTED)  
**Fix**: Automatic retry with API key rotation

---

## 🔴 The Problem

When running `process-mentions`, you encountered:

```
Error during analysis: 429 RESOURCE_EXHAUSTED
* Quota exceeded for metric: generativelanguage.googleapis.com/generate_content_free_tier_requests
```

**What this means:**
- Your Gemini API key hit its free tier quota limit
- Free tier limits: 15 requests/minute, 1500 requests/day
- The agent couldn't complete the AI analysis step

---

## ✅ The Solution

I've added **automatic retry with API key rotation** to the `process-mentions` command. Now when one API key hits quota:

1. ⚠️  Detects quota error (429)
2. 🔄 Automatically rotates to next API key
3. ⏱️  Waits 2 seconds
4. 🔁 Retries the request
5. ✅ Continues until success or all keys exhausted

---

## 🎯 How It Works Now

### Before (Without Fix)
```
Processing mentions...
Found 2 authorized mention(s). Analyzing...
Error during analysis: 429 RESOURCE_EXHAUSTED
❌ STOPPED
```

### After (With Fix)
```
Processing mentions...
Found 2 authorized mention(s). Analyzing...

⚠️  Quota exceeded (Attempt 1/2). Rotating to next API key...
✅ Success with backup key!

AGENT ANALYSIS
[AI analysis continues...]
```

---

## 📋 What You Have

You currently have **2 API keys** configured in your `.env`:
- `GOOGLE_API_KEY` (primary)
- `GOOGLE_API_KEY_2` (backup)

This means the agent will:
1. Try with primary key
2. If quota exceeded → automatically switch to backup key
3. If both exhausted → show helpful error message

---

## 💡 Recommendations

### Option 1: Wait for Quota Reset (Free)

**Per-Minute Quota**: Resets every 60 seconds
```bash
# Wait 1 minute, then retry
sleep 60
python3 main.py process-mentions --channels C07FMAQ3485
```

**Daily Quota**: Resets at midnight Pacific Time
- Check your usage: https://ai.dev/usage?tab=rate-limit

### Option 2: Add More API Keys (Free)

Create additional free API keys and add them to `.env`:

1. **Get more API keys**:
   - Go to: https://aistudio.google.com/app/apikey
   - Click "Create API Key"
   - Repeat for multiple keys (you can create several)

2. **Add to `.env`**:
   ```bash
   GOOGLE_API_KEY=your-first-key
   GOOGLE_API_KEY_2=your-second-key
   GOOGLE_API_KEY_3=your-third-key
   GOOGLE_API_KEY_4=your-fourth-key
   # Add as many as you want!
   ```

3. **Restart the agent** - it will automatically use all keys

**Benefits**:
- More total quota (each key has its own limits)
- Automatic failover between keys
- Still completely free!

### Option 3: Upgrade to Paid Plan (Recommended for Production)

**Gemini API Pay-as-you-go**:
- No daily limits
- Much higher rate limits
- Only pay for what you use
- Very affordable for most use cases

**How to upgrade**:
1. Go to: https://ai.google.dev/pricing
2. Enable billing for your Google Cloud project
3. Your existing API key will automatically get higher limits

---

## 🧪 Testing the Fix

Try running the command again:

```bash
python3 main.py process-mentions --channels C07FMAQ3485
```

**Expected behavior**:
- If primary key is exhausted → automatically tries backup key
- If both exhausted → shows helpful error message with suggestions

---

## 📊 Understanding Your Quota

### Free Tier Limits (per API key)

| Metric | Limit |
|--------|-------|
| Requests per minute | 15 |
| Requests per day | 1,500 |
| Tokens per minute | 1,000,000 |

### How to Check Usage

Visit: https://ai.dev/usage?tab=rate-limit

You'll see:
- Current usage
- Remaining quota
- When quota resets

---

## 🔧 Advanced: Monitoring Quota

### Check Which Keys Are Working

The `ClientManager` in your code automatically tracks:
- Which keys have been tried
- Which key is currently active
- Rotation between keys

### Add More Keys Dynamically

Just add to `.env`:
```bash
GOOGLE_API_KEY_5=another-key
GOOGLE_API_KEY_6=yet-another-key
# No code changes needed!
```

The agent will automatically detect and use them.

---

## 🎯 Best Practices

### 1. Spread Out Your Requests

Instead of running many times in a row:
```bash
# ❌ Bad - will hit quota quickly
python3 main.py process-mentions --channels C07FMAQ3485
python3 main.py process-mentions --channels C07FMAQ3485
python3 main.py process-mentions --channels C07FMAQ3485
```

Space them out:
```bash
# ✅ Good - respects rate limits
python3 main.py process-mentions --channels C07FMAQ3485
# Wait 1 minute
sleep 60
python3 main.py process-mentions --channels C07FMAQ3485
```

### 2. Use Multiple Channels in One Call

Instead of:
```bash
# ❌ Uses 3 API calls
python3 main.py process-mentions --channels C07FMAQ3485
python3 main.py process-mentions --channels C08JF2UFCR1
python3 main.py process-mentions --channels C08JF2UFCR2
```

Do:
```bash
# ✅ Uses 1 API call
python3 main.py process-mentions --channels C07FMAQ3485 C08JF2UFCR1 C08JF2UFCR2
```

### 3. Schedule Regular Runs

Set up a cron job to run once or twice per day:
```bash
# Run at 9 AM and 6 PM daily
0 9 * * * cd /Users/mohitkumawat/PythonAIAgent && python3 main.py process-mentions --channels C07FMAQ3485
0 18 * * * cd /Users/mohitkumawat/PythonAIAgent && python3 main.py process-mentions --channels C07FMAQ3485
```

---

## 🚨 Error Messages Explained

### If All Keys Exhausted

You'll see:
```
❌ Error: All API keys exhausted or failed.
💡 Suggestions:
   1. Wait for quota to reset (usually 1 minute or 24 hours)
   2. Add more API keys to your .env file (GOOGLE_API_KEY_2, GOOGLE_API_KEY_3, etc.)
   3. Upgrade to a paid Gemini API plan
   4. Check your usage at: https://ai.dev/usage?tab=rate-limit
```

**What to do:**
1. Check the error message for retry delay (e.g., "Please retry in 40s")
2. Wait that long
3. Try again
4. Or add more API keys

---

## ✅ Summary

**What Changed:**
- ✅ Added automatic retry with API key rotation
- ✅ Graceful handling of quota errors
- ✅ Helpful error messages with suggestions
- ✅ Works with unlimited API keys

**What You Should Do:**
1. **Short term**: Wait 1 minute between runs
2. **Medium term**: Add 2-3 more free API keys to `.env`
3. **Long term**: Consider upgrading to paid plan for production use

**Current Status:**
- ✅ Code updated and tested
- ✅ Automatic rotation enabled
- ✅ Ready to use with your 2 existing keys

---

## 🎉 Try It Now

The fix is live! Try running:

```bash
python3 main.py process-mentions --channels C07FMAQ3485
```

If your primary key is still exhausted, it will automatically try your backup key!

---

**Need Help?**
- Check quota: https://ai.dev/usage?tab=rate-limit
- Get more keys: https://aistudio.google.com/app/apikey
- Pricing info: https://ai.google.dev/pricing
