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
    "poll",
    "whatis",
    "youtube",
    "imageblacklist",
]
MINOR_SHOWOFF_COMMANDS = [
    "choose",
    "emojispam",
]


def cmd_help_text(bot, cmd):
    cmd_help = bot.all_commands[cmd].help
    help_brief = cmd_help.split('\n')[0] if cmd_help is not None else "(Undefined)"
    return f"**mb.{cmd}**\n> {help_brief}\n"


def get_help_commands_text(bot):
    text = ""
    for cmd in SHOWOFF_COMMANDS:
        if cmd:
            text += cmd_help_text(bot, cmd)
        else:
            text += "\n"
    return text


def get_minor_help_commands_text():
    # This can probably be simplified
    text = ""
    for i, cmd in enumerate(MINOR_SHOWOFF_COMMANDS):
        if len(MINOR_SHOWOFF_COMMANDS) - i == 1:
            text += f"and `mb.{cmd}`!"
        else:
            text += f"`mb.{cmd}`, "
    return f"Some other commands include {text}"


HELP_TEXT = """
aaaaaaAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA please don't use this bot if you're new to it, I hate this bot
{help_commands_text}
{minor_help_commands_text} \
For detailed help on a command and how to use it, use `mb.help CommandName`!
"""


class MyHelpCommand(commands.DefaultHelpCommand):
    async def send_bot_help(self, mapping):
        destination = self.get_destination()
        await destination.send(
            HELP_TEXT.format(
                help_commands_text=get_help_commands_text(self.context.bot),
                minor_help_commands_text=get_minor_help_commands_text()
            )
        )

    async def send_command_help(self, command):
        if command.callback.__name__ == "send_image_func":
            await self.get_destination().send(
                "Use this command to send an image from an image directory!")
        else:
            await super().send_command_help(command)


class Help(discord.ext.commands.Cog):
    def __init__(self, bot):
        self._original_help_command = bot.help_command
        bot.help_command = MyHelpCommand()
        bot.help_command.cog = self
        self.bot = bot

    @commands.command()
    async def superhelp(self, ctx):
        all_non_image_commands = [
            cmd for cmd, command in self.bot.all_commands.items()
            if command != self.bot.all_commands["send_image_func"]
        ]
        await ctx.send(", ".join(all_non_image_commands))


async def setup(bot):
    logger.info("help starting setup")
    await bot.add_cog(Help(bot))
    logger.info("help ending setup")
