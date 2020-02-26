import discord
from discord.ext import commands, tasks
import logging
import concurrent
import asyncio
from psycopg2.extras import RealDictCursor
from . import commandutil

logger = logging.getLogger()


class RoleGiver(discord.ext.commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        cursor = self.bot.db_connection.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rolegivers (
            message_id CHARACTER(18) PRIMARY KEY,
            channel_id CHARACTER(18),
            role_id CHARACTER(18),
            emoji_id CHARACTER(18)
            );
            """)
        self.bot.db_connection.commit()
        self.cycle_rolegivers.start()

    def cog_unload(self):
        self.cycle_rolegivers.stop()

    async def update_rolegiver_message(self, channel_id, message_id, role_id,
                                       emoji_id):
        channel = self.bot.get_channel(int(channel_id))
        message = await channel.fetch_message(message_id)
        emoji = discord.utils.get(self.bot.emojis, id=emoji_id)
        await message.add_reaction(emoji)
        role = channel.guild.get_role(role_id)
        reaction = discord.utils.get(message.reactions, emoji=emoji)
        users_with_reaction = (await reaction.users().flatten()
                               if reaction else [])
        members_with_reaction = {channel.guild.get_member(user.id) for user
                                 in users_with_reaction}
        members_set = set(role.members)
        members_to_remove_role_from = members_set - members_with_reaction
        members_to_add_role_to = members_with_reaction - members_set
        remove_role_tasks = [
            member.remove_roles(role, reason="Removed reaction")
            for member in members_to_remove_role_from]
        add_roles_tasks = [
            member.add_roles(role, reason="Added reaction")
            for member in members_to_add_role_to]
        await asyncio.gather(*remove_role_tasks, *add_roles_tasks)

    def get_rolegiver_ids(self):
        cursor = self.bot.db_connection.cursor(cursor_factory=RealDictCursor)
        cursor.execute(
            """
            SELECT * FROM rolegivers;
            """
            )
        results = cursor.fetchall()
        id_order = ["channel_id", "message_id", "role_id", "emoji_id"]
        return [[int(result[id_name]) for id_name in id_order]
                for result in results]

    def add_rolegiver_ids(self, channel_id, message_id, role_id, emoji_id):
        cursor = self.bot.db_connection.cursor()
        cursor.execute(
            """
            INSERT INTO rolegivers (
            message_id,
            channel_id,
            role_id,
            emoji_id
            )
            VALUES (%s, %s, %s, %s);
            """,
            (str(message_id), str(channel_id), str(role_id), str(emoji_id))
            )
        self.bot.db_connection.commit()

    @tasks.loop(seconds=5)  # TODO change to 60 after confirmed working
    async def cycle_rolegivers(self):
        try:
            rolegiver_tasks = [
                self.update_rolegiver_message(*rolegiver_ids)
                for rolegiver_ids in self.get_rolegiver_ids()]
            await asyncio.gather(*rolegiver_tasks)
        except (concurrent.futures._base.CancelledError,
                asyncio.exceptions.CancelledError):
            return
        except Exception as e:
            print(commandutil.get_formatted_traceback(e))

    @cycle_rolegivers.before_loop
    async def before_cycling(self):
        await self.bot.wait_until_ready()

    @commands.command()
    @commands.is_owner()
    @commands.bot_has_permissions(manage_roles=True)
    async def rolegiver(self, ctx, message: discord.Message,
                        role: discord.Role, emoji: discord.Emoji):
        """Have a message give whoever reacts to it with a given emoji
        a role. The emoji MUST be a custom emoji."""
        rolegiver_ids = [message.channel.id, message.id, role.id, emoji.id]
        self.add_rolegiver_ids(*rolegiver_ids)


def setup(bot):
    logger.info("rolegiver starting setup")
    bot.add_cog(RoleGiver(bot))
    logger.info("rolegiver ending setup")
