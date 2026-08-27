import discord
from discord.ext import commands
import requests
import io
import os

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

@bot.event
async def on_ready():
    # These prints will directly output inside your GitHub Actions console log window
    print("----------------------------------------")
    print(f"STATUS LOG: Bot is officially connected to Discord.")
    print(f"LOGGED IN AS: {bot.user.name}")
    print("----------------------------------------")

@bot.command(name="syncpfp")
async def syncpfp(ctx):
    """Fetches the sender's Roblox avatar and updates the bot's PFP."""
    discord_user_id = ctx.author.id
    await ctx.send("⏳ Connected! Querying registry database...")

    rover_url = f"https://rover.link{discord_user_id}"
    
    try:
        rover_resp = requests.get(rover_url)
        if rover_resp.status_code != 200:
            await ctx.send("❌ Error: Verification registry server cannot be reached.")
            return
            
        data_payload = rover_resp.json()
        roblox_id = data_payload.get("robloxId")
        
        if not roblox_id:
            await ctx.send("❌ Error: Your profile isn't linked to a Roblox account on rover.link.")
            return

        roblox_api = f"https://roblox.com{roblox_id}&size=150x150&format=Png&isCircular=false"
        roblox_data = requests.get(roblox_api).json()
        raw_image_url = roblox_data['data'][0]['imageUrl']

        image_stream = requests.get(raw_image_url).content
        byte_buffer = io.BytesIO(image_stream)

        await bot.user.edit(avatar=byte_buffer.read())
        await ctx.send("🎯 Success! Bot profile picture updated.")

    except Exception as error:
        await ctx.send(f"⚠️ API Process Error: `{str(error)}`")

if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if token:
        bot.run(token)
    else:
        print("CRITICAL ERROR: DISCORD_TOKEN environmental secret is missing.")
