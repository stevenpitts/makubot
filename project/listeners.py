import random
from pathlib import Path
import discord
from discord.ext import commands
from discord.ext.commands.errors import (CommandError, CommandNotFound,
                                         CommandOnCooldown, NotOwner,
                                         MissingPermissions,
                                         BotMissingPermissions,
                                         BadUnionArgument,
                                         MissingRequiredArgument)
from . import commandutil

SCRIPT_DIR = Path(__file__).parent
PARENT_DIR = SCRIPT_DIR.parent
DATA_DIR = PARENT_DIR / 'data'


class Listeners(discord.ext.commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        '''Called when a member joins to tell them that Maku loves them
        (because Maku does) <3'''
        if member.guild.id in self.bot.shared['data']['free_guilds']:
            try:
                await member.guild.system_channel.send(f'Hi {member.mention}! '
                                                       'Maku loves you! '
                                                       '<333333')
            except AttributeError:
                print(f"{member.mention} joined, but guild "
                      f"{member.guild.name} has no system_channel. ID is "
                      f"{member.guild._system_channel_id}.")

    @commands.Cog.listener()
    async def on_command_error(self, ctx,
                               caught_exception: CommandError):
        if isinstance(caught_exception, CommandNotFound):
            if self.bot.user.mention in ctx.message.content:
                to_eval = ctx.message.content.replace(
                    self.bot.user.mention, '').strip()
                await self.bot.get_cog("Evaluations").eval_and_respond(
                    ctx, to_eval, force_reply=False)
        elif isinstance(caught_exception, NotOwner):
            await ctx.send('Sorry, only Maku can use that command :(')
        elif isinstance(caught_exception, CommandOnCooldown):
            await ctx.send('Slow down! You\'re going too fast for me ;a;\
                            I\'m sorry :(')
        elif isinstance(caught_exception, (MissingPermissions,
                                           BotMissingPermissions,
                                           BadUnionArgument,
                                           MissingRequiredArgument)):
            await ctx.send(str(caught_exception))
        else:
            print(commandutil.get_formatted_traceback(caught_exception))
            await ctx.send("Something went wrong, sorry!")

    @commands.Cog.listener()
    async def on_error(self, ctx, caught_exception):
        print(commandutil.get_formatted_traceback(caught_exception))

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author != self.bot.user:
            if ("+hug" in message.content.lower()
                    and str(self.bot.user.id) in message.content):
                hug_responses = (
                    "!!! *hug*",
                    "!!! *hug u*",
                    "*Hugs*!",
                    "Awwh!!! <333",
                    "*Hug u bak*",
                    "*Hugs you!!*")
                await message.channel.send(random.choice(hug_responses))
            if (message.guild
                    and (message.guild.id
                         in self.bot.shared['data']['free_guilds'])
                    and message.mention_everyone):
                await message.channel.send(message.author.mention+' grr')
            if (message.guild
                    and (message.guild.id
                         in self.bot.shared['data']['free_guilds'])
                    and 'vore' in message.content.split()
                    and random.random() > 0.8):
                await message.pin()
            if (not message.author.bot
                and ((message.guild and self.bot.user in message.mentions)
                     or (message.guild
                         and (message.guild.id
                              in self.bot.shared['data']['free_guilds'])))):
                new_activity = discord.Game(name=message.author.name)
                await self.bot.change_presence(activity=new_activity)


def setup(bot):
    bot.add_cog(Listeners(bot))
