import discord
from discord.ext import commands
import requests
import io
import os

# 1. Load exact required gateway intents
intents = discord.Intents.default()
intents.members = True          # Absolute requirement to edit server profiles
intents.message_content = True  # Absolute requirement to read the message trigger

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

async def perform_sync(member: discord.Member):
    """Core function to find a user's Roblox link and update their server look."""
    if member.bot:
        return

    # Hit the public unauthenticated lookup proxy directly
    rover_url = f"https://rover.link{member.id}"
    
    try:
        response = requests.get(rover_url)
        if response.status_code != 200:
            return  # Exit quietly if the user has never linked at rover.link
            
        payload = response.json()
        roblox_id = payload.get("robloxId")
        roblox_username = payload.get("robloxUsername")
        
        if not roblox_id:
            return

        # Fetch the official headshot image url string from Roblox metadata
        roblox_api = f"https://roblox.com{roblox_id}&size=150x150&format=Png&isCircular=false"
        roblox_data = requests.get(roblox_api).json()
        raw_image_url = roblox_data['data'][0]['imageUrl'] # Mapped to array index 0 to pull the raw string directly

        # Download the image bytes straight into memory
        img_bytes = requests.get(raw_image_url).content
        byte_buffer = io.BytesIO(img_bytes)

        # Force edit the user's nickname and server-specific avatar
        if roblox_username and member.nick != roblox_username:
            try:
                await member.edit(nick=roblox_username)
            except discord.Forbidden:
                print(f"HIERARCHY ERROR: Bot role is too low to change nickname for {member.name}")

        try:
            await member.edit(avatar=byte_buffer.read())
            print(f"SUCCESS: Automatically synchronized profile for {member.name}")
        except discord.Forbidden:
            print(f"HIERARCHY ERROR: Bot role is too low to change profile picture for {member.name}")

    except Exception as error:
        print(f"CRASH SHIELD: Handled background error: {str(error)}")


@bot.event
async def on_ready():
    print("----------------------------------------")
    print(f"LIVE LOG: Bot is authenticated as {bot.user.name}")
    print("AUTOMATION: Listening for message activity triggers...")
    print("----------------------------------------")


@bot.event
async def on_message(message):
    """Triggers automatically the exact split-second any user chats."""
    # Prevent bot feedback loops and ignore direct messages (DMs)
    if message.author.bot or not message.guild:
        return

    # Pull the sender as a Member object and pass it to the synchronization sync
    await perform_sync(message.author)


if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if token:
        bot.run(token)
    else:
        print("FATAL EXCEPTION: DISCORD_TOKEN is completely missing from GitHub Secrets.")
