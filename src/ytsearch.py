import discord
from discord.ext import commands
import logging
from googleapiclient.discovery import build
from discord_slash import SlashCommand, cog_ext

logger = logging.getLogger()


class YTSearch(discord.ext.commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.youtube_search = self.bot.google_api_key and build(
            "youtube", "v3", developerKey=self.bot.google_api_key
            ).search()

    async def youtube(self, ctx, search_term):
        """Post a YouTube video based on a search phrase!
        Idea stolen from KitchenSink"""
        if not self.youtube_search:
            await ctx.send("Sorry, I can\'t connect to Google API!")
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

    @cog_ext.cog_slash(name="youtube")
    async def _ytslash(self, ctx, *, search_term: str):
        await self.youtube(ctx, search_term)
    @commands.command(name="youtube", aliases=["yt"])
    async def _ytcmd(self, ctx, *, search_term: str):
        await self.youtube(ctx, search_term)


def setup(bot):
    logger.info("ytsearch starting setup")
    bot.add_cog(YTSearch(bot))
    logger.info("ytsearch ending setup")
