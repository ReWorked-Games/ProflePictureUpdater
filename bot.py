import discord
from discord.ext import commands
import requests
import io
import os
import asyncio

# 1. Initialize custom bot with explicit gateway flags
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name} ({bot.user.id})")
    print("Bot is fully connected and listening for messages.")

@bot.command(name="syncpfp")
async def syncpfp(ctx):
    """Fetches the sender's Roblox avatar and overwrites the bot's PFP."""
    discord_user_id = ctx.author.id
    
    # Send immediate confirmation to prove the bot reads the message text
    await ctx.send("⏳ Connected! Querying registry database...")

    # Step 1: Query the registry API
    rover_url = f"https://rover.link{discord_user_id}"
    
    try:
        rover_resp = requests.get(rover_url).json()
        roblox_id = rover_resp.get("robloxId")
        
        if not roblox_id:
            await ctx.send("❌ Error: Could not find a Roblox account linked to your Discord profile via RoVer.")
            return

        # Step 2: Grab the exact image payload URL string
        roblox_api = f"https://roblox.com{roblox_id}&size=150x150&format=Png&isCircular=false"
        roblox_data = requests.get(roblox_api).json()
        raw_image_url = roblox_data['data'][0]['imageUrl']  # Target array index matching standard layout

        # Step 3: Stream payload directly into the profile avatar slot
        image_stream = requests.get(raw_image_url).content
        byte_buffer = io.BytesIO(image_stream)

        await bot.user.edit(avatar=byte_buffer.read())
        await ctx.send("🎯 Success! Bot profile picture updated.")

    except Exception as error:
        await ctx.send(f"⚠️ API Process Error: `{str(error)}`")

# Force execution through a clean environmental check
if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if token:
        bot.run(token)
    else:
        print("Error: DISCORD_TOKEN environment variable is missing.")
