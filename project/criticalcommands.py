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
        for to_reload in ['reminders', 'picturecommands', 'makucommands']:
            ctx.bot.unload_extension(f'project.{to_reload}')
            try:
                ctx.bot.load_extension(f'project.{to_reload}')
                logging.info(f'Successfully reloaded {to_reload}')
                await ctx.send(f'Successfully reloaded {to_reload}!')
            except Exception as e:
                logging.info('Failed to reload {}:\n{}\n\n\n'
                             .format(to_reload,
                                     commandutil.get_formatted_traceback(e)))
                await commandutil.send_formatted_message(
                    ctx, commandutil.get_formatted_traceback(e))


def setup(bot):
    bot.add_cog(CriticalCommands(bot))
