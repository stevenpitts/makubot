"""
Module containing the majority of the basic commands makubot can execute.
"""
import sys
import importlib
import logging
import itertools
import discord
from discord.ext import commands
from . import util
from psycopg2.extras import RealDictCursor

logger = logging.getLogger()

SUPPORT_SERVER_ID = 704113879919099914


class Base(discord.ext.commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        version_formatted = ".".join(map(str, sys.version_info[:3]))
        self.bot.description = f"""
        Hey there! I'm Makubot!
        I know a lot of commands. Test my vast knowledge!
        You can use mb.help <command> for detailed help!
        I'm currently running Python {version_formatted}.
        Also, you can join the support server at discord.gg/JqfeT4J! ^_^
        If there are legal issues with an image, please join:
            discord.gg/JqfeT4J
        """
        prefix_combinations = itertools.product('mMnN', 'bB', '.!', [' ', ''])
        prefixes = [''.join(r) for r in prefix_combinations]
        self.bot.command_prefix = prefixes
        cursor = self.bot.db_connection.cursor(cursor_factory=RealDictCursor)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS free_guilds (
            guild_id CHARACTER(18) PRIMARY KEY
            );
            """)
        self.bot.db_connection.commit()

    @commands.command()
    @commands.guild_only()
    async def areyoufree(self, ctx):
        """If I have free reign I'll tell you"""
        is_free = str(ctx.guild.id) in self.get_free_guild_ids()
        await ctx.send("Yes, I am free." if is_free else
                       "This is not a free reign guild.")

    @commands.command(hidden=True)
    @commands.is_owner()
    async def perish(self, ctx):
        """Murders me :( """
        await self.bot.close()

    @commands.command()
    async def support(self, ctx):
        """I'll send you a link to my support server!"""
        support_server = self.bot.get_guild(SUPPORT_SERVER_ID)
        invite = await support_server.system_channel.create_invite(
            max_age=600)
        await ctx.send(invite.url)

    @commands.command()
    async def invite(self, ctx):
        """I'll send you a link to invite me to your server!"""
        link = (
            f"https://discordapp.com/oauth2/authorize?"
            f"&client_id={self.bot.user.id}&scope=bot&permissions=314432/"
        )
        await ctx.send(link)

    def get_free_guild_ids(self):
        cursor = self.bot.db_connection.cursor(cursor_factory=RealDictCursor)
        cursor.execute(
            """
            SELECT * FROM free_guilds
            """,
        )
        results = cursor.fetchall()
        return [result["guild_id"] for result in results]

    @commands.command()
    @commands.is_owner()
    @commands.guild_only()
    async def gowild(self, ctx):
        """Add the current guild as a gowild guild; I do a bit more on these.
        Only Maku can add guilds though :("""
        cursor = self.bot.db_connection.cursor(cursor_factory=RealDictCursor)
        if not ctx.message.guild:
            return
        cursor.execute(
            """
            INSERT INTO free_guilds (
            guild_id)
            VALUES (%s)
            """,
            (str(ctx.message.guild.id),))
        self.bot.db_connection.commit()
        await ctx.send("Ayaya~")

    @commands.command()
    @commands.bot_has_permissions(manage_messages=True)
    async def opentxt(self, ctx):
        """Opens the most recent file for reading!!!"""
        try:
            previous_messages = (message async for message in
                                 ctx.channel.history() if message.attachments)
            message_with_file = await previous_messages.__anext__()
            attachment = message_with_file.attachments[0]
            temp_save_dir = self.bot.shared["temp_dir"]
            await attachment.save(temp_save_dir / attachment.filename)
            with open(temp_save_dir / attachment.filename, "r") as file:
                out_text = "\n".join(file.readlines()).replace("```", '"""')
        except UnicodeDecodeError:
            await ctx.send(f"It looks like you\"re trying to get me to "
                           f"read ```{attachment.filename}```, but that "
                           "doesn\"t seem to be a text file, sorry!! :<")
        except StopAsyncIteration:
            await ctx.send("Ah, I couldn't find any text file, sorry!")
        else:
            await util.displaytxt(ctx, out_text)


def setup(bot):
    logger.info("base starting setup")
    bot.add_cog(Base(bot))
    logger.info("base ending setup")
