import discord
from discord.ext import commands
from discord.utils import escape_markdown
import logging
from pathlib import Path
import os
import random
import aiohttp
import asyncio
import shutil
import concurrent
from . import commandutil

SCRIPT_DIR = Path(__file__).parent
PARENT_DIR = SCRIPT_DIR.parent
DATA_DIR = PARENT_DIR / 'data'
PICTURES_DIR = DATA_DIR / 'pictures'

#
# def collection_has_image_bytes(collection: str, image_bytes):
#     collection_dir = PICTURES_DIR / collection


class PictureAdder(discord.ext.commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.temp_save_dir = self.bot.shared['temp_dir']

    async def image_suggestion(self, image_dir, filename, requestor):
        image_collection = image_dir.parts[-1]
        try:
            proposal = (f"Add image {filename} to {image_collection}? "
                        f"Requested by {requestor.name}"
                        if image_dir.exists() else
                        f"Add image to ***NEW*** {image_collection}? "
                        f"Requested by {requestor.name}")
            try:
                request = await self.bot.makusu.send(
                    proposal, file=discord.File(self.temp_save_dir
                                                / filename))
            except discord.errors.HTTPException:
                await requestor.send("Sorry, that image is too large ;~;")
                return
            no_emoji, yes_emoji = "❌", "✅"
            await request.add_reaction(no_emoji)
            await request.add_reaction(yes_emoji)

            def reaction_check(reaction, user):
                return (user == self.bot.makusu
                        and reaction.message.id == request.id
                        and reaction.emoji in [no_emoji, yes_emoji])
            res = None
            while not res:
                try:
                    res = await self.bot.wait_for(
                        "reaction_add", check=reaction_check)
                except concurrent.futures._base.CancelledError:
                    return
                except Exception as e:
                    print(commandutil.get_formatted_traceback(e))
                    await asyncio.sleep(1)
            if res[0].emoji == yes_emoji:
                image_dir.mkdir(parents=True, exist_ok=True)
                new_filename = commandutil.get_nonconflicting_filename(
                    filename, image_dir)
                shutil.move(self.temp_save_dir / filename,
                            image_dir / new_filename)
                self.bot.get_cog("ReactionImages").add_pictures_dir(
                    image_collection)
                await requestor.send(f"Your image {new_filename} "
                                     "was approved!")
            else:
                await requestor.send(f"Your image {filename} "
                                     "was not approved. "
                                     "Feel free to ask Maku why ^_^")
            await request.delete()
        except Exception as e:
            print(commandutil.get_formatted_traceback(e))

    @commands.command(hidden=True, aliases=["aliasimage", "aliaspicture"])
    @commands.is_owner()
    async def add_picture_alias(self, ctx, ref_invocation, true_invocation):
        if not ref_invocation.isalnum() or not true_invocation.isalnum():
            await ctx.send("Please only include letters and numbers.")
            return
        elif self.bot.get_command(ref_invocation):
            await ctx.send(f"{ref_invocation} is already a command :<")
        elif not self.bot.get_command(true_invocation):
            await ctx.send(f"{true_invocation} isn't a command, though :<")
        else:
            aliases = self.bot.shared['data']['alias_pictures']
            if true_invocation in aliases:
                # true_invocation was in turn referencing another invocation
                true_invocation = aliases[true_invocation]
            true_command = self.bot.get_command(true_invocation)
            maps_to_image = (hasattr(true_command, "instance")
                             and isinstance(true_command.instance,
                                            ReactionImages))
            if maps_to_image:
                aliases[ref_invocation] = true_invocation
                true_command.aliases += [ref_invocation]
                self.bot.shared['pictures_commands'] += [ref_invocation]
                self.bot.all_commands[ref_invocation] = true_command
                await ctx.send("Added!")
            else:
                await ctx.send(f"{true_invocation} is not an image command :?")

    @commands.command(aliases=["randomimage", "yo", "hey", "makubot"])
    async def random_image(self, ctx):
        """For true shitposting."""
        files = [Path(dirpath) / Path(filename)
                 for dirpath, dirnames, filenames in os.walk(PICTURES_DIR)
                 for filename in filenames]
        chosen_file = random.choice(files)
        await ctx.send(file=discord.File(chosen_file))

    @commands.command(aliases=["addimage"])
    async def add_image(self, ctx, image_collection: str, *, urls: str = ""):
        """Requests an image be added.
        mb.addimage nao http://static.zerochan.net/Tomori.Nao.full.1901643.jpg
        Then, it'll be sent to maku for approval!"""
        image_collection = image_collection.lower()
        if not image_collection.isalnum():
            await ctx.send("Please only include letters and numbers.")
            return
        image_collection = self.bot.shared['data']['alias_pictures'].get(
            image_collection, image_collection)
        existing_command = self.bot.get_command(image_collection)
        command_taken = (existing_command is not None
                         and (not hasattr(existing_command, "instance")
                              or not isinstance(existing_command.instance,
                                                ReactionImages)))
        if command_taken:
            await ctx.send("That is already a command name.")
            return
        if not urls and not ctx.message.attachments:
            await ctx.send("You must include a URL at the end of your "
                           "message or attach image(s).")
            return
        urls = urls.split() + [attachment.url for attachment
                               in ctx.message.attachments]
        for url in urls:
            filename = commandutil.get_nonconflicting_filename(
                commandutil.slugify(url.split(r"/")[-1]), self.temp_save_dir)
            try:
                data = await self.bot.http.get_from_cdn(url)
                with open(self.temp_save_dir / filename, 'wb') as f:
                    f.write(data)
            except (aiohttp.client_exceptions.ClientConnectorError,
                    aiohttp.client_exceptions.InvalidURL,
                    discord.errors.HTTPException):
                await ctx.send("I can't download that image, sorry!")
            else:
                await ctx.send("Sent to Maku for approval!")
                self.bot.loop.create_task(self.image_suggestion(
                    PICTURES_DIR / image_collection, filename, ctx.author))


class ReactionImages(discord.ext.commands.Cog):

    async def send_image_func(ctx):
        true_path = PICTURES_DIR / ctx.command.name
        file_to_send = true_path / random.choice(os.listdir(true_path))
        await ctx.channel.send(file=discord.File(file_to_send))

    def __init__(self, bot):
        self.bot = bot
        self.bot.shared['pictures_commands'] = []
        self.image_aliases = {}
        for key, val in self.bot.shared['data']['alias_pictures'].items():
            self.image_aliases[val] = self.image_aliases.get(val, []) + [key]
        for folder_name in os.listdir(PICTURES_DIR):
            self.add_pictures_dir(folder_name)

    def add_pictures_dir(self, folder_name: str):
        if folder_name in self.bot.shared['pictures_commands']:
            return
        self.bot.shared['pictures_commands'].append(folder_name)
        collection_aliases = self.image_aliases.get(folder_name, [])
        folder_command = commands.Command(
            ReactionImages.send_image_func,
            name=folder_name,
            brief=folder_name,
            aliases=collection_aliases,
            hidden=True)
        folder_command.instance = self
        folder_command.module = self.__module__
        self.bot.add_command(folder_command)
        for collection_alias in collection_aliases:
            self.bot.shared['pictures_commands'].append(collection_alias)

    @commands.command(aliases=["listreactions"])
    async def list_reactions(self, ctx):
        """List all my reactions"""
        pictures_desc = ', '.join(self.bot.shared['pictures_commands'])
        block_size = 1500
        text_blocks = [f'{pictures_desc[i:i+block_size]}'
                       for i in range(0, len(pictures_desc), block_size)]
        for text_block in text_blocks:
            await ctx.send(f"```{escape_markdown(text_block)}```")


def setup(bot):
    logging.info('picturecommands starting setup')
    bot.add_cog(ReactionImages(bot))
    bot.add_cog(PictureAdder(bot))
    logging.info('picturecommands ending setup')
