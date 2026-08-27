import os
import asyncio
import discord
import aiohttp

from discord.ext import commands, tasks


# ============================================================
# CONFIG
# ============================================================

TOKEN = os.getenv("DISCORD_TOKEN")

SYNC_INTERVAL = 30

# IMPORTANT:
# This is the endpoint your original script was attempting to use.
# It MUST be replaced with the actual Rover API endpoint if
# Rover does not expose this endpoint.
ROVER_API_URL = "https://rover.link/api/user/{discord_id}"


# ============================================================
# INTENTS
# ============================================================

intents = discord.Intents.default()

intents.members = True
intents.message_content = True


# ============================================================
# BOT
# ============================================================

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    help_command=None
)


# ============================================================
# HTTP SESSION
# ============================================================

http_session = None


async def get_session():

    global http_session

    if http_session is None or http_session.closed:

        timeout = aiohttp.ClientTimeout(total=10)

        http_session = aiohttp.ClientSession(
            timeout=timeout
        )

    return http_session


# ============================================================
# ROVER LOOKUP
# ============================================================

async def get_rover_user(discord_id):

    session = await get_session()

    url = ROVER_API_URL.format(
        discord_id=discord_id
    )

    try:

        async with session.get(url) as response:

            if response.status != 200:

                print(
                    f"[ROVER] HTTP {response.status} "
                    f"for Discord ID {discord_id}"
                )

                return None

            try:

                data = await response.json()

            except Exception:

                print(
                    "[ROVER] Response was not valid JSON."
                )

                return None

            return data

    except asyncio.TimeoutError:

        print(
            f"[ROVER] Timeout for {discord_id}"
        )

        return None

    except aiohttp.ClientError as error:

        print(
            f"[ROVER] HTTP error: {error}"
        )

        return None

    except Exception as error:

        print(
            f"[ROVER] Error: {error}"
        )

        return None


# ============================================================
# GET ROBLOX USERNAME
# ============================================================

async def get_roblox_username(discord_id):

    data = await get_rover_user(
        discord_id
    )

    if not data:
        return None

    username = data.get(
        "robloxUsername"
    )

    if username:
        return username

    # Support some common alternative response names.
    username = data.get(
        "username"
    )

    if username:
        return username

    return None


# ============================================================
# SYNCHRONIZE MEMBER
# ============================================================

async def sync_member(member):

    if member.bot:
        return

    if member.guild is None:
        return

    roblox_username = await get_roblox_username(
        member.id
    )

    if not roblox_username:
        return

    # Already correct
    if member.nick == roblox_username:
        return

    # Check role hierarchy before attempting edit
    if member == member.guild.owner:
        print(
            f"[SYNC] Cannot rename server owner: "
            f"{member}"
        )
        return

    if member.top_role >= member.guild.me.top_role:
        print(
            f"[SYNC] Bot role is not high enough for: "
            f"{member}"
        )
        return

    try:

        await member.edit(
            nick=roblox_username,
            reason="Automatic Roblox nickname synchronization"
        )

        print(
            f"[SYNC] {member} -> {roblox_username}"
        )

    except discord.Forbidden:

        print(
            f"[SYNC] Permission denied for {member}"
        )

    except discord.HTTPException as error:

        print(
            f"[SYNC] Discord error for {member}: "
            f"{error}"
        )

    except Exception as error:

        print(
            f"[SYNC] Unexpected error for {member}: "
            f"{error}"
        )


# ============================================================
# AUTOMATIC 30 SECOND SYNC
# ============================================================

@tasks.loop(seconds=SYNC_INTERVAL)
async def automatic_sync():

    print(
        "[AUTO SYNC] Checking all servers..."
    )

    for guild in bot.guilds:

        print(
            f"[AUTO SYNC] Checking {guild.name}"
        )

        for member in guild.members:

            try:

                await sync_member(member)

            except Exception as error:

                print(
                    f"[AUTO SYNC] Error with "
                    f"{member}: {error}"
                )

            # Avoid hammering the API
            await asyncio.sleep(0.05)


# ============================================================
# WAIT UNTIL BOT IS READY
# ============================================================

@automatic_sync.before_loop
async def before_automatic_sync():

    await bot.wait_until_ready()


# ============================================================
# /syncpfp
# ============================================================

@bot.tree.command(
    name="syncpfp",
    description="Sync your Discord server nickname with your Roblox account."
)
async def syncpfp(
    interaction: discord.Interaction
):

    if interaction.guild is None:

        await interaction.response.send_message(
            "This command can only be used in a server.",
            ephemeral=True
        )

        return

    member = interaction.guild.get_member(
        interaction.user.id
    )

    if member is None:

        await interaction.response.send_message(
            "I couldn't find your server member profile.",
            ephemeral=True
        )

        return

    await interaction.response.defer(
        ephemeral=True
    )

    username = await get_roblox_username(
        member.id
    )

    if not username:

        await interaction.followup.send(
            "I couldn't find a Roblox account linked to your Discord account.",
            ephemeral=True
        )

        return

    if member == interaction.guild.owner:

        await interaction.followup.send(
            "I can't change the server owner's nickname.",
            ephemeral=True
        )

        return

    if member.top_role >= interaction.guild.me.top_role:

        await interaction.followup.send(
            "My bot role must be above your highest role.",
            ephemeral=True
        )

        return

    try:

        await member.edit(
            nick=username,
            reason="Manual Roblox nickname synchronization"
        )

        await interaction.followup.send(
            f"Synced your nickname to **{username}**.",
            ephemeral=True
        )

    except discord.Forbidden:

        await interaction.followup.send(
            "Discord denied the nickname change. "
            "Check my Manage Nicknames permission and role hierarchy.",
            ephemeral=True
        )

    except discord.HTTPException as error:

        print(
            f"[SYNC PFP] Discord error: {error}"
        )

        await interaction.followup.send(
            "Discord rejected the nickname change.",
            ephemeral=True
        )


# ============================================================
# READY
# ============================================================

@bot.event
async def on_ready():

    print("========================================")
    print("BOT ONLINE")
    print(f"Bot: {bot.user}")
    print(f"Bot ID: {bot.user.id}")
    print("========================================")

    try:

        synced = await bot.tree.sync()

        print(
            f"Slash commands synced: {len(synced)}"
        )

        for command in synced:

            print(
                f"  /{command.name}"
            )

    except Exception as error:

        print(
            f"Slash command sync failed: {error}"
        )

    if not automatic_sync.is_running():

        automatic_sync.start()

        print(
            "30-second automatic sync started."
        )


# ============================================================
# CLEANUP
# ============================================================

@bot.event
async def on_close():

    global http_session

    if http_session is not None:

        await http_session.close()

        http_session = None


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    if not TOKEN:

        print(
            "ERROR: DISCORD_TOKEN is missing."
        )

        raise SystemExit(1)

    print(
        "Starting bot..."
    )

    bot.run(TOKEN)
