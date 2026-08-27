import discord
from discord.ext import commands
import requests
import io
import os

# 1. Force explicitly loaded intents configuration
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

@bot.event
async def on_ready():
    print(f"STATUS LOG: Connected to Discord API Gateway.")
    print(f"LOGGED IN AS: {bot.user.name}#{bot.user.discriminator}")

@bot.command(name="syncpfp")
async def syncpfp(ctx):
    """Fetches the sender's Roblox avatar free without Bloxlink."""
    discord_user_id = ctx.author.id
    
    # Instant visual verification to prove the bot reads the channel feed
    await ctx.send("⏳ Connected! Querying registry database...")

    # Step 1: Query the updated public RoVer directory registry API
    rover_url = f"https://rover.link{discord_user_id}"
    
    try:
        rover_resp = requests.get(rover_url)
        
        if rover_resp.status_code != 200:
            await ctx.send("❌ Error: Could not reach the verification registry server database.")
            return
            
        data_payload = rover_resp.json()
        roblox_id = data_payload.get("robloxId")
        
        if not roblox_id:
            await ctx.send("❌ Error: Your profile isn't linked to a Roblox account on rover.link.")
            return

        # Step 2: Grab the exact image payload URL string array structure
        roblox_api = f"https://roblox.com{roblox_id}&size=150x150&format=Png&isCircular=false"
        roblox_data = requests.get(roblox_api).json()
        raw_image_url = roblox_data['data'][0]['imageUrl']  # Explicitly targeting index 0 of the matching data block

        # Step 3: Stream payload directly into the profile avatar slot
        image_stream = requests.get(raw_image_url).content
        byte_buffer = io.BytesIO(image_stream)

        await bot.user.edit(avatar=byte_buffer.read())
        await ctx.send("🎯 Success! Bot profile picture updated.")

    except Exception as error:
        await ctx.send(f"⚠️ API Process Error: `{str(error)}`")

# Start execution process
if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if token:
        bot.run(token)
    else:
        print("CRITICAL ERROR: DISCORD_TOKEN environmental secret is missing.")
