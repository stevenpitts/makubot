import discord
from discord.ext import commands
import logging
import aiohttp
from datetime import datetime
import asyncio

logger = logging.getLogger()


class ServerLogging(discord.ext.commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.last_deleted_message = {}
        """Maps channel ID to (last deleted message content, sender)"""
        self.bot.db_cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS log_channels (
            guild_id CHARACTER(18) PRIMARY KEY,
            log_channel_id CHARACTER(18));
            """)
        self.bot.db_cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS extra_log_channel (
            guild_id CHARACTER(18) PRIMARY KEY,
            log_channel_id CHARACTER(18));
            """)
        self.bot.db_connection.commit()

    @commands.command(hidden=True, aliases=["removelogchannel"])
    @commands.is_owner()
    async def remove_log_channel(self, ctx):
        # self.bot.shared["data"]["log_channels"].pop(str(ctx.guild.id), None)
        self.bot.db_cursor.execute(
            """
            DELETE FROM log_channels WHERE guild_id = %s
            """,
            (ctx.guild.id,)
            )
        self.bot.db_connection.commit()
        # TODO DATA DONE
        await ctx.send("Coolio")

    @commands.command(hidden=True, aliases=["addlogchannel"])
    @commands.is_owner()
    async def add_log_channel(self, ctx, log_channel: discord.TextChannel):
        guild_id, log_channel_id = str(ctx.guild.id), str(log_channel.id)
        # self.bot.shared["data"]["log_channels"][guild_id] = log_channel_id
        # TODO see what happens when you add a second log channel
        # (wouldn't be unique primary key)
        self.bot.db_cursor.execute(
            """
            INSERT INTO log_channels (
            guild_id,
            log_channel_id)
            VALUES (%s, %s)
            """,
            (guild_id, log_channel_id)
            )
        self.bot.db_connection.commit()
        await ctx.send(r"You gotcha \o/")

    @commands.command(aliases=["what was that",
                               "whatwasthat?",
                               "what was that?"])
    async def whatwasthat(self, ctx):
        """Tells you what that fleeting message was"""
        try:
            await ctx.send(self.last_deleted_message.pop(ctx.channel.id))
        except KeyError:
            await ctx.send("I can't find anything, sorry :(")

    @commands.command(hidden=True)
    @commands.is_owner()
    async def set_extra_log_channel(self, ctx,
                                    log_channel: discord.TextChannel):
        self.bot.db_cursor.execute(
            """
            DELETE FROM extra_log_channel *;
            """
            )
        self.bot.db_cursor.execute(
            """
            INSERT INTO extra_log_channel (
            guild_id,
            log_channel_id)
            VALUES (%s, %s)
            """,
            (str(log_channel.guild.id), str(log_channel.id))
            )
        self.bot.db_connection.commit()
        await ctx.send("Done!")

    def get_extra_log_channel(self):
        self.bot.db_cursor.execute(
            """
            SELECT * FROM extra_log_channel;
            """
            )
        results = self.bot.db_cursor.fetchall()
        if not results:
            return None
        result = results[0]
        channel_id = result["log_channel_id"]
        extra_log_channel = self.bot.get_channel(int(channel_id))
        return extra_log_channel

    async def get_log_channels(self, guild, channel):
        # log_channels = self.bot.shared["data"]["log_channels"]
        if guild is None:
            return [self.get_extra_log_channel()]
        self.bot.db_cursor.execute(
            """
            SELECT * FROM log_channels
            WHERE guild_id = %s
            AND log_channel_id != %s
            LIMIT 1""",
            (str(guild.id), str(channel.id))
            )
        log_channel_results = self.bot.db_cursor.fetchall()
        extra_log_channel = self.get_extra_log_channel()
        if not log_channel_results:
            if extra_log_channel:
                return (extra_log_channel,)
            return ()
        log_to_channel_dict = log_channel_results[0]
        log_to_channels = []
        log_to_channel_id = log_to_channel_dict["log_channel_id"]
        if log_to_channel_id != str(channel.id):
            log_to_channel_obj = self.bot.get_channel(
                int(log_to_channel_id))
            log_to_channels.append(log_to_channel_obj)
        if extra_log_channel and log_to_channel_id != extra_log_channel.id:
            log_to_channels.append(extra_log_channel)
        return tuple(log_to_channels)

        # log_to_channels = [log_channel_result["log_channel_id"]
        #                    for log_channel_result in log_channel_results
        #                    ]
        # log_to_channels = []
        # extra_log_channel = self.bot.get_channel(
        #     int(self.bot.shared["data"]["extra_log_channel"]))
        # try:
        #     log_channel_id = log_channels[str(guild.id)]
        #     should_be_logged = log_channel_id != str(channel.id)
        # except (AttributeError, KeyError):
        #     should_be_logged = False
        # if should_be_logged:
        #     log_to_channels.append(self.bot.get_channel(int(log_channel_id)))
        # if channel != extra_log_channel:
        #     log_to_channels.append(extra_log_channel)
        # return tuple(log_to_channels)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if after.author.bot:
            return
        if after.content == before.content:
            return
        guild_description = getattr(before.guild, "name", "DMs")
        log_to_channels = await self.get_log_channels(
            before.guild, before.channel)
        embed = discord.Embed(
            title="Edited message",
            description=(f"{datetime.now()}: A message from "
                         f"{before.author.name} has been "
                         f"edited in {before.channel} of {guild_description}.")
            )
        if after.content != before.content:
            before_content = before.content[:1000].strip() or "[NOTHING]"
            after_content = after.content[:1000].strip() or "[NOTHING]"
            embed.add_field(name="Before", value=before_content)
            embed.add_field(name="After", value=after_content)
        before_fields = [field for before_embed in before.embeds
                         for field in before_embed.fields]
        after_fields = [field for after_embed in after.embeds
                        for field in after_embed.fields]
        removed_fields = set(before_fields) - set(after_fields)
        added_fields = set(after_fields) - set(before_fields)
        for field in removed_fields:
            embed.add_field(
                name=f"Removed field ({field.name})", value=field.value)
        for field in added_fields:
            embed.add_field(
                name=f"Added field ({field.name})", value=field.value)
        for log_to_channel in log_to_channels:
            await log_to_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        guild = member.guild
        leave_message = f"{datetime.now()}: {member} has left {guild}"
        log_to_channels = await self.get_log_channels(
            guild, guild.system_channel)
        for log_to_channel in log_to_channels:
            await log_to_channel.send(leave_message)

    @commands.Cog.listener()
    async def on_user_update(self, before, after):
        new_username = str(before) != str(after)
        embed = discord.Embed(
            title="User Profile Update",
            description=(
                f"{after} has updated their "
                f"{'username' if new_username else 'avatar'}")
            )
        if new_username:
            embed.add_field(name="Old", value=str(before))
            embed.add_field(name="New", value=str(after))
        else:
            embed.set_image(url=after.avatar_url)
        log_to_channels = set.union(*[
            set(await self.get_log_channels(server,
                                            server.system_channel))
            for server in self.bot.guilds
            if server.get_member(after.id)])
        for log_to_channel in log_to_channels:
            try:
                await log_to_channel.send(embed=embed)
            except (aiohttp.client_exceptions.ClientConnectorError,
                    asyncio.TimeoutError):
                embed.set_image(url=(
                    r"https://t7.rbxcdn.com/"
                    r"b108964694f35a0db26262e4ba1d3d86"))
                await log_to_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_bulk_message_delete(self, messages):
        asyncio.gather(*[self.on_message_delete(msg) for msg in messages])

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.author.bot:
            return
        guild_description = getattr(message.guild, "name", "DMs")
        attachment_files = []
        for attachment in message.attachments:
            filepath = self.bot.shared["temp_dir"] / attachment.filename
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
        failed_attachments_str = (f" ({num_failed} failed to save)"
                                  if num_failed else "")
        embed_content_str = "\n".join([f"Embed: {captured_embed.to_dict()}"
                                       for captured_embed in message.embeds])
        embed_content_str = str(embed_content_str).strip()
        deletion_description = (
            f"{datetime.now()}: A message from {message.author.name} "
            f"has been deleted in {message.channel} of {guild_description} "
            f"with {len(message.attachments)} attachment(s)"
            f"{failed_attachments_str} and "
            f"{len(message.embeds)} embed(s)")
        deletion_text = (f"{deletion_description}: "
                         f"{message.content}\n{embed_content_str}")
        self.last_deleted_message[message.channel.id] = deletion_text
        log_to_channels = await self.get_log_channels(message.guild,
                                                      message.channel)
        embed = discord.Embed(
            title="Deleted message",
            description=deletion_description)
        if message.content.strip():
            embed.add_field(name="Deleted content",
                            value=message.content[:1000])
        for deleted_embed in message.embeds:
            for field in deleted_embed.fields:
                embed.add_field(name=field.name, value=field.value)
        for log_to_channel in log_to_channels:
            discord_files = tuple(discord.File(f) for f in attachment_files)
            await log_to_channel.send(embed=embed, files=discord_files)


def setup(bot):
    logger.info("serverlogging starting setup")
    bot.add_cog(ServerLogging(bot))
    logger.info("serverlogging ending setup")
