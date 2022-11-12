import discord
from discord.ext import commands
import logging
import wikipedia

logger = logging.getLogger()


class Wikisearch(discord.ext.commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=["wiki", "wikipedia"])
    async def whatis(self, ctx, *, query):
        """Searches Wikipedia to see what something is!"""
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


async def setup(bot):
    logger.info("wikisearch starting setup")
    await bot.add_cog(Wikisearch(bot))
    logger.info("wikisearch ending setup")
