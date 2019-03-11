from queue import PriorityQueue
from pathlib import Path
import discord
from discord.ext import commands
import time
import logging
import asyncio
import re
import json


SCRIPT_DIR = Path(__file__).parent
PARENT_DIR = SCRIPT_DIR.parent
DATA_DIR = PARENT_DIR / 'data'
REMINDERS_PATH = DATA_DIR / 'reminders.txt'


class ReminderCommands(discord.ext.commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.reminders = None

    @commands.Cog.listener()
    async def on_ready(self):
        await self.load_reminders()
        await self.keep_checking_reminders()

    @commands.command()
    async def remindme(self, ctx, timelength: str, *, reminder: str):
        '''Reminds you of a thing!
        Usage:
          remindme [<days>d][<hours>h] [<minutes>m][<seconds>s] <reminder>
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
            await ctx.send(
                "Coolio I'll remind you in {} seconds".format(total_seconds))
            reminder_time = time.time() + total_seconds
            await self.add_reminder(reminder_time, total_seconds,
                                    ctx.message.author, ctx.channel,
                                    reminder)

    def save_reminders(self):
        serializable_reminders = [reminder.as_serializable()
                                  for reminder in self.reminders.queue]
        with open(REMINDERS_PATH, 'w') as open_file:
            json.dump(serializable_reminders, open_file)

    async def keep_checking_reminders(self):
        while True:
            if not self.reminders.empty():
                if self.reminders.queue[0].ready_to_send():
                    next_reminder = self.reminders.get()
                    self.save_reminders()
                    await next_reminder.channel.send(
                        '{}, you have a message from {} seconds ago: {}'
                        .format(next_reminder.user.mention,
                                next_reminder.reminder_delay,
                                next_reminder.reminder_message))
            await asyncio.sleep(1)

    async def load_reminders(self):
        with open(REMINDERS_PATH, 'r') as open_file:
            self.reminders = PriorityQueue()
            for data in json.load(open_file):
                self.reminders.put(
                    await Reminder.from_bot_and_serializable(self.bot, data))

    async def add_reminder(self, remind_time, reminder_delay,
                           user, channel, reminder_message):
        self.reminders.put(Reminder(self.bot, remind_time, reminder_delay,
                                    user, channel, reminder_message))
        self.save_reminders()


class Reminder:
    def __init__(self, bot, remind_time, reminder_delay, user: discord.User,
                 channel: discord.TextChannel, reminder_message):
        self.remind_time = remind_time
        self.reminder_delay = reminder_delay
        self.user = user
        self.channel = channel
        self.reminder_message = reminder_message

    @classmethod
    async def from_bot_and_serializable(cls, bot, data):
        return cls(bot, data['remind_time'], data['reminder_delay'],
                   await bot.get_user_info(data['user_id']),
                   bot.get_channel(data['channel_id']),
                   data['reminder_message'])

    def as_serializable(self):
        return {'remind_time': self.remind_time,
                'reminder_delay': self.reminder_delay,
                'user_id': self.user.id,
                'channel_id': self.channel.id,
                'reminder_message': self.reminder_message}

    def ready_to_send(self):
        return self.remind_time < time.time()

    def __eq__(self, other):
        return self.remind_time == other.remind_time

    def __lt__(self, other):
        return self.remind_time < other.remind_time


def setup(bot):
    logging.info('remindercommands starting setup')
    bot.add_cog(ReminderCommands(bot))
    logging.info('remindercommands ending setup')
