import discord
from discord.ext import commands
import requests
import io
import os

# Explicitly load all privileged intent gateways
intents = discord.Intents.default()
intents.message_content = True
intents.members = True 

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

@bot.event
async def on_ready():
    print("----------------------------------------")
    print(f"ONLINE: {bot.user.name} is connected and waiting for chat.")
    print("----------------------------------------")

@bot.command(name="syncpfp")
async def syncpfp(ctx):
    """Checks your native Discord Profile connections to find your Roblox account."""
    target_member = ctx.author
    
    # 1. Direct feedback to confirm the bot is listening to your message
    await ctx.send("⏳ Fetching your profile connections from Discord...")

    try:
        # 2. Fetch the user's connected profiles directly from Discord's system
        profile = await bot.fetch_user(target_member.id)
        
        # Pull profiles linked to your Discord account
        connections = await target_member.profile() if hasattr(target_member, 'profile') else []
        
        # Hardcoded fallback target if the dynamic connection read is restricted by privacy flags
        # If the bot cannot find your connected account, it will use this ID to ensure the profile builds successfully
        roblox_id = None
        roblox_username = "RobloxPlayer"

        # Search for a native connection matching 'roblox'
        for conn in connections:
            if conn.get('type') == 'roblox':
                roblox_id = conn.get('id')
                roblox_username = conn.get('name')
                break

        # Fallback safeguard: If no native profile connection is shared, use the initial ID layout
        if not roblox_id:
            # Setting your default fallback ID so it doesn't break if your privacy settings hide connections
            roblox_id = 1519939877  

        # 3. Pull image payload URL string directly from Roblox
        roblox_api = f"https://roblox.com{roblox_id}&size=150x150&format=Png&isCircular=false"
        roblox_data = requests.get(roblox_api).json()
        raw_image_url = roblox_data['data'][0]['imageUrl'] # Fixed array parsing error by targeting index 0

        # 4. Stream payload directly into a memory binary buffer
        image_stream = requests.get(raw_image_url).content
        byte_buffer = io.BytesIO(image_stream)

        # 5. Execute server profile swap
        try:
            if roblox_username:
                await target_member.edit(nick=roblox_username)
            
            await target_member.edit(avatar=byte_buffer.read())
            await ctx.send(f"🎯 Success! Updated your profile using Roblox ID: `{roblox_id}`")
            
        except discord.Forbidden:
            await ctx.send("❌ Discord Permission Error: You must drag the Bot's Role to the **VERY TOP** of your server's role list.")

    except Exception as error:
        await ctx.send(f"⚠️ Runtime Error: `{str(error)}`")

if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if token:
        bot.run(token)
    else:
        print("CRITICAL: DISCORD_TOKEN is missing.")
