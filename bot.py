import discord
from discord.ext import commands
import requests
import io
import os

intents = discord.Intents.default()
intents.members = True          # Required to auto-update users
intents.message_content = True  # Required to auto-check text activity

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

async def auto_sync_profile(member: discord.Member):
    """Internal helper function to automatically sync a user without any commands."""
    # Skip bots entirely
    if member.bot:
        return

    # Step 1: Query the unauthenticated public RoVer proxy registry
    rover_url = f"https://rover.link{member.id}"
    
    try:
        rover_resp = requests.get(rover_url)
        if rover_resp.status_code != 200:
            return  # Fail silently if user isn't verified on RoVer
            
        data_payload = rover_resp.json()
        roblox_id = data_payload.get("robloxId")
        roblox_username = data_payload.get("robloxUsername")
        
        if not roblox_id:
            return

        # Step 2: Grab the exact headshot image string from the Roblox API array index
        roblox_api = f"https://roblox.com{roblox_id}&size=150x150&format=Png&isCircular=false"
        roblox_data = requests.get(roblox_api).json()
        raw_image_url = roblox_data['data'][0]['imageUrl']  # Target explicit index 0 array mapping

        # Step 3: Stream the asset download into a memory buffer
        image_stream = requests.get(raw_image_url).content
        byte_buffer = io.BytesIO(image_stream)

        # Step 4: Silently update the member's server profile
        if roblox_username and member.nick != roblox_username:
            await member.edit(nick=roblox_username)
        
        await member.edit(avatar=byte_buffer.read())
        print(f"AUTOMATION: Successfully synced {member.name} to Roblox account {roblox_username}")

    except discord.Forbidden:
        print(f"AUTOMATION ERROR: Failed to edit {member.name}. Check role hierarchy positions.")
    except Exception as e:
        print(f"AUTOMATION ERROR: {str(e)}")


@bot.event
async def on_ready():
    print("----------------------------------------")
    print(f"AUTOMATION ONLINE: Running background trackers.")
    print("----------------------------------------")


@bot.event
async def on_member_join(member: discord.Member):
    """Scenario 1: Triggers automatically the exact split-second someone joins your server."""
    await auto_sync_profile(member)


@bot.event
async def on_message(message: discord.Member):
    """Scenario 2: Triggers automatically every single time a user types a normal sentence in chat."""
    if message.author.bot or not message.guild:
        return
        
    # Process the silent background update on the person who chatted
    await auto_sync_profile(message.author)
    
    # Keep standard command handling active just in case
    await bot.process_commands(message)


if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if token:
        bot.run(token)
    else:
        print("CRITICAL: DISCORD_TOKEN environment variable is missing.")
