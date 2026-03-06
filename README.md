# openslackbot

Slack bot to call local AI for RAG and maybe more!

## Setup

### 1. Create a Slack App

1. Go to [api.slack.com/apps](https://api.slack.com/apps) and click **Create New App** → **From scratch**
2. Under **Socket Mode**, enable it and generate an **App-Level Token** with `connections:write` scope — save this as `SLACK_APP_TOKEN`
3. Under **OAuth & Permissions**, add these **Bot Token Scopes**:
   - `chat:write`
   - `channels:history`
   - `groups:history`
   - `im:history`
   - `mpim:history`
   - `app_mentions:read`
4. Install the app to your workspace and copy the **Bot User OAuth Token** — save this as `SLACK_BOT_TOKEN`
5. Under **Event Subscriptions**, enable events and subscribe to:
   - `message.channels`
   - `message.groups`
   - `message.im`
   - `message.mpim`
   - `app_mention`

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your tokens
```

### 3. Install & Run

```bash
pip install -r requirements.txt
python bot.py
```

Invite the bot to a channel and send a message — it will respond immediately.
