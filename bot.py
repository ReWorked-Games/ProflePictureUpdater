import discord
from discord.ext import commands
import requests
import io
import os

# 1. Load required gateway intents
intents = discord.Intents.default()
intents.members = True          # Required to update server profiles
intents.message_content = True  # Required to read text activity triggers

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

async def auto_sync_profile(member: discord.Member):
    """Background helper that updates a user's server profile using their Roblox link."""
    if member.bot:
        return

    # Step 1: Query the unauthenticated public RoVer registry proxy
    rover_url = f"https://rover.link{member.id}"
    
    try:
        rover_resp = requests.get(rover_url)
        if rover_resp.status_code != 200:
            return  # Silently skip if user isn't verified on rover.link
            
        data_payload = rover_resp.json()
        roblox_id = data_payload.get("robloxId")
        roblox_username = data_payload.get("robloxUsername")
        
        if not roblox_id:
            return

        # Step 2: Grab the exact headshot image link belonging to their verified account
        roblox_api = f"https://roblox.com{roblox_id}&size=150x150&format=Png&isCircular=false"
        roblox_data = requests.get(roblox_api).json()
        raw_image_url = roblox_data['data'][0]['imageUrl']  # Target explicit index 0 array mapping

        # Step 3: Stream the image bytes directly into a memory buffer
        image_stream = requests.get(raw_image_url).content
        byte_buffer = io.BytesIO(image_stream)

        # Step 4: Silently update the member's server profile settings
        if roblox_username and member.nick != roblox_username:
            await member.edit(nick=roblox_username)
        
        await member.edit(avatar=byte_buffer.read())
        print(f"AUTOMATION SUCCESS: Synced {member.name} to Roblox account {roblox_username}")

    except discord.Forbidden:
        print(f"PERMISSION ERROR: Failed to edit {member.name}. Drag bot role higher.")
    except Exception as e:
        print(f"RUNTIME ERROR: {str(e)}")


@bot.event
async def on_ready():
    print("----------------------------------------")
    print(f"AUTOMATION ONLINE: Bot is watching for chat messages.")
    print("----------------------------------------")


@bot.event
async def on_member_join(member: discord.Member):
    """Triggers automatically the exact second someone joins your server."""
    await auto_sync_profile(member)


@bot.event
async def on_message(message):
    """Triggers automatically every single time a user types a normal message."""
    # Fixed syntax error: 'message' object is passed here, not a Member object
    if message.author.bot or not message.guild:
        return
        
    # Process the silent background update on the person who chatted
    await auto_sync_profile(message.author)
    
    # Process any standard commands if needed
    await bot.process_commands(message)


if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if token:
        bot.run(token)
    else:
        print("CRITICAL ERROR: DISCORD_TOKEN environmental secret is missing.")
