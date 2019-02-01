import discord
from discord.ext import commands
import sys
from io import StringIO
import traceback



class CriticalCommands:
    def __init__(self,bot):
        self.bot = bot
        
    async def send_maku_message(self,msg):
        for i in range(0, len(msg), 1500):
            await self.bot.makusu.send(r"```"+msg[i:i+1500]+r"```")
            
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
            await self.send_maku_message(''.join(traceback.format_exception(type(e), e, e.__traceback__)))
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