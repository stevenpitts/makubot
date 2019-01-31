import discord
from discord.ext import commands
import random
import asyncio
import time
import tokens
from tokens import *
import re
import sys

#TODO switch superclass from bot to client cuz bot is stupid
#Actually maybe don't?




class MakuBot(commands.Bot):
    #So, bot is a subclass of discord.Client, and this is a subclass of bot.

    def __init__(self,log_to_file=True):
        self.log_to_file = log_to_file
        commands.Bot.__init__(self,command_prefix=commands.when_mentioned,case_insensitive=True,owner_id=203285581004931072)
        self.makusu = None

    def printDebugInfo(self):
        print("Current servers: ",{guild.name:guild.id for guild in self.guilds})
        

    async def on_ready(self):
        """Triggered when bot connects. Event."""
        self.makusu = await self.get_user_info(self.owner_id)
        print('Logged in as ',self.user.name,' with ID ',self.user.id)
        await self.change_presence(activity=discord.Game(name=r"SmugBot is being tsun to me :<"))
        self.load_extension('makucommands')
        self.printDebugInfo()
        
    @commands.command()
    @commands.is_owner()
    async def superreload(self,ctx): 
        """Reloads my command cogs. Works even in fatal situations."""
        self.unload_extension('makucommands')
        self.load_extension('makucommands')

        

    

makubot = MakuBot()

def main():
	makubot.run(makubotToken)

if __name__=="__main__":
    main()


#add_reaction
#Fact command that makes bot print the first sentence of a random wikipedia article
