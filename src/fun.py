import discord
from discord.ext import commands
import logging
import random
import asyncio
import time
import itertools
import collections
import re
from . import util

logger = logging.getLogger()

FACTS = """Geese are NEAT
How can mirrors be real if our eyes aren't real
I'm the captain now
Maku is awesome
Maku
Super electromagnetic shrapnel cannon FIRE!
Ideas are bulletproof
What do we say to Death? Not today.
Nao Tomori is best person
Please do not use any ligma-related software in parallel with Makubot
Wear polyester when doing laptop repairs
Fighting's good when it's not a magic orb that can throw you against the wall
Don't f*** with Frug's shovel
If I don't come back within five minutes assume I died
You you eat sleep eat sleep whoa why can't I see anything
Expiration dates are just suggestions
Cake am lie
Oh dang is that a gun -Uncle Ben
With great power comes great responsibility -Uncle Ben""".split("\n")


class Fun(discord.ext.commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(hidden=True, aliases=["is gay"])
    async def isgay(self, ctx):
        """Tells me I'm gay :("""
        await ctx.send("No u")

    @commands.command()
    async def bully(self, ctx):
        """Bullies me :("""
        if ctx.guild and ctx.guild.get_member(self.bot.makusu.id) is not None:
            await ctx.send(f"{self.bot.makusu.mention} "
                           "HELP I'M BEING BULLIED ;a;")
        else:
            await ctx.send("M-maku? W-where are you? Help!!!!")

    @commands.command(aliases=["hug me"])
    async def hugme(self, ctx):
        """Hugs you <3"""
        await ctx.send(f"*Hugs you* {ctx.message.author.mention}")

    @commands.command(aliases=["emoji spam"])
    @commands.bot_has_permissions(add_reactions=True)
    async def emojispam(self, ctx):
        """Prepare to be spammed by the greatest emojis you've ever seen"""
        max_reacts = 20
        emojis_random_order = iter(sorted(self.bot.emojis,
                                          key=lambda *args: random.random()))
        emojis_to_add = itertools.islice(emojis_random_order, max_reacts)
        emoji_futures = [ctx.message.add_reaction(emoji_to_add)
                         for emoji_to_add in emojis_to_add]
        all_emoji_futures = asyncio.gather(*emoji_futures)
        try:
            await all_emoji_futures
        except discord.errors.Forbidden:
            return

    @commands.command(aliases=["english"], hidden=True)
    async def translate(self, ctx, *, text: str):
        """Translate some text into English!
        Idea stolen from KitchenSink."""
        await ctx.send("Not implemented :<")

    @commands.command()
    async def fact(self, ctx):
        """Sends a fun fact!"""
        await ctx.send(random.choice(FACTS))

    @commands.command(hidden=True, aliases=["sayto", ])
    @commands.is_owner()
    async def sendto(self, ctx, channel: discord.TextChannel, *,
                     message_text: str):
        await channel.send(message_text)

    @commands.command(hidden=True)
    @commands.is_owner()
    async def thisify(self, ctx, message: discord.Message):
        this_emojis = [emoji for emoji in self.bot.emojis
                       if emoji.name.startswith("this")
                       and len(emoji.name) < 8
                       ]
        all_emoji_futures = [message.add_reaction(this_emoji)
                             for this_emoji in this_emojis]
        all_emoji_futures = asyncio.gather(*all_emoji_futures)
        try:
            await all_emoji_futures
        except discord.errors.Forbidden:
            return

    @commands.command(hidden=True)
    @commands.is_owner()
    async def reactionspeak(self, ctx, message: discord.Message, *, text: str):
        """Adds an emoji reaction to a message!"""
        text = text.lower()
        if not text.isalpha():
            await ctx.send("I can only add letters :<")
            return
        elif len(set(text)) < len(text):
            await ctx.send("I can't do duplicate letters :<")
            return
        text_emojis = [chr(ord("🇦")+ord(letter)-ord("a"))
                       for letter in text]
        present_emojis = [reaction.emoji for reaction in message.reactions]
        shared_emojis = set(text_emojis) & set(present_emojis)
        if shared_emojis:
            await ctx.send("Cannot add, some used emojis are already present "
                           f"in the message: {' '.join(shared_emojis)}")
            return
        for emoji in text_emojis:
            await message.add_reaction(emoji)
        await ctx.send("Done!")

    @commands.command()
    async def choose(self, ctx, *args):
        """
        Returns a random choice from the choices you provide!
        Separated  by spaces, but you can put options in quotes
        to allow spaces in a single option.
        For example: `mb.choose "North Carolina" Maine "Rhode Island"`
        """
        if not args:
            await ctx.send(f"You gotta give options!\n{ctx.command.help}")
            return
        await ctx.send(f"I choose {random.choice(args)}!")

    @commands.command(aliases=["vote"])
    async def poll(self, ctx, *args):
        """
        Starts a poll from the choices you provide!
        I'll also delete your message after I start the poll, if I can.
        The first argument should be the question, followed by choices.
        Arguments are separated by spaces.
        You can put options in quotes to allow spaces in a single option.
        Example: `mb.poll "Favorite state?" "North Carolina" Maine Iowa`
        You can also add "timeout=SECONDS" after the question
        to limit the poll.
        Example: `mb.poll timeout=30 "Favorite state?" RI MA`
        Put "ONLYONEVOTE" anywhere in your command to limit people to one vote.
        Example: `mb.poll ONLYONEVOTE timeout=30 "Favorite state?" RI MA`
        """
        only_one_vote = "ONLYONEVOTE" in args
        args = [
            await util.clean(ctx, arg) for arg in args
            if arg != "ONLYONEVOTE"]
        if not args:
            await ctx.send(f"You gotta give a question and options!")
            return
        if len(args) == 1:
            await ctx.send("That's just a question, you need options!")
            return
        if len(args) == 2:
            await ctx.send(f"That's only one option, {args[1]}...")
            return
        if len(set(args)) != len(args):
            await ctx.send("You're repeating options...")
            return
        if len(args) > 3 and re.match(r"timeout=\d+", args[0]):
            timeout = int(args[0].split("=")[-1])
            question = args[1]
            choices = args[2:]
        else:
            timeout = None
            question = args[0]
            choices = args[1:]

        if timeout is None and only_one_vote:
            await ctx.send(
                "You can only use ONLYONEVOTE if there is a timeout :(")
            return

        choice_to_emoji = {choice: chr(i+ord("🇦"))
                           for i, choice in enumerate(choices)}
        choices_str = "\n".join([f"{emoji} {choice}"
                                 for choice, emoji
                                 in choice_to_emoji.items()])
        message = await ctx.send(
            f"Poll by {ctx.message.author.name}: {question}\n"
            f"Reply with the emoji to vote:\n{choices_str}")
        for emoji in choice_to_emoji.values():
            await message.add_reaction(emoji)

        try:
            await ctx.message.delete()
            logger.info(f"Deleted poll message")
        except discord.errors.Forbidden:
            logger.info(f"Couldn't delete message {ctx.message.jump_url}")

        if not timeout:
            return
        elif not only_one_vote:
            await asyncio.sleep(timeout)
        else:
            start_time = time.time()
            while time.time() - start_time < timeout:
                message = await ctx.fetch_message(message.id)
                # Check for duplicate reactions
                users_reacted = [
                    user for reaction in message.reactions
                    for user in await reaction.users().flatten()
                    if not user == self.bot.user
                ]
                user_reaction_count = collections.Counter(users_reacted)
                multi_reaction_users = {
                    user for user, count in user_reaction_count.items()
                    if count > 1
                }
                for multi_reaction_user in multi_reaction_users:
                    for reaction in message.reactions:
                        try:
                            await reaction.remove(multi_reaction_user)
                            logger.info(
                                f"Removed {multi_reaction_user}'s "
                                f"reaction {reaction} due to ONLYONEVOTE")
                        except discord.errors.Forbidden:
                            logger.info(
                                f"Couldn't remove {multi_reaction_user}'s "
                                f"reaction {reaction} due to permissions")

        choice_to_reaction = {
            choice: discord.utils.get(message.reactions, emoji=emoji)
            for choice, emoji in choice_to_emoji.items()}
        choice_clauses = [f"{reaction.count - 1} for \"{choice}\""
                          for choice, reaction in choice_to_reaction.items()]
        results = ", ".join(choice_clauses)
        await message.edit(content=f"{message.content}\nResults: {results}")


def setup(bot):
    logger.info("fun starting setup")
    bot.add_cog(Fun(bot))
    logger.info("fun ending setup")
