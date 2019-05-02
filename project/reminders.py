import concurrent
from pathlib import Path
import discord
from discord.ext import commands
import time
import logging
import asyncio
import re
from . import commandutil


SCRIPT_DIR = Path(__file__).parent
PARENT_DIR = SCRIPT_DIR.parent


def get_human_delay(seconds):
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    days_str = f"{days} days" if days else ""
    hours_str = f"{hours} hours" if hours else ""
    minutes_str = f"{minutes} minutes" if minutes else ""
    seconds_str = f"{seconds} seconds" if seconds else ""
    parts = [part for part in [days_str, hours_str, minutes_str, seconds_str]
             if part]
    human_delay = ", ".join(parts)
    return f"{human_delay}."


class ReminderCommands(discord.ext.commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.reminder_check_task = self.bot.loop.create_task(
            self.keep_checking_reminders())

    def cog_unload(self):
        self.reminder_check_task.cancel()

    @commands.command(aliases=["remindme"])
    async def remind_me(self, ctx, timelength: str, *, reminder_message: str):
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
            await ctx.send("Coolio I'll remind you in {}"
                           .format(get_human_delay(total_seconds)))
            reminder_time = time.time() + total_seconds
            reminder = get_reminder(reminder_time, total_seconds,
                                    ctx.message.author.id,
                                    ctx.message.channel.id,
                                    reminder_message)
            self.bot.shared['data']['reminders'].append(reminder)

    @commands.command(aliases=["listreminders"])
    async def list_reminders(self, ctx):
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

    @commands.command(aliases=["cancelreminder"])
    async def cancel_reminder(self, ctx):
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
