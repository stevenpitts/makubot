import discord
from discord.ext import commands
import logging
from pathlib import Path
import os
import random
import aiohttp
import shutil
import re

SCRIPT_DIR = Path(__file__).parent
PARENT_DIR = SCRIPT_DIR.parent
DATA_DIR = PARENT_DIR / 'data'
PICTURES_DIR = DATA_DIR / 'pictures'
SAVED_ATTACHMENTS_DIR = DATA_DIR / 'saved_attachments'


class PictureAdder(discord.ext.commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def image_suggestion(self, image_dir, filename, requestor):
        proposal = (f"Add image {filename} to {image_dir}?"
                    if image_dir.exists() else
                    f"Add image to ***NEW*** dir {image_dir}?")
        request = await self.bot.makusu.send(
            proposal, file=discord.File(SAVED_ATTACHMENTS_DIR / filename))
        no_emoji, yes_emoji = "❌", "✅"
        await request.add_reaction(no_emoji)
        await request.add_reaction(yes_emoji)

        def reaction_check(reaction, user):
            return (user == self.bot.makusu
                    and reaction.message.id == request.id
                    and reaction.emoji in [no_emoji, yes_emoji])
        res = await self.bot.wait_for("reaction_add", check=reaction_check)
        if res[0].emoji == yes_emoji:
            if not image_dir.exists():
                os.makedirs(image_dir)
            shutil.move(SAVED_ATTACHMENTS_DIR / filename,
                        image_dir / filename)
            self.bot.reload_extension("project.picturecommands")
            await requestor.send(f"Your image {filename.split('.')[0]} "
                                 "was approved!")
        else:
            await requestor.send(f"Your image {filename.split('.')[0]} "
                                 "was not approved. "
                                 "Feel free to ask Maku why ^_^")
        await request.delete()

    @commands.command(aliases=["aliasimage", "aliaspicture"])
    @commands.is_owner()
    async def add_picture_alias(self, ctx, ref_invocation, true_invocation):
        if not ref_invocation.isalpha() or not true_invocation.isalpha():
            await ctx.send("Please only include letters.")
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
            else:
                await ctx.send(f"{true_invocation} is not an image command :?")

    @commands.command(aliases=["addimage"])
    async def add_image(self, ctx, image_collection: str, *, urls: str = ""):
        """Requests an image be added.
        mb.addimage reaction nao
        Makubot will then ask the for the image to be added.
        You must send the image as an attachment; I can't save URLs ;~;
        Then, it'll be sent to maku for approval!"""
        if not image_collection.isalpha():
            await ctx.send("Please only include letters.")
            return
        existing_command = self.bot.get_command(image_collection)
        command_taken = (existing_command is not None
                         and (not hasattr(existing_command, "instance")
                              or not isinstance(existing_command.instance,
                                                ReactionImages)))
        if command_taken:
            await ctx.send("That is already a command name.")
            return
        request_tasks = []
        if not urls and not ctx.message.attachments:
            await ctx.send("You must include a URL at the end of your "
                           "message or attach image(s).")
            return
        for attachment in ctx.message.attachments:
            await attachment.save(SAVED_ATTACHMENTS_DIR
                                  / attachment.filename)
            request_tasks.append(self.image_suggestion(
                PICTURES_DIR / image_collection,
                attachment.filename, ctx.author))
            await ctx.send("Sent to Maku for approval!")
        for url in urls.split():
            filename = re.sub(r"\W+", "", url.split(r"/")[-1])
            if "." not in filename:
                filename += ".notactuallypng.png"
            while os.path.exists(PICTURES_DIR
                                 / image_collection
                                 / filename):
                filename = f"{str(random.randint(1, 1000))}{filename}"
            try:
                data = await self.bot.http.get_from_cdn(url)
                with open(SAVED_ATTACHMENTS_DIR / filename, 'wb') as f:
                    f.write(data)
            except aiohttp.client_exceptions.ClientConnectorError:
                await ctx.send("I can't download that image, sorry!")
            else:
                await ctx.send("Sent to Maku for approval!")
                request_tasks.append(self.image_suggestion(
                    PICTURES_DIR / image_collection, filename, ctx.author))
        for request_task in request_tasks:
            await request_task


# async def post_picture(channel, folder_name):
#     file_to_send_name = random.choice(os.listdir(folder_name))
#     file_to_send = str(folder_name / file_to_send_name)
#     await channel.send(file=discord.File(file_to_send))


class ReactionImages(discord.ext.commands.Cog):

    async def folder_func(ctx):
        true_path = PICTURES_DIR / ctx.command.name
        file_to_send_name = random.choice(os.listdir(true_path))
        file_to_send = true_path / file_to_send_name
        await ctx.channel.send(file=discord.File(file_to_send))
        #await post_picture(ctx.channel, true_path)

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


def setup(bot):
    logging.info('picturecommands starting setup')
    bot.add_cog(ReactionImages(bot))
    bot.add_cog(PictureAdder(bot))
    logging.info('picturecommands ending setup')
