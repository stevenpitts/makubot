import discord
from discord.ext import commands
import logging
from pathlib import Path
import os
import random

SCRIPT_DIR = Path(__file__).parent
PARENT_DIR = SCRIPT_DIR.parent
DATA_DIR = PARENT_DIR / 'data'
PICTURES_DIR = DATA_DIR / 'pictures'


class PictureAdder(discord.ext.commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def image_suggestion(self, image_dir, attachment):
        proposal = (f"Add image to {image_dir}?\n{attachment.url}"
                    if image_dir.exists() else
                    f"Add image to new dir {image_dir}?\n{attachment.url}")
        request = await self.bot.makusu.send(proposal)
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
            await attachment.save(str(image_dir / attachment.filename))
        await request.delete()

    @commands.command(aliases=["addimage"])
    async def add_image(self, ctx, type, *, image_collection: str):
        """Requests an image be added.
        mb.addimage reaction nao
        Makubot will then ask the for the image to be added.
        You must send the image as an attachment; I can't save URLs ;~;
        Then, it'll be sent to maku for approval!"""
        type = type.lower().strip()
        image_collection = image_collection.lower().strip()
        if type not in ["reaction", "association"]:
            await ctx.send("You must specify whether your image is a reaction "
                           "or an association image. Association would be an "
                           "image specific to a user, reaction would be a "
                           "generic reaction image.")
            return
        if not image_collection.isalpha():
            await ctx.send("Please only include letters.")
            return
        await ctx.send("Please send your image(s).")

        def image_message_check(message):
            return (message.channel == ctx.channel
                    and message.author == ctx.author
                    and message.attachments)
        image_message = await self.bot.wait_for('message',
                                                check=image_message_check,
                                                timeout=120)
        for attachment in image_message.attachments:
            await ctx.send("Sent to Maku for approval!")
            await self.image_suggestion(PICTURES_DIR/image_collection, attachment)


async def post_picture(channel, folder_name):
    file_to_send_name = random.choice(os.listdir(folder_name))
    file_to_send = str(folder_name / file_to_send_name)
    await channel.send(file=discord.File(file_to_send))


class ReactionImages(discord.ext.commands.Cog):

    async def folder_func(ctx):
        true_path = PICTURES_DIR / ctx.invoked_with
        await post_picture(ctx.channel, true_path)

    def __init__(self, bot):
        self.bot = bot
        self.bot.shared['pictures_commands'] = []
        for folder_name in os.listdir(PICTURES_DIR):
            self.bot.shared['pictures_commands'].append(folder_name)
            folder_command = commands.Command(ReactionImages.folder_func,
                                              name=folder_name,
                                              brief=folder_name,
                                              hidden=True)
            folder_command.instance = self
            folder_command.module = self.__module__
            self.bot.add_command(folder_command)


def setup(bot):
    logging.info('picturecommands starting setup')
    bot.add_cog(ReactionImages(bot))
    bot.add_cog(PictureAdder(bot))
    logging.info('picturecommands ending setup')
