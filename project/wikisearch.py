import discord
from discord.ext import commands
import logging
from pathlib import Path
import wikipedia

SCRIPT_DIR = Path(__file__).parent
PARENT_DIR = SCRIPT_DIR.parent
DATA_DIR = PARENT_DIR / 'data'

logger = logging.getLogger()


class Wikisearch(discord.ext.commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def whatis(self, ctx, *, query):
        '''Searches Wikipedia to see what something is! Give it a try!'''
        try:
            result = wikipedia.page(wikipedia.search(query)[0])
            summary = ''.join(result.summary)[:1024]
        except wikipedia.exceptions.DisambiguationError:
            await ctx.send("Sorry, please be more specific than that ;~;")
        except IndexError:
            await ctx.send("Hmm, I can't find anything matching that...")
        else:
            embed = discord.Embed(title="Results", description=query)
            embed.add_field(name=result.url, value=summary)
            await ctx.send(embed=embed)


def setup(bot):
    logger.info('wikisearch starting setup')
    bot.add_cog(Wikisearch(bot))
    logger.info('wikisearch ending setup')
