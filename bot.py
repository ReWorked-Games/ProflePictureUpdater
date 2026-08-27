import os
import discord
from discord.ext import commands


# ============================================================
# TOKEN
# ============================================================

TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    print("ERROR: DISCORD_TOKEN is missing from GitHub Secrets.")
    raise SystemExit(1)


# ============================================================
# INTENTS
# ============================================================

intents = discord.Intents.default()
intents.members = True
intents.message_content = True


# ============================================================
# BOT
# ============================================================

class MyBot(commands.Bot):

    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None
        )

    async def setup_hook(self):

        print("Registering slash commands...")

        try:
            synced = await self.tree.sync()

            print(
                f"SUCCESS: Registered {len(synced)} slash command(s)."
            )

            for command in synced:
                print(
                    f"  /{command.name}"
                )

        except Exception as error:

            print(
                f"ERROR REGISTERING SLASH COMMANDS: {error}"
            )


bot = MyBot()


# ============================================================
# /syncpfp
# ============================================================

@bot.tree.command(
    name="syncpfp",
    description="Synchronize your Roblox profile."
)
async def syncpfp(interaction: discord.Interaction):

    await interaction.response.send_message(
        "The `/syncpfp` command is working.",
        ephemeral=True
    )


# ============================================================
# READY
# ============================================================

@bot.event
async def on_ready():

    print("========================================")
    print("BOT ONLINE")
    print(f"Bot: {bot.user}")
    print(f"Bot ID: {bot.user.id}")
    print("========================================")


# ============================================================
# START
# ============================================================

print("Starting Discord bot...")

bot.run(TOKEN)
