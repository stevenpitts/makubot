'''
Module containing the majority of the basic commands makubot can execute.
'''
import random
import sys
import importlib
from pathlib import Path
import json
import logging
import time
import discord
from discord.ext import commands
from discord.errors import (NotFound)
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

    @commands.command(hidden=True)
    @commands.is_owner()
    async def reload(self, ctx):
        '''
        Reloads my command cogs. Works even in fatal situations. Sometimes.
        '''
        logging.info('---Reloading makucommands and commandutil---')
        importlib.reload(commandutil)
        reload_response = ''
        for to_reload in self.bot.shared['default_extensions']:
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

    @commands.command(aliases=['are you free',
                               'areyoufree?',
                               'are you free?'])
    @commands.guild_only()
    async def areyoufree(self, ctx):
        '''If I have free reign I'll tell you'''
        is_free = ctx.guild.id in self.bot.shared['data']['free_guilds']
        await ctx.send('Yes, I am free.' if is_free else
                       'This is not a free reign guild.')

    @commands.command()
    @commands.is_owner()
    async def perish(self, ctx):
        '''Murders me :( '''
        await self.bot.close()

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

    @commands.command(aliases=["english"], hidden=True)
    async def translate(self, ctx, *, text: str):
        """Translate some text into English!
        Idea stolen from KitchenSink."""
        await ctx.send("Not implemented :<")

    @commands.command()
    async def fact(self, ctx):
        '''Sends a fun fact!'''
        await ctx.send(random.choice(FACTS))

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


def setup(bot):
    logging.info('makucommands starting setup')
    bot.add_cog(MakuCommands(bot))
    logging.info('makucommands ending setup')
