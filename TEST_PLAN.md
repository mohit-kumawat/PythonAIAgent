# System Test Plan: Dual-Output Command Processing

**Channel ID:** C08JF2UFCR1
**Date:** 2025-12-05

## Test Scenarios

### ✅ Test Case 1: Smart Reminder (Time Extraction)
**Objective:** Verify the agent extracts ISO time and creates a `schedule_reminder` action.
**User Action:** Post this message in Slack:
> @The Real PM remind me to check the deployment logs in 10 minutes

**Expected Output:**
- **Analysis:** "User wants a reminder in 10 mins."
- **JSON:**
  ```json
  {
    "action_type": "schedule_reminder",
    "data": {
      "time_iso": "2025-12-05T... (calculated future time)"
    }
  }
  ```

### ✅ Test Case 2: Context Update (Project State)
**Objective:** Verify the agent identifies a project update and creates an `update_context_task` action.
**User Action:** Post this message in Slack:
> @The Real PM The Home Page Update is now Ready for Testing. Umang finished the implementation.

**Expected Output:**
- **Analysis:** "Update 'Home Page Update' status to 'Ready for Testing' and owner to 'Umang'."
- **JSON:**
  ```json
  {
    "action_type": "update_context_task",
    "data": {
      "epic_title": "Home Page Update",
      "new_status": "Ready for Testing",
      "new_owner": "Umang"
    }
  }
  ```

### ✅ Test Case 3: Drift Detection (Sync Mode)
**Objective:** Verify the agent detects discrepancies between Slack and Context.
**User Action:** (After posting the above) Run `python main.py sync`
**Expected Output:**
- Proposal to update `context.md` with the new status from Test Case 2.

---
