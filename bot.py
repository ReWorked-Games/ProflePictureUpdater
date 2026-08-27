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
    print("----------------------------------------")
    print(f"ONLINE: {bot.user.name} is listening for commands.")
    print("----------------------------------------")

@bot.command(name="syncpfp")
async def syncpfp(ctx):
    """Fetches the sender's Roblox avatar and updates their server profile."""
    discord_user_id = ctx.author.id
    target_member = ctx.author
    
    # 1. Immediate chat confirmation to verify the bot reads the channel feed
    await ctx.send("⏳ Connected! Querying public verification database...")

    # 2. Use the open public lookup endpoint (Fixes the silent API block crash)
    rover_url = f"https://rover.link{discord_user_id}"
    
    try:
        rover_resp = requests.get(rover_url)
        
        if rover_resp.status_code != 200:
            await ctx.send("❌ Error: Verification registry returned an invalid response. Are you linked on rover.link?")
            return
            
        data_payload = rover_resp.json()
        roblox_id = data_payload.get("robloxId")
        roblox_username = data_payload.get("robloxUsername")
        
        if not roblox_id:
            await ctx.send("❌ Error: No Roblox ID found attached to your Discord account.")
            return

        # 3. Pull image payload URL string array layout
        roblox_api = f"https://roblox.com{roblox_id}&size=150x150&format=Png&isCircular=false"
        roblox_data = requests.get(roblox_api).json()
        raw_image_url = roblox_data['data'][0]['imageUrl']

        # 4. Stream payload directly into memory buffer
        image_stream = requests.get(raw_image_url).content
        byte_buffer = io.BytesIO(image_stream)

        # 5. Execute server profile swap
        try:
            if roblox_username:
                await target_member.edit(nick=roblox_username)
            
            await target_member.edit(avatar=byte_buffer.read())
            await ctx.send(f"🎯 Success! Updated your profile to match Roblox user: **{roblox_username}** (`{roblox_id}`)")
            
        except discord.Forbidden:
            await ctx.send("❌ Discord Permission Error: You must drag the Bot's Role to the **VERY TOP** of your server's role list, otherwise Discord blocks the bot from editing your profile.")

    except Exception as error:
        await ctx.send(f"⚠️ Runtime Error: `{str(error)}`")

if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if token:
        bot.run(token)
    else:
        print("CRITICAL: DISCORD_TOKEN is missing.")
