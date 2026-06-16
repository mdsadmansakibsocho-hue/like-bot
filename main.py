import discord
import os
import asyncio
from discord.ext import commands
from dotenv import load_dotenv

# Load .env variables
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

class LikeBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True 
        intents.members = True          

        super().__init__(
            command_prefix="!", 
            intents=intents,
            help_command=None
        )

    async def setup_hook(self):
        print("--- Loading Cogs ---")
        try:
            # We use 'cogs.like_commands' because the file is now inside the 'cogs' folder
            await self.load_extension("cogs.like_commands") 
            print("✅ 'LikeCommands' loaded.")
        except Exception as e:
            print(f"❌ Failed to load Cog: {e}")
        
        # await self.tree.sync()
        # print("✅ Slash commands synced.")
        
        # # Sync slash commands
        # await self.tree.sync()
        # print("✅ Slash commands synced.")

    async def on_ready(self):
        print(f"--- Logged in as {self.user} ---")
        await self.change_presence(activity=discord.Game(name="!like | Free Fire"))

async def main():
    bot = LikeBot()
    async with bot:
        if not TOKEN:
            print("❌ Error: DISCORD_TOKEN not found in .env")
            return
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
