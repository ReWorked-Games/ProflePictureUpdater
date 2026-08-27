import os
import asyncio

import aiohttp
import discord

from discord.ext import commands, tasks


# ============================================================
# CONFIG
# ============================================================

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
BLOXLINK_API_KEY = os.getenv("BLOXLINK_API_KEY")
BLOXLINK_GUILD_ID = os.getenv("BLOXLINK_GUILD_ID")

SYNC_INTERVAL = 30


# ============================================================
# VALIDATE CONFIG
# ============================================================

if not DISCORD_TOKEN:
    print("FATAL ERROR: DISCORD_TOKEN is missing.")
    raise SystemExit(1)

if not BLOXLINK_API_KEY:
    print("FATAL ERROR: BLOXLINK_API_KEY is missing.")
    raise SystemExit(1)


# ============================================================
# DISCORD INTENTS
# ============================================================

intents = discord.Intents.default()

intents.members = True
intents.message_content = True


# ============================================================
# BOT
# ============================================================

class RobloxProfileBot(commands.Bot):

    def __init__(self):

        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None
        )

    async def setup_hook(self):

        print("Registering slash commands...")

        try:

            synced = await self.tree.sync()

            print(
                f"SUCCESS: Registered {len(synced)} slash command(s)."
            )

            for command in synced:

                print(
                    f"  /{command.name}"
                )

        except Exception as error:

            print(
                f"SLASH COMMAND ERROR: {error}"
            )

        if not automatic_sync.is_running():

            automatic_sync.start()

            print(
                "30-second automatic sync started."
            )


bot = RobloxProfileBot()


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
# BLOXLINK
# DISCORD USER -> ROBLOX USER ID
# ============================================================

async def get_bloxlink_roblox_id(
    guild_id,
    discord_user_id
):

    session = await get_http_session()

    url = (
        "https://api.blox.link/v4/public/guilds/"
        f"{guild_id}/discord-to-roblox/{discord_user_id}"
    )

    headers = {
        "Authorization": BLOXLINK_API_KEY
    }

    try:

        async with session.get(
            url,
            headers=headers
        ) as response:

            body = await response.text()

            print("========================================")
            print("BLOXLINK DEBUG")
            print(f"Guild ID: {guild_id}")
            print(f"Discord ID: {discord_user_id}")
            print(f"HTTP STATUS: {response.status}")
            print(f"RESPONSE: {body}")
            print("========================================")

            if response.status != 200:

                return None

            try:

                data = await response.json()

            except Exception as error:

                print(
                    f"BLOXLINK JSON ERROR: {error}"
                )

                return None

            roblox_id = data.get("robloxID")

            if not roblox_id:

                print(
                    "BLOXLINK: No robloxID was returned."
                )

                return None

            print(
                f"BLOXLINK: Roblox ID = {roblox_id}"
            )

            return int(roblox_id)

    except Exception as error:

        print(
            f"BLOXLINK ERROR: {error}"
        )

        return None


# ============================================================
# ROBLOX
# USER ID -> USERNAME
# ============================================================

async def get_roblox_user(
    roblox_id: int
):

    session = await get_http_session()

    url = (
        "https://users.roblox.com/v1/users/"
        f"{roblox_id}"
    )

    try:

        async with session.get(url) as response:

            print(
                f"ROBLOX USER | "
                f"{roblox_id} | "
                f"HTTP {response.status}"
            )

            if response.status != 200:

                return None

            data = await response.json()

            return {
                "id": data.get("id"),
                "name": data.get("name"),
                "displayName": data.get("displayName")
            }

    except Exception as error:

        print(
            f"ROBLOX USER ERROR: {error}"
        )

        return None


# ============================================================
# ROBLOX
# USER ID -> AVATAR
# ============================================================

async def get_roblox_avatar(
    roblox_id: int
):

    session = await get_http_session()

    url = (
        "https://thumbnails.roblox.com/v1/users/avatar-headshot"
        f"?userIds={roblox_id}"
        "&size=420x420"
        "&format=Png"
        "&isCircular=false"
    )

    try:

        async with session.get(url) as response:

            print(
                f"ROBLOX AVATAR | "
                f"{roblox_id} | "
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

            return image_url

    except Exception as error:

        print(
            f"ROBLOX AVATAR ERROR: {error}"
        )

        return None


# ============================================================
# COMPLETE MEMBER LOOKUP
# ============================================================

async def lookup_member(member):

    print("----------------------------------------")

    print(
        f"LOOKUP: {member} "
        f"({member.id})"
    )

    # --------------------------------------------------------
    # Bloxlink
    # --------------------------------------------------------

    roblox_id = await get_bloxlink_roblox_id(
        member.guild.id,
        member.id
    )

    if not roblox_id:

        print(
            "RESULT: No Bloxlink Roblox account."
        )

        print("----------------------------------------")

        return None

    # --------------------------------------------------------
    # Roblox user
    # --------------------------------------------------------

    roblox_user = await get_roblox_user(
        roblox_id
    )

    if not roblox_user:

        print(
            "RESULT: Roblox user could not be retrieved."
        )

        return None

    # --------------------------------------------------------
    # Roblox avatar
    # --------------------------------------------------------

    avatar_url = await get_roblox_avatar(
        roblox_id
    )

    if not avatar_url:

        print(
            "RESULT: Roblox avatar could not be retrieved."
        )

        return None

    result = {
        "roblox_id": roblox_id,
        "username": roblox_user["name"],
        "display_name": roblox_user["displayName"],
        "avatar_url": avatar_url
    }

    print(
        f"ROBLOX USERNAME: {result['username']}"
    )

    print(
        f"ROBLOX DISPLAY NAME: {result['display_name']}"
    )

    print(
        f"ROBLOX ID: {result['roblox_id']}"
    )

    print(
        f"ROBLOX AVATAR: {result['avatar_url']}"
    )

    print("----------------------------------------")

    return result


# ============================================================
# APPLY ROBLOX PROFILE TO DISCORD SERVER MEMBER
# ============================================================

async def apply_roblox_profile(
    member,
    result
):

    # ========================================================
    # CHANGE SERVER NICKNAME
    #
    # IMPORTANT:
    # This does NOT change the user's actual Discord account.
    #
    # It changes their nickname only inside this server.
    # ========================================================

    desired_nickname = result["username"]

    # Discord nickname limit
    if len(desired_nickname) > 32:

        desired_nickname = desired_nickname[:32]

    # Don't repeatedly edit the member
    if member.display_name != desired_nickname:

        try:

            await member.edit(
                nick=desired_nickname,
                reason="Automatic Roblox/Bloxlink profile sync"
            )

            print(
                f"NICKNAME UPDATED | "
                f"{member} -> {desired_nickname}"
            )

        except discord.Forbidden:

            print(
                f"NICKNAME ERROR | "
                f"{member} | Bot does not have permission."
            )

        except discord.HTTPException as error:

            print(
                f"NICKNAME HTTP ERROR | "
                f"{member} | {error}"
            )

        except Exception as error:

            print(
                f"NICKNAME ERROR | "
                f"{member} | {error}"
            )

    else:

        print(
            f"NICKNAME ALREADY CORRECT | "
            f"{member}"
        )


# ============================================================
# /syncpfp
# ============================================================

@bot.tree.command(
    name="syncpfp",
    description="Sync your Discord server profile with your Bloxlink Roblox account."
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

    await interaction.response.defer(
        ephemeral=True
    )

    member = interaction.guild.get_member(
        interaction.user.id
    )

    if member is None:

        await interaction.followup.send(
            "I couldn't find your server profile.",
            ephemeral=True
        )

        return

    result = await lookup_member(
        member
    )

    if not result:

        await interaction.followup.send(
            "I couldn't find a Bloxlink-linked Roblox account for you.",
            ephemeral=True
        )

        return

    # ========================================================
    # APPLY ROBLOX USERNAME AS DISCORD SERVER NICKNAME
    # ========================================================

    await apply_roblox_profile(
        member,
        result
    )

    # ========================================================
    # EMBED
    # ========================================================

    embed = discord.Embed(
        title="Roblox Profile Synced",
        description=(
            f"**Discord User:** {member.mention}\n\n"
            f"**Username:** `{result['username']}`\n"
            f"**Display Name:** `{result['display_name']}`\n"
            f"**Roblox ID:** `{result['roblox_id']}`"
        )
    )

    embed.set_thumbnail(
        url=result["avatar_url"]
    )

    embed.add_field(
        name="Roblox Avatar URL",
        value=result["avatar_url"],
        inline=False
    )

    embed.set_footer(
        text="Bloxlink → Roblox → Discord Server Profile"
    )

    await interaction.followup.send(
        embed=embed,
        ephemeral=True
    )


# ============================================================
# AUTOMATIC 30 SECOND CHECK
# ============================================================

@tasks.loop(seconds=SYNC_INTERVAL)
async def automatic_sync():

    print("========================================")
    print("30 SECOND SCAN")
    print("========================================")

    for guild in bot.guilds:

        print(
            f"SERVER: {guild.name} "
            f"({guild.id})"
        )

        for member in guild.members:

            if member.bot:
                continue

            try:

                result = await lookup_member(
                    member
                )

                if result:

                    # ----------------------------------------
                    # APPLY ROBLOX PROFILE
                    # ----------------------------------------

                    await apply_roblox_profile(
                        member,
                        result
                    )

                    print(
                        f"SYNC READY | "
                        f"{member} → "
                        f"{result['username']} | "
                        f"{result['avatar_url']}"
                    )

            except Exception as error:

                print(
                    f"MEMBER ERROR | "
                    f"{member} | {error}"
                )

            await asyncio.sleep(
                0.1
            )


# ============================================================
# WAIT UNTIL BOT IS READY
# ============================================================

@automatic_sync.before_loop
async def before_automatic_sync():

    await bot.wait_until_ready()


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


# ============================================================
# SHUTDOWN HTTP SESSION
# ============================================================

@bot.event
async def on_disconnect():

    global http_session

    if http_session and not http_session.closed:

        await http_session.close()

        http_session = None


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    print(
        "Starting Discord bot..."
    )

    bot.run(
        DISCORD_TOKEN
    )
