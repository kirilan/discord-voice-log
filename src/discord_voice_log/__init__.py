"""Discord bot that logs voice channel joins, leaves and moves to a text channel."""

import logging
import os
import sys

import discord
from dotenv import load_dotenv

log = logging.getLogger("discord_voice_log")


def describe_change(
    member: discord.Member,
    before: discord.abc.GuildChannel | None,
    after: discord.abc.GuildChannel | None,
) -> str | None:
    """Return the log line for a voice state change, or None if the channel didn't change."""
    if before == after:
        # Mute/deafen/stream/video toggles also fire voice state updates; ignore them.
        return None

    who = member.mention
    if before is None:
        return f"📥 {who} joined {after.mention} ({_count(after)})"
    if after is None:
        return f"📤 {who} left {before.mention} ({_count(before)})"
    return f"🔀 {who} moved {before.mention} → {after.mention} ({_count(after)})"


def _count(channel: discord.abc.GuildChannel) -> str:
    # voice_states is built from gateway voice state events, so it's accurate
    # without the privileged members intent.
    in_channel = len(channel.voice_states)
    in_guild = sum(len(c.voice_states) for c in channel.guild.voice_channels + channel.guild.stage_channels)
    return f"{in_channel} in channel, {in_guild} in voice total"


class VoiceLogBot(discord.Client):
    def __init__(self, guild_id: int, log_channel_id: int) -> None:
        intents = discord.Intents.none()
        intents.guilds = True
        intents.voice_states = True
        super().__init__(
            intents=intents,
            # Show names as mentions without actually pinging anyone.
            allowed_mentions=discord.AllowedMentions.none(),
        )
        self.guild_id = guild_id
        self.log_channel_id = log_channel_id

    async def on_ready(self) -> None:
        guild = self.get_guild(self.guild_id)
        channel = self.get_channel(self.log_channel_id)
        if guild is None:
            log.error("Bot is not in guild %s; check GUILD_ID and that the bot was invited", self.guild_id)
        if channel is None:
            log.error("Can't see log channel %s; check LOG_CHANNEL_ID and permissions", self.log_channel_id)
        log.info("Logged in as %s, watching %s, posting to #%s", self.user, guild, channel)

    async def on_voice_state_update(
        self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState
    ) -> None:
        if member.guild.id != self.guild_id:
            return

        message = describe_change(member, before.channel, after.channel)
        if message is None:
            return

        channel = self.get_channel(self.log_channel_id)
        if channel is None:
            log.warning("Log channel %s not available, dropping: %s", self.log_channel_id, message)
            return

        try:
            await channel.send(message)
        except discord.HTTPException:
            log.exception("Failed to post to log channel")


def _require_int(name: str) -> int:
    value = os.environ.get(name, "").strip()
    if not value.isdigit():
        sys.exit(f"{name} must be set to a numeric Discord ID (see .env.example)")
    return int(value)


def main() -> None:
    load_dotenv()
    token = os.environ.get("DISCORD_TOKEN", "").strip()
    if not token:
        sys.exit("DISCORD_TOKEN must be set (see .env.example)")

    bot = VoiceLogBot(
        guild_id=_require_int("GUILD_ID"),
        log_channel_id=_require_int("LOG_CHANNEL_ID"),
    )
    bot.run(token, log_level=logging.INFO, root_logger=True)
