import discord
from discord.ext import commands
import logging
import wikipedia
from discord_slash import cog_ext
from . import util

logger = logging.getLogger()
STAGING_PREFIX = util.get_staging_prefix()
DEV_GUILDS = util.get_dev_guilds()

class Wikisearch(discord.ext.commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def wiki(self, ctx, query):
        try:
            first_result = wikipedia.search(query)[0]
            result = wikipedia.page(first_result)
            summary = "".join(result.summary)[:1024]
        except wikipedia.exceptions.DisambiguationError:
            await ctx.send("Sorry, please be more specific than that ;~;")
        except IndexError:
            await ctx.send("Hmm, I can't find anything matching that...")
        except wikipedia.exceptions.PageError:
            await ctx.send(
                f"Wikipedia suggested the {first_result} page "
                "for that, but I can't find that page... weird.")
        else:
            embed = discord.Embed(title="Results", description=query)
            embed.add_field(name=result.url, value=summary)
            await ctx.send(embed=embed)

    @cog_ext.cog_slash(name=f"{STAGING_PREFIX}wiki", description="Searches Wikipedia to see what something is!", guild_ids=DEV_GUILDS)
    async def _wikislash(self, ctx, *, query):
        await self.wiki(ctx, query)

    @commands.command(name="wiki")
    async def _wikicmd(self, ctx, *, query):
        """Searches Wikipedia to see what something is!"""
        await ctx.send("Sorry, you'll have to type `/wiki` to do that now.")


def setup(bot):
    logger.info("wikisearch starting setup")
    bot.add_cog(Wikisearch(bot))
    logger.info("wikisearch ending setup")
