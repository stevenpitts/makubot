"""
Module used for any activity that must stay usable even in the event that makucommands become unusable.
This can happen if, for example, makucommands is reloaded with a syntax error.
"""
import discord
from discord.ext import commands
import sys
from io import StringIO
import traceback
import commandutil
import importlib
import logging



class CriticalCommands:
    def __init__(self,bot):
        self.bot = bot
            
    @commands.command(hidden=True)
    @commands.is_owner()
    async def reload(self,ctx): 
        """Reloads my command cogs. Works even in fatal situations. Sometimes."""
        logging.info("---Reloading makucommands and commandutil---")
        importlib.reload(commandutil)
        ctx.bot.unload_extension('makucommands')
        try:
            ctx.bot.load_extension('makucommands')
            logging.info("Successfully reloaded makucommands")
            await ctx.send("Successfully reloaded!")
        except Exception as e:
            logging.info(r"Failed to reload makucommands:\n{}\n\n\n".format(commandutil.get_formatted_traceback(e)))
            await commandutil.send_formatted_message(ctx,commandutil.get_formatted_traceback(e))
def setup(bot):
    bot.add_cog(CriticalCommands(bot))