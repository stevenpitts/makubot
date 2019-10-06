import discord
from discord.ext import commands, tasks
import logging
from pathlib import Path
from io import StringIO
from datetime import datetime
from discord.utils import escape_markdown
import sys
from . import commandutil
import time

SCRIPT_DIR = Path(__file__).parent
PARENT_DIR = SCRIPT_DIR.parent
DATA_DIR = PARENT_DIR / 'data'


class Debugging(discord.ext.commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.last_delay_time = time.time()
        self.test_delay.start()

    @commands.command(hidden=True)
    @commands.is_owner()
    async def long_computation(self, ctx):
        result = 2 ** 1000000
        await ctx.send(str(result)[:1000])

    @commands.command(hidden=True)
    @commands.is_owner()
    async def supereval(self, ctx, *, to_eval: str):
        sys.stdout = StringIO()
        eval_result = ''
        eval_err = ''
        try:
            eval_result = eval(to_eval) or ''
        except Exception as e:
            eval_err = commandutil.get_formatted_traceback(e)
        eval_output = sys.stdout.getvalue() or ''
        sys.stdout = sys.__stdout__
        if eval_result or eval_output or eval_err:
            eval_result = (f"{escape_markdown(str(eval_result))}\n"
                           if eval_result else "")
            eval_output = (f"```{escape_markdown(str(eval_output))}```\n"
                           if eval_output else "")
            eval_err = (f"```{escape_markdown(str(eval_err))}```"
                        if eval_err else "")
            await ctx.send(f'{eval_output}{eval_result}{eval_err}'.strip())
        else:
            await ctx.send("Hmm, I didn't get any output for that ;~;")

    @commands.command(hidden=True)
    @commands.is_owner()
    async def clearshell(self, ctx):
        '''Adds a few newlines to Maku's shell (for clean debugging)'''
        print('\n'*10)

    @commands.command(hidden=True, aliases=['deletehist'])
    @commands.is_owner()
    async def removehist(self, ctx, num_to_delete: int):
        '''Removes a specified number of previous messages by me'''
        bot_history = (message async for message in ctx.channel.history()
                       if message.author == self.bot.user)
        to_delete = []
        for _ in range(num_to_delete):
            try:
                to_delete.append(await bot_history.__anext__())
            except StopAsyncIteration:
                break
        await ctx.channel.delete_messages(to_delete)

    @tasks.loop(seconds=0)
    async def test_delay(self):
        new_delay_time = time.time()
        delta_time = new_delay_time-self.last_delay_time
        if delta_time > 0.1:
            logging.warning(f"{datetime.now()}: Time delay: {delta_time}")
        self.last_delay_time = new_delay_time

    @commands.command()
    @commands.cooldown(1, 1, type=commands.BucketType.user)
    async def ping(self, ctx):
        '''
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
        '''
        time_passed = datetime.utcnow() - ctx.message.created_at
        ms_passed = time_passed.microseconds/1000
        await ctx.send(f'pong! It took me {ms_passed}ms to get the ping.')

    @commands.command(hidden=True, aliases=['status'])
    @commands.is_owner()
    async def getstatus(self, ctx):
        current_servers_string = 'Current servers: {}'.format(
            {guild.name: guild.id for guild in self.bot.guilds})
        await self.bot.makusu.send(f"```{current_servers_string}```")

    def cog_unload(self):
        self.test_delay.stop()


def setup(bot):
    logging.info('debugging starting setup')
    bot.add_cog(Debugging(bot))
    logging.info('debugging ending setup')
