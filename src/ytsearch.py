import discord
from discord.ext import commands
import logging
from pathlib import Path
from googleapiclient.discovery import build
import httplib2
from . import tokens


try:
    YOUTUBE_SEARCH = tokens.googleAPI and build('youtube', 'v3',
                                                developerKey=tokens.googleAPI,
                                                ).search()
except httplib2.ServerNotFoundError:
    YOUTUBE_SEARCH = None


SCRIPT_DIR = Path(__file__).parent
PARENT_DIR = SCRIPT_DIR.parent
DATA_DIR = PARENT_DIR / 'data'

logger = logging.getLogger()


class YTSearch(discord.ext.commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=['yt'])
    async def youtube(self, ctx, *, search_term: str):
        '''Post a YouTube video based on a search phrase!
        Idea stolen from KitchenSink'''
        if YOUTUBE_SEARCH is None:
            await ctx.send('Sorry, I can\'t connect to Google API!')
            return
        search_response = YOUTUBE_SEARCH.list(q=search_term,
                                              part='id',
                                              maxResults=10).execute()
        search_results = (search_result['id']['videoId']
                          for search_result in search_response.get('items', [])
                          if search_result['id']['kind'] == 'youtube#video')
        search_result = next(search_results, None)
        await ctx.send(f'https://www.youtube.com/watch?v={search_result}'
                       if search_result else 'Sowwy, I can\'t find it :(')


def setup(bot):
    logger.info('ytsearch starting setup')
    bot.add_cog(YTSearch(bot))
    logger.info('ytsearch ending setup')
