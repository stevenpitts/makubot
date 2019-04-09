from queue import PriorityQueue
from pathlib import Path
import discord
from discord.ext import commands
import time
import logging
import asyncio
import re
import json
from . import commandutil


SCRIPT_DIR = Path(__file__).parent
PARENT_DIR = SCRIPT_DIR.parent


class ReminderCommands(discord.ext.commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.loop.create_task(self.keep_checking_reminders())

    @commands.command()
    async def remindme(self, ctx, timelength: str, *, reminder_message: str):
        '''Reminds you of a thing!
        Usage:
          remindme [<days>d][<hours>h] [<minutes>m][<seconds>s] <reminder_message>
        Example: remindme 1d2h9s do laundry
        '''
        def get_num_seconds(timelength):
            if timelength.isnumeric():
                return int(timelength)
            timereg = re.compile(''.join([
                r'((?P<{}>\d*){})?'.format(cha, cha) for cha in 'dhms']))
            matches = re.search(timereg, timelength)
            if matches:
                days, hours, minutes, seconds = [int(val) if val else 0
                                                 for val
                                                 in matches.group(*'dhms')]
                return days*86400 + hours*3600 + minutes*60 + seconds
            return None

        total_seconds = get_num_seconds(timelength)
        if total_seconds is None:
            await ctx.send(
                "Hmm, that doesn't look valid. Ask for help if you need it!")
            return
        else:
            await ctx.send("Coolio I'll remind you in {} seconds"
                           .format(total_seconds))
            reminder_time = time.time() + total_seconds
            reminder = get_reminder(reminder_time, total_seconds,
                                    ctx.message.author.id,
                                    ctx.message.channel.id,
                                    reminder_message)
            self.bot.shared['data']['reminders'].append(reminder)

    async def keep_checking_reminders(self):
        try:
            while not self.bot.makusu:
                # Bot hasn't connected yet. Ugly but oh well.
                await asyncio.sleep(1)
            while True:
                for reminder in self.bot.shared['data']['reminders']:
                    if reminder['remind_time'] < time.time():
                        reminder_channel = self.bot.get_channel(reminder["channel_id"])
                        reminder_user = self.bot.get_user(reminder["user_id"])
                        await reminder_channel.send(
                            '{}, you have a message from {} seconds ago: {}'
                            .format(reminder_user.mention,
                                    reminder["reminder_delay"],
                                    reminder["reminder_message"]))
                        self.bot.shared['data']['reminders'].remove(reminder)
                    await asyncio.sleep(0)
                await asyncio.sleep(1)
        except concurrent.futures._base.CancelledError:
            return
        except Exception as e:
            print(commandutil.get_formatted_traceback(e))


def get_reminder(remind_time, reminder_delay, user_id, channel_id,
                 reminder_message):
    return {'remind_time': remind_time,
            'reminder_delay': reminder_delay,
            'user_id': user_id,
            'channel_id': channel_id,
            'reminder_message': reminder_message}


def setup(bot):
    logging.info('remindercommands starting setup')
    bot.add_cog(ReminderCommands(bot))
    logging.info('remindercommands ending setup')
