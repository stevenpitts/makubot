'''
Main module for makubot.
This module should never have to be reloaded.
All reloading should take place in makucommands,
criticalcommands, and commandutil.
'''
import logging
import discord
from discord.ext import commands
from pathlib import Path


SCRIPT_DIR = Path(__file__).parent
PARENT_DIR = SCRIPT_DIR.parent
DATA_DIR = PARENT_DIR / 'data'
logging.basicConfig(filename=DATA_DIR/'makubot.log', level=logging.INFO)


class MakuBot(commands.Bot):
    '''
    MakuBot class
    Client -> Bot -> MakuBot
    '''

    def __init__(self):
        commands.Bot.__init__(self, command_prefix=commands.when_mentioned,
                              case_insensitive=True,
                              owner_id=203285581004931072)
        self.makusu = None
        self.shared = {}
        self.load_extension('project.criticalcommands')
        self.load_extension('project.reminders')
        self.load_extension('project.picturecommands')
        self.load_extension('project.makucommands')

    async def on_ready(self):
        '''
        Called when MakuBot has logged in and is ready to accept commands
        '''
        self.makusu = await self.get_user_info(self.owner_id)
        print('Logged in as {} with ID {}'
              .format(self.user.name, self.user.id))
        await self.change_presence(activity=discord.Game(
            name=r'Lilybot is being tsun to me :<'))
