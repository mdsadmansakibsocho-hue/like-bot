import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import json
import os
import asyncio
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
LIKE_API_URL = os.getenv("LIKE_API_URL")
KEY = os.getenv("LIKE_API_KEY")

CONFIG_FILE = "like_channels.json"

class LikeCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api_url = LIKE_API_URL
        self.session = aiohttp.ClientSession()
        self.config_data = self.load_config()
        self.key = KEY


    def load_config(self):
        default = {
            "servers": {},
            "roles": {},
            "global_settings": {"default_cooldown": 30, "default_daily_limit_for_roles": 3},
            "user_daily_usage": {}
        }
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    return json.load(f)
            except:
                return default
        return default

    def save_config(self):
        with open(CONFIG_FILE, 'w') as f:
            json.dump(self.config_data, f, indent=4)

    async def is_channel_allowed(self, ctx):
        if not ctx.guild: return True
        channels = self.config_data["servers"].get(str(ctx.guild.id), {}).get("like_channels", [])
        return not channels or str(ctx.channel.id) in channels

    def get_effective_limit(self, member):
        # Vérification accès illimité
        for role in member.roles:
            if self.config_data["roles"].get(str(role.id), {}).get("unlimited_access"):
                return {"unlimited": True, "limit": -1}
        
        # Calcul de la limite max selon les rôles
        max_lim = self.config_data["global_settings"]["default_daily_limit_for_roles"]
        for role in member.roles:
            role_lim = self.config_data["roles"].get(str(role.id), {}).get("daily_limit")
            if role_lim and role_lim > max_lim:
                max_lim = role_lim
        return {"unlimited": False, "limit": max_lim}

    def check_limit(self, member):
        limit_info = self.get_effective_limit(member)
        if limit_info["unlimited"]: return True

        uid = str(member.id)
        usage = self.config_data["user_daily_usage"].setdefault(uid, {"count": 0, "last_reset": ""})
        today = datetime.utcnow().strftime("%Y-%m-%d")

        if usage["last_reset"] != today:
            usage["count"] = 0
            usage["last_reset"] = today
        
        if usage["count"] >= limit_info["limit"]:
            return False
        
        usage["count"] += 1
        self.save_config()
        return True

    @commands.hybrid_command(name="setlikechannel")
    @commands.has_permissions(administrator=True)
    async def set_like_channel(self, ctx, channel: discord.TextChannel):
        config = self.config_data["servers"].setdefault(str(ctx.guild.id), {"like_channels": []})

        if str(channel.id) not in config["like_channels"]:
            config["like_channels"].append(str(channel.id))
            self.save_config()
            await ctx.send(f"✅ Channel {channel.mention} is now allowed for `/like` commands.", ephemeral=True)
        else:
            await ctx.send(f"ℹ️ Channel {channel.mention} is already allowed for `/like` commands.", ephemeral=True)


    @commands.hybrid_command(name="like")
    @app_commands.describe(uid="Player UID", region="Region (ex: IND, US, BR)")
    async def like(self, ctx, region: str, uid: str):
        if not await self.is_channel_allowed(ctx):
            return await ctx.send("❌ ❌ This command can only be used in designated channels. Please use one of the allowed channels.", ephemeral=True, delete_after=5)



        reg_map = {"ind": "ind", "br": "nx", "us": "nx", "na": "nx", "nx": "nx"}
        server = reg_map.get(region.lower(), "ag")

        async with ctx.typing():
            try:
     
                async with self.session.get(f"{self.api_url}?uid={uid}&region={server}&key={KEY}") as resp:
                    if resp.status == 429:
                        return await ctx.send(
                            "> ⚠️ API limit reached. Please contact the developer (@thug4ff) to purchase more credits."
                        )


                    if resp.status != 200:
                        return await ctx.send("⚠️ Erreur API.")
                    
                    data = await resp.json()
                    success = data.get("status") == 1
                    
                    embed = discord.Embed(
                        title="Likes envoyés !" if success else "Failde to send likes!",
                        color=0xbc31db if success else 0xE74C3C,
                        timestamp=datetime.utcnow()
                    )
                    print(resp.status)

                    if success:
                        player = data.get("player", {})
                        likes = data.get("likes", {})
                        l = data.get("api_key_details", {})
                        embed.description = (
                            f"> **Nickname:** {player.get('nickname', 'Unknown')}\n"
                            f"> **Region:** {player.get('region', 'Unknown')}\n"
                            f"> **Player UID:** {player.get('uid', 0)}\n"
                            f"> **Like before:** {likes.get('before', 0)}\n"
                            f"> **Like added :** +{likes.get('added_by_api', 0)}\n"
                            f"> **Like after:** {likes.get('after', 0)}\n"
                           
                            f"> **Remaining API :** {l.get('current_usage', 0)}/ {l.get('usage_limit', 0)} \n"
                        )
                    else:
                        embed.description = (
                            "> This UID has already received the maximum likes today.\n"
                            "> Please wait 24 hours and try again"
                        )
                    embed.set_footer(text="DEVELOPED BY THUG4FF")
                    await ctx.reply(embed=embed)
            except Exception as e:
                await ctx.send(f"Erreur: {e}")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild: return

        if await self.is_channel_allowed(message) and not message.content.startswith(('!like', '/like')):
            try:
                await message.delete()
            except:
                pass

    def cog_unload(self):
        asyncio.create_task(self.session.close())

async def setup(bot):
    await bot.add_cog(LikeCommands(bot))