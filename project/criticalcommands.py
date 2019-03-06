'''
Module used for any activity that must stay usable \
even in the event that makucommands become unusable.
This can happen if, for example, makucommands is reloaded with a syntax error.
'''
import discord
from . import commandutil
import importlib
import logging


class CriticalCommands(discord.ext.commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.ext.commands.command(hidden=True)
    @discord.ext.commands.is_owner()
    async def reload(self, ctx):
        '''
        Reloads my command cogs. Works even in fatal situations. Sometimes.
        '''
        logging.info('---Reloading makucommands and commandutil---')
        importlib.reload(commandutil)
        reload_response = ''
        for to_reload in ['reminders',
                          'picturecommands',
                          'serverlogging',
                          'makucommands',
                          'movement']:
            ctx.bot.unload_extension(f'project.{to_reload}')
            try:
                ctx.bot.load_extension(f'project.{to_reload}')
                logging.info(f'Successfully reloaded {to_reload}')
                reload_response += f'\nSuccessfully reloaded {to_reload}!'
            except Exception as e:
                excepted_traceback = commandutil.get_formatted_traceback(e)
                logging.info(f'Failed to reload {to_reload}:\
                             {excepted_traceback}\n\n\n')
                reload_response += f'\nFailed to reload {to_reload}'
                print('Error importing {to_reload}: \n{excepted_traceback}')
        await ctx.send(reload_response)


def setup(bot):
    bot.add_cog(CriticalCommands(bot))
