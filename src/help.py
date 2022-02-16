import logging

import discord
from discord.ext import commands
from discord_slash import cog_ext

logger = logging.getLogger()


class MyHelpCommand(commands.DefaultHelpCommand):
    async def send_bot_help(self, mapping):
        destination = self.get_destination()
        await destination.send("Sorry, mb.help (along with all prefix commands) is now deprecated. Type `/slashhelp` for more info.")


class Help(discord.ext.commands.Cog):
    def __init__(self, bot):
        self._original_help_command = bot.help_command
        bot.help_command = MyHelpCommand()
        bot.help_command.cog = self
        self.bot = bot

    @cog_ext.cog_slash(name="slashhelp", description="Learn about the new Slash Commands!")
    async def slashhelp(self, ctx):
        embed = {
            "title": "A wild Slash Commands appeared!",
            "description": "In **April 2022** Discord will be removing the ability to use bot prefixes. (Unfortunately, this was done against the wishes of most developers, including mine!)",
            "fields": [
                {
                    "name": "What does this mean?",
                    "value": "You'll no longer be able to interact with me by typing `mb.command`! Now, you'll type a `/` and be greeted with an interactive menu showing all of my commands (along with all the commands of any other migrated bot in the server). From there, you can either scroll to the command you want or keep typing until it autocompletes.",
                    "inline": False
                },
                {
                    "name": "How do I do it?",
                    "value": "By typing `/slashhelp` to run this command, you've already tried it out! Simple, right? ~~Though not as simple as consulting bot devs on their opinion about major API changes~~",
                    "inline": False
                }
            ],
            "color": 0x00e1ff,
        }
        embed = discord.Embed.from_dict(embed)
        await ctx.send(embed=embed)


def setup(bot):
    logger.info("help starting setup")
    bot.add_cog(Help(bot))
    logger.info("help ending setup")
