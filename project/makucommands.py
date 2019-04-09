'''
Module containing the majority of the basic commands makubot can execute.
Also used to reload criticalcommands.
'''
import random
import sys
import importlib
from pathlib import Path
from io import StringIO
import datetime
import json
import logging
from googleapiclient.discovery import build
import asteval
import discord
from discord.ext import commands
from discord.ext.commands.errors import (CommandError, CommandNotFound,
                                         CommandOnCooldown, NotOwner,
                                         MissingPermissions,
                                         BotMissingPermissions,
                                         BadUnionArgument,
                                         MissingRequiredArgument)
import wikipedia
from . import tokens
from . import commandutil


SCRIPT_DIR = Path(__file__).parent
PARENT_DIR = SCRIPT_DIR.parent
DATA_DIR = PARENT_DIR / 'data'
WORKING_DIR = DATA_DIR / 'working_directory'
DATAFILE_PATH = DATA_DIR / 'data.json'
SAVED_ATTACHMENTS_DIR = DATA_DIR / 'saved_attachments'


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
    output = temp_string_io.getvalue()
    if result or output:
        output_str = '```{}\n```'.format(output) if output else ''
        result_str = f'```Result: {result}```' if result else 'No Result.'
        return f'{output_str}{result_str}'
    elif return_error:
        return 'No result'


class MakuCommands(discord.ext.commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.description = '''
        Hey there! I'm Makubot!
        I'm a dumb bot made by a person who codes stuff.
        I'm currently running Python {}.
        Also you can just ask Makusu2#2222. They love making new friends <333
        '''.format('.'.join(map(str, sys.version_info[:3])))
        prefixes = [m+b+punc+maybespace for m in 'mM' for b in 'bB'
                    for punc in '.!' for maybespace in [' ', '']]
        self.bot.command_prefix = commands.when_mentioned_or(*prefixes)

        with open(DATAFILE_PATH, 'r') as open_file:
            self.bot.shared['data'] = json.load(open_file)

    @commands.command(hidden=True, aliases=['status'])
    @commands.is_owner()
    async def getstatus(self, ctx):
        current_servers_string = 'Current servers: {}'.format(
            {guild.name: guild.id for guild in self.bot.guilds})
        await commandutil.send_formatted_message(
            self.bot.makusu, current_servers_string)

    @commands.command(hidden=True)
    @commands.is_owner()
    async def reload(self, ctx):
        '''
        Reloads my command cogs. Works even in fatal situations. Sometimes.
        '''
        logging.info('---Reloading makucommands and commandutil---')
        importlib.reload(commandutil)
        reload_response = ''
        for to_reload in ['reminders',
                          'picturecommands',
                          'serverlogging',
                          'makucommands',
                          'movement']:
            try:
                ctx.bot.reload_extension(f"project.{to_reload}")
            except Exception as e:
                reload_response += f"Failed to reload {to_reload}\n"
                fail_tb = commandutil.get_formatted_traceback(e)
                fail_message = f"Error reloading {to_reload}: \n{fail_tb}\n\n"
                print(fail_message)
                logging.info(fail_message)
        reload_response += "Done!"
        await ctx.send(reload_response)
        print("Reloaded")

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
        time_passed = datetime.datetime.utcnow() - ctx.message.created_at
        ms_passed = time_passed.microseconds/1000
        await ctx.send(f'pong! It took me {ms_passed}ms to get the ping.')

    @commands.command(aliases=['are you free',
                               'areyoufree?',
                               'are you free?'])
    @commands.guild_only()
    async def areyoufree(self, ctx):
        '''If I have free reign I'll tell you'''
        is_free = ctx.guild.id in self.bot.shared['data']['free_guilds']
        await ctx.send('Yes, I am free.' if is_free else
                       'This is not a free reign guild.')

    @commands.command(aliases=['emoji spam'])
    @commands.bot_has_permissions(add_reactions=True)
    async def emojispam(self, ctx):
        '''Prepare to be spammed by the greatest emojis you've ever seen'''
        emojis_random_order = iter(sorted(self.bot.emojis,
                                          key=lambda *args: random.random()))
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

    @commands.command(aliases=['is gay'])
    async def isgay(self, ctx):
        '''Tells me I'm gay (CAUTION: May mirror attack at sender)'''
        await ctx.send('No u')

    @commands.command()
    async def bully(self, ctx):
        '''Bullies me :('''
        if ctx.guild and ctx.guild.get_member(self.bot.makusu.id) is not None:
            await ctx.send(f'{self.bot.makusu.mention} '
                           'HELP I\'M BEING BULLIED ;a;')
        else:
            await ctx.send('M-makusu? W-where are you? Help!!!!')

    @commands.command(aliases=['hug me'])
    async def hugme(self, ctx):
        '''Hugs you <3'''
        await ctx.send(f'*Hugs you* {ctx.message.author.mention}')

    @commands.command(aliases=['go wild'])
    @commands.is_owner()
    @commands.guild_only()
    async def gowild(self, ctx):
        '''Add the current guild as a gowild guild; I do a bit more on these.
        Only Maku can add guilds though :('''
        if ctx.message.guild:
            self.bot.shared['data']['free_guilds'].append(ctx.message.guild.id)
            await ctx.send('Ayaya~')

    def cog_unload(self):
        with open(DATAFILE_PATH, 'w') as open_file:
            json.dump(self.bot.shared['data'], open_file)

    @commands.command(aliases=['yt'])
    async def youtube(self, ctx, *, search_term: str):
        '''Post a YouTube video based on a search phrase!
        Idea stolen from KitchenSink'''
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
        await ctx.send(f'https://www.youtube.com/watch?v={search_result}'
                       if search_result else 'Sowwy, I can\'t find it :(')

    @commands.command(aliases=["english"], hidden=True)
    async def translate(self, ctx, *, text: str):
        """Translate some text into English!
        Idea stolen from KitchenSink."""
        await ctx.send("Not implemented :<")

    @commands.command()
    async def eval(self, ctx, *, to_eval: str):
        r'''Evals a statement. Feel free to inject malicious code \o/
        Example:
            @makubot eval 3+3
            >>>6
            @makubot eval self.__import__(
                'EZ_sql_inject_api').destroy_maku_computer_operating_system()
            >>>ERROR ERROR MAJOR ERROR SELF DESTRUCT SEQUENCE INITIALIZE'''
        try:
            await ctx.send(aeval(to_eval))
        except AttributeError:
            logging.error(f"Couldn't get a match on {ctx.message.content}.")

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
            block_size = 500
            button_emojis = left_arrow, right_arrow, stop_emote = '👈👉❌'
            text_blocks = [r'```{}```'.format(extracted_text[i:i+block_size])
                           for i in range(0, len(extracted_text), block_size)]
            current_index = 0
            block_message = await ctx.send(text_blocks[current_index])

            def check(reaction, user):
                return (user != self.bot.user
                        and reaction.emoji in button_emojis
                        and reaction.message.id == block_message.id)

            while current_index is not None:
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
                    current_index = None
        try:
            previous_messages = (message async for message in
                                 ctx.channel.history() if message.attachments)
            message_with_file = await previous_messages.__anext__()
            attachment = message_with_file.attachments[0]
            await attachment.save(WORKING_DIR / attachment.filename)
            with open(WORKING_DIR / attachment.filename, 'r') as file:
                out_text = '\n'.join(file.readlines()).replace("```", "'''")
        except UnicodeDecodeError:
            await ctx.send(f'It looks like you\'re trying to get me to '
                           f'read ```{attachment.filename}```, but that '
                           'doesn\'t seem to be a text file, sorry!! :<')
        except StopAsyncIteration:
            await ctx.send("Ah, I couldn't find any text file, sorry!")
        else:
            await displaytxt(out_text)

    @commands.command()
    async def whatis(self, ctx, *, query):
        '''Searches Wikipedia to see what something is! Give it a try!'''
        try:
            result = wikipedia.page(wikipedia.search(query)[0])
            summary = ''.join(result.summary)[:1500]
        except wikipedia.exceptions.DisambiguationError:
            await ctx.send("Sorry, please be more specific than that ;~;")
        else:
            await ctx.send(f'```{summary}...```\n{result.url}')

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
    async def clearshell(self, ctx):
        '''Adds a few newlines to Maku's shell (for clean debugging)'''
        print('\n'*10)

    @commands.command()
    async def choose(self, ctx, *args):
        '''
        Returns a random choice from the choices you provide!
        Separated  by spaces
        '''
        await ctx.send(f'I choose {random.choice(args)}!')

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
            await ctx.send('Slow down! You\'re going too fast for me ;a;\
                            I\'m sorry :(')
        elif isinstance(caught_exception, (MissingPermissions,
                                           BotMissingPermissions,
                                           BadUnionArgument,
                                           MissingRequiredArgument)):
            await ctx.send(str(caught_exception))
        else:
            print(commandutil.get_formatted_traceback(caught_exception))

    @commands.Cog.listener()
    async def on_error(self, ctx, caught_exception):
        print(commandutil.get_formatted_traceback(caught_exception))

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author != self.bot.user:
            if (message.guild
                    and (message.guild.id
                         in self.bot.shared['data']['free_guilds'])
                    and message.mention_everyone):
                await message.channel.send(message.author.mention+' grr')
            if (message.guild
                    and (message.guild.id
                         in self.bot.shared['data']['free_guilds'])
                    and 'vore' in message.content.split()):
                await message.pin()
            if message.guild and self.bot.user in message.mentions:
                new_activity = discord.Game(name=message.author.name)
                await self.bot.change_presence(activity=new_activity)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        '''Called when a member joins to tell them that Maku loves them
        (because Maku does) <3'''
        if member.guild.id in self.bot.shared['data']['free_guilds']:
            try:
                await member.guild.system_channel.send(f'Hi {member.mention}! '
                                                       'Maku loves you! '
                                                       '<333333')
            except AttributeError:
                print(f"{member.mention} joined, but guild "
                      f"{member.guild.name} has no system_channel. ID is "
                      f"{member.guild._system_channel_id}.")


class MakuHelpCommand(discord.ext.commands.help.DefaultHelpCommand):
    def get_ending_note(self):
        pictures_desc = ', '.join(
            self.context.bot.shared['pictures_commands'])
        return (f'Reaction images: {pictures_desc}\n\n\n'
                f"{super().get_ending_note()}")


def setup(bot):
    logging.info('makucommands starting setup')
    bot.add_cog(MakuCommands(bot))
    bot.help_command = MakuHelpCommand()
    logging.info('makucommands ending setup')
