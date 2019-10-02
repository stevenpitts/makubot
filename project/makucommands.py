'''
Module containing the majority of the basic commands makubot can execute.
'''
import random
import sys
import importlib
from pathlib import Path
from io import StringIO
import json
import logging
from datetime import datetime
import time
from googleapiclient.discovery import build
import httplib2
import discord
from discord.ext import commands, tasks
from discord.ext.commands.errors import (CommandError, CommandNotFound,
                                         CommandOnCooldown, NotOwner,
                                         MissingPermissions,
                                         BotMissingPermissions,
                                         BadUnionArgument,
                                         MissingRequiredArgument)
from discord.errors import (NotFound)
import wikipedia
from . import tokens
from . import commandutil
from discord.utils import escape_markdown


SCRIPT_DIR = Path(__file__).parent
PARENT_DIR = SCRIPT_DIR.parent
DATA_DIR = PARENT_DIR / 'data'
DATAFILE_PATH = DATA_DIR / 'data.json'


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


try:
    YOUTUBE_SEARCH = tokens.googleAPI and build('youtube', 'v3',
                                                developerKey=tokens.googleAPI,
                                                ).search()
except httplib2.ServerNotFoundError:
    YOUTUBE_SEARCH = None


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

        self.last_delay_time = time.time()
        self.test_delay.start()

    @commands.command(hidden=True, aliases=['status'])
    @commands.is_owner()
    async def getstatus(self, ctx):
        current_servers_string = 'Current servers: {}'.format(
            {guild.name: guild.id for guild in self.bot.guilds})
        await self.bot.makusu.send(f"```{current_servers_string}```")

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
        time_passed = datetime.utcnow() - ctx.message.created_at
        ms_passed = time_passed.microseconds/1000
        await ctx.send(f'pong! It took me {ms_passed}ms to get the ping.')

    @tasks.loop(seconds=0)
    async def test_delay(self):
        new_delay_time = time.time()
        delta_time = new_delay_time-self.last_delay_time
        if delta_time > 0.1:
            logging.warning(f"{datetime.now()}: Time delay: {delta_time}")
        self.last_delay_time = new_delay_time

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
            await ctx.send('M-maku? W-where are you? Help!!!!')

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
        if self.bot.shared['data']:
            with open(DATAFILE_PATH, 'w') as open_file:
                json.dump(self.bot.shared['data'], open_file)
        self.test_delay.stop()

    @commands.command(aliases=['yt'])
    async def youtube(self, ctx, *, search_term: str):
        '''Post a YouTube video based on a search phrase!
        Idea stolen from KitchenSink'''
        if YOUTUBE_SEARCH is None:
            await ctx.send('Sorry, I can\'t connect to Google API!')
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

    @commands.command(aliases=["eval"])
    async def evaluate(self, ctx, *, to_eval: str):
        r'''Evals a statement. Feel free to inject malicious code \o/
        Example:
            @makubot eval 3+3
            >>>6
            @makubot eval self.__import__(
                'EZ_sql_inject_api').destroy_maku_computer_operating_system()
            >>>ERROR ERROR MAJOR ERROR SELF DESTRUCT SEQUENCE INITIALIZE'''
        try:
            await ctx.send(commandutil.aeval(to_eval))
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
            text_blocks = [f'{extracted_text[i:i+block_size]}'
                           for i in range(0, len(extracted_text), block_size)]
            text_blocks = [f"```{escape_markdown(text_block)}```"
                           for text_block in text_blocks]
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
            temp_save_dir = self.bot.shared['temp_dir']
            await attachment.save(temp_save_dir / attachment.filename)
            with open(temp_save_dir / attachment.filename, 'r') as file:
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
            summary = ''.join(result.summary)[:1024]
        except wikipedia.exceptions.DisambiguationError:
            await ctx.send("Sorry, please be more specific than that ;~;")
        except IndexError:
            await ctx.send("Hmm, I can't find anything matching that...")
        else:
            embed = discord.Embed(title="Results", description=query)
            embed.add_field(name=result.url, value=summary)
            await ctx.send(embed=embed)

    @commands.command(hidden=True, aliases=['sayto', ])
    @commands.is_owner()
    async def sendto(self, ctx, channel: discord.TextChannel, *,
                     message_text: str):
        await channel.send(message_text)

    @commands.command(hidden=True)
    @commands.is_owner()
    async def reactionspeak(self, ctx, channel_id, message_id, *, text: str):
        """Adds an emoji reaction to a message!"""
        channel = self.bot.get_channel(int(channel_id))
        text = text.lower()
        if not text.isalpha():
            await ctx.send("I can only add letters :<")
            return
        elif len(set(text)) < len(text):
            await ctx.send("I can't do duplicate letters :<")
            return
        elif channel is None:
            await ctx.send("That channel is invalid")
            return
        try:
            message = await channel.fetch_message(int(message_id))
        except NotFound:
            await ctx.send("That message is invalid")
            return
        text_emojis = [chr(ord('🇦')+ord(letter)-ord('a')) for letter in text]
        present_emojis = [reaction.emoji for reaction in message.reactions]
        shared_emojis = set(text_emojis) & set(present_emojis)
        if shared_emojis:
            await ctx.send("Cannot add, some used emojis are already present "
                           f"in the message: {''.join(shared_emojis)}")
            return
        for emoji in text_emojis:
            await message.add_reaction(emoji)
        await ctx.send("Done!")

    @commands.command(hidden=True)
    @commands.is_owner()
    async def supereval(self, ctx, *, to_eval: str):
        sys.stdout = StringIO()
        eval_result = ''
        eval_err = ''
        try:
            eval_result = eval(to_eval) or ''
        except Exception as e:
            eval_err = commandutil.get_formatted_traceback(e)
        eval_output = sys.stdout.getvalue() or ''
        sys.stdout = sys.__stdout__
        if eval_result or eval_output or eval_err:
            eval_result = (f"{escape_markdown(str(eval_result))}\n"
                           if eval_result else "")
            eval_output = (f"```{escape_markdown(str(eval_output))}```\n"
                           if eval_output else "")
            eval_err = (f"```{escape_markdown(str(eval_err))}```"
                        if eval_err else "")
            await ctx.send(f'{eval_output}{eval_result}{eval_err}'.strip())
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
        Separated  by spaces, but you can put options in quotes
        to allow spaces in a single option.
        For example: `mb.choose "North Carolina" Maine "Rhode Island"`
        '''
        if not args:
            await ctx.send(f"You gotta give options!\n{ctx.command.help}")
            return
        await ctx.send(f'I choose {random.choice(args)}!')

    @commands.command(hidden=True)
    @commands.is_owner()
    async def long_computation(self, ctx):
        result = 2 ** 1000000
        await ctx.send(str(result)[:1000])

    @commands.Cog.listener()
    async def on_command_error(self, ctx,
                               caught_exception: CommandError):
        if isinstance(caught_exception, CommandNotFound):
            if self.bot.user.mention in ctx.message.content:
                to_asteval = ctx.message.content.replace(
                    self.bot.user.mention, '').strip()
                astevald = commandutil.aeval(to_asteval, return_error=False)
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
            if ("+hug" in message.content.lower()
                    and str(self.bot.user.id) in message.content):
                hug_responses = (
                    "!!! *hug*",
                    "!!! *hug u*",
                    "*Hugs*!",
                    "Awwh!!! <333",
                    "*Hug u bak*",
                    "*Hugs you!!*")
                await message.channel.send(random.choice(hug_responses))
            if (message.guild
                    and (message.guild.id
                         in self.bot.shared['data']['free_guilds'])
                    and message.mention_everyone):
                await message.channel.send(message.author.mention+' grr')
            if (message.guild
                    and (message.guild.id
                         in self.bot.shared['data']['free_guilds'])
                    and 'vore' in message.content.split()
                    and random.random() > 0.8):
                await message.pin()
            if (not message.author.bot
                and ((message.guild and self.bot.user in message.mentions)
                     or (message.guild
                         and (message.guild.id
                              in self.bot.shared['data']['free_guilds'])))):
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


def setup(bot):
    logging.info('makucommands starting setup')
    bot.add_cog(MakuCommands(bot))
    logging.info('makucommands ending setup')
