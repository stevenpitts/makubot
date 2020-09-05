import discord
from discord.ext import commands
import logging

logger = logging.getLogger()


SHOWOFF_COMMANDS = [
    "addimage",
    "mycommands",
    "myimagecount",
    "bigten",
    "listreactions",
    "randomimage",
    "howbig",
    "",
    "invite",
    "support",
    "",
    "evaluate",
    "bully",
    "choose",
    "emojispam",
    "fact",
    "hugme",
    "poll",
    "remindme",
    "whatis",
    "youtube"
]


def cmd_help_text(bot, cmd):
    help_brief = bot.all_commands[cmd].help.split('\n')[0]
    return f"**{cmd}**\n> {help_brief}\n"


def get_help_commands_text(bot):
    help_text = ""
    for cmd in SHOWOFF_COMMANDS:
        if cmd:
            help_text += cmd_help_text(bot, cmd)
        else:
            help_text += "\n"
    return help_text


HELP_TEXT = """
I'm Makubot! I have ***hundreds*** of community-driven image commands, \
and you can add more!
If you can think of an emotion, or a character, or a TV show, I probably have \
a command for it. Try `mb.angry`, `mb.nao`, or `mb.f`!

If I don't have that command, you can add an image to it by using \
`mb.addimage`! Then my owner will approve the image, and it'll \
get added to my collection!

I'm not just another image bot; I can process lots of image/video types, \
I'll try to show you only images relevant to you, and I'm \
super speedy! Check me out!

{help_commands_text}
"""


class MyHelpCommand(commands.DefaultHelpCommand):
    async def send_bot_help(self, mapping):
        destination = self.get_destination()
        await destination.send(
            HELP_TEXT.format(
                help_commands_text=get_help_commands_text(self.context.bot)
            )
        )


class Help(discord.ext.commands.Cog):
    def __init__(self, bot):
        self._original_help_command = bot.help_command
        bot.help_command = MyHelpCommand()
        bot.help_command.cog = self
        self.bot = bot


def setup(bot):
    logger.info("help starting setup")
    bot.add_cog(Help(bot))
    logger.info("help ending setup")
