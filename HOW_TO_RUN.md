# How to Run Your AI Agent - Complete Guide

This guide will help you run your Python AI Agent. You can run it in two ways:
1. **Interactive Mode** (CLI): Run commands manually when you want.
2. **Autonomous Mode** (Daemon + Dashboard): Run it in the background with a web interface.

---

## ✅ Prerequisites

1.  **Python 3.10+** installed.
2.  **Node.js 18+** installed (only for the dashboard).
3.  **Slack App** configured (Tokens & IDs).
4.  **Gemini API Key**.

Ensure your `.env` file has:
```env
GOOGLE_API_KEY=AIza...
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...
SLACK_USER_ID=U...       # Your User ID (Agent listens to you)
SLACK_BOT_USER_ID=U...   # Bot's User ID
USER_EMAIL=you@example.com
```

---

## 🚀 Option 1: Autonomous Mode (Recommended)

This runs the agent continuously in the background and gives you a visual dashboard.

### Step 1: Start the Background Daemon
The daemon monitors Slack, processes logic, and queues actions.

Open a terminal:
```bash
# Activate virtual environment
source .venv/bin/activate

# Start the daemon with the channels you want to monitor
# Usage: python daemon.py <channel_id_1> <channel_id_2> ...
python daemon.py C07FMAQ3485 C08JF2UFCR1
```

*The daemon is now running. It will print logs to the terminal.*

### Step 2: Start the Web Dashboard
The dashboard lets you see what the agent is doing and **approve/reject** actions.

Open a **new** terminal tab/window:
```bash
cd dashboard

# Install dependencies (only needed once)
npm install

# Start the dashboard
npm run dev
```

*Open http://localhost:3000 in your browser.*

---

## 🛠 Option 2: Manual CLI Mode

Use these commands if you just want to run specific tasks once.

### 1. Process Mentions (Smart Command)
Checks recent messages where you mentioned the bot and executes commands.
```bash
python main.py process-mentions --channels C08JF2UFCR1 C07FMAQ3485
```

### 2. Chat Mode
Talk to the agent directly in the terminal.
```bash
python main.py chat
```

### 3. Sync Mode
Checks for project drift between Slack and your `context.md` file.
```bash
python main.py sync --channels C08JF2UFCR1 --todo-sync
```

---

## 🐳 Docker Deployment (Local or Server)

You can run the entire system (Agent + Dashboard) in a single container.

1.  **Build the image:**
    ```bash
    docker build -t pm-agent .
    ```

2.  **Run the container:**
    ```bash
    docker run -d \
      -p 3000:3000 \
      --env-file .env \
      pm-agent
    ```

---

## 🚀 Deploying to Render (For Non-Developers)

Deploy your Agent to the cloud easily using [Render](https://render.com).

### Prerequisites
1.  **GitHub Account**: Ensure this code is pushed to a GitHub repository.
2.  **Render Account**: Sign up at [render.com](https://render.com).

### Step-by-Step Guide

1.  **Push your code to GitHub**
    *   Make sure all your latest changes (including `Dockerfile` and `start.sh`) are committed and pushed to your GitHub repository.

2.  **Create a New Web Service on Render**
    *   Go to your Render Dashboard.
    *   Click **New +** -> **Web Service**.
    *   Connect your GitHub account and select your `PythonAIAgent` repository.

3.  **Configure the Service**
    *   **Name**: `pm-agent-dashboard` (or any name you like)
    *   **Runtime**: Select **Docker**.
    *   **Region**: Choose a region close to you (e.g., Singapore, Frankfurt).
    *   **Branch**: `main`
    *   **Instance Type**: The "Free" tier *might* work, but "Starter" ($7/mo) is recommended for reliable performance of AI & build processes.

4.  **Add Environment Variables**
    *   Scroll down to the **Environment Variables** section.
    *   Click "Add Environment Variable" and add ALL keys from your local `.env` file:
        *   `GOOGLE_API_KEY`: ...
        *   `SLACK_BOT_TOKEN`: ...
        *   `SLACK_APP_TOKEN`: ...
        *   `SLACK_USER_ID`: ...
        *   `SLACK_BOT_USER_ID`: ...
        *   `USER_EMAIL`: ...
        *   `SLACK_CHANNELS`: `C07FMAQ3485 C08JF2UFCR1` (Space separated list of channels to monitor)

5.  **Deploy**
    *   Click **Create Web Service**.
    *   Render will now build your Docker image. This may take 5-10 minutes.
    *   Watch the logs. You should see "Starting Python Daemon..." and "Starting Next.js Dashboard...".

6.  **Access Your Agent**
    *   Once deployed, Render will verify you a URL (e.g., `https://pm-agent-dashboard.onrender.com`).
    *   Open this URL to see your Command Center.
    *   Your Agent is now LIVE and monitoring Slack 24/7!

---

## 💡 How to Use the Agent

### 1. Give Commands in Slack
Mention the bot in a monitored channel:
> "@The Real PM Remind me to review the dashboard designs tomorrow at 10am"

> "@The Real PM Update the context: @Alice is now leading the frontend migration."

### 2. Approve Actions
- **If running Daemon + Dashboard**: Go to http://localhost:3000. You will see a "Pending Action". Click **Approve**.
- **If running CLI**: The terminal will verify the action plan and ask `Do you approve? [y/n]`.

### 3. Check Status
- Look at the **Dashboard** to see the agent's memory, logs, and current status ("IDLE", "THINKING", "EXECUTING").

---

## ❓ Troubleshooting

**"Module not found: schedule"**
```bash
pip install schedule
```

**"Address already in use" (Dashboard)**
The dashboard uses port 3000. If it's taken, Next.js will usually try 3001. Check the terminal output.

**Daemon not seeing messages?**
- Ensure the bot is **invited** to the channel (`/invite @The Real PM`).
- Ensure `SLACK_USER_ID` in `.env` matches YOUR user ID.
