import discord
from discord.ext import commands
import aiohttp
import io
import os

# 1. Initialize exact intents required for tracking text strings and profiles
intents = discord.Intents.default()
intents.members = True          # Allows changing server avatars and names
intents.message_content = True  # Allows catching chat message activity triggers

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

async def auto_sync_profile(member: discord.Member):
    """Asynchronous background worker that safely pulls linked Roblox assets."""
    if member.bot:
        return

    # Use a non-blocking asynchronous session handler
    async with aiohttp.ClientSession() as session:
        # Step 1: Query the unauthenticated RoVer proxy registry using aiohttp
        rover_url = f"https://rover.link{member.id}"
        
        try:
            async with session.get(rover_url) as rover_resp:
                if rover_resp.status != 200:
                    return  # Fail quietly if the user has never linked on rover.link
                
                data_payload = await rover_resp.json()
                roblox_id = data_payload.get("robloxId")
                roblox_username = data_payload.get("robloxUsername")

            if not roblox_id:
                return

            # Step 2: Request the image string array safely from the official Roblox CDN endpoints
            roblox_api = f"https://roblox.com{roblox_id}&size=150x150&format=Png&isCircular=false"
            async with session.get(roblox_api) as roblox_resp:
                if roblox_resp.status != 200:
                    return
                
                roblox_data = await roblox_resp.json()
                raw_image_url = roblox_data['data'][0]['imageUrl']  # Target explicit index 0 wrapper mapping

            # Step 3: Stream the raw picture asset download cleanly into a memory buffer
            async with session.get(raw_image_url) as img_resp:
                if img_resp.status != 200:
                    return
                img_bytes = await img_resp.read()
                byte_buffer = io.BytesIO(img_bytes)

            # Step 4: Execute server-specific profile upgrades safely
            # Changes their server nickname to match their Roblox account name
            if roblox_username and member.nick != roblox_username:
                try:
                    await member.edit(nick=roblox_username)
                except discord.Forbidden:
                    print(f"HIERARCHY EXCEPTION: Cannot rename {member.name} (Owner or higher role).")

            # Updates their server-specific avatar image inside this server
            try:
                await member.edit(avatar=byte_buffer.read())
                print(f"AUTOMATION SUCCESS: Synced profile assets for {member.name}.")
            except discord.Forbidden:
                print(f"HIERARCHY EXCEPTION: Cannot update avatar image for {member.name}.")

        except Exception as error:
            print(f"BACKGROUND CRASH SHIELD: Handled connection event anomaly: {str(error)}")


@bot.event
async def on_ready():
    print("----------------------------------------")
    print(f"LIVE LOG: Bot has authenticated as {bot.user.name}")
    print("STATUS: Active and waiting for message activity triggers...")
    print("----------------------------------------")


@bot.event
async def on_message(message):
    """Triggers automatically the exact split-second any member sends a normal message."""
    # Ignore bot accounts and ignore direct messages (DMs)
    if message.author.bot or not message.guild:
        return

    # Pass the member object straight into our asynchronous lookup pipeline
    await auto_sync_profile(message.author)


if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if token:
        bot.run(token)
    else:
        print("CRITICAL LOG: DISCORD_TOKEN is missing inside your GitHub Environments.")
