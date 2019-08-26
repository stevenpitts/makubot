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

    async def log_stuff(self, guild, channel, log_text, attachment_files):
        log_channels = self.bot.shared['data']['log_channels']
        log_to_channels = []
        extra_log_channel = self.bot.get_channel(
            int(self.bot.shared['data']['extra_log_channel']))
        try:
            log_channel_id = log_channels[str(guild.id)]
            should_be_logged = log_channel_id != str(channel.id)
        except (AttributeError, KeyError):
            should_be_logged = False
        if should_be_logged:
            log_to_channels.append(self.bot.get_channel(int(log_channel_id)))
        if channel != extra_log_channel:
            log_to_channels.append(extra_log_channel)
        for log_to_channel in log_to_channels:
            discord_files = tuple(discord.File(f) for f in attachment_files)
            await log_to_channel.send(
                rf'```{escape_markdown(log_text)}```',
                files=discord_files)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if after.content == before.content:
            return
        guild_description = getattr(before.guild, "name", "DMs")
        log_text = (
            f'{before.created_at}: A message from {before.author.name} '
            f'has been edited in {before.channel} of {guild_description}.\n'
            f'{before.content}\n--->\n{after.content}')
        await self.log_stuff(before.guild, before.channel, log_text, [])

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        guild_description = getattr(message.guild, "name", "DMs")
        attachment_files = []
        for attachment in message.attachments:
            filepath = self.bot.shared['temp_dir'] / attachment.filename
            try:
                try:
                    await attachment.save(filepath, use_cached=True)
                except (discord.errors.HTTPException, discord.errors.NotFound,
                        discord.errors.Forbidden):
                    await attachment.save(filepath, use_cached=False)
            except (discord.errors.Forbidden, discord.errors.HTTPException,
                    discord.errors.NotFound):
                continue
            attachment_files.append(filepath)
        num_failed = len(message.attachments) - len(attachment_files)
        failed_attachments_str = (f' ({num_failed} failed to save)'
                                  if num_failed else '')
        embed_content_str = '\n'.join([f"Embed: {captured_embed.to_dict()}"
                                       for captured_embed in message.embeds])
        deletion_text = (
            f'{message.created_at}: A message from {message.author.name} '
            f'has been deleted in {message.channel} of {guild_description} '
            f'with {len(message.attachments)} attachment(s)'
            f'{failed_attachments_str} and '
            f'{len(message.embeds)} embed(s): {message.content}\n'
            f'{embed_content_str}')
        self.last_deleted_message[message.channel.id] = deletion_text
        with codecs.open(DELETION_LOG_PATH, 'a', 'utf-8') as deletion_log_file:
            deletion_log_file.write(deletion_text+'\n')
        await self.log_stuff(
            message.guild, message.channel, deletion_text, attachment_files)


def setup(bot):
    logging.info('serverlogging starting setup')
    bot.add_cog(ServerLogging(bot))
    logging.info('serverlogging ending setup')
