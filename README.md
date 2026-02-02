# Repost Father Bot

A Telegram bot that tracks repost exchanges in group topics. Users post reel links with hashtags, others react with thumbs up to confirm reposts, and the bot tracks points based on a weighted system.

## Features

- **Hashtag Detection**: Posts with `#repost` are tracked
- **Reaction Tracking**: 👍 reactions count as repost confirmations
- **Point System**:
  - Reactor gains points based on post owner's weight
  - Post owner loses points based on reactor's weight
- **Weight System**: Admins can set user weights based on subscriber counts
- **Private Commands**: Stats and leaderboard sent via DM to keep the chat clean
- **Public Stats**: Only the bot's reply to hashtag posts is visible in chat

## Commands

| Command | Description | Visibility |
|---------|-------------|------------|
| `/stats` | View your personal stats | Private (DM) |
| `/leaderboard` | View top 10 users by points | Private (DM) |
| `/setweight @user 1.5` | Set user's weight (admin only) | Private (DM) |
| `/setup` | Enable bot for this chat + sync admins | Public (group) |
| `/syncadmins` | Re-sync admins from Telegram | Public (group) |
| `/settopic <id>` | Restrict tracking to one topic (admin only) | Public (group) |
| `/cleartopic` | Allow tracking in all topics (admin only) | Public (group) |

## Deployment on Railway

### Prerequisites

1. A Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
2. A [Railway](https://railway.app) account

### Step 1: Create a New Project on Railway

1. Go to [railway.app](https://railway.app) and sign in
2. Click **"New Project"**
3. Select **"Deploy from GitHub repo"**
4. Connect your GitHub account and select this repository

### Step 2: Add PostgreSQL Database

1. In your Railway project, click **"+ New"**
2. Select **"Database"** → **"Add PostgreSQL"**
3. Railway will automatically provision the database

### Step 3: Configure Environment Variables

Click on your service (not the database) and go to **"Variables"** tab. Add:

| Variable | Value | Description |
|----------|-------|-------------|
| `BOT_TOKEN` | `your_bot_token` | From BotFather |
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` | Reference to Postgres (auto-filled) |
| `HASHTAG` | `#repost` | Hashtag to track (optional, default: #repost) |
| `REACTION_EMOJI` | `👍` | Emoji to track (optional, default: 👍) |

Notes:
- `ADMIN_IDS` is no longer used. Admins are synced per-chat from Telegram via `/setup` and `/syncadmins`.
- Topic restriction is configured per chat via `/settopic` (or auto-set to the current topic if you run `/setup` inside a topic).

### Step 4: Run Database Migrations

1. In Railway, click on your service
2. Go to **"Settings"** → **"Deploy"**
3. Under **"Custom Start Command"**, temporarily set:
   ```
   alembic upgrade head && python -m bot.main
   ```
4. Deploy once to run migrations
5. After successful deployment, change back to:
   ```
   python -m bot.main
   ```

Or use Railway's shell feature:
1. Click **"Settings"** → **"Railway Shell"**
2. Run: `/opt/venv/bin/python -m alembic upgrade head`

### Step 5: Verify Deployment

1. Check the **"Deployments"** tab for successful deployment
2. View **"Logs"** to see "Starting bot..."
3. Test the bot in your Telegram group
4. In each group where you add the bot, run `/setup` once (must be a Telegram chat admin)

## Getting Your Telegram User ID

You may still need your Telegram user ID for debugging, but the bot no longer uses a global admin list. Admins are synced per chat from Telegram.

1. Start a chat with [@userinfobot](https://t.me/userinfobot)
2. It will reply with your user ID
3. No need to add it anywhere — admins are synced per chat from Telegram using `/setup` and `/syncadmins`

## Getting Topic ID

If you want to restrict the bot to a specific topic in a group with topics:

1. Right-click on a message in the topic
2. Select "Copy Message Link"
3. The URL format is: `https://t.me/c/CHAT_ID/TOPIC_ID/MESSAGE_ID`
4. The `TOPIC_ID` is the second number

## Local Development

### Setup

```bash
# Clone the repository
git clone <your-repo-url>
cd repost_father_bot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export BOT_TOKEN="your_bot_token"
export DATABASE_URL="postgresql://user:pass@localhost:5432/repost_bot"

# Run migrations
alembic upgrade head

# Start the bot
python -m bot.main
```

### Database Setup (Local)

```bash
# Using Docker
docker run -d \
  --name repost-bot-db \
  -e POSTGRES_USER=bot \
  -e POSTGRES_PASSWORD=bot \
  -e POSTGRES_DB=repost_bot \
  -p 5432:5432 \
  postgres:15

# Set DATABASE_URL
export DATABASE_URL="postgresql://bot:bot@localhost:5432/repost_bot"
```

## Project Structure

```
repost_father_bot/
├── bot/
│   ├── __init__.py
│   ├── main.py              # Entry point
│   ├── config.py            # Environment config
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── message.py       # Hashtag post detection
│   │   ├── reaction.py      # Reaction tracking
│   │   └── commands.py      # Bot commands
│   └── services/
│       ├── __init__.py
│       ├── user_service.py
│       ├── post_service.py
│       └── stats_service.py
├── db/
│   ├── __init__.py
│   ├── models.py
│   ├── database.py
│   └── migrations/
├── requirements.txt
├── Procfile
├── railway.toml
├── alembic.ini
└── README.md
```

## How Points Work

1. **User A** posts a reel link with `#repost`
2. **User B** reposts it and adds 👍 reaction
3. Point changes:
   - **User B** gains `1.0 × User A's weight` points (did a repost for someone)
   - **User A** loses `1.0 × User B's weight` points (owes reposts to others)

**Example with weights:**
- User A has weight 2.0 (10k followers)
- User B has weight 1.0 (default)

When B reacts to A's post:
- B gains 2.0 points (reposting for high-value account)
- A loses 1.0 points

## Troubleshooting

### Bot doesn't respond to messages
- Ensure the bot is added to the group as admin
- If you restricted the bot to a topic, verify it with `/settopic` / `/cleartopic`
- Verify the hashtag matches (case-insensitive)

### Can't receive DMs
- Users must start a private chat with the bot first
- Send `/start` to the bot in DM

### Reactions not tracked
- Bot needs permission to see reactions in group settings
- Ensure the reaction emoji matches `REACTION_EMOJI`

### Database errors
- Check `DATABASE_URL` format
- Ensure migrations are run: `alembic upgrade head`
