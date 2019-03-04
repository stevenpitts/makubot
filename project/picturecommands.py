import discord
from discord.ext import commands
import logging
from pathlib import Path
import os
import random

SCRIPT_DIR = Path(__file__).parent
PARENT_DIR = SCRIPT_DIR.parent
DATA_DIR = PARENT_DIR / 'data'
PICTURE_ASSOCIATIONS_DIR = DATA_DIR / 'picture_associations'
PICTURE_REACTIONS_DIR = DATA_DIR / 'picture_reactions'


async def post_picture(channel, folder_name):
    file_to_send_name = random.choice(os.listdir(folder_name))
    file_to_send = str(folder_name / file_to_send_name)
    await channel.send(file=discord.File(file_to_send))


class FavePictures(discord.ext.commands.Cog):

    async def folder_func(ctx):
        true_path = PICTURE_ASSOCIATIONS_DIR / ctx.invoked_with
        await post_picture(ctx.channel, true_path)

    def __init__(self, bot):
        self.bot = bot
        self.bot.shared['fave_pictures_commands'] = []
        for folder_name in os.listdir(PICTURE_ASSOCIATIONS_DIR):
            self.bot.shared['fave_pictures_commands'].append(folder_name)
            folder_brief = f"Post one of {folder_name}'s favorite pictures~"
            folder_command = commands.Command(FavePictures.folder_func,
                                              brief=folder_brief,
                                              name=folder_name,
                                              hidden=True)
            folder_command.instance = self
            folder_command.module = self.__module__
            self.bot.add_command(folder_command)


class ReactionImages(discord.ext.commands.Cog):

    async def folder_func(ctx):
        true_path = PICTURE_REACTIONS_DIR / ctx.invoked_with
        await post_picture(ctx.channel, true_path)

    def __init__(self, bot):
        self.bot = bot
        self.bot.shared['reaction_images_commands'] = []
        for folder_name in os.listdir(PICTURE_REACTIONS_DIR):
            self.bot.shared['reaction_images_commands'].append(folder_name)
            folder_command = commands.Command(ReactionImages.folder_func,
                                              name=folder_name,
                                              brief=folder_name,
                                              hidden=True)
            folder_command.instance = self
            folder_command.module = self.__module__
            self.bot.add_command(folder_command)


def setup(bot):
    logging.info('picturecommands starting setup')
    bot.add_cog(FavePictures(bot))
    bot.add_cog(ReactionImages(bot))
    logging.info('picturecommands ending setup')
