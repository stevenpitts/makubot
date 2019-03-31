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
    async def on_message_delete(self, message):
        guild_description = (message.channel.guild.name if
                             isinstance(message.channel,
                                        discord.abc.GuildChannel)
                             else "DMs")
        attachment_files = []
        for attachment in message.attachments:
            filepath = SAVED_ATTACHMENTS_DIR / attachment.filename
            try:
                await attachment.save(filepath, use_cached=True)
            except discord.errors.HTTPException:
                await attachment.save(filepath, use_cached=False)
            except discord.errors.NotFound:
                continue
            attachment_files.append(discord.File(filepath))
        deletion_message = (
            f'{message.created_at}: A message from {message.author.name} '
            f'has been deleted in {message.channel} of {guild_description} '
            f'with {len(message.attachments)} attachments: {message.content}')
        self.last_deleted_message[message.channel.id] = deletion_message
        with codecs.open(DELETION_LOG_PATH, 'a', 'utf-8') as deletion_log_file:
            deletion_log_file.write(deletion_message+'\n')
        should_be_logged = (
            message.author != self.bot.user and message.guild
            and message.channel.guild.id == commandutil.known_ids['aagshit']
            and message.channel.id != commandutil.known_ids['aagshit_lawgs'])
        if should_be_logged:
            aagshit_lawgs_channel = self.bot.get_channel(
                commandutil.known_ids['aagshit_lawgs'])
            escaped_deletion = deletion_message.replace(r"`", r"'")
            await aagshit_lawgs_channel.send(rf'```{escaped_deletion}```',
                                             files=attachment_files)


def setup(bot):
    logging.info('serverlogging starting setup')
    bot.add_cog(ServerLogging(bot))
    logging.info('serverlogging ending setup')
