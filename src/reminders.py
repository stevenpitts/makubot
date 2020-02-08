import concurrent
from pathlib import Path
import discord
from discord.ext import commands, tasks
import time
import datetime
import logging
import sqlite3
import asyncio
import re
from . import commandutil
from dateutil.parser import parse as date_parse


SCRIPT_DIR = Path(__file__).parent
PARENT_DIR = SCRIPT_DIR.parent

logger = logging.getLogger()


class RemindersDB:
    def __init__(self, db=PARENT_DIR / 'data' / 'reminders.db'):
        self.conn = sqlite3.connect(db)
        self.conn.row_factory = sqlite3.Row
        self.c = self.conn.cursor()
        self.c.execute('''CREATE TABLE IF NOT EXISTS reminders
                           (id INTEGER PRIMARY KEY AUTOINCREMENT,
                           remind_set_time DATE,
                           remind_time DATE NOT NULL,
                           user_id CHARACTER(18),
                           channel_id CHARACTER(18),
                           reminder_message TEXT);''')
        self.c.execute('''CREATE INDEX IF NOT EXISTS date_index
                           ON reminders (remind_time);''')
        self.conn.commit()

    def add_reminder(self, remind_set_time, remind_time, user_id, channel_id,
                     reminder_message):
        self.c.execute('''INSERT INTO reminders
                       (remind_set_time,
                       remind_time,
                       user_id,
                       channel_id,
                       reminder_message)
                       VALUES (?, ?, ?, ?, ?)''',
                       (remind_set_time, remind_time, user_id, channel_id,
                        reminder_message))
        self.conn.commit()

    def drop_reminder(self, reminder_id):
        self.c.execute('''DELETE FROM reminders WHERE id = ?''',
                       (reminder_id,))
        self.conn.commit()

    def ready_reminders(self, current_time):
        self.c.execute('''SELECT * FROM reminders
                           WHERE remind_time <= ?''', (current_time, ))
        return self.c.fetchall()

    def reminders_from_user(self, user_id):
        user_id = str(user_id)
        self.c.execute('''SELECT * FROM reminders WHERE user_id = ?''',
                       (user_id, ))
        return self.c.fetchall()

    def from_id(self, id):
        self.c.execute('''SELECT * FROM reminders WHERE id = ?''', (id,))
        return self.c.fetchone()


def rows_as_str(rows):
    return '\n'.join([str(dict(row)) for row in rows])


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
        self.reminders_db = RemindersDB()
        self.cycle_reminders.start()

    def cog_unload(self):
        self.cycle_reminders.stop()
        self.reminders_db.conn.close()

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
        total_seconds, reminder_message = parse_remind_me(
            time_and_reminder)
        reminder_message = await commandutil.clean(ctx, reminder_message)
        total_seconds = total_seconds and int(total_seconds)
        if total_seconds is None or reminder_message is None:
            await ctx.send(
                "Hmm, that doesn't look valid. Ask Maku for help!")
            return
        elif total_seconds < 0:
            await ctx.send("That's a time in the past :?")
            return
        reminder_cleaned = await commandutil.clean(ctx, reminder_message)
        remind_set_time = int(time.time())
        remind_time = remind_set_time + total_seconds
        user_id = str(ctx.message.author.id)
        channel_id = str(ctx.message.channel.id)
        try:
            self.reminders_db.add_reminder(
                remind_set_time, remind_time, user_id, channel_id,
                reminder_cleaned)
        except OverflowError:
            await ctx.send("I can't handle a number that big, sorry!")
        else:
            await ctx.send(f"Coolio I'll remind you '{reminder_cleaned}' "
                           f"in {get_human_delay(total_seconds)}.")

    @commands.command(aliases=["listreminders"])
    async def list_reminders(self, ctx):
        """List all active reminders for you"""
        active_reminders = self.reminders_db.reminders_from_user(ctx.author.id)
        await ctx.send(rows_as_str(active_reminders) if active_reminders
                       else "You have no active reminders")

    @commands.command(aliases=["cancelreminder", "deletereminder",
                               "delete_reminder"])
    async def cancel_reminder(self, ctx):
        """Cancels a reminder. I'll ask which one you want to cancel."""
        active_reminders = self.reminders_db.reminders_from_user(ctx.author.id)
        if not active_reminders:
            await ctx.send("You have no active reminders.")
            return
        else:
            reminder_list_display = rows_as_str(active_reminders)
            await ctx.send(f"Which reminder would you like to delete? "
                           f"Enter the ID: \n{reminder_list_display}")
            message = await self.bot.wait_for('message', check=lambda message:
                                              ctx.author == message.author)
            try:
                choice = int(message.content)
                chosen_reminder = self.reminders_db.from_id(choice)
                if chosen_reminder is None:
                    raise ValueError("chosen_reminder wasn't valid")
            except (IndexError, ValueError):
                await ctx.send("Invalid choice")
                return
        if chosen_reminder['user_id'] != str(ctx.author.id):
            await ctx.send("It looks like that isn't your reminder!")
            return
        self.reminders_db.drop_reminder(choice)
        await ctx.send(f"Reminder deleted: "
                       f"'{chosen_reminder['reminder_message']}'")

    async def send_reminder(self, reminder):
        reminder_channel = self.bot.get_channel(int(reminder["channel_id"]))
        reminder_user = self.bot.get_user(int(reminder["user_id"]))
        time_delta = int(time.time()) - reminder["remind_set_time"]
        human_delay = get_human_delay(time_delta)
        if reminder_user and not reminder_channel:
            await reminder_user.send(
                "Hey, you had a reminder set but I couldn't find the channel "
                "you'd set it in. Your reminder was: "
                f"{reminder['reminder_message']}")
        elif reminder_channel and not reminder_user:
            await reminder_channel.send(
                "Uhh there was a person but they're gone now but the reminder "
                f"was {reminder['reminder_message']}")
        elif not reminder_channel and not reminder_user:
            await self.bot.makusu.send(f"Couldn't find stuff for {reminder}")
        else:
            await reminder_channel.send(
                f"{reminder_user.mention}, you have a message from "
                f"{human_delay} ago: {reminder['reminder_message']}")

    @tasks.loop(seconds=1)
    async def cycle_reminders(self):
        try:
            ready_reminders = self.reminders_db.ready_reminders(
                current_time=int(time.time()))
            reminder_coros = [self.send_reminder(reminder)
                              for reminder in ready_reminders]
            await asyncio.gather(*reminder_coros, return_exceptions=True)
            for reminder in ready_reminders:
                self.reminders_db.drop_reminder(reminder['id'])
        except (concurrent.futures._base.CancelledError,
                sqlite3.ProgrammingError):
            return
        except Exception as e:
            print(commandutil.get_formatted_traceback(e))

    @cycle_reminders.before_loop
    async def before_cycling(self):
        await self.bot.wait_until_ready()


def setup(bot):
    logger.info('remindercommands starting setup')
    bot.add_cog(ReminderCommands(bot))
    logger.info('remindercommands ending setup')
