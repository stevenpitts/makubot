import discord
from discord.ext import commands
import random
import asyncio
import time
import tokens
from tokens import *
import re
import sys


class MakuBot(commands.Bot):
    #So, bot is a subclass of discord.Client, and this is a subclass of bot.

    def __init__(self):
        commands.Bot.__init__(self,command_prefix=commands.when_mentioned_or('mb!','mb.','mb! ','mb. '),case_insensitive=True,owner_id=203285581004931072)
        self.makusu = None

        

    async def on_ready(self):
        """Triggered when bot connects. Event."""
        self.makusu = await self.get_user_info(self.owner_id)
        print('Logged in as ',self.user.name,' with ID ',self.user.id)
        await self.change_presence(activity=discord.Game(name=r"SmugBot is being tsun to me :<"))
        self.load_extension('criticalcommands')
        try:
            self.load_extension('makucommands')
        except NameError:
            print("Error loading makucommands.")
            raise
        


makubot = MakuBot()

def main():
	makubot.run(makubotToken)

if __name__=="__main__":
    main()


