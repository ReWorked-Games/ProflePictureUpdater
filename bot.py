import discord
from discord.ext import commands
import requests
import io
import os

intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # Required to modify server members

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

@bot.event
async def on_ready():
    print("----------------------------------------")
    print(f"STATUS LOG: Connected to Discord API Gateway.")
    print(f"LOGGED IN AS: {bot.user.name}")
    print("----------------------------------------")

@bot.command(name="syncpfp")
async def syncpfp(ctx):
    """Fetches the sender's Roblox avatar and updates THE SENDER'S server profile."""
    discord_user_id = ctx.author.id
    target_member = ctx.author  # The user who ran the command
    
    await ctx.send("⏳ Fetching your Roblox data to update YOUR server profile...")

    # Step 1: Query the public RoVer registry API
    rover_url = f"https://rover.link{discord_user_id}"
    
    try:
        rover_resp = requests.get(rover_url)
        if rover_resp.status_code != 200:
            await ctx.send("❌ Error: Verification registry database cannot be reached.")
            return
            
        data_payload = rover_resp.json()
        roblox_id = data_payload.get("robloxId")
        roblox_username = data_payload.get("robloxUsername")
        
        if not roblox_id:
            await ctx.send("❌ Error: Your account isn't linked to a Roblox profile on rover.link.")
            return

        # Step 2: Grab the actual image payload URL string from Roblox
        roblox_api = f"https://roblox.com{roblox_id}&size=150x150&format=Png&isCircular=false"
        roblox_data = requests.get(roblox_api).json()
        raw_image_url = roblox_data['data']['imageUrl']

        # Step 3: Stream the image bytes into memory
        image_stream = requests.get(raw_image_url).content
        byte_buffer = io.BytesIO(image_stream)

        # Step 4: Update the SENDER'S server nickname and server avatar
        try:
            # Change their nickname in the server to match their Roblox name
            if roblox_username:
                await target_member.edit(nick=roblox_username)
            
            # Change their server-specific avatar
            await target_member.edit(avatar=byte_buffer.read())
            
            await ctx.send(f"🎯 Success! Updated your server profile to match Roblox user **{roblox_username}**.")
            
        except discord.Forbidden:
            await ctx.send("❌ Bot Permission Error: Ensure the bot's role is placed ABOVE your role in Server Settings, and that the bot has 'Manage Nicknames' and 'Manage Expressions/Guild Members' enabled.")

    except Exception as error:
        await ctx.send(f"⚠️ API Process Error: `{str(error)}`")

if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if token:
        bot.run(token)
else:
    print("CRITICAL ERROR: DISCORD_TOKEN environmental secret is missing.")
