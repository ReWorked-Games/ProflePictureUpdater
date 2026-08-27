import os
import asyncio
import discord
import aiohttp
from discord.ext import commands

# ============================================================
# CONFIG
# ============================================================

TOKEN = os.getenv("DISCORD_TOKEN")

# How long before the same Discord user can be checked again
SYNC_COOLDOWN = 60  # seconds


# ============================================================
# DISCORD INTENTS
# ============================================================

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    help_command=None
)


# ============================================================
# CACHE / COOLDOWN
# ============================================================

last_sync = {}


# ============================================================
# ROBLOX / ROVER LOOKUP
# ============================================================

async def get_rover_username(discord_user_id: int):
    """
    Look up a Discord user's linked Roblox username.

    NOTE:
    The Rover API endpoint must match the actual Rover API you
    have access to. The old `https://rover.link{member.id}` URL
    was malformed.
    """

    # Replace this with the actual Rover endpoint you intend to use.
    url = f"https://rover.link/api/user/{discord_user_id}"

    try:
        timeout = aiohttp.ClientTimeout(total=10)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as response:

                if response.status != 200:
                    print(
                        f"ROVER LOOKUP FAILED: "
                        f"Discord ID {discord_user_id} "
                        f"returned HTTP {response.status}"
                    )
                    return None

                try:
                    data = await response.json()
                except Exception:
                    print("ROVER ERROR: Response was not valid JSON.")
                    return None

                return data.get("robloxUsername")

    except asyncio.TimeoutError:
        print("ROVER ERROR: Request timed out.")
        return None

    except aiohttp.ClientError as error:
        print(f"ROVER ERROR: {error}")
        return None

    except Exception as error:
        print(f"ROVER CRASH SHIELD: {error}")
        return None


# ============================================================
# NICKNAME SYNC
# ============================================================

async def auto_sync_nickname(member: discord.Member):
    """
    Automatically synchronize the Discord nickname with
    the user's linked Roblox username.
    """

    if member.bot:
        return

    now = asyncio.get_running_loop().time()

    last_time = last_sync.get(member.id)

    if last_time is not None:
        if now - last_time < SYNC_COOLDOWN:
            return

    # Update cooldown BEFORE making request so message spam
    # cannot create many simultaneous requests.
    last_sync[member.id] = now

    roblox_username = await get_rover_username(member.id)

    if not roblox_username:
        return

    # Roblox usernames have a maximum length of 20 characters.
    # Discord nicknames can be longer, but keeping the returned
    # Roblox username unchanged is what we want here.
    if member.nick == roblox_username:
        return

    try:
        await member.edit(
            nick=roblox_username,
            reason="Automatic Roblox nickname synchronization"
        )

        print(
            f"AUTOMATION SUCCESS: "
            f"{member} -> {roblox_username}"
        )

    except discord.Forbidden:
        print(
            f"HIERARCHY ERROR: "
            f"Cannot change nickname for {member}. "
            f"Check Manage Nicknames permission and role hierarchy."
        )

    except discord.HTTPException as error:
        print(
            f"DISCORD ERROR: "
            f"Could not change nickname for {member}: {error}"
        )

    except Exception as error:
        print(
            f"NICKNAME CRASH SHIELD: "
            f"{member}: {error}"
        )


# ============================================================
# BOT READY
# ============================================================

@bot.event
async def on_ready():

    print("----------------------------------------")
    print(f"LIVE LOG: Bot is authenticated as {bot.user}")
    print(f"BOT ID: {bot.user.id}")
    print("AUTOMATION: Roblox nickname synchronization enabled.")
    print("----------------------------------------")


# ============================================================
# MESSAGE LISTENER
# ============================================================

@bot.event
async def on_message(message):

    # Ignore bots
    if message.author.bot:
        return

    # Ignore DMs
    if message.guild is None:
        return

    # Make sure the author is represented as a Member
    if not isinstance(message.author, discord.Member):
        return

    # Automatically synchronize nickname
    await auto_sync_nickname(message.author)

    # Keep normal bot commands working
    await bot.process_commands(message)


# ============================================================
# OPTIONAL COMMAND
# ============================================================

@bot.command()
@commands.has_permissions(manage_nicknames=True)
async def sync(ctx):
    """
    Manually synchronize your own nickname.
    """

    if not isinstance(ctx.author, discord.Member):
        return

    # Remove cooldown for manual synchronization
    last_sync.pop(ctx.author.id, None)

    await auto_sync_nickname(ctx.author)

    await ctx.send(
        "Nickname synchronization attempted.",
        delete_after=5
    )


# ============================================================
# ERROR HANDLER
# ============================================================

@sync.error
async def sync_error(ctx, error):

    if isinstance(error, commands.MissingPermissions):
        await ctx.send(
            "You need the Manage Nicknames permission to use this command.",
            delete_after=5
        )


# ============================================================
# START BOT
# ============================================================

if __name__ == "__main__":

    if not TOKEN:
        print(
            "FATAL EXCEPTION: DISCORD_TOKEN is missing.\n"
            "Set the DISCORD_TOKEN environment variable or "
            "GitHub Actions secret."
        )
        raise SystemExit(1)

    print("Starting Discord bot...")

    bot.run(TOKEN)
