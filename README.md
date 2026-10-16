# discord-voice-log

A small Discord bot that helps server moderators see who is using the voice channels. It watches every voice channel in one server and posts a message to a log channel each time someone joins, leaves or moves between voice channels:

```
📥 @alice joined #General (3 in channel, 5 in voice total)
🔀 @bob moved #General → #Gaming (1 in channel, 5 in voice total)
📤 @alice left #General (1 in channel, 4 in voice total)
```

## What it does

- **Logs joins, leaves and moves.** One message per change, in the log channel you choose.
- **Shows live counts.** Each message says how many people are in that channel and how many are in voice across the whole server right after the change.
- **Works as a timeline.** Discord timestamps every message, so scrolling the log channel shows who was in voice and when.
- **Never pings anyone.** Names appear as clickable mentions, but nobody gets a notification.
- **Skips the noise.** Mute, deafen, screen-share and camera changes are not logged.
- **Watches one server.** It ignores events from any other server it happens to be in.
- **Needs no privileged intents.** You don't have to switch anything on under "Privileged Gateway Intents" in the developer portal.

The bot only logs while it is running. Anything that happens while it is offline is not recorded.

## Requirements

- [uv](https://docs.astral.sh/uv/), which installs Python 3.12 and the dependencies for you:

  ```sh
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```

- A Discord server where you have the **Manage Server** permission, or are the owner, so you can add the bot.

## Setup

### 1. Create the bot and get its token

1. Go to <https://discord.com/developers/applications> and sign in.
2. Click **New Application**, give it a name (e.g. "Voice Log") and create it.
3. Open the **Bot** tab and click **Reset Token**, then **Copy**. Discord only shows the token once, so keep it until step 4. If you lose it, reset it again.

Treat the token like a password: anyone who has it can control the bot. If it leaks, click **Reset Token** to cancel the old one.

### 2. Invite the bot to your server

1. In the same application, open **OAuth2** and find the **OAuth2 URL Generator**.
2. Under **Scopes**, tick **`bot`**.
3. Under **Bot Permissions**, tick **View Channels** and **Send Messages**.
4. Copy the generated URL, open it in your browser, pick your server and click **Authorize**.

You can also build the link by hand. Take the **Application ID** from the **General Information** page and use:

```
https://discord.com/oauth2/authorize?client_id=YOUR_APP_ID&scope=bot&permissions=3072
```

The bot now shows up in the member list. It stays offline until you start it.

### 3. Check channel permissions

Channel settings can override the bot's role, so check that it can:

- **send messages in the log channel.** If the channel is private, open its settings → **Permissions**, add the bot or its role, and allow **View Channel** and **Send Messages**.
- **see every voice channel it should watch.** For each private voice channel, allow **View Channel** for the bot. The bot can't log channels it can't see.

### 4. Configure

The bot reads three settings from a `.env` file in the project folder. Start from the example:

```sh
cp .env.example .env
```

Then fill in the values:

```
DISCORD_TOKEN=MTIz...your-token...
GUILD_ID=123456789012345678
LOG_CHANNEL_ID=987654321098765432
```

| Setting | What it is | Where to find it |
| --- | --- | --- |
| `DISCORD_TOKEN` | The bot's token | Step 1 |
| `GUILD_ID` | The server to watch | Right-click the server icon → **Copy Server ID** |
| `LOG_CHANNEL_ID` | The text channel to post in | Right-click the channel → **Copy Channel ID** |

The **Copy ID** options only appear once you turn on Developer Mode in Discord:

- **Desktop or browser:** User Settings (gear icon, bottom left) → **Advanced** → **Developer Mode**.
- **Mobile:** profile picture → gear icon → **Advanced** → **Developer Mode**.

The IDs are plain numbers, about 17–20 digits long. `.env` is excluded from git, so the token won't be committed.

## Run

```sh
uv run discord-voice-log
```

The first run downloads the dependencies. When the output shows `Logged in as …`, join a voice channel and a message should appear in the log channel. Press Ctrl+C to stop the bot.

The bot has to keep running for logging to continue. To keep it up all the time, run it as a service on an always-on machine.

## Run as a service

On Linux, systemd can start the bot at boot, restart it if it crashes and keep its logs. These steps need `sudo`.

Stop the bot first if you started it with `uv run`. If two copies run at once, every event is posted twice.

### 1. Create the service

Run this from the project folder. It fills in your username, the project path and the path to `uv`:

```sh
sudo tee /etc/systemd/system/discord-voice-log.service > /dev/null <<EOF
[Unit]
Description=Discord voice channel logger
Wants=network-online.target
After=network-online.target

[Service]
User=$(whoami)
WorkingDirectory=$(pwd)
ExecStart=$(command -v uv) run --frozen discord-voice-log
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
```

Check that the paths in the file look right:

```sh
cat /etc/systemd/system/discord-voice-log.service
```

The service runs as your user, from the project folder, and reads the same `.env` file. If the bot exits with an error, systemd waits 10 seconds and starts it again. `--frozen` installs the exact dependency versions in `uv.lock`, so the service never upgrades anything by itself.

### 2. Start it

```sh
sudo systemctl daemon-reload
sudo systemctl enable --now discord-voice-log
```

`enable` starts the bot at every boot, and `--now` also starts it right away.

### 3. Check that it's running

```sh
systemctl status discord-voice-log
```

Look for `active (running)` and, in the log lines below it, `Logged in as …`.

### Managing the service

| To | Run |
| --- | --- |
| Follow the bot's log live (Ctrl+C to stop) | `journalctl -u discord-voice-log -f` |
| See today's log | `journalctl -u discord-voice-log --since today` |
| Restart it after editing `.env` or updating the code | `sudo systemctl restart discord-voice-log` |
| Stop it until you start it again or the machine reboots | `sudo systemctl stop discord-voice-log` |
| Stop it and keep it from starting at boot | `sudo systemctl disable --now discord-voice-log` |

If you move the project folder or reinstall `uv` somewhere else, run step 1 again, then `sudo systemctl daemon-reload` and restart the service.

To remove the service completely:

```sh
sudo systemctl disable --now discord-voice-log
sudo rm /etc/systemd/system/discord-voice-log.service
sudo systemctl daemon-reload
```

## Troubleshooting

| Problem | Likely cause |
| --- | --- |
| `DISCORD_TOKEN must be set` or `GUILD_ID must be set to a numeric Discord ID` | The value is missing from `.env`, or it has quotes or extra characters. |
| `Improper token has been passed` | The token is wrong or was reset. Copy a fresh one from the **Bot** tab. |
| `Bot is not in guild …` | `GUILD_ID` is wrong, or the bot hasn't been invited to that server. |
| `Can't see log channel …` | `LOG_CHANNEL_ID` is wrong, or the bot can't view that channel. |
| `Failed to post to log channel` | The bot can see the log channel but isn't allowed to send messages there. |
| Nothing is posted for one particular voice channel | The bot can't view that channel. Allow **View Channel** for it. |
| Every event is posted twice | Two copies of the bot are running, for example the service plus one started with `uv run`. Stop one of them. |
| The service keeps restarting | Run `journalctl -u discord-voice-log -n 50` and look up the error in this table. |
| Your server isn't in the invite dropdown | You need **Manage Server** on that server. Ask an admin to open the link instead. |
