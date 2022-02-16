import discord
from discord.ext import commands
import logging
from io import StringIO
import aiohttp
from discord.utils import escape_markdown
from psycopg2.extras import RealDictCursor
import asyncio
import concurrent
import sys
import os
from . import util
from .picturecommands_utils import get_all_cmds_aliases_from_db

logger = logging.getLogger()


class Debugging(discord.ext.commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(hidden=True)
    @commands.is_owner()
    async def supereval(self, ctx, *, to_eval: str):
        sys.stdout = StringIO()
        eval_result = ""
        eval_err = ""
        try:
            eval_result = eval(to_eval) or ""
        except Exception as e:
            eval_err = util.get_formatted_traceback(e)
        eval_output = sys.stdout.getvalue() or ""
        sys.stdout = sys.__stdout__
        if eval_result or eval_output or eval_err:
            eval_result = (f"{escape_markdown(str(eval_result))}\n"
                           if eval_result else "")
            eval_output = (f"```{escape_markdown(str(eval_output))}```\n"
                           if eval_output else "")
            eval_err = (f"```{escape_markdown(str(eval_err))}```"
                        if eval_err else "")
            await ctx.send(f"{eval_output}{eval_result}{eval_err}".strip())
        else:
            await ctx.send("Hmm, I didn't get any output for that ;~;")

    @commands.command(hidden=True)
    @commands.is_owner()
    async def superevalsql(self, ctx, *, to_eval: str):
        cursor = self.bot.db_connection.cursor(cursor_factory=RealDictCursor)
        cursor.execute(to_eval)
        await ctx.send(str([dict(row) for row in cursor.fetchall()]))
        self.bot.db_connection.commit()

    @commands.command(hidden=True)
    @commands.is_owner()
    async def superevalrollback(self, ctx):
        self.bot.db_connection.rollback()
        await ctx.send("Done")

    @commands.command(hidden=True, aliases=["deletehist"])
    @commands.is_owner()
    async def removehist(self, ctx, num_to_delete: int):
        """Removes a specified number of previous messages by me"""
        bot_history = (message async for message in ctx.channel.history()
                       if message.author == self.bot.user)
        to_delete = []
        for _ in range(num_to_delete):
            try:
                to_delete.append(await bot_history.__anext__())
            except StopAsyncIteration:
                break
        await ctx.channel.delete_messages(to_delete)

    @commands.command()
    @commands.cooldown(1, 1, type=commands.BucketType.user)
    async def ping(self, ctx):
        """
        Pong was the first commercially successful video game,
        which helped to establish the video game industry along with
        the first home console, the Magnavox Odyssey. Soon after its
        release, several companies began producing games that copied
        its gameplay, and eventually released new types of games.
        As a result, Atari encouraged its staff to produce more
        innovative games. The company released several sequels
        which built upon the original's gameplay by adding new features.
        During the 1975 Christmas season, Atari released a home version of
        Pong exclusively through Sears retail stores. It also was a
        commercial success and led to numerous copies.
        The game has been remade on numerous home and portable platforms
        following its release. Pong is part of the permanent collection
        of the Smithsonian Institution in Washington, D.C.
        due to its cultural impact.
        """
        response = await ctx.send(f"pong!")
        time_delta = response.created_at - ctx.message.created_at
        latency_ms = int((time_delta).total_seconds() * 1000)
        await response.edit(content=f"pong! My latency is {latency_ms} ms.")

    @commands.command(hidden=True, aliases=["status"])
    @commands.is_owner()
    async def getstatus(self, ctx):
        current_servers_string = "Current servers: {}".format(
            {guild.name: guild.id for guild in self.bot.guilds})
        total_reactions = len(
            get_all_cmds_aliases_from_db(self.bot.db_connection))
        db_size = util.db_size(self.bot.db_connection)
        status_text = (
            f"I'm in {len(self.bot.guilds)} servers!\n"
            f"I have {total_reactions} reaction commands.\n"
            f"The database size is {db_size}.\n"
            f"I'm using {util.hardware_usage()}.\n"
            f"{current_servers_string}")
        await util.displaytxt(ctx, status_text, blockify=True)

    @commands.command(hidden=True, aliases=["restoredatabase", "restoredb"])
    @commands.is_owner()
    async def restore_db(self, ctx, backup_key):
        with concurrent.futures.ThreadPoolExecutor() as pool:
            await asyncio.get_running_loop().run_in_executor(
                pool, util.restore_db, self.bot.s3_bucket, backup_key)
        await ctx.send("Done!")


def setup(bot):
    logger.info("debugging starting setup")
    bot.add_cog(Debugging(bot))
    logger.info("debugging ending setup")
