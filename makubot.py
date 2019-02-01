import discord
from discord.ext import commands
import tokens

class MakuBot(commands.Bot):

    def __init__(self):
        commands.Bot.__init__(self,command_prefix=commands.when_mentioned_or('mb!','mb.','mb! ','mb. '),case_insensitive=True,owner_id=203285581004931072)
        self.makusu = None

    async def on_ready(self):
        self.makusu = await self.get_user_info(self.owner_id)
        print('Logged in as ',self.user.name,' with ID ',self.user.id)
        await self.change_presence(activity=discord.Game(name=r"SmugBot is being tsun to me :<"))
        self.load_extension('criticalcommands')
        self.load_extension('makucommands')

if __name__=="__main__":
    MakuBot().run(tokens.makubotToken)


