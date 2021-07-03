import concurrent
import discord
from discord.ext import commands, tasks
from datetime import datetime, timedelta
import logging
import asyncio
import re
from psycopg2.extras import RealDictCursor
from . import util
from dateutil.parser import parse as date_parse
from dateutil.relativedelta import relativedelta

logger = logging.getLogger()

DATABASE_CONNECT_MAX_RETRIES = 10


class RemindersDB:
    def __init__(self, bot):
        self.bot = bot
        cursor = self.bot.db_connection.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
            id SERIAL PRIMARY KEY,
            remind_set_time TIMESTAMP,
            remind_time TIMESTAMP NOT NULL,
            user_id CHARACTER(18),
            channel_id CHARACTER(18),
            reminder_message TEXT
            );
            """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS date_index
            ON reminders (remind_time);
            """)
        self.bot.db_connection.commit()

    def add_reminder(self, remind_set_time, remind_time, user_id, channel_id,
                     reminder_message):
        cursor = self.bot.db_connection.cursor()
        query = """
            INSERT INTO reminders (
            remind_set_time,
            remind_time,
            user_id,
            channel_id,
            reminder_message)
            VALUES (%s, %s, %s, %s, %s)
            """
        cursor.execute(
            query,
            (remind_set_time,
             remind_time,
             user_id,
             channel_id,
             reminder_message)
        )
        self.bot.db_connection.commit()

    def drop_reminder(self, reminder_id):
        cursor = self.bot.db_connection.cursor()
        cursor.execute(
            """
            DELETE FROM reminders WHERE id = %s
            """,
            (reminder_id,)
        )
        self.bot.db_connection.commit()

    def ready_reminders(self):
        cursor = self.bot.db_connection.cursor(cursor_factory=RealDictCursor)
        current_time = datetime.utcnow()
        cursor.execute("""SELECT * FROM reminders
                           WHERE remind_time <= %s""", (current_time, ))
        return cursor.fetchall()

    def reminders_from_user(self, user_id):
        cursor = self.bot.db_connection.cursor(cursor_factory=RealDictCursor)
        user_id = str(user_id)
        cursor.execute(
            """
            SELECT * FROM reminders WHERE user_id = %s
            """,
            (user_id, ))
        return cursor.fetchall()

    def reminder_from_id(self, id):
        cursor = self.bot.db_connection.cursor(cursor_factory=RealDictCursor)
        cursor.execute(
            """
            SELECT * FROM reminders WHERE id = %s
            """,
            (id,))
        return cursor.fetchone()


def rows_as_str(rows):
    return "\n".join([str(dict(row)) for row in rows])


def get_human_delay(seconds, ignore_partial_seconds=True):
    if isinstance(seconds, timedelta):
        seconds = seconds.total_seconds()
    if ignore_partial_seconds:
        seconds = int(seconds)
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
    conjunctions = [" ", ".", ",", ";", "-", "/", "\"", "at", "on", "and",
                    "to", "that", "of"]
    while words and words[0].lower() in conjunctions:
        words = words[1:]
    while words and words[-1].lower() in conjunctions:
        words = words[:-1]
    return words


def parse_remind_me(time_and_reminder):
    words = time_and_reminder.split(" ")
    timereg_parts = [r"((?P<{}>\d*){})?".format(cha, cha) for cha in "yMdhms"]
    timereg = re.compile(r"^"+"".join(timereg_parts)+r"$")
    short_match = re.search(timereg, words[0])
    if short_match:
        years, months, days, hours, minutes, seconds = [int(val) if val else 0
                                                for val
                                                in short_match.group(*"yMdhms")]
        relative_delta = relativedelta(years=years,months=months,days=days,
                                hours=hours,minutes=minutes,seconds=seconds)
        utcnow = datetime.utcnow()
        total_seconds = (utcnow + relative_delta - utcnow).total_seconds()
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
    reminder_message_raw = max(reminder_tokens, key=len)
    words = strip_conjunctions(reminder_message_raw.split(" "))
    if not words:
        return None, None
    reminder_message = " ".join(words)
    return total_seconds, reminder_message


class ReminderCommands(discord.ext.commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.reminders_db = RemindersDB(self.bot)
        self.cycle_reminders.start()

    def cog_unload(self):
        self.cycle_reminders.stop()

    @commands.command(aliases=["remindme"])
    async def remind_me(self, ctx, *, time_and_reminder: str):
        """Reminds you of a thing!
        Usage:
          remindme [<years>y][<months>M][<days>d][<hours>h][<minutes>m][<seconds>s]
                   <reminder>
          remindme in 1 day to <reminder>
        Many other forms are also supported, but they must use UTC and
        day-before-month format. Also they're a tad wonky.
        Example: remindme 1d2h9s do laundry
        """
        total_seconds, reminder_message = parse_remind_me(
            time_and_reminder)
        reminder_message = (
            await util.clean(ctx, reminder_message) if reminder_message else ""
        )
        total_seconds = total_seconds and int(total_seconds)
        if total_seconds is None or reminder_message is None:
            await ctx.send(
                "Hmm, that doesn't look valid. Ask Maku for help!")
            return
        elif total_seconds < 0:
            await ctx.send("That's a time in the past :?")
            return
        reminder_cleaned = await util.clean(ctx, reminder_message)
        remind_set_time = datetime.utcnow()
        remind_time = remind_set_time + timedelta(seconds=total_seconds)
        user_id = str(ctx.message.author.id)
        channel_id = str(ctx.message.channel.id)
        try:
            self.reminders_db.add_reminder(
                remind_set_time,
                remind_time,
                user_id,
                channel_id,
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
            message = await self.bot.wait_for("message", check=lambda message:
                                              ctx.author == message.author)
            try:
                choice = int(message.content)
                chosen_reminder = self.reminders_db.reminder_from_id(choice)
                if chosen_reminder is None:
                    raise ValueError("chosen_reminder wasn't valid")
            except (IndexError, ValueError):
                await ctx.send("Invalid choice")
                return
        if chosen_reminder["user_id"] != str(ctx.author.id):
            await ctx.send("It looks like that isn't your reminder!")
            return
        self.reminders_db.drop_reminder(choice)
        await ctx.send(f"Reminder deleted: "
                       f"'{chosen_reminder['reminder_message']}'")

    async def send_reminder(self, reminder):
        reminder_channel = self.bot.get_channel(int(reminder["channel_id"]))
        reminder_user = self.bot.get_user(int(reminder["user_id"]))
        time_delta = datetime.utcnow() - reminder["remind_set_time"]
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
            ready_reminders = self.reminders_db.ready_reminders()
            reminder_coros = [self.send_reminder(reminder)
                              for reminder in ready_reminders]
            await asyncio.gather(*reminder_coros)
            for reminder in ready_reminders:
                self.reminders_db.drop_reminder(reminder["id"])
        except concurrent.futures._base.CancelledError:
            return
        except Exception:
            logger.error("", exc_info=True)

    @cycle_reminders.before_loop
    async def before_cycling(self):
        await self.bot.wait_until_ready()


def setup(bot):
    logger.info("remindercommands starting setup")
    bot.add_cog(ReminderCommands(bot))
    logger.info("remindercommands ending setup")
