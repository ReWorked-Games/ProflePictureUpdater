import discord
from discord.ext import commands
import requests
import io
import os

# 1. Force load required gateway intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True 

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

@bot.event
async def on_ready():
    print("----------------------------------------")
    print(f"ONLINE: {bot.user.name} is running perfectly.")
    print("----------------------------------------")

@bot.command(name="syncpfp")
async def syncpfp(ctx):
    """Automatically finds the sender's linked Roblox account and applies it."""
    discord_user_id = ctx.author.id
    target_member = ctx.author

    # Instant confirmation that the command fired
    await ctx.send("⏳ Searching public registry for your connected Roblox account...")

    try:
        # Step 1: Query the unauthenticated, open RoVer Registry API for the executor's ID
        rover_url = f"https://rover.link{discord_user_id}"
        rover_resp = requests.get(rover_url)
        
        if rover_resp.status_code != 200:
            await ctx.send("❌ Error: You are not verified! Please link your account for free at https://rover.link first.")
            return
            
        data_payload = rover_resp.json()
        roblox_id = data_payload.get("robloxId")
        roblox_username = data_payload.get("robloxUsername")
        
        if not roblox_id:
            await ctx.send("❌ Error: No verified Roblox account found linked to your Discord profile.")
            return

        # Step 2: Grab the exact headshot image link belonging to THEIR verified account
        roblox_api = f"https://roblox.com{roblox_id}&size=150x150&format=Png&isCircular=false"
        roblox_data = requests.get(roblox_api).json()
        raw_image_url = roblox_data['data'][0]['imageUrl']

        # Step 3: Stream the image bytes directly into memory
        image_stream = requests.get(raw_image_url).content
        byte_buffer = io.BytesIO(image_stream)

        # Step 4: Securely apply it only to the user who ran the command
        try:
            # Changes their server nickname to match their verified Roblox name
            if roblox_username:
                await target_member.edit(nick=roblox_username)
            
            # Upgrades their server-specific profile picture
            await target_member.edit(avatar=byte_buffer.read())
            await ctx.send(f"🎯 Success! Updated your profile to match your verified Roblox account: **{roblox_username}** (`{roblox_id}`)")
            
        except discord.Forbidden:
            await ctx.send("❌ Discord Permission Error: Move the Bot's Role to the **VERY TOP** of your Server Settings role list, or it can't edit your profile.")

    except Exception as error:
        await ctx.send(f"⚠️ Process Crash Prevented: `{str(error)}`")

if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if token:
        bot.run(token)
    else:
        print("CRITICAL: DISCORD_TOKEN is missing.")
