import discord
from discord.ext import commands
import logging
from pathlib import Path
import random

SCRIPT_DIR = Path(__file__).parent
PARENT_DIR = SCRIPT_DIR.parent
DATA_DIR = PARENT_DIR / 'data'


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
        emojis_random_order = iter(sorted(self.bot.emojis,
                                   key=lambda *args: random.random()))
        for emoji_to_add in emojis_random_order:
            try:
                await ctx.message.add_reaction(emoji_to_add)
            except discord.errors.Forbidden:
                return


def setup(bot):
    logging.info('fun starting setup')
    bot.add_cog(Fun(bot))
    logging.info('fun ending setup')
