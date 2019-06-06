import concurrent
from pathlib import Path
import discord
from discord.ext import commands
import time
import datetime
import logging
import asyncio
import re
from . import commandutil
from dateutil.parser import parse as date_parse


SCRIPT_DIR = Path(__file__).parent
PARENT_DIR = SCRIPT_DIR.parent


def get_human_delay(seconds):
    time_strs = ("seconds", "minutes", "hours", "days", "years")
    time_mults = (60, 60, 24, 365)
    parts = [seconds]
    for time_mult in time_mults:
        quotient, parts[-1] = divmod(parts[-1], time_mult)
        parts.append(quotient)
    human_strs = (f"{part} {time_str}" for part, time_str
                  in reversed(list(zip(parts, time_strs))) if part)
    return ", ".join(human_strs)


def strip_conjunctions(words):
    conjunctions = [' ', '.', ',', ';', '-', '/', "'", 'at', 'on', 'and',
                    'to', 'that', 'of']
    while words and words[0].lower() in conjunctions:
        words = words[1:]
    while words and words[-1].lower() in conjunctions:
        words = words[:-1]
    return words


def parse_remind_me(time_and_reminder):
    words = time_and_reminder.split(" ")
    timereg_parts = [r'((?P<{}>\d*){})?'.format(cha, cha) for cha in 'ydhms']
    timereg = re.compile(r'^'+''.join(timereg_parts)+r'$')
    short_match = re.search(timereg, words[0])
    if short_match:
        years, days, hours, minutes, seconds = [int(val) if val else 0
                                                for val
                                                in short_match.group(*'ydhms')]
        total_seconds = (years*31557600 + days*86400 + hours*3600 + minutes*60
                         + seconds)
        words = strip_conjunctions(words[1:])
        if not words:
            return None, None
        reminder_message = " ".join(words)
        return total_seconds, reminder_message
    try:
        time_specified, reminder_tokens = date_parse(time_and_reminder,
                                                     fuzzy_with_tokens=True,
                                                     ignoretz=True,
                                                     dayfirst=True)
    except (ValueError, OverflowError):
        return None, None
    if not reminder_tokens:
        return None, None
    time_difference = time_specified - datetime.datetime.utcnow()
    total_seconds = time_difference.total_seconds()
    reminder_message_raw = max(reminder_tokens, key=len)
    words = strip_conjunctions(reminder_message_raw.split(" "))
    if not words:
        return None, None
    reminder_message = " ".join(words)
    return total_seconds, reminder_message


class ReminderCommands(discord.ext.commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.reminder_check_task = self.bot.loop.create_task(
            self.keep_checking_reminders())

    def cog_unload(self):
        self.reminder_check_task.cancel()

    @commands.command(aliases=["remindme"])
    async def remind_me(self, ctx, *, time_and_reminder: str):
        '''Reminds you of a thing!
        Usage:
          remindme [<years>y][<days>d][<hours>h][<minutes>m][<seconds>s]
                   <reminder>
          remindme in 1 day to <reminder>
        Many other forms are also supported, but they must use UTC and
        day-before-month format. Also they're a tad wonky.
        Example: remindme 1d2h9s do laundry
        '''
        total_seconds, reminder_message = parse_remind_me(time_and_reminder)
        total_seconds = total_seconds and int(total_seconds)
        if total_seconds is None or reminder_message is None:
            await ctx.send(
                "Hmm, that doesn't look valid. Ask for help if you need it!")
            return
        elif total_seconds < 0:
            await ctx.send("That's a time in the past :?")
            return
        await ctx.send(f"Coolio I'll remind you `{reminder_message}` in "
                       f"{get_human_delay(total_seconds)}.")
        reminder_time = int(time.time()) + total_seconds
        reminder = get_reminder(reminder_time, total_seconds,
                                ctx.message.author.id,
                                ctx.message.channel.id,
                                reminder_message)
        self.bot.shared['data']['reminders'].append(reminder)

    @commands.command(aliases=["listreminders"])
    async def list_reminders(self, ctx):
        """List all active reminders for you"""
        active_reminders = [reminder for reminder
                            in self.bot.shared['data']['reminders']
                            if reminder['user_id'] == ctx.author.id]
        if not active_reminders:
            await ctx.send("You have no active reminders.")
            return
        reminder_list_display = '\n'.join(
            [f"{reminder_num}: `{reminder['reminder_message']}`"
             for reminder_num, reminder in enumerate(active_reminders)])
        await ctx.send(reminder_list_display)

    @commands.command(aliases=["cancelreminder", "deletereminder",
                               "delete_reminder"])
    async def cancel_reminder(self, ctx):
        """Cancels a reminder. I'll ask which one you want to cancel."""
        active_reminders = [reminder for reminder
                            in self.bot.shared['data']['reminders']
                            if reminder['user_id'] == ctx.author.id]
        if not active_reminders:
            await ctx.send("You have no active reminders.")
            return
        if len(active_reminders) == 1:
            choice = active_reminders[0]
        else:
            reminder_list_display = '\n'.join(
                [f"{reminder_num}: `{reminder['reminder_message']}`"
                 for reminder_num, reminder in enumerate(active_reminders)])
            await ctx.send(f"Which reminder would you like to delete? "
                           f"Enter a number: \n{reminder_list_display}")
            message = await self.bot.wait_for('message', check=lambda message:
                                              ctx.author == message.author)
            try:
                choice = active_reminders[int(message.content)]
            except (IndexError, ValueError):
                await ctx.send("Invalid choice")
                return
        self.bot.shared['data']['reminders'].remove(choice)
        await ctx.send(f"Reminder deleted: "
                       f"`{choice['reminder_message']}`")

    async def send_reminder(self, reminder):
        reminder_channel = self.bot.get_channel(reminder["channel_id"])
        reminder_user = self.bot.get_user(reminder["user_id"])
        human_delay = get_human_delay(reminder["reminder_delay"])
        await reminder_channel.send('{}, you have a message from {} ago: {}'
                                    .format(reminder_user.mention,
                                            human_delay,
                                            reminder["reminder_message"]))

    async def keep_checking_reminders(self):
        try:
            await self.bot.wait_until_ready()
            while True:
                for reminder in self.bot.shared['data']['reminders']:
                    if reminder['remind_time'] < time.time():
                        await self.send_reminder(reminder)
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
