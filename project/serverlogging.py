import discord
from discord.ext import commands
from discord.utils import escape_markdown
import logging
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

    @commands.command(hidden=True, aliases=['removelogchannel'])
    @commands.is_owner()
    async def remove_log_channel(self, ctx):
        self.bot.shared['data']['log_channels'].pop(str(ctx.guild.id), None)
        await ctx.send("Coolio")

    @commands.command(hidden=True, aliases=['addlogchannel'])
    @commands.is_owner()
    async def add_log_channel(self, ctx, log_channel: discord.TextChannel):
        guild_id, log_channel_id = str(ctx.guild.id), str(log_channel.id)
        self.bot.shared['data']['log_channels'][guild_id] = log_channel_id
        await ctx.send(r"You gotcha \o/")

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
        guild_description = getattr(message.guild, "name", "DMs")
        attachment_files = []
        for attachment in message.attachments:
            filepath = SAVED_ATTACHMENTS_DIR / attachment.filename
            try:
                try:
                    await attachment.save(filepath, use_cached=True)
                except (discord.errors.HTTPException, discord.errors.NotFound,
                        discord.errors.Forbidden):
                    await attachment.save(filepath, use_cached=False)
            except (discord.errors.Forbidden, discord.errors.HTTPException,
                    discord.errors.NotFound):
                continue
            attachment_files.append(discord.File(filepath))
        num_failed = len(message.attachments) - len(attachment_files)
        deletion_text = (
            f'{message.created_at}: A message from {message.author.name} '
            f'has been deleted in {message.channel} of {guild_description} '
            f'with {len(message.attachments)} attachments '
            f'({num_failed} failed to save): {message.content}')
        self.last_deleted_message[message.channel.id] = deletion_text
        with codecs.open(DELETION_LOG_PATH, 'a', 'utf-8') as deletion_log_file:
            deletion_log_file.write(deletion_text+'\n')
        log_channels = self.bot.shared['data']['log_channels']
        should_be_logged = (message.guild and message.channel
                            and str(message.guild.id) in log_channels
                            and (log_channels[str(message.guild.id)]
                                 != str(message.channel.id)))
        if should_be_logged:
            log_channel = self.bot.get_channel(int(log_channels
                                                   [str(message.guild.id)]))
            await log_channel.send(rf'```{escape_markdown(deletion_text)}```',
                                   files=attachment_files)


def setup(bot):
    logging.info('serverlogging starting setup')
    bot.add_cog(ServerLogging(bot))
    logging.info('serverlogging ending setup')
