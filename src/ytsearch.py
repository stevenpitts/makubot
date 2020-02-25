import discord
from discord.ext import commands
import logging
from pathlib import Path
from googleapiclient.discovery import build


SCRIPT_DIR = Path(__file__).parent
PARENT_DIR = SCRIPT_DIR.parent
DATA_DIR = PARENT_DIR / "data"

logger = logging.getLogger()


class YTSearch(discord.ext.commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.youtube_search = self.bot.google_api_key and build(
            "youtube", "v3", developerKey=self.bot.google_api_key
            ).search()

    @commands.command(aliases=["yt"])
    async def youtube(self, ctx, *, search_term: str):
        """Post a YouTube video based on a search phrase!
        Idea stolen from KitchenSink"""
        if self.youtube_search is None:
            await ctx.send("Sorry, I can\"t connect to Google API!")
            return
        search_response = self.youtube_search.list(
            q=search_term, part="id", maxResults=10
            ).execute()
        search_results = (search_result["id"]["videoId"]
                          for search_result in search_response.get("items", [])
                          if search_result["id"]["kind"] == "youtube#video")
        search_result = next(search_results, None)
        await ctx.send(f"https://www.youtube.com/watch?v={search_result}"
                       if search_result else "Sowwy, I can\"t find it :(")


def setup(bot):
    logger.info("ytsearch starting setup")
    bot.add_cog(YTSearch(bot))
    logger.info("ytsearch ending setup")
