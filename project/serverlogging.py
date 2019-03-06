import discord
from discord.ext import commands
import logging
from . import commandutil
import codecs
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PARENT_DIR = SCRIPT_DIR.parent
DATA_DIR = PARENT_DIR / 'data'
DELETION_LOG_PATH = DATA_DIR / 'deletion_log.txt'
SAVED_ATTACHMENTS_DIR = DATA_DIR / 'saved_attachments'


class ServerLogging(discord.ext.commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.last_deleted_message = {}
        '''Maps channel ID to (last deleted message content, sender)'''

    @commands.command(aliases=['what was that',
                               'whatwasthat?',
                               'what was that?'])
    async def whatwasthat(self, ctx):
        '''Tells you what that fleeting message was'''
        try:
            await ctx.send(self.last_deleted_message.pop(ctx.channel.id))
        except KeyError:
            await ctx.send("I can't find anything, sorry :(")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        should_be_logged = (
            message.author != self.bot.user
            and message.guild
            and message.guild.id == commandutil.known_ids['aagshit']
            and message.channel.id != commandutil.known_ids['aagshit_lawgs'])
        if should_be_logged:
            for attachment in message.attachments:
                await attachment.save(
                    str(SAVED_ATTACHMENTS_DIR / attachment.filename))
                aagshit_lawgs_channel = self.bot.get_channel(
                    commandutil.known_ids['aagshit_lawgs'])
                try:
                    await aagshit_lawgs_channel.send(
                        rf'Posted by {message.author.name} '
                        'in {message.channel.mention}:',
                        file=discord.File(str(SAVED_ATTACHMENTS_DIR
                                              / attachment.filename)))
                except discord.errors.Forbidden:
                    print("Unable to log message due to permission error")

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        deletion_message = (
            f'{message.created_at}:A message from {message.author.name} '
            f'has been deleted in {message.channel.name} of '
            f'{message.channel.guild.name} with {len(message.attachments)} '
            f'attachment(s): {message.content}')
        self.last_deleted_message[message.channel.id] = deletion_message
        with codecs.open(DELETION_LOG_PATH, 'a', 'utf-8') as deletion_log_file:
            deletion_log_file.write(deletion_message+'\n')
        should_be_logged = (
            message.guild
            and message.channel.guild.id == commandutil.known_ids['aagshit']
            and message.channel.id != commandutil.known_ids['aagshit_lawgs'])
        if should_be_logged:
            aagshit_lawgs_channel = self.bot.get_channel(
                commandutil.known_ids['aagshit_lawgs'])
            await aagshit_lawgs_channel.send(rf'```{deletion_message}```')


def setup(bot):
    logging.info('serverlogging starting setup')
    bot.add_cog(ServerLogging(bot))
    logging.info('serverlogging ending setup')
