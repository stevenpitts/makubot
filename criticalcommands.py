import discord
from discord.ext import commands
import sys
from io import StringIO

class CriticalCommands:
    def __init__(self,bot):
        self.bot = bot
        
    async def send_maku_message(self,msg):
        for i in range(0, len(msg), 2000):
            await self.bot.makusu.send(msg[i:i+2000])
            
    @commands.command()
    @commands.is_owner()
    async def reload(self,ctx): 
        """Reloads my command cogs. Works even in fatal situations. Sometimes."""
        self.bot.unload_extension('makucommands')
        temp_output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = temp_output
        self.bot.load_extension('makucommands')
        sys.stdout = old_stdout
        await self.send_maku_message(temp_output.getvalue())
        
        
def setup(bot):
    bot.add_cog(CriticalCommands(bot))