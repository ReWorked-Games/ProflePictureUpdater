import discord
from discord.ext import commands
import requests
import io
import os

# Initialize your custom bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Pull the secret token stored safely in GitHub Environments
DISCORD_BOT_TOKEN = os.getenv("DISCORD_TOKEN")

@bot.command()
async def syncpfp(ctx):
    """Fetches the sender's Roblox avatar free without Bloxlink."""
    discord_user_id = ctx.author.id
    await ctx.send("🔄 Fetching your linked Roblox ID...")

    # Step 1: Get the Roblox ID using the public RoVer registry API
    rover_url = f"https://registry.rover.link/api/guilds/{ctx.guild.id}/discord-to-roblox/{discord_user_id}"
    
    try:
        rover_resp = requests.get(rover_url).json()
        roblox_id = rover_resp.get("robloxId")
        
        if not roblox_id:
            await ctx.send("❌ Could not find a Roblox account linked to your Discord profile.")
            return

        # Step 2: Grab the actual image URL string directly from Roblox APIs
        roblox_api = f"https://roblox.com{roblox_id}&size=150x150&format=Png&isCircular=false"
        roblox_data = requests.get(roblox_api).json()
        raw_image_url = roblox_data['data'][0]['imageUrl'] # Extracted string from payload array

        # Step 3: Stream image bytes and overwrite your bot's profile picture
        image_stream = requests.get(raw_image_url).content
        byte_buffer = io.BytesIO(image_stream)

        await bot.user.edit(avatar=byte_buffer.read())
        await ctx.send("🎯 Bot profile picture updated successfully using your Roblox avatar!")

    except Exception as error:
        await ctx.send(f"⚠️ Failed to update avatar. Error details: `{str(error)}`")

bot.run(DISCORD_BOT_TOKEN)
