import discord
from discord.ext import commands
import logging
import re
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PARENT_DIR = SCRIPT_DIR.parent
DATA_DIR = PARENT_DIR / 'data'


class Listeners(discord.ext.commands.Cog):
    def __init__(self, bot):
        self.bot = bot

def setup(bot):
    logging.info('movement starting setup')
    bot.add_cog(Listeners(bot))
    logging.info('movement ending setup')
