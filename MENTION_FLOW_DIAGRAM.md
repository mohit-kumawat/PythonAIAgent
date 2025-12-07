# Enhanced Mention Detection - Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    ENHANCED MENTION DETECTION                    │
│                         Process Flow                             │
└─────────────────────────────────────────────────────────────────┘

Step 1: SCAN CHANNELS
┌──────────────────────────────────────────────────────────────┐
│  For each channel in --channels list:                        │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ Search for BOT mentions + keywords                      │ │
│  │  • @The Real PM (direct mention)                       │ │
│  │  • "mohit" (keyword, case-insensitive)                 │ │
│  │  • "the real pm" (phrase, case-insensitive)            │ │
│  └────────────────────────────────────────────────────────┘ │
│                           ↓                                   │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ Search for USER mentions                               │ │
│  │  • @Mohit (your Slack user ID)                         │ │
│  └────────────────────────────────────────────────────────┘ │
│                           ↓                                   │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ Combine & Deduplicate                                  │ │
│  │  • Use message timestamp as unique key                 │ │
│  │  • Remove duplicates (same msg, multiple triggers)     │ │
│  └────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
                           ↓

Step 2: FILTER BY SENDER
┌──────────────────────────────────────────────────────────────┐
│  For each detected message:                                  │
│                                                               │
│  ┌─────────────────┐                                         │
│  │ Check sender ID │                                         │
│  └────────┬────────┘                                         │
│           │                                                   │
│     ┌─────┴─────┐                                            │
│     │           │                                            │
│  ┌──▼──┐     ┌──▼──────────┐                                │
│  │ Bot │     │ Authorized? │                                │
│  │ Self│     │ (Mohit)     │                                │
│  └──┬──┘     └──┬──────┬───┘                                │
│     │           │      │                                     │
│  ┌──▼──┐     ┌──▼──┐ ┌▼────────────┐                        │
│  │SKIP │     │ YES │ │     NO      │                        │
│  └─────┘     └──┬──┘ └──┬──────────┘                        │
│                 │        │                                   │
│                 │    ┌───▼────────────────────────┐          │
│                 │    │ Send Refusal Message       │          │
│                 │    │ "I only accept commands    │          │
│                 │    │  from Mohit..."            │          │
│                 │    └────────────────────────────┘          │
│                 │                                            │
│            ┌────▼────┐                                       │
│            │ Process │                                       │
│            │ Message │                                       │
│            └─────────┘                                       │
└──────────────────────────────────────────────────────────────┘
                           ↓

Step 3: AI ANALYSIS
┌──────────────────────────────────────────────────────────────┐
│  Send to Gemini AI with:                                     │
│  • Agent instruction (from agent_instruction.txt)            │
│  • Project context (from context.md)                         │
│  • All authorized messages                                   │
│  • Current time (IST)                                        │
│                                                               │
│  AI generates:                                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ 1. Human-readable analysis                             │ │
│  │    "Found 2 reminders and 1 task update..."            │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ 2. Structured JSON action plan                         │ │
│  │    [                                                   │ │
│  │      {                                                 │ │
│  │        "action_type": "schedule_reminder",             │ │
│  │        "reasoning": "...",                             │ │
│  │        "data": {...}                                   │ │
│  │      }                                                 │ │
│  │    ]                                                   │ │
│  └────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
                           ↓

Step 4: USER APPROVAL
┌──────────────────────────────────────────────────────────────┐
│  Display AI analysis and proposed actions                    │
│                                                               │
│  Prompt: "Approve and execute? [y/n/u to update]"            │
│                                                               │
│  ┌─────┬─────────┬─────────────────────────────────────┐    │
│  │  y  │   n     │           u                         │    │
│  └──┬──┴────┬────┴──────────┬──────────────────────────┘    │
│     │       │               │                               │
│  ┌──▼──┐ ┌──▼──────┐  ┌────▼──────────────────────────┐    │
│  │ YES │ │ CANCEL  │  │ UPDATE MODE                    │    │
│  └──┬──┘ └─────────┘  │ • delete <n> - Remove action   │    │
│     │                 │ • edit <n>   - Modify action   │    │
│     │                 │ • done       - Finish editing  │    │
│     │                 │ • cancel     - Abort all       │    │
│     │                 └────┬───────────────────────────┘    │
│     │                      │                               │
│     └──────────────────────┘                               │
└──────────────────────────────────────────────────────────────┘
                           ↓

Step 5: EXECUTE ACTIONS
┌──────────────────────────────────────────────────────────────┐
│  For each approved action:                                   │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ schedule_reminder                                      │ │
│  │  • Validate time is in future                          │ │
│  │  • Check for duplicates in context.md                  │ │
│  │  • Call schedule_slack_message()                       │ │
│  │  • Add to context.md tracking                          │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ send_message                                           │ │
│  │  • Call send_slack_message()                           │ │
│  │  • Immediate delivery                                  │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ draft_reply                                            │ │
│  │  • Display drafted message                             │ │
│  │  • Prompt: "Send this reply now? [y/n]"                │ │
│  │  • Send if approved                                    │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ update_context_task                                    │ │
│  │  • Update section in context.md                        │ │
│  │  • Maintain markdown structure                         │ │
│  └────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
                           ↓

Step 6: REPORT RESULTS
┌──────────────────────────────────────────────────────────────┐
│  Display execution results:                                  │
│  ✓ Scheduled reminder: ... for 2025-12-06T14:00:00          │
│  ✓ Message sent: ...                                         │
│  ✗ Failed to schedule: ...                                   │
│  ⏭️  Skipped past-time reminder: ...                         │
└──────────────────────────────────────────────────────────────┘


═══════════════════════════════════════════════════════════════
                    DETECTION EXAMPLES
═══════════════════════════════════════════════════════════════

Example 1: Direct Bot Mention
┌─────────────────────────────────────────────────────────────┐
│ Message: "@The Real PM schedule a meeting tomorrow at 2pm" │
│ Detected: ✅ (bot mention)                                  │
│ Sender: Mohit                                               │
│ Action: Process → AI proposes schedule_reminder             │
└─────────────────────────────────────────────────────────────┘

Example 2: Keyword "mohit"
┌─────────────────────────────────────────────────────────────┐
│ Message: "Hey mohit, can you review the PR?"                │
│ Detected: ✅ (keyword "mohit")                              │
│ Sender: Alice                                               │
│ Action: Send refusal message                                │
└─────────────────────────────────────────────────────────────┘

Example 3: Phrase "the real pm"
┌─────────────────────────────────────────────────────────────┐
│ Message: "Ask the real pm about the deployment"             │
│ Detected: ✅ (phrase "the real pm")                         │
│ Sender: Bob                                                 │
│ Action: Send refusal message                                │
└─────────────────────────────────────────────────────────────┘

Example 4: User Mention
┌─────────────────────────────────────────────────────────────┐
│ Message: "@Mohit what's the status?"                        │
│ Detected: ✅ (user mention)                                 │
│ Sender: Mohit (self-message)                                │
│ Action: Process → AI may propose draft_reply                │
└─────────────────────────────────────────────────────────────┘

Example 5: Multiple Triggers
┌─────────────────────────────────────────────────────────────┐
│ Message: "@Mohit ask the real pm to remind mohit"           │
│ Detected: ✅ (user mention + phrase + keyword)              │
│ Deduplicated: Single message (by timestamp)                │
│ Sender: Mohit                                               │
│ Action: Process → AI proposes schedule_reminder             │
└─────────────────────────────────────────────────────────────┘

Example 6: No Triggers
┌─────────────────────────────────────────────────────────────┐
│ Message: "The project is on track"                          │
│ Detected: ❌ (no triggers)                                  │
│ Sender: Anyone                                              │
│ Action: Ignored                                             │
└─────────────────────────────────────────────────────────────┘


═══════════════════════════════════════════════════════════════
                    SECURITY FLOW
═══════════════════════════════════════════════════════════════

┌─────────────────────────────────────────────────────────────┐
│                    Message Detected                          │
└────────────────────────┬────────────────────────────────────┘
                         │
                    ┌────▼────┐
                    │ Sender? │
                    └────┬────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
    ┌───▼───┐      ┌────▼────┐     ┌────▼─────┐
    │  Bot  │      │  Mohit  │     │  Others  │
    │  Self │      │(Authrzd)│     │(Unauthrz)│
    └───┬───┘      └────┬────┘     └────┬─────┘
        │               │                │
    ┌───▼───┐      ┌────▼────┐     ┌────▼─────┐
    │ SKIP  │      │ PROCESS │     │ REFUSE   │
    │       │      │ for     │     │ Send:    │
    │       │      │ Actions │     │ "I only  │
    │       │      │         │     │  accept  │
    │       │      │         │     │  from    │
    │       │      │         │     │  Mohit"  │
    └───────┘      └─────────┘     └──────────┘
```
