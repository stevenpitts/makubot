import random
import discord
from discord.ext import commands
from discord.ext.commands.errors import (CommandError, CommandNotFound,
                                         CommandOnCooldown, NotOwner,
                                         MissingPermissions,
                                         BotMissingPermissions,
                                         BadUnionArgument,
                                         MissingRequiredArgument,
                                         BadArgument)
from . import commandutil


class Listeners(discord.ext.commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Called when a member joins to tell them that Maku loves them
        (because Maku does) <3"""
        guild_is_free = (
            str(member.guild.id)
            in self.bot.get_cog("MakuCommands").get_free_guild_ids()
            )
        if not guild_is_free:
            return
        try:
            await member.guild.system_channel.send(
                f"Hi {member.mention}! Maku loves you! <333333")
        except AttributeError:
            print(f"{member.mention} joined, but guild "
                  f"{member.guild.name} has no system_channel. ID is "
                  f"{member.guild._system_channel_id}.")

    @commands.Cog.listener()
    async def on_command_error(self, ctx,
                               caught_exception: CommandError):
        if isinstance(caught_exception, CommandNotFound):
            if str(self.bot.user.id) in ctx.message.content.split()[0]:
                to_eval = " ".join(ctx.message.content.split()[1:]).strip()
                await self.bot.get_cog("Evaluations").eval_and_respond(
                    ctx, to_eval, force_reply=False)
        elif isinstance(caught_exception, NotOwner):
            await ctx.send("Sorry, only Maku can use that command :(")
        elif isinstance(caught_exception, CommandOnCooldown):
            await ctx.send("Slow down! You\"re going too fast for me ;a;\
                            I\"m sorry :(")
        elif isinstance(caught_exception, (MissingPermissions,
                                           BotMissingPermissions,
                                           BadUnionArgument,
                                           MissingRequiredArgument,
                                           BadArgument)):
            await ctx.send(str(caught_exception))
        else:
            print(commandutil.get_formatted_traceback(caught_exception))
            await ctx.send("Something went wrong, sorry!")

    @commands.Cog.listener()
    async def on_error(self, ctx, caught_exception):
        print(commandutil.get_formatted_traceback(caught_exception))

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        guild_is_free = (
            str(message.guild.id)
            in self.bot.get_cog("MakuCommands").get_free_guild_ids()
            )
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
        if guild_is_free or self.bot.user in message.mentions:
            new_activity = discord.Game(name=message.author.name)
            await self.bot.change_presence(activity=new_activity)
        if not guild_is_free:
            return
        if message.mention_everyone:
            await message.channel.send(message.author.mention+" grr")
        if "vore" in message.content.split() and random.random() > 0.8:
            await message.pin()


def setup(bot):
    bot.add_cog(Listeners(bot))
