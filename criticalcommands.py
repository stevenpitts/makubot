import discord
from discord.ext import commands
import sys
from io import StringIO
import traceback
import commandutil



class CriticalCommands:
    def __init__(self,bot):
        self.bot = bot
            
    @commands.command()
    @commands.is_owner()
    async def reload(self,ctx): 
        """Reloads my command cogs. Works even in fatal situations. Sometimes."""
        self.bot.unload_extension('makucommands')
        try:
            self.bot.load_extension('makucommands')
            await ctx.send("Successfully reloaded!")
        except Exception as e:
            await ctx.send("Failed to reload, sending you the details :(")
            await commandutil.send_formatted_message(self.bot.makusu,commandutil.get_formatted_traceback(e))
        print("---Reloading---")
    
    @commands.command()
    @commands.is_owner()
    async def criticalping(self,ctx):
        await ctx.send("Critical pong")
        
    @commands.command()
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