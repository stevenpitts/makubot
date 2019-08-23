import discord
from discord.ext import commands
from discord.utils import escape_markdown
import logging
from pathlib import Path
import os
import random
import aiohttp
import shutil
import re
import itertools
from . import commandutil

SCRIPT_DIR = Path(__file__).parent
PARENT_DIR = SCRIPT_DIR.parent
DATA_DIR = PARENT_DIR / 'data'
PICTURES_DIR = DATA_DIR / 'pictures'
SAVED_ATTACHMENTS_DIR = DATA_DIR / 'saved_attachments'


def slugify(candidate_filename: str):
    slugified = candidate_filename.replace(" ", "_")
    slugified = re.sub(r'(?u)[^-\w.]', '', slugified)
    slugified = slugified.strip(" .")
    if "." not in slugified:
        slugified += ".unknown"
    return slugified


def get_nonconflicting_filename(candidate_filename: str, directory: Path):
    if not (directory / candidate_filename).is_file():
        return candidate_filename
    try:
        filename_prefix, filename_suffix = candidate_filename.split(".", 1)
    except ValueError:
        raise("Filename was not valid (needs prefix and suffix")
    for addition in itertools.count():
        candidate_filename = f"{filename_prefix}{addition}.{filename_suffix}"
        if not (directory / candidate_filename).is_file():
            return candidate_filename
    raise AssertionError("Shouldn't ever get here")


class PictureAdder(discord.ext.commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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
                    proposal, file=discord.File(SAVED_ATTACHMENTS_DIR
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
            res = await self.bot.wait_for("reaction_add", check=reaction_check)
            if res[0].emoji == yes_emoji:
                image_dir.mkdir(parents=True, exist_ok=True)
                new_filename = get_nonconflicting_filename(filename, image_dir)
                shutil.move(SAVED_ATTACHMENTS_DIR / filename,
                            image_dir / new_filename)
                self.bot.reload_extension("project.picturecommands")
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
                self.bot.reload_extension("project.picturecommands")
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
        mb.addimage reaction nao
        Makubot will then ask the for the image to be added.
        You must send the image as an attachment; I can't save URLs ;~;
        Then, it'll be sent to maku for approval!"""
        image_collection = image_collection.lower()
        if not image_collection.isalnum():
            await ctx.send("Please only include letters and numbers.")
            return
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
            filename = get_nonconflicting_filename(
                slugify(url.split(r"/")[-1]), SAVED_ATTACHMENTS_DIR)
            # while (os.path.exists(PICTURES_DIR / image_collection / filename)
            #        or os.path.exists(SAVED_ATTACHMENTS_DIR / filename)):
            #     filename = f"{str(random.randint(1, 1000))}{filename}"
            try:
                data = await self.bot.http.get_from_cdn(url)
                with open(SAVED_ATTACHMENTS_DIR / filename, 'wb') as f:
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

    async def folder_func(ctx):
        true_path = PICTURES_DIR / ctx.command.name
        file_to_send = true_path / random.choice(os.listdir(true_path))
        await ctx.channel.send(file=discord.File(file_to_send))

    def __init__(self, bot):
        self.bot = bot
        self.bot.shared['pictures_commands'] = []
        aliases = {}
        for key, val in self.bot.shared['data']['alias_pictures'].items():
            aliases[val] = aliases.get(val, []) + [key]
        for folder_name in os.listdir(PICTURES_DIR):
            self.bot.shared['pictures_commands'].append(folder_name)
            folder_command = commands.Command(ReactionImages.folder_func,
                                              name=folder_name,
                                              brief=folder_name,
                                              aliases=aliases.get(folder_name,
                                                                  []),
                                              hidden=True)
            folder_command.instance = self
            folder_command.module = self.__module__
            self.bot.add_command(folder_command)

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
