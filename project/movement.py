import discord
from discord.ext import commands
import logging
import re
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PARENT_DIR = SCRIPT_DIR.parent
DATA_DIR = PARENT_DIR / 'data'
SAVED_ATTACHMENTS_DIR = DATA_DIR / 'saved_attachments'

MOVE_EMOTE = '\U0001f232'


class Movement(discord.ext.commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        '''Called when a user adds a reaction to a message which is in my cache.
        Currently only looks for the 'move message' emoji.'''

        def author_is_user_check(message):
            return message.author == user

        if reaction.emoji == MOVE_EMOTE:
            await reaction.message.channel.send(
                f'{user.mention} Move to which channel?')
            while True:
                message = await self.bot.wait_for('message',
                                                  check=author_is_user_check)
                if message.content.lower().strip() == 'cancel':
                    await message.channel.send('Cancelled')
                    return
                try:
                    channel_id = int(re.match(r'<#([0-9]+)>$',
                                              message.content).group(1))
                    channel_to_move_to = self.bot.get_channel(channel_id)
                    if channel_to_move_to is None:
                        raise ValueError('Channel to move to is none')
                except (ValueError, AttributeError):
                    await message.channel.send(
                        'That does not look like a tagged channel, '
                        'try again. (You do not need to readd the '
                        'reaction. Say "cancel" to cancel the move request.)')
                except TypeError:
                    await message.channel.send(
                        'Hmmm, that looks like a channel but I am unable '
                        'to figure out what it is. It has already '
                        'been logged for Maku to debug.')
                    logging.error(
                        'Could not figure out what channel {} was.'
                        .format(channel_id))
                else:
                    await self.move_message_attempt(reaction.message,
                                                    channel_to_move_to,
                                                    message.author)

    async def move_message_attempt(self, message: discord.Message,
                                   channel: discord.TextChannel,
                                   move_request_user: discord.Member):
        '''
        Called when ther user attempts to move a message.
        Can be called with an emoji or with a command.
        '''
        member_can_move_messages = channel.permissions_for(
            move_request_user).manage_messages
        should_get_moved = (member_can_move_messages
                            or move_request_user == message.author
                            or move_request_user.id == self.bot.makusu.id)
        if should_get_moved:
            for attachment in message.attachments:
                await attachment.save(SAVED_ATTACHMENTS_DIR
                                      / attachment.filename)
            attachment_files = [
                discord.File(SAVED_ATTACHMENTS_DIR / attachment.filename)
                for attachment in message.attachments]
            move_description = (f'{move_request_user.mention} has moved '
                                f'this here from {message.channel.mention}. '
                                f'OP was {message.author.mention}.\n'
                                f'{message.content}')
            await channel.send(move_description, files=attachment_files)
            await message.delete()
        else:
            await message.channel.send('Looks like you don\'t have the manage '
                                       'messages role and you\'re not OP :(')

    @commands.command()
    @commands.bot_has_permissions(manage_messages=True)
    async def move(self, ctx, msg_id, channel_to_move_to: discord.TextChannel):
        '''
        move <message_id> <channel_mention>: move a message.
        Message is moved from the current channel to the channel specified.
        You can also add the reaction \U0001f232 to automate this process.
        '''
        try:
            message_to_move = await ctx.message.channel.fetch_message(msg_id)
        except discord.errors.HTTPException:
            await ctx.message.channel.send(
                "That, uh, doesn't look like a valid message ID. Try again.")
        else:
            await self.move_message_attempt(message_to_move,
                                            channel_to_move_to,
                                            ctx.message.author)


def setup(bot):
    logging.info('movement starting setup')
    bot.add_cog(Movement(bot))
    logging.info('movement ending setup')
