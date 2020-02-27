import discord
from discord.ext import commands
import logging
import re
import asyncio
from . import commandutil

MOVE_EMOTE = "\U0001f232"

logger = logging.getLogger()


class Movement(discord.ext.commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        """Called when a user adds a reaction to a message which is in my cache.
        Currently only looks for the "move message" emoji."""

        def author_is_user_check(message):
            return message.author == user

        if (reaction.emoji == MOVE_EMOTE and
                reaction.message.channel.permissions_for(self).send_messages):
            await reaction.message.channel.send(
                f"{user.mention} Move to which channel?")
            while True:
                message = await self.bot.wait_for("message",
                                                  check=author_is_user_check)
                if message.content.lower().strip() == "cancel":
                    await message.channel.send("Cancelled")
                    return
                try:
                    channel_id = int(re.match(r"<#([0-9]+)>$",
                                              message.content).group(1))
                    channel_to_move_to = self.bot.get_channel(channel_id)
                    if channel_to_move_to is None:
                        raise ValueError("Channel to move to is none")
                except (ValueError, AttributeError):
                    await message.channel.send(
                        "That does not look like a tagged channel, "
                        "try again. (You do not need to readd the "
                        "reaction. Say 'cancel' to cancel the move request.)")
                except TypeError:
                    await message.channel.send(
                        "Hmmm, that looks like a channel but I am unable "
                        "to figure out what it is. It has already "
                        "been logged for Maku to debug.")
                    logger.error(
                        "Could not figure out what channel {} was."
                        .format(channel_id))
                else:
                    await self.move_message_attempt(reaction.message,
                                                    channel_to_move_to,
                                                    message.author)

    @commands.command(aliases=["savepins"])
    async def save_pins(self, ctx, pins_channel: discord.TextChannel):
        """
        Send all the pins in the current channel
        to a dedicated pins channel!
        Remember to use mb.deleteallpins after this!
        """
        bot_as_member = ctx.guild.get_member(self.bot.user.id)
        member_can_move_messages = pins_channel.permissions_for(
            ctx.message.author).send_messages
        bot_can_send_messages = pins_channel.permissions_for(
            bot_as_member).send_messages
        if not member_can_move_messages:
            await ctx.send("I'm not sure if you're allowed to do that, sorry!")
            return
        if not bot_can_send_messages:
            await ctx.send("I don't have permissions to send messages there!")
            return
        save_pin_futures = []
        for message in await ctx.channel.pins():
            pin_embed_dict = {
                "title": await commandutil.clean(ctx, message.content),
                "footer": {"text": f"In {message.channel.name}"},
                "author": {"name": message.author.name,
                           "icon_url": str(message.author.avatar_url)
                           },
                "timestamp": message.created_at.isoformat()
             }
            pin_embed = discord.Embed.from_dict(pin_embed_dict)
            save_pin_futures.append(pins_channel.send(embed=pin_embed))
        await asyncio.gather(*save_pin_futures)
        await ctx.send("Done!")

    @commands.command(aliases=["deleteallpins"])
    @commands.bot_has_permissions(manage_messages=True)
    async def delete_all_pins(self, ctx):
        """
        Delete all pins from the current channel. I'll really do it!
        """
        member_can_move_messages = ctx.channel.permissions_for(
            ctx.message.author).manage_messages
        if not member_can_move_messages:
            await ctx.send("I'm not sure if you're allowed to do that, sorry!")
            return
        for pin in await ctx.channel.pins():
            await pin.unpin()
        await ctx.send("Done!")

    async def move_message_attempt(self, message: discord.Message,
                                   channel: discord.TextChannel,
                                   move_request_user: discord.Member):
        """
        Called when ther user attempts to move a message.
        Can be called with an emoji or with a command.
        """
        member_can_move_messages = channel.permissions_for(
            move_request_user).manage_messages
        should_get_moved = (member_can_move_messages
                            or move_request_user == message.author
                            or move_request_user.id == self.bot.makusu.id)
        if should_get_moved:
            attachment_files = [
                await attachment.to_file()
                for attachment in message.attachments
                ]
            move_description = (f"{move_request_user.mention} has moved "
                                f"this here from {message.channel.mention}. "
                                f"OP was {message.author.mention}.\n"
                                f"{message.content}")
            await channel.send(move_description, files=attachment_files)
            await message.delete()
        else:
            await message.channel.send("Looks like you don\"t have the manage "
                                       "messages role and you\"re not OP :(")

    @commands.command()
    @commands.bot_has_permissions(manage_messages=True)
    async def move(self, ctx, msg_id, channel_to_move_to: discord.TextChannel):
        """
        move <message_id> <channel_mention>: move a message.
        Message is moved from the current channel to the channel specified.
        You can also add the reaction \U0001f232 to automate this process.
        """
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
    logger.info("movement starting setup")
    bot.add_cog(Movement(bot))
    logger.info("movement ending setup")
