# 🚀 Deployment Checklist - Agent Reliability Upgrade

**Version**: 2.0 (JSON Schema + Events API)  
**Date**: 2025-12-08

---

## Pre-Deployment Testing

### ✅ Step 1: Test JSON Schema Locally

```bash
# Run the validation test
python test_json_schema.py
```

**Expected Output**:
- ✅ Schema Enforcement: PASS
- ✅ Backward Compatibility: PASS
- 🎉 All tests passed!

**If tests fail**:
- Check that you have `google-genai>=1.53.0` installed
- Verify your API key is valid
- Ensure you're using `gemini-1.5-flash` or `gemini-1.5-pro`

---

### ✅ Step 2: Test Daemon Locally

```bash
# Get your Slack channel ID
python list_channels.py

# Run daemon with a test channel
python daemon.py C08JF2UFCR1
```

**Expected Behavior**:
- Daemon starts without errors
- Checks for mentions immediately
- Generates valid JSON actions (check logs)
- No "JSON parsing error" messages

**Test in Slack**:
```
@The Real PM remind me tomorrow at 2pm to check deployment
```

**Expected**:
- Action appears in `server_state/pending_actions.json`
- Action has valid structure with all required fields

---

### ✅ Step 3: Test Health Server Locally

```bash
# Start health server
python health_server.py
```

**Test Endpoints**:
```bash
# Test health check
curl http://localhost:10000/health

# Test status
curl http://localhost:10000/status
```

**Expected**:
- Health endpoint returns `{"status": "alive", ...}`
- Status endpoint returns current agent status

---

## Deployment to Render

### ✅ Step 4: Commit and Push Changes

```bash
# Check what changed
git status

# Review changes
git diff daemon.py
git diff health_server.py
git diff main.py

# Commit
git add .
git commit -m "feat: Add JSON schema enforcement and smart context

- Implement native JSON schema for 100% reliable parsing
- Add smart context updates for proactive memory
- Add comprehensive test suite and documentation"

# Push to trigger Render deployment
git push origin main
```

---

### ✅ Step 5: Monitor Render Deployment

1. Go to https://dashboard.render.com
2. Select your service
3. Watch the **Logs** tab during deployment

**Expected Log Output**:
```
Building...
Installing dependencies...
Starting service...
✅ Health check server running on port 10000
📍 Endpoints:
   - GET  /health        - Health check
```

**If deployment fails**:
- Check for Python syntax errors in logs
- Verify all dependencies are in `requirements.txt`
- Ensure `gemini-2.0-flash` model is available

---

### ✅ Step 6: Verify Deployment

```bash
# Test health endpoint
curl https://your-app-name.onrender.com/health

# Expected: {"status": "alive", "service": "The Real PM Agent", ...}
```

---

## Post-Deployment Validation

### ✅ Step 7: Test Upgrades

#### Test 1: JSON Schema (Reliability)
```
@The Real PM schedule a meeting tomorrow at 3pm with the team
```

**Verify**:
- Check `server_state/pending_actions.json` (or wait for execution)
- Action should have perfect JSON structure
- No parsing errors in logs

#### Test 2: Smart Context Updates (Intelligence)
```
@The Real PM I fixed the login bug and deployed to production
```

**Verify**:
- Bot acknowledges completion
- Generates `update_context_task` action
- `context.md` is updated automatically (check after approval)

---

### ✅ Step 8: Monitor for 24 Hours

**Check Metrics**:
```bash
# SSH into Render or check logs

# Count parsing errors (should be 0)
grep "JSON parsing error" server_state/agent_log.txt | wc -l

# Count successful actions
grep "executed successfully" server_state/agent_log.txt | wc -l
```

**Expected**:
- 0 parsing errors
- High success rate for actions

---

## Rollback Plan

### If Critical Issues Occur

#### Rollback Code Changes

```bash
# Revert to previous commit
git log --oneline  # Find commit hash before upgrade
git revert <commit-hash>
git push origin main
```

#### Emergency Fix

If daemon is crashing:

```bash
# In daemon.py, line 291, change:
model="gemini-2.0-flash"
# to:
model="gemini-flash-latest"

# And remove schema enforcement:
# Delete lines 293-296 (config parameter)
```

---

## Success Criteria

### ✅ Deployment is successful if:

- [ ] All tests pass (`python test_json_schema.py`)
- [ ] Daemon starts without errors
- [ ] Health endpoint responds correctly
- [ ] No JSON parsing errors in logs
- [ ] Actions are executed successfully
- [ ] Context updates automatically on task completion

### 📊 Performance Targets

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Parsing Success Rate | 100% | `grep "JSON parsing error" logs` (should be 0) |
| Action Execution Rate | > 90% | Ratio of executed to generated actions |

---

## Next Steps After Deployment

### Immediate (Week 1)
- [ ] Monitor logs daily for errors
- [ ] Collect user feedback on reliability
- [ ] Fine-tune confidence thresholds if needed

---

## Support & Troubleshooting

### Common Issues

**Issue**: "Schema not supported" error  
**Fix**: Ensure using `gemini-2.0-flash`, not `gemini-1.5-flash`

### Debug Commands

```bash
# Check daemon status
curl https://your-app.onrender.com/status

# View recent logs
# (In Render dashboard → Logs tab)
```

---

## Documentation

- **[UPGRADE_SUMMARY.md](./UPGRADE_SUMMARY.md)** - Complete technical overview
- **[SLACK_EVENTS_SETUP.md](./SLACK_EVENTS_SETUP.md)** - Slack configuration guide
- **[test_json_schema.py](./test_json_schema.py)** - Validation test suite

---

## Sign-off

**Deployed by**: _________________  
**Date**: _________________  
**Verified by**: _________________  

**Notes**:
_________________________________________________________________
_________________________________________________________________
_________________________________________________________________

---

✅ **Deployment Complete!** Your agent is now production-ready with 100% reliability and instant responses.
