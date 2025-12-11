# 🐘 Setting Up Free PostgreSQL on Render

To make your AI Agent robust and give it a "Permanent Brain" (so it never forgets anything), follow these steps to use the **Free PostgreSQL Database** on Render.

## Step 1: Create the Database
1.  Log in to your [Render Dashboard](https://dashboard.render.com).
2.  Click **New +** and select **PostgreSQL**.
3.  **Name:** `agent-brain-db` (or anything you like).
4.  **Database:** `agent_brain_db` (keep it simple).
5.  **User:** `admin`.
6.  **Region:** Choose the one closest to you (e.g., Singapore, Oregon).
7.  **PostgreSQL Version:** 16 (or latest).
8.  **Instance Type:** **Free** (Select the Free Tier option).
9.  Click **Create Database**.

## Step 2: Get the Connection String
1.  Wait a minute for the database to be "Available".
2.  On the database page, find the **Connections** section.
3.  Look for **Internal Database URL**.
    *   *Note:* Since your Python Agent is also on Render, using the *Internal* URL is faster and free.
    *   It looks like: `postgres://admin:password@hostname/database`
4.  **Copy this URL.**

## Step 3: Connect Your Agent
1.  Go to your **PythonAIAgent** service on Render.
2.  Click **Environment**.
3.  Add a new Environment Variable:
    *   **Key:** `DATABASE_URL`
    *   **Value:** (Paste the URL you copied)
4.  Click **Save Changes**.

## Step 4: Validate
1.  Render will automatically redeploy your agent.
2.  Check the **Logs**.
3.  You should see a message:
    `🔌 Connecting to PostgreSQL Database...`

---

## ✅ What Just Happened?
*   Your agent now stores its **Context** (Project Updates) and **Memory** (Decisions, Thread Summaries) in this database.
*   **No more data loss** when the bot restarts.
*   **No more "Scanning last 7 days..."** on every boot. It loads instantly.
*   You have successfully moved from a "script" to a **Cloud-Native Application**.
