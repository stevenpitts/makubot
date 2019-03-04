'''
Module containing the majority of the basic commands makubot can execute.
Also used to reload criticalcommands.
'''
import random
import sys
from pathlib import Path
import asyncio
import re
from io import StringIO
import datetime
import json
import logging
import codecs
from googleapiclient.discovery import build
import asteval
import discord
from discord.ext import commands
from discord.ext.commands.errors import (CommandError, CommandNotFound,
                                         CommandOnCooldown, NotOwner,
                                         MissingPermissions,
                                         BotMissingPermissions,
                                         BadUnionArgument)
import wikipedia
from . import tokens
from . import commandutil


SCRIPT_DIR = Path(__file__).parent
PARENT_DIR = SCRIPT_DIR.parent
DATA_DIR = PARENT_DIR / 'data'
SAVED_ATTACHMENTS_DIR = DATA_DIR / 'saved_attachments'
WORKING_DIR = DATA_DIR / 'working_directory'
DELETION_LOG_PATH = DATA_DIR / 'deletion_log.txt'
FREE_REIGN_PATH = DATA_DIR / 'free_reign.txt'


FACTS = '''Geese are NEAT
How can mirrors be real if our eyes aren't real
I'm the captain now
Maku is awesome
Maku
Super electromagnetic shrapnel cannon FIRE!
Ideas are bulletproof
What do we say to Death? Not today.
Nao Tomori is best person
Please do not use any ligma-related software in parallel with Makubot
Wear polyester when doing laptop repairs
Fighting's good when it's not a magic orb that can throw you against the wall
Don't f*** with Frug's shovel
If I don't come back within five minutes assume I died
You you eat sleep eat sleep whoa why can't I see anything
Expiration dates are just suggestions
Cake am lie
Oh dang is that a gun -Uncle Ben
With great power comes great responsibility -Uncle Ben'''.split('\n')


YOUTUBE_SEARCH = None if tokens.googleAPI is None else build(
    'youtube', 'v3', developerKey=tokens.googleAPI).search()


def aeval(to_evaluate, return_error=True) -> str:
    temp_string_io = StringIO()
    aeval_interpreter = asteval.Interpreter(writer=temp_string_io,
                                            err_writer=temp_string_io)
    result = aeval_interpreter(to_evaluate)
    if not result:
        if return_error:
            result = 'No result found.'
        else:
            return None
    temp_str_val = temp_string_io.getvalue()
    output_str = '```{}\n```'.format(temp_str_val) if temp_str_val else ''
    return f'{output_str}```Result: {result}```'


MOVE_EMOTE = '\U0001f232'


class MakuCommands(discord.ext.commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.description = '''
Hey there! I'm Makubot!
I'm a dumb bot made by a person who codes stuff.
I'm currently running Python {}.
Also you can just ask Makusu2#2222 cuz they love making new friends <333
        '''.format('.'.join(map(str, sys.version_info[:3])))
        self.free_guilds = set()
        prefixes = [m+b+punc+maybespace for m in 'mM' for b in 'bB'
                    for punc in '.!' for maybespace in [' ', '']]
        self.bot.command_prefix = commands.when_mentioned_or(*prefixes)
        self.last_deleted_message = {}
        '''Maps channel ID to last deleted message content, \
        along with a header of who send it.'''

    @commands.Cog.listener()
    async def on_ready(self):
        self.load_free_reign_guilds()

    @commands.command(hidden=True, aliases=['status'])
    @commands.is_owner()
    async def getstatus(self, ctx):
        current_servers_string = 'Current servers: {}'.format(
            {guild.name: guild.id for guild in self.bot.guilds})
        await commandutil.send_formatted_message(
            self.bot.makusu, current_servers_string)

    @commands.command()
    @commands.cooldown(1, 1, type=commands.BucketType.user)
    async def ping(self, ctx):
        '''
        Pong was the first commercially successful video game,
        which helped to establish the video game industry along with
        the first home console, the Magnavox Odyssey. Soon after its
        release, several companies began producing games that copied
        its gameplay, and eventually released new types of games.
        As a result, Atari encouraged its staff to produce more
        innovative games. The company released several sequels
        which built upon the original's gameplay by adding new features.
        During the 1975 Christmas season, Atari released a home version of
        Pong exclusively through Sears retail stores. It also was a
        commercial success and led to numerous copies.
        The game has been remade on numerous home and portable platforms
        following its release. Pong is part of the permanent collection
        of the Smithsonian Institution in Washington, D.C.
        due to its cultural impact.
        '''
        time_passed = (datetime.datetime.utcnow()-ctx.message.created_at)
        ms_passed = time_passed.microseconds/1000
        await ctx.send(
            'pong! It took me {} milliseconds to get the ping.'
            .format(ms_passed))

    @commands.command(aliases=['are you free',
                               'areyoufree?',
                               'are you free?'])
    @commands.guild_only()
    async def areyoufree(self, ctx):
        '''If I have free reign I'll tell you'''
        is_free = ctx.guild.id in self.free_guilds
        await ctx.send('Yes, I am free.' if is_free
                       else 'This is not a free reign guild.')

    @commands.command(aliases=['emoji spam'])
    @commands.bot_has_permissions(add_reactions=True)
    async def emojispam(self, ctx):
        '''Prepare to be spammed by the greatest emojis you've ever seen'''
        emojis_random_order = iter(sorted(
            self.bot.emojis, key=lambda *args: random.random()))
        for emoji_to_add in emojis_random_order:
            try:
                await ctx.message.add_reaction(emoji_to_add)
            except discord.errors.Forbidden:
                return

    @commands.command()
    @commands.is_owner()
    async def perish(self, ctx):
        '''Murders me :( '''
        await self.bot.close()

    @commands.command()
    @commands.bot_has_permissions(manage_messages=True)
    async def move(self, ctx, msg_id, channel_to_move_to: discord.TextChannel):
        '''
        move <message_id> <channel_mention>: move a message.
        Message is moved from the current channel to the channel specified.
        You can also add the reaction \U0001f232 to automate this process.
        '''
        try:
            message_to_move = await ctx.message.channel.get_message(msg_id)
        except discord.errors.HTTPException:
            await ctx.message.channel.send(
                "That, uh, doesn't look like a valid message ID. Try again.")
        else:
            await self.move_message_attempt(message_to_move,
                                            channel_to_move_to,
                                            ctx.message.author)

    @commands.command(aliases=['is gay'])
    async def isgay(self, ctx):
        '''Tells me I'm gay (CAUTION: May mirror the attack at the sender)'''
        await ctx.send('No u')

    @commands.command()
    async def bully(self, ctx):
        '''Bullies me :('''
        if ctx.guild and ctx.guild.get_member(self.bot.makusu.id) is not None:
            await ctx.send("{} HELP I'M BEING BULLIED ;a;"
                           .format(self.bot.makusu.mention))
        else:
            await ctx.send('M-makusu? W-where are you? Help!!!!')

    @commands.command(aliases=['hug me'])
    async def hugme(self, ctx):
        '''Hugs you <3'''
        await ctx.send(r'*Hugs you* {}'.format(ctx.message.author.mention))

    @commands.command(aliases=['go wild'])
    @commands.is_owner()
    @commands.guild_only()
    async def gowild(self, ctx):
        '''
        Add the current guild as a gowild guild; I do a bit more on these.
        Only Maku can add guilds though :(
        '''
        if ctx.message.guild:
            await self.add_free_reign_guild(ctx.message.guild.id)
            await ctx.send('Ayaya~')

    @commands.command(aliases=['yt'])
    async def youtube(self, ctx, *, search_term: str):
        '''Post a YouTube video based on a search phrase!'''
        if YOUTUBE_SEARCH is None:
            await ctx.send('Sorry, I\'m missing the google API key!')
            return
        search_response = YOUTUBE_SEARCH.list(q=search_term,
                                              part='id',
                                              maxResults=10).execute()
        search_results = (search_result['id']['videoId']
                          for search_result in search_response.get('items', [])
                          if search_result['id']['kind'] == 'youtube#video')
        search_result = next(search_results, None)
        await ctx.send(
            r'https://www.youtube.com/watch?v={}'
            .format(search_result) if search_result
            else "Sowwy, I can't find it :(")

    @commands.command()
    async def eval(self, ctx, *, to_eval: str):
        r'''Evals a statement. Feel free to inject malicious code \o/
        Example:
            @makubot eval 3+3
            >>>6
            @makubot eval self.__import__(
                'EZ_sql_inject_api').destroy_maku_computer_operating_system()
            >>>ERROR ERROR MAJOR ERROR SELF DESTRUCT SEQUENCE INITIALIZE
        '''
        try:
            await ctx.send(aeval(to_eval))
        except AttributeError:
            logging.error(f"Couldn't get a match on {ctx.message.content}.")

    @commands.command(aliases=['what was that',
                               'whatwasthat?',
                               'what was that?'])
    async def whatwasthat(self, ctx):
        '''Tells you what that fleeting message was'''
        try:
            await ctx.send(self.last_deleted_message.pop(ctx.channel.id))
        except KeyError:
            await ctx.send("I can't find anything, sorry :(")

    @commands.command()
    async def fact(self, ctx):
        '''Sends a fun fact!'''
        await ctx.send(random.choice(FACTS))

    @commands.command(hidden=True, aliases=['deletehist'])
    @commands.is_owner()
    async def removehist(self, ctx, num_to_delete: int):
        '''Removes a specified number of previous messages by me'''
        bot_history = (message async for message in ctx.channel.history()
                       if message.author == self.bot.user)
        to_delete = []
        for _ in range(num_to_delete):
            try:
                to_delete.append(await bot_history.__anext__())
            except StopAsyncIteration:
                break
        await ctx.channel.delete_messages(to_delete)

    @commands.command()
    @commands.bot_has_permissions(manage_messages=True)
    async def opentxt(self, ctx):
        '''Opens the most recent file for reading!!!'''
        async def displaytxt(extracted_text: str):
            text_block_size = 500
            button_emojis = left_arrow, right_arrow, stop_emote = '👈👉❌'
            text_blocks = [
                r'```{}```'.format(extracted_text[i:i+text_block_size])
                for i in range(0, len(extracted_text), text_block_size)]
            current_index = 0
            block_message = await ctx.send(text_blocks[current_index])

            def check(reaction, user):
                return (user != self.bot.user
                        and reaction.emoji in button_emojis
                        and reaction.message.id == block_message.id)

            while True:
                await block_message.edit(content=text_blocks[current_index])
                for emoji_to_add in button_emojis:
                    await block_message.add_reaction(emoji_to_add)
                res = await self.bot.wait_for('reaction_add', check=check)
                emoji_result = res[0].emoji
                await block_message.remove_reaction(emoji_result, res[1])
                if emoji_result == left_arrow:
                    current_index -= 1
                elif emoji_result == right_arrow:
                    current_index += 1
                else:
                    await block_message.clear_reactions()
                    await block_message.edit(content=r'```File closed.```')
                    break
        try:
            previous_messages = ((message async for message
                                  in ctx.channel.history()
                                  if message.attachments))
            message_with_file = await previous_messages.__anext__()
            attachment = message_with_file.attachments[0]
            await attachment.save(str(WORKING_DIR
                                      / attachment.filename))
            filename_path = WORKING_DIR / attachment.filename
            with open(filename_path, 'r') as read_file:
                extracted_text = '\n'.join(read_file.readlines())
            extracted_text = extracted_text.replace("```", "'''")
        except UnicodeDecodeError:
            await ctx.send(
                "It looks like you're trying to get me to read ```{}```\
                , but that doesn't seem to be a text file, sorry!! :<"
                .format(attachment.filename))
        except StopAsyncIteration:
            await ctx.send("Ah, I couldn't find any text file, sorry!")
        else:
            asyncio.get_event_loop().create_task(displaytxt(extracted_text))
        finally:
            # Remove if you feel like it, or do whatever idc
            pass

    @commands.command()
    async def sayhitolily(self, ctx):
        '''Says hi to Lilybot~'''
        lily_in_guild = ctx.guild and any(
            ctx.guild.get_member(id) is not None
            for id in commandutil.known_ids['lilybots'])
        await ctx.send('Hi Lily! I love you!' if lily_in_guild
                       else 'L-lily? Where are you? ;~;')

    @commands.command()
    async def whatis(self, ctx, *, query):
        '''Searches Wikipedia to see what something is! Give it a try!'''
        closest_result = wikipedia.search(query)[0]
        try:
            description_result = ''.join(
                wikipedia.page(closest_result).summary)[:1500]
        except wikipedia.exceptions.DisambiguationError:
            await ctx.send(
                "Sorry, you'll have to be more specific than that ;~;")
        else:
            await ctx.send('```{}...```\nhttps://en.wikipedia.org/wiki/{}'
                           .format(description_result, closest_result))

    @commands.command(hidden=True)
    @commands.is_owner()
    async def sendto(self, ctx, channel: discord.TextChannel, *,
                     message_text: str):
        await channel.send(message_text)

    @commands.command(hidden=True)
    @commands.is_owner()
    async def supereval(self, ctx, *, to_eval: str):
        old_stdout = sys.stdout
        sys.stdout = temp_output = StringIO()
        eval_result = eval(to_eval) or ''
        sys.stdout = old_stdout
        eval_output = temp_output.getvalue() or ''
        if eval_result or eval_output:
            await ctx.send(f'{eval_output}\n```{eval_result}```'.strip())
        else:
            await ctx.send("Hmm, I didn't get any output for that ;~;")

    @commands.command(hidden=True)
    @commands.is_owner()
    async def reloadcritical(self, ctx):
        '''Reloads my critical commands'''
        logging.info('---Reloading criticalcommands---')
        ctx.bot.unload_extension('project.criticalcommands')
        try:
            ctx.bot.load_extension('project.criticalcommands')
            logging.info('Successfully reloaded criticalcommands')
            await ctx.send('Successfully reloaded!')
        except Exception as caught_exception:
            logging.info(
                r'Failed to reload criticalcommands:\n{}\n\n\n'
                .format(commandutil.get_formatted_traceback(
                    caught_exception)))
            await commandutil.send_formatted_message(
                ctx,
                commandutil.get_formatted_traceback(caught_exception))

    @commands.command(hidden=True)
    @commands.is_owner()
    async def clearshell(self, ctx):
        '''Adds a few newlines to Maku's shell (for clean debugging)'''
        print('\n'*10)

    @commands.command()
    async def choose(self, ctx, *args):
        '''
        Returns a random choice from the choices you provide!
        Separated  by spaces
        '''
        await ctx.send('I choose {}!'.format(random.choice(args)))

    def load_free_reign_guilds(self):
        '''Loads free reign guilds from FREE_REIGN_PATH'''
        with open(FREE_REIGN_PATH, 'r') as open_file:
            self.free_guilds = set(json.load(open_file))

    def save_free_reign_guilds(self):
        '''Saves free reign guilds to FREE_REIGN_PATH'''
        with open(FREE_REIGN_PATH, 'w') as open_file:
            json.dump(list(self.free_guilds), open_file)

    def add_free_reign_guild(self, guild_id):
        '''Adds a given guild ID to free reign guilds and saves it'''
        self.free_guilds.add(guild_id)
        self.save_free_reign_guilds()

    def remove_free_reign_guild(self, guild_id):
        '''Removes a given guild ID from free reign guilds and saves it'''
        self.free_guilds.remove(guild_id)
        self.save_free_reign_guilds()

    @commands.Cog.listener()
    async def on_command_error(self, ctx,
                               caught_exception: CommandError):
        if isinstance(caught_exception, CommandNotFound):
            if self.bot.user.mention in ctx.message.content:
                to_asteval = ctx.message.content.replace(
                    self.bot.user.mention, '').strip()
                astevald = aeval(to_asteval, return_error=False)
                if astevald:
                    await ctx.send(astevald)
        elif isinstance(caught_exception, NotOwner):
            await ctx.send('Sorry, only Maku can use that command :(')
        elif isinstance(caught_exception, CommandOnCooldown):
            await ctx.send(
                '''
                Slow down! You're going too fast for me ;a;
                I'm sorry that I'm not good enough to keep up with you :(
                ''')
        elif isinstance(caught_exception, (
                MissingPermissions,
                BotMissingPermissions,
                BadUnionArgument)):
            await ctx.send(str(caught_exception))
        else:
            await commandutil.send_formatted_message(
                self.bot.makusu,
                commandutil.get_formatted_traceback(caught_exception))

    @commands.Cog.listener()
    async def on_error(self, ctx, caught_exception):
        await commandutil.send_formatted_message(
            self.bot.makusu,
            commandutil.get_formatted_traceback(caught_exception))

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        def should_be_logged(message):
            return (
                message.author != self.bot.user
                and message.guild
                and message.guild.id == commandutil.known_ids['aagshit']
                and message.channel.id != commandutil.known_ids[
                    'aagshit_lawgs'])
        if message.author != self.bot.user:
            if message.guild and message.guild.id in self.free_guilds\
               and message.mention_everyone:
                await message.channel.send(message.author.mention+' grr')
            if message.guild and message.guild.id in self.free_guilds\
               and 'vore' in message.content.split():
                await message.pin()
            if message.guild and self.bot.user in message.mentions:
                new_activity = discord.Game(name=message.author.name)
                await self.bot.change_presence(activity=new_activity)
            if should_be_logged(message):
                for attachment in message.attachments:
                    await attachment.save(
                        str(SAVED_ATTACHMENTS_DIR / attachment.filename))
                    aagshit_lawgs_channel = self.bot.get_channel(
                        commandutil.known_ids['aagshit_lawgs'])
                    try:
                        await aagshit_lawgs_channel.send(
                            rf'Posted by {message.author.name} '
                            'in {message.channel.mention}:',
                            file=discord.File(str(SAVED_ATTACHMENTS_DIR
                                                  / attachment.filename)))
                    except discord.errors.Forbidden:
                        print("Unable to log message due to permission error")
        lily_is_greeting_makubot = (
            message.author.id in commandutil.known_ids['lilybots']
            and 'Hi makubot!' in message.content)
        if lily_is_greeting_makubot:
            await message.channel.send(
                "Hi Lily! You're amazing and I love you so much!!!!")

    async def move_message_attempt(self, message: discord.Message,
                                   channel: discord.TextChannel,
                                   move_request_user: discord.Member):
        '''
        Called when ther user attempts to move a message.
        Can be called with an emoji or with a command.
        '''
        member_can_move_messages = channel.permissions_for(
            move_request_user).manage_messages
        should_get_moved = (member_can_move_messages
                            or move_request_user == message.author
                            or move_request_user.id == self.bot.makusu.id)

        if should_get_moved:
            for attachment in message.attachments:
                await attachment.save(SAVED_ATTACHMENTS_DIR
                                      / attachment.filename)
            attachment_files = [
                discord.File(SAVED_ATTACHMENTS_DIR / attachment.filename)
                for attachment in message.attachments]
            new_message_content = '{} has moved this here from {}. OP was {}.\
                                   \n{}'.format(move_request_user.mention,
                                                message.channel.mention,
                                                message.author.mention,
                                                message.content)
            await channel.send(new_message_content, files=attachment_files)
            await message.delete()
        else:
            await message.channel.send(
                "Looks like you don't have the manage messages role and \
                you're not OP. sorry.")

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        deletion_message = (
            f'{message.created_at}:A message from {message.author.name} '
            f'has been deleted in {message.channel.name} of '
            f'{message.channel.guild.name} with {len(message.attachments)} '
            f'attachment(s): {message.content}')
        self.last_deleted_message[message.channel.id] = deletion_message
        with codecs.open(DELETION_LOG_PATH, 'a', 'utf-8') as deletion_log_file:
            deletion_log_file.write(deletion_message+'\n')
        should_be_logged = (
            message.guild
            and message.channel.guild.id == commandutil.known_ids['aagshit']
            and message.channel.id != commandutil.known_ids['aagshit_lawgs'])
        if should_be_logged:
            aagshit_lawgs_channel = self.bot.get_channel(
                commandutil.known_ids['aagshit_lawgs'])
            await aagshit_lawgs_channel.send(rf'```{deletion_message}```')

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        '''Called when a member joins to tell them that Maku loves them
        (because Maku does) <3'''
        if member.guild.id in self.free_guilds:
            await member.guild.system_channel.send(
                f'Hi {member.mention}! Maku loves you! <333333')

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        '''Called when a user adds a reaction to a message which is in my cache.
        Currently only looks for the 'move message' emoji.'''

        def author_is_user_check(message):
            return message.author == user

        if reaction.emoji == MOVE_EMOTE:
            await reaction.message.channel.send(
                f'{user.mention} Move to which channel?')
            while True:
                message = await self.bot.wait_for('message',
                                                  check=author_is_user_check)
                if message.content.lower().strip() == 'cancel':
                    await message.channel.send('Cancelled')
                    return
                try:
                    channel_id = int(re.match(r'<#([0-9]+)>$',
                                              message.content).group(1))
                    channel_to_move_to = self.bot.get_channel(channel_id)
                    if channel_to_move_to is None:
                        raise ValueError('Channel to move to is none')
                except (ValueError, AttributeError):
                    await message.channel.send(
                        'That does not look like a tagged channel, '
                        'try again. (You do not need to readd the '
                        'reaction. Say "cancel" to cancel the move request.)')
                except TypeError:
                    await message.channel.send(
                        'Hmmm, that looks like a channel but I am unable '
                        'to figure out what it is. It has already '
                        'been logged for Maku to debug.')
                    logging.error(
                        'Could not figure out what channel {} was.'
                        .format(channel_id))
                else:
                    await self.move_message_attempt(reaction.message,
                                                    channel_to_move_to,
                                                    message.author)
                    return


class CustomFormatter(discord.ext.commands.formatter.HelpFormatter):
    async def format(self):
        default_help_text = await super(CustomFormatter, self).format()
        people_desc = ', '.join(
            self.context.bot.shared['fave_pictures_commands'])
        reaction_desc = ', '.join(
            self.context.bot.shared['reaction_images_commands'])
        full_help = default_help_text + [
            '```Favorite people commands: {}```'.format(people_desc),
            '```Reaction image commands: {}```'.format(reaction_desc)]
        return full_help


def setup(bot):
    logging.info('makucommands starting setup')
    bot.add_cog(MakuCommands(bot))
    bot.formatter = CustomFormatter()
    logging.info('makucommands ending setup')
