import discord
from discord.ext import commands
import logging
from pathlib import Path
import random
import asyncio
import itertools

SCRIPT_DIR = Path(__file__).parent
PARENT_DIR = SCRIPT_DIR.parent
DATA_DIR = PARENT_DIR / 'data'


FACTS = '''Geese are NEAT
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
With great power comes great responsibility -Uncle Ben'''.split('\n')


class Fun(discord.ext.commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=['is gay'])
    async def isgay(self, ctx):
        '''Tells me I'm gay (CAUTION: May mirror attack at sender)'''
        await ctx.send('No u')

    @commands.command()
    async def bully(self, ctx):
        '''Bullies me :('''
        if ctx.guild and ctx.guild.get_member(self.bot.makusu.id) is not None:
            await ctx.send(f'{self.bot.makusu.mention} '
                           'HELP I\'M BEING BULLIED ;a;')
        else:
            await ctx.send('M-maku? W-where are you? Help!!!!')

    @commands.command(aliases=['hug me'])
    async def hugme(self, ctx):
        '''Hugs you <3'''
        await ctx.send(f'*Hugs you* {ctx.message.author.mention}')

    @commands.command(aliases=['emoji spam'])
    @commands.bot_has_permissions(add_reactions=True)
    async def emojispam(self, ctx):
        '''Prepare to be spammed by the greatest emojis you've ever seen'''
        max_reacts = 20
        emojis_random_order = iter(sorted(self.bot.emojis,
                                   key=lambda *args: random.random()))
        emojis_to_add = itertools.islice(emojis_random_order, max_reacts)
        emoji_futures = [ctx.message.add_reaction(emoji_to_add)
                         for emoji_to_add in emojis_to_add]
        all_emoji_futures = asyncio.gather(*emoji_futures,
                                           return_exceptions=True)
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
        '''Sends a fun fact!'''
        await ctx.send(random.choice(FACTS))

    @commands.command(hidden=True, aliases=['sayto', ])
    @commands.is_owner()
    async def sendto(self, ctx, channel: discord.TextChannel, *,
                     message_text: str):
        await channel.send(message_text)

    @commands.command(hidden=True)
    @commands.is_owner()
    async def reactionspeak(self, ctx, message: discord.Message, *, text: str):
        """Adds an emoji reaction to a message!"""
        # channel = self.bot.get_channel(int(channel_id))
        text = text.lower()
        if not text.isalpha():
            await ctx.send("I can only add letters :<")
            return
        elif len(set(text)) < len(text):
            await ctx.send("I can't do duplicate letters :<")
            return
        # elif channel is None:
        #     await ctx.send("That channel is invalid")
        #     return
        # try:
        #     message = await channel.fetch_message(int(message_id))
        # except NotFound:
        #     await ctx.send("That message is invalid")
        #     return
        text_emojis = [chr(ord('🇦')+ord(letter)-ord('a')) for letter in text]
        present_emojis = [reaction.emoji for reaction in message.reactions]
        shared_emojis = set(text_emojis) & set(present_emojis)
        if shared_emojis:
            await ctx.send("Cannot add, some used emojis are already present "
                           f"in the message: {''.join(shared_emojis)}")
            return
        for emoji in text_emojis:
            await message.add_reaction(emoji)
        await ctx.send("Done!")

    @commands.command()
    async def choose(self, ctx, *args):
        '''
        Returns a random choice from the choices you provide!
        Separated  by spaces, but you can put options in quotes
        to allow spaces in a single option.
        For example: `mb.choose "North Carolina" Maine "Rhode Island"`
        '''
        if not args:
            await ctx.send(f"You gotta give options!\n{ctx.command.help}")
            return
        await ctx.send(f'I choose {random.choice(args)}!')


def setup(bot):
    logging.info('fun starting setup')
    bot.add_cog(Fun(bot))
    logging.info('fun ending setup')