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
from discord.utils import escape_markdown

logger = logging.getLogger()


class Base(discord.ext.commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        version_formatted = ".".join(map(str, sys.version_info[:3]))
        self.bot.description = f"""
        Hey there! I'm Nao!
        I know a lot of commands. Test my vast knowledge!
        You can use nb.help <command> for detailed help!
        I'm currently running Python {version_formatted}.
        Also, you can join the support server at support.naobot.net! ^_^
        If there is a legal issue with an image, please join support.naobot.net
        """
        prefix_combinations = itertools.product('mMnN', 'bB', '.!', [' ', ''])
        prefixes = [''.join(r) for r in prefix_combinations]
        self.bot.command_prefix = commands.when_mentioned_or(*prefixes)
        cursor = self.bot.db_connection.cursor(cursor_factory=RealDictCursor)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS free_guilds (
            guild_id CHARACTER(18) PRIMARY KEY
            );
            """)
        self.bot.db_connection.commit()

    @commands.command(hidden=True)
    @commands.is_owner()
    async def reload(self, ctx):
        """
        Reloads my command cogs. Works even in fatal situations. Sometimes.
        """
        logger.info("---Reloading base and util---")
        importlib.reload(util)
        reload_response = ""
        for to_reload in self.bot.shared["default_extensions"]:
            try:
                ctx.bot.reload_extension(f"src.{to_reload}")
            except Exception as e:
                reload_response += f"Failed to reload {to_reload}\n"
                fail_tb = util.get_formatted_traceback(e)
                fail_message = f"Error reloading {to_reload}: \n{fail_tb}\n\n"
                logger.error(fail_message)
                logger.info(fail_message)
        reload_response += "Done!"
        await ctx.send(reload_response)
        logger.info("Reloaded")

    @commands.command(aliases=["are you free",
                               "areyoufree?",
                               "are you free?"])
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
        util.backup_db(self.bot.s3_bucket)
        await self.bot.close()

    def get_free_guild_ids(self):
        cursor = self.bot.db_connection.cursor(cursor_factory=RealDictCursor)
        cursor.execute(
            """
            SELECT * FROM free_guilds
            """,
        )
        results = cursor.fetchall()
        return [result["guild_id"] for result in results]

    @commands.command(aliases=["go wild"])
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
        async def displaytxt(extracted_text: str):
            block_size = 500
            button_emojis = left_arrow, right_arrow, stop_emote = "👈👉❌"
            text_blocks = [f"{extracted_text[i:i+block_size]}"
                           for i in range(0, len(extracted_text), block_size)]
            text_blocks = [f"```{escape_markdown(text_block)}```"
                           for text_block in text_blocks]
            current_index = 0
            block_message = await ctx.send(text_blocks[current_index])

            def check(reaction, user):
                return (user != self.bot.user
                        and reaction.emoji in button_emojis
                        and reaction.message.id == block_message.id)

            while current_index is not None:
                await block_message.edit(content=text_blocks[current_index])
                for emoji_to_add in button_emojis:
                    await block_message.add_reaction(emoji_to_add)
                res = await self.bot.wait_for("reaction_add", check=check)
                emoji_result = res[0].emoji
                await block_message.remove_reaction(emoji_result, res[1])
                if emoji_result == left_arrow:
                    current_index -= 1
                elif emoji_result == right_arrow:
                    current_index += 1
                else:
                    await block_message.clear_reactions()
                    await block_message.edit(content=r"```File closed.```")
                    current_index = None
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
            await displaytxt(out_text)


def setup(bot):
    logger.info("base starting setup")
    bot.add_cog(Base(bot))
    logger.info("base ending setup")
