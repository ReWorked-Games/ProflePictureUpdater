import discord
from discord.ext import commands
from discord import app_commands
import requests
import io
import os

# 1. Standard intents for server profile updates
intents = discord.Intents.default()
intents.members = True 

class CustomBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents, help_command=None)

    async def setup_hook(self):
        # This registers the slash commands globally to Discord's servers
        await self.tree.sync()
        print("SLASH COMMANDS: Successfully synced globally.")

bot = CustomBot()

@bot.event
async def on_ready():
    print("----------------------------------------")
    print(f"ONLINE: {bot.user.name} is ready for slash commands.")
    print("----------------------------------------")

# 2. Define the Slash Command
@bot.tree.command(name="syncpfp", description="Automatically connects and matches your server profile to your linked Roblox account.")
async def syncpfp(interaction: discord.Interaction):
    """Slash command to auto-lookup the executor's verified Roblox account."""
    discord_user_id = interaction.user.id
    target_member = interaction.user

    # Acknowledge the slash command instantly so Discord doesn't say "Interaction Failed"
    await interaction.response.send_message("⏳ Accessing database... Searching for your verified Roblox link.")

    # Step 1: Hit the public unauthenticated RoVer integration proxy
    rover_url = f"https://rover.link{discord_user_id}"
    
    try:
        rover_resp = requests.get(rover_url)
        
        if rover_resp.status_code != 200:
            await interaction.followup.send("❌ Link Not Found: Go to https://rover.link and verify your account first.")
            return
            
        data_payload = rover_resp.json()
        roblox_id = data_payload.get("robloxId")
        roblox_username = data_payload.get("robloxUsername")
        
        if not roblox_id:
            await interaction.followup.send("❌ Error: No Roblox data bound to this Discord ID.")
            return

        # Step 2: Extract the image path string from the dictionary array
        roblox_api = f"https://roblox.com{roblox_id}&size=150x150&format=Png&isCircular=false"
        roblox_data = requests.get(roblox_api).json()
        raw_image_url = roblox_data['data']['imageUrl']

        # Step 3: Stream the image download into the buffer
        image_stream = requests.get(raw_image_url).content
        byte_buffer = io.BytesIO(image_stream)

        # Step 4: Force apply settings to the user's server profile
        try:
            if roblox_username:
                await target_member.edit(nick=roblox_username)
            
            await target_member.edit(avatar=byte_buffer.read())
            await interaction.followup.send(f"🎯 Success! Profile synced to Roblox user: **{roblox_username}** (`{roblox_id}`)")
            
        except discord.Forbidden:
            await interaction.followup.send("❌ Discord Permission Error: Move the Bot's Role to the **VERY TOP** of your Server Settings role list.")

    except Exception as error:
        await interaction.followup.send(f"⚠️ Internal Processing Failure: `{str(error)}`")

if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if token:
        bot.run(token)
else:
    print("CRITICAL: DISCORD_TOKEN is missing.")
