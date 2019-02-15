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
        self.bot.unload_extension('makucommands')
        try:
            self.bot.load_extension('makucommands')
            logging.info("Successfully reloaded makucommands")
            await ctx.send("Successfully reloaded!")
        except Exception as e:
            logging.info(r"Failed to reload makucommands:\n{}\n\n\n".format(commandutil.get_formatted_traceback(e)))
            await ctx.send("Failed to reload, sending you the details :(")
            await commandutil.send_formatted_message(self.bot.makusu,commandutil.get_formatted_traceback(e))
    
    @commands.command(hidden=True)
    @commands.is_owner()
    async def criticalping(self,ctx):
        await ctx.send("Critical pong")
        
    @commands.command(hidden=True)
    @commands.is_owner()
    async def supereval(self,ctx,*,to_eval:str):
        temp_output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = temp_output
        eval(to_eval)
        sys.stdout = old_stdout
        await self.send_maku_message(temp_output.getvalue())
        
        
        
def setup(bot):
    bot.add_cog(CriticalCommands(bot))