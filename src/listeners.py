import random
import itertools
import discord
import logging
from discord.ext import commands, tasks
from discord.ext.commands.errors import (
    CommandError, CommandNotFound, CommandOnCooldown, NotOwner,
    MissingPermissions, BotMissingPermissions, BadUnionArgument,
    MissingRequiredArgument, BadArgument, PrivateMessageOnly, NoPrivateMessage,
    UserInputError,
)
from . import util

logger = logging.getLogger()

STATUS_MESSAGES = [
    "mb.help",
    "mb.support",
    "mb.invite"
]


class Listeners(discord.ext.commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.status_messages = itertools.cycle(STATUS_MESSAGES)
        self.cycle_status_message.start()

    def cog_unload(self):
        self.cycle_status_message.stop()

    @commands.Cog.listener()
    async def on_command_error(self, ctx,
                               caught_exception: CommandError):
        if isinstance(caught_exception, CommandNotFound):
            await ctx.send("srryyyyyyyyyyyYYYY i dont now that COMMAND that you told me to useeeeeeeeeee ;a; ;a ;a ;a; ;a ;aa;;a;a;a;a;a;a;;a;a;a aaaaaaAAAAAAAAAAAAAAAAAAAAAAWAAAAAAAHHHHHHHHHHHHHHHHHHH fuck this bot")
        elif isinstance(caught_exception, NotOwner):
            await ctx.send("Sorry, only Maku can use that command :(")
        elif isinstance(caught_exception, CommandOnCooldown):
            await ctx.send("Slow down! You\"re going too fast for me ;a;\
                            I\"m sorry :(")
        elif isinstance(caught_exception, (
                MissingPermissions,
                BotMissingPermissions,
                BadUnionArgument,
                MissingRequiredArgument,
                BadArgument,
                PrivateMessageOnly,
                NoPrivateMessage,
        )):
            await ctx.send(str(caught_exception))
        elif isinstance(caught_exception, UserInputError):
            await ctx.send(
                "Hmm, I can't tell what you're saying... did you make a typo?"
            )
        else:
            formatted_tb = util.get_formatted_traceback(
                caught_exception)
            logger.error(formatted_tb)
            await ctx.send("Something went wrong, sorry!")
            await self.bot.makusu.send(
                f"Something went wrong!\n```{formatted_tb}```")

    @commands.Cog.listener()
    async def on_error(self, ctx, caught_exception):
        logger.error(util.get_formatted_traceback(caught_exception))

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        guild_is_free = (
            str(message.guild.id)
            in self.bot.get_cog("Base").get_free_guild_ids()
        )
        if guild_is_free or self.bot.user in message.mentions:
            new_activity = discord.Game(name=message.author.name)
            await self.bot.change_presence(activity=new_activity)
        if not guild_is_free:
            return
        if message.mention_everyone:
            await message.channel.send(message.author.mention+" grr")
        if ("vore" in message.content.lower().split()
            and message.content.lower().strip() != "vore"
                and random.random() > 0.8):
            await message.pin()

    @tasks.loop(seconds=10)
    async def cycle_status_message(self):
        new_activity = discord.Game(name=next(self.status_messages))
        await self.bot.change_presence(activity=new_activity)

    @cycle_status_message.before_loop
    async def before_cycle_status_message(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(Listeners(bot))
