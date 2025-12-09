# Self-Questioning Prevention Fix

## Problem
The AI agent was creating circular conversations by:
1. **Asking questions back to the user who just asked it a question**
2. **Sending messages that tagged/mentioned itself** (e.g., "@The Real PM, can you...")
3. **Not preserving thread context**, causing replies to appear in the main channel instead of in threads

### Example from Screenshot:
- **Mohit asks in #my-insights**: "What's in the plate for @Abhinav Singh Today?"
- **Bot incorrectly responds**: "Hi @Mohit Kumawat, I am still working on the follow up question buttons tap issue..."
- **Then bot asks itself**: "@The Real PM, I'll find out from... and let you know."

This creates confusion and makes the bot appear broken.

## Root Cause Analysis

### Issue 1: Self-Questioning
The AI was not explicitly instructed to avoid asking clarification questions back to the triggering user. When the AI couldn't find information in the context, it would default to asking the user for more details.

### Issue 2: Self-Tagging
The AI was generating messages that mentioned its own user ID or name (e.g., "<@BOT_ID>" or "@The Real PM"), creating the appearance of talking to itself.

### Issue 3: Missing Thread Context
When replying to messages in threads, the AI wasn't consistently including the `thread_ts` parameter, causing replies to appear in the main channel instead of the thread.

## Solution Implemented

### 1. Enhanced AI Prompt (daemon.py lines 280-319)
Added explicit rules to the AI's system prompt:

```
CRITICAL RULES:
1. **NEVER ASK QUESTIONS TO THE USER WHO JUST ASKED YOU A QUESTION**: 
{{ ... }}
   analysis asking them to clarify their own question.

3. **Think First**: 
   If you need to "check with" someone OTHER than the person who asked, 
   you MUST generate a `send_message` action to that other person.

4. **Reply in Thread**: 
   When responding to a message, always use the same thread_ts to keep 
   conversations organized.
```

### 2. Four-Layer Validation System (daemon.py lines 334-393)
Added runtime validation that filters out problematic actions BEFORE they are added to the queue:

#### **RULE 1: Block Self-Questioning**
- Detect if a message contains a question mark (`?`)
- Check if the target channel/user is the same as the triggering user/channel
- If both conditions are true, BLOCK the action

```python
is_question = '?' in message_text
targets_triggering_user = target_channel in triggering_users
targets_triggering_channel = target_channel in triggering_channels

if is_question and (targets_triggering_user or targets_triggering_channel):
    log(f"⚠️ BLOCKED self-questioning action")
    continue
```

#### **RULE 2: Block Asking Mohit to Clarify His Own Questions**
- Specifically check if the target is Mohit and the message is a question
- Verify if Mohit was the one who triggered the message
- Block if both are true

```python
mohit_id = os.environ.get('SLACK_USER_ID')
if mohit_id and target_channel == mohit_id and is_question:
    if mohit_id in triggering_users:
        log(f"⚠️ BLOCKED asking Mohit to clarify his own question")
        continue
```

#### **RULE 3: Block Self-Tagging (NEW)**
- Check if the message contains the bot's user ID tag (e.g., `<@U123BOT>`)
- Check if the message contains "@The Real PM"
- Block any message that mentions the bot itself

```python
bot_id = os.environ.get('SLACK_BOT_USER_ID')
if bot_id:
    if f'<@{bot_id}>' in message_text or '@The Real PM' in message_text:
        log(f"⚠️ BLOCKED message that tags the bot itself")
        continue
```

#### **RULE 4: Auto-Infer Thread Context (NEW)**
- If the AI forgets to include `thread_ts`, automatically infer it
- Match the target channel with the triggering message's channel
- Use the triggering message's `thread_ts` or `ts` as the thread

```python
if not data.get('thread_ts'):
    for m in filtered_mentions:
        if m.get('channel') == target_channel:
            inferred_thread_ts = m.get('thread_ts') or m.get('ts')
            if inferred_thread_ts:
                data['thread_ts'] = inferred_thread_ts
                log(f"📎 Auto-added thread_ts: {inferred_thread_ts}")
                break
```

### 3. Comprehensive Testing
Created `test_self_questioning.py` with three test cases:
1. **Test 1**: Verify that self-questioning actions are blocked
2. **Test 2**: Verify that valid actions (asking other users) still work
3. **Test 3**: Verify that self-tagging messages are blocked

**Test Results:**
```
✅ SUCCESS: Self-questioning action was correctly blocked!
✅ SUCCESS: Valid action was correctly allowed!
✅ SUCCESS: Self-tagging message was correctly blocked!
🎉 ALL TESTS PASSED!
```

## What This Prevents

### ❌ BLOCKED Scenarios:
- Bot asking Mohit to clarify Mohit's own question
- Bot asking for more context from the user who just asked
- Bot creating circular question loops in threads
- **Bot sending messages that tag/mention itself**
- **Bot replying in the main channel instead of in threads**

### ✅ ALLOWED Scenarios:
- Bot asking OTHER team members for information
- Bot providing answers based on available context
- Bot stating it needs more information (without asking the user)
- Bot sending non-question messages to the triggering user
- **Bot replying in the correct thread**

## Deployment
The fix is now active in `daemon.py`. The next time the daemon runs:
1. It will use the enhanced prompt with anti-self-questioning rules
2. It will validate all generated actions before queuing them
3. Any self-questioning or self-tagging actions will be blocked and logged
4. Thread context will be automatically preserved

## Monitoring
Watch for these log messages to confirm the fix is working:
```
⚠️ BLOCKED self-questioning action: '<message preview>' to <channel_id>
   Triggering users: {...}, channels: {...}
⚠️ BLOCKED asking Mohit to clarify his own question: '<message preview>'
⚠️ BLOCKED message that tags the bot itself: '<message preview>'
📎 Auto-added thread_ts: <timestamp>
```

## Future Improvements
1. **Smarter Context Usage**: Train the AI to better extract information from the project context before considering asking anyone
2. **User Intent Detection**: Improve understanding of when a user is asking for information vs. giving a command
3. **Confidence Scoring**: Add confidence scores to determine when the bot should admit it doesn't know vs. trying to answer
4. **Thread Awareness**: Further enhance thread detection to handle complex nested conversations

---

**Status**: ✅ Fixed and Tested  
**Date**: 2025-12-09  
**Files Modified**: 
- `daemon.py` (lines 280-393)
- `test_self_questioning.py` (new file)

**Test Coverage**: 3/3 tests passing ✅
