import os
import asyncio
import discord
import aiohttp

from discord.ext import commands, tasks


# ============================================================
# CONFIGURATION
# ============================================================

TOKEN = os.getenv("DISCORD_TOKEN")

SYNC_INTERVAL = 30

# ------------------------------------------------------------
# IMPORTANT:
#
# Put the REAL RoVer endpoint you have access to here.
#
# This script expects the endpoint to return JSON containing
# the linked Roblox USERNAME.
#
# Example expected response:
#
# {
#     "robloxUsername": "Builderman"
# }
#
# Do NOT put the old:
# https://rover.link{member.id}
#
# there was no verified endpoint for that URL.
# ------------------------------------------------------------

ROVER_API_URL = os.getenv("ROVER_API_URL")


# ============================================================
# DISCORD INTENTS
# ============================================================

intents = discord.Intents.default()

intents.members = True
intents.message_content = True


# ============================================================
# BOT
# ============================================================

class RobloxSyncBot(commands.Bot):

    def __init__(self):

        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None
        )

    async def setup_hook(self):

        print("Registering slash commands...")

        try:

            commands_synced = await self.tree.sync()

            print(
                f"SUCCESS: Registered "
                f"{len(commands_synced)} slash command(s)."
            )

            for command in commands_synced:

                print(
                    f"  /{command.name}"
                )

        except Exception as error:

            print(
                f"SLASH COMMAND ERROR: {error}"
            )

        # Start the 30-second automatic updater

        if not automatic_sync.is_running():

            automatic_sync.start()

            print(
                "Automatic 30-second synchronization started."
            )


bot = RobloxSyncBot()


# ============================================================
# HTTP SESSION
# ============================================================

http_session = None


async def get_http_session():

    global http_session

    if http_session is None or http_session.closed:

        timeout = aiohttp.ClientTimeout(
            total=15
        )

        http_session = aiohttp.ClientSession(
            timeout=timeout
        )

    return http_session


# ============================================================
# ROVER
# ============================================================

async def get_rover_username(discord_id):

    if not ROVER_API_URL:

        print(
            "ROVER ERROR: ROVER_API_URL is not configured."
        )

        return None

    session = await get_http_session()

    url = ROVER_API_URL.format(
        discord_id=discord_id
    )

    try:

        async with session.get(url) as response:

            print(
                f"ROVER | Discord ID {discord_id} | "
                f"HTTP {response.status}"
            )

            if response.status != 200:

                return None

            data = await response.json()

            username = data.get(
                "robloxUsername"
            )

            if not username:

                username = data.get(
                    "username"
                )

            if not username:

                print(
                    f"ROVER | No Roblox username returned "
                    f"for {discord_id}"
                )

                return None

            return username

    except asyncio.TimeoutError:

        print(
            f"ROVER | Request timed out for {discord_id}"
        )

        return None

    except aiohttp.ClientError as error:

        print(
            f"ROVER | HTTP error: {error}"
        )

        return None

    except Exception as error:

        print(
            f"ROVER | Error: {error}"
        )

        return None


# ============================================================
# ROBLOX USERNAME → USER ID
# ============================================================

async def get_roblox_user_id(username):

    session = await get_http_session()

    url = (
        "https://users.roblox.com/v1/usernames/users"
    )

    payload = {

        "usernames": [
            username
        ],

        "excludeBannedUsers": False
    }

    try:

        async with session.post(
            url,
            json=payload
        ) as response:

            print(
                f"ROBLOX USER LOOKUP | "
                f"{username} | HTTP {response.status}"
            )

            if response.status != 200:

                return None

            data = await response.json()

            users = data.get(
                "data",
                []
            )

            if not users:

                print(
                    f"ROBLOX | User not found: {username}"
                )

                return None

            # Roblox returns the canonical username here.
            user = users[0]

            roblox_id = user.get(
                "id"
            )

            canonical_username = user.get(
                "name"
            )

            print(
                f"ROBLOX | "
                f"{canonical_username} = {roblox_id}"
            )

            return roblox_id

    except asyncio.TimeoutError:

        print(
            f"ROBLOX | Username lookup timed out: "
            f"{username}"
        )

        return None

    except aiohttp.ClientError as error:

        print(
            f"ROBLOX | HTTP error: {error}"
        )

        return None

    except Exception as error:

        print(
            f"ROBLOX | Lookup error: {error}"
        )

        return None


# ============================================================
# ROBLOX USER ID → AVATAR THUMBNAIL
# ============================================================

async def get_roblox_avatar_url(roblox_user_id):

    session = await get_http_session()

    url = (
        "https://thumbnails.roblox.com/v1/users/avatar-headshot"
        f"?userIds={roblox_user_id}"
        "&size=420x420"
        "&format=Png"
        "&isCircular=false"
    )

    try:

        async with session.get(url) as response:

            print(
                f"ROBLOX THUMBNAIL | "
                f"{roblox_user_id} | "
                f"HTTP {response.status}"
            )

            if response.status != 200:

                return None

            data = await response.json()

            results = data.get(
                "data",
                []
            )

            if not results:

                return None

            image_url = results[0].get(
                "imageUrl"
            )

            if image_url:

                print(
                    f"ROBLOX AVATAR URL: {image_url}"
                )

            return image_url

    except asyncio.TimeoutError:

        print(
            f"ROBLOX | Thumbnail request timed out: "
            f"{roblox_user_id}"
        )

        return None

    except aiohttp.ClientError as error:

        print(
            f"ROBLOX | Thumbnail HTTP error: "
            f"{error}"
        )

        return None

    except Exception as error:

        print(
            f"ROBLOX | Thumbnail error: "
            f"{error}"
        )

        return None


# ============================================================
# COMPLETE ROBLOX LOOKUP
# ============================================================

async def get_member_roblox_avatar(member):

    # 1. Discord ID
    discord_id = member.id

    # 2. Get linked Roblox USERNAME
    username = await get_rover_username(
        discord_id
    )

    if not username:

        return None

    print(
        f"LINKED ACCOUNT | "
        f"{member} -> Roblox username: {username}"
    )

    # 3. Username -> Roblox USER ID
    roblox_user_id = await get_roblox_user_id(
        username
    )

    if not roblox_user_id:

        return None

    # 4. Roblox USER ID -> avatar thumbnail
    avatar_url = await get_roblox_avatar_url(
        roblox_user_id
    )

    if not avatar_url:

        return None

    return {
        "username": username,
        "user_id": roblox_user_id,
        "avatar_url": avatar_url
    }


# ============================================================
# NICKNAME SYNCHRONIZATION
# ============================================================

async def sync_member(member):

    if member.bot:

        return

    if member.guild is None:

        return

    roblox_data = await get_member_roblox_avatar(
        member
    )

    if not roblox_data:

        return

    username = roblox_data["username"]

    avatar_url = roblox_data["avatar_url"]

    print(
        "----------------------------------------"
    )

    print(
        f"MEMBER: {member}"
    )

    print(
        f"ROBLOX USERNAME: {username}"
    )

    print(
        f"ROBLOX USER ID: {roblox_data['user_id']}"
    )

    print(
        f"ROBLOX AVATAR: {avatar_url}"
    )

    print(
        "----------------------------------------"
    )

    # Keep nickname synchronized where Discord permits it.

    if member == member.guild.owner:

        print(
            f"SYNC | Cannot change server owner's nickname."
        )

        return

    bot_member = member.guild.me

    if bot_member is None:

        return

    if member.top_role >= bot_member.top_role:

        print(
            f"SYNC | Bot role is not high enough for {member}."
        )

        return

    if member.nick != username:

        try:

            await member.edit(
                nick=username,
                reason="Roblox profile synchronization"
            )

            print(
                f"SYNC | Nickname changed: "
                f"{member} -> {username}"
            )

        except discord.Forbidden:

            print(
                f"SYNC | Discord denied nickname change "
                f"for {member}"
            )

        except discord.HTTPException as error:

            print(
                f"SYNC | Discord HTTP error: {error}"
            )


# ============================================================
# /syncpfp
# ============================================================

@bot.tree.command(
    name="syncpfp",
    description="Find your linked Roblox account and retrieve its current avatar."
)
async def syncpfp(
    interaction: discord.Interaction
):

    if interaction.guild is None:

        await interaction.response.send_message(
            "This command can only be used inside a server.",
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

    roblox_data = await get_member_roblox_avatar(
        member
    )

    if not roblox_data:

        await interaction.followup.send(
            "I couldn't find a linked Roblox account or its avatar.",
            ephemeral=True
        )

        return

    username = roblox_data["username"]

    roblox_id = roblox_data["user_id"]

    avatar_url = roblox_data["avatar_url"]

    # Discord cannot assign this URL to another member's
    # server avatar through the bot API.
    #
    # We therefore return the verified Roblox information
    # instead of pretending the unsupported Discord operation
    # succeeded.

    embed = discord.Embed(
        title="Roblox Profile Found",
        description=(
            f"**Username:** `{username}`\n"
            f"**User ID:** `{roblox_id}`"
        )
    )

    embed.set_thumbnail(
        url=avatar_url
    )

    embed.add_field(
        name="Roblox Avatar",
        value=avatar_url,
        inline=False
    )

    await interaction.followup.send(
        embed=embed,
        ephemeral=True
    )


# ============================================================
# AUTOMATIC 30 SECOND SYNC
# ============================================================

@tasks.loop(seconds=SYNC_INTERVAL)
async def automatic_sync():

    print(
        "========================================"
    )

    print(
        "AUTOMATIC SYNC | Starting 30-second scan"
    )

    print(
        "========================================"
    )

    for guild in bot.guilds:

        print(
            f"SERVER | {guild.name}"
        )

        for member in guild.members:

            try:

                await sync_member(
                    member
                )

            except Exception as error:

                print(
                    f"SYNC ERROR | "
                    f"{member} | {error}"
                )

            # Small delay to avoid making a huge burst
            # of requests.

            await asyncio.sleep(
                0.10
            )


# ============================================================
# WAIT FOR BOT
# ============================================================

@automatic_sync.before_loop
async def before_automatic_sync():

    await bot.wait_until_ready()


# ============================================================
# BOT READY
# ============================================================

@bot.event
async def on_ready():

    print(
        "========================================"
    )

    print(
        "BOT ONLINE"
    )

    print(
        f"Bot: {bot.user}"
    )

    print(
        f"Bot ID: {bot.user.id}"
    )

    print(
        "========================================"
    )


# ============================================================
# SHUTDOWN
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

    print(
        "Starting Discord bot..."
    )

    if not TOKEN:

        print(
            "FATAL ERROR: DISCORD_TOKEN is missing."
        )

        raise SystemExit(1)

    if not ROVER_API_URL:

        print(
            "WARNING: ROVER_API_URL is not configured."
        )

        print(
            "The Roblox username lookup cannot start "
            "until the linked-account source is configured."
        )

    bot.run(
        TOKEN
    )
