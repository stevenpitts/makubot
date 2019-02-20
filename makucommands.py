"""
Module containing the majority of the basic commands makubot can execute.
Also used to reload criticalcommands.
"""
import discord
from discord.ext import commands
import random
import sys
import asyncio
import traceback
import os
import asteval
import re
from io import StringIO
from tokens import *
import googleapiclient
from googleapiclient.discovery import build
import datetime
import commandutil
import json
import logging
import codecs
import wikipedia

last_deleted_message = {} #Maps channel ID to last deleted message content, along with a header of who send it.


facts = """Geese are NEAT
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
With great power comes great responsibility -Uncle Ben""".split('\n')

youtube_search = build('youtube', 'v3',developerKey=googleAPI).search()

def aeval(s,return_error=True) -> str:
    temp_string_io = StringIO()
    aeval_interpreter = asteval.Interpreter(writer=temp_string_io,err_writer=temp_string_io)
    result = aeval_interpreter(s)
    if not result:
         if return_error:
             result = "No result found."
         else:
             return None
    temp_str_val = temp_string_io.getvalue()
    return "{}```Result: {}```".format('```{}\n```'.format(temp_str_val) if temp_str_val else '',result)




move_emote = "\U0001f232"





class MakuCommands():
    def __init__(self,bot):
        self.bot = bot
        self.bot.description = """
Hey there! I'm Makubot!
I'm a dumb bot made by a person who codes stuff.
I'm currently running Python {}.
Also you can just ask Makusu2#2222 cuz they're never too busy to make a new friend <3
        """.format(".".join(map(str, sys.version_info[:3])))
        self.free_guilds = set()
        self.bot.command_prefix = commands.when_mentioned_or(*[m+b+punc+maybespace for m in ['m','M'] for b in ['b','B'] for punc in ['.','!'] for maybespace in [' ','']])
        asyncio.get_event_loop().create_task(self.load_free_reign_guilds())



    @commands.command(hidden=True,aliases=["status",])
    @commands.is_owner()
    async def getstatus(self,ctx):
        await commandutil.send_formatted_message(self.bot.makusu,"Current servers: {}".format({guild.name:guild.id for guild in self.bot.guilds}))

    @commands.command()
    @commands.cooldown(1,1,type=commands.BucketType.user)
    async def ping(self,ctx):
        """
        Pong was the first commercially successful video game, which helped to establish the video game industry along with the first home console, the Magnavox Odyssey. Soon after its release, several companies began producing games that copied its gameplay, and eventually released new types of games. As a result, Atari encouraged its staff to produce more innovative games. The company released several sequels which built upon the original's gameplay by adding new features. During the 1975 Christmas season, Atari released a home version of Pong exclusively through Sears retail stores. It also was a commercial success and led to numerous copies. The game has been remade on numerous home and portable platforms following its release. Pong is part of the permanent collection of the Smithsonian Institution in Washington, D.C. due to its cultural impact.
        """
        time_passed = (datetime.datetime.utcnow()-ctx.message.created_at).microseconds/1000
        await ctx.send("pong! It took me {} milliseconds to get the ping.".format(time_passed))


    @commands.command(aliases=["are you free","areyoufree?","are you free?"])
    @commands.guild_only()
    async def areyoufree(self,ctx):
        """If I have free reign I'll tell you"""
        await ctx.send("Yes, I am free." if ctx.guild.id in self.free_guilds else "This is not a free reign guild.")

    @commands.command(aliases=["emoji spam"])
    @commands.bot_has_permissions(add_reactions=True)
    async def emojispam(self,ctx):
        """Prepare to be spammed by the greatest emojis you've ever seen"""
        for emoji_to_add in iter(sorted(self.bot.emojis,key=lambda *args: random.random())):
            try:
                await ctx.message.add_reaction(emoji_to_add)
            except discord.errors.Forbidden:
                return

    @commands.command()
    @commands.is_owner()
    async def perish(self,ctx):
        """Murders me :( """
        await self.bot.close()

    @commands.command()
    @commands.bot_has_permissions(manage_messages=True)
    async def move(self,ctx,msg_id,channel_to_move_to:discord.TextChannel):
        """move <message_id> <channel_mention>: move a message from the current channel to the channel specified. You can also add the reaction \U0001f232 to automate this process."""
        try:
            message_to_move = await ctx.message.channel.get_message(msg_id)
        except discord.errors.HTTPException:
            await ctx.message.channel.send("That, uh, doesn't look like a valid message ID. Try again.")
        else:
            await self.move_message_attempt(message_to_move,channel_to_move_to,ctx.message.author)

    @commands.command(aliases=["is gay"])
    async def isgay(self,ctx):
        """Tells me I'm gay (CAUTION: May mirror the attack at the sender)"""
        await ctx.send("No u")

    @commands.command()
    async def bully(self,ctx):
        """Bullies me :("""
        if ctx.guild and ctx.guild.get_member(self.bot.makusu.id) is not None:
            await ctx.send("{} HELP I'M BEING BULLIED ;a;".format(self.bot.makusu.mention))
        else:
            await ctx.send("M-makusu? W-where are you? Help!!!!")

    @commands.command(aliases=["hug me"])
    async def hugme(self,ctx):
        """Hugs you <3"""
        await ctx.send(r"*Hugs you* {}".format(ctx.message.author.mention))

    @commands.command(aliases=["go wild"])
    @commands.is_owner()
    @commands.guild_only()
    async def gowild(self,ctx):
        """Add the current guild as a gowild guild; I do a bit more on these. Only Maku can add guilds though :("""
        if ctx.message.guild:
            await self.add_free_reign_guild(ctx.message.guild.id)
            await ctx.send("Ayaya~")

    @commands.command(aliases=["youtube"])
    async def yt(self,ctx,*,search_term:str):
        """Post a YouTube video based on a search phrase!"""
        search_response = youtube_search.list(q=search_term,part='id',maxResults=10).execute()
        search_result =  next((search_result['id']['videoId'] for search_result in search_response.get('items', []) if search_result['id']['kind'] == 'youtube#video'),None)
        await ctx.send(r"https://www.youtube.com/watch?v={}".format(search_result) if search_result else "Sowwy, I can't find it :(")

    @commands.command()
    async def eval(self,ctx,*,to_eval:str):
        """Evals a statement. Feel free to inject malicious code \o/
        Example:
            @makubot eval 3+3
            >>>6
            @makubot eval self.__import("EZ_sql_inject_api").destroy_maku_computer_operating_system()
            >>>ERROR ERROR MAJOR ERROR SELF DESTRUCT SEQUENCE INITIALIZE
        """
        try:
            await ctx.send(aeval(to_eval))
        except AttributeError:
            logging.error("Couldn't get a match on {}. Weird.".format(ctx.message.content))

    @commands.command(aliases=["what was that","whatwasthat?","what was that?"])
    async def whatwasthat(self,ctx):
        """Tells you what that fleeting message was"""
        try:
            await ctx.send(last_deleted_message.pop(ctx.channel.id))
        except KeyError:
            await ctx.send("I can't find anything, sorry :(")

    @commands.command()
    async def fact(self,ctx):
        """Sends a fun fact!"""
        await ctx.send(random.choice(facts))

    @commands.command()
    async def remindme(self,ctx,timelength:str,*,reminder:str):
        """Reminds you of a thing (not reliable)
        Usage: remindme [<days>d][<hours>h][<minutes>m][<seconds>s] <reminder message>
        Example: remindme 1d2h9s do laundry
        Do not rely on me to remind you for long periods of time! Yet. Eventually I'll be run on a VPS :3
        """
        async def send_reminder(channel,reminder_target:discord.Member,seconds:int,reminder_message:str):
            await asyncio.sleep(seconds)
            await channel.send("{}, you have a reminder from {} seconds ago:\n{}".format(reminder_target.name,seconds,reminder_message))
        timereg = re.compile(''.join([r"((?P<{}>\d*){})?".format(cha,cha) for cha in "dhms"]))
        matches = re.search(timereg,timelength)
        if matches:
            days,hours,minutes,seconds = [int(val) if val else 0 for val in matches.group("d","h","m","s")]
            total_seconds = days*86400 + hours*3600 + minutes*60 + seconds
            await ctx.send("Coolio I'll remind you in {} seconds".format(total_seconds))
            asyncio.get_event_loop().create_task(send_reminder(ctx.channel,ctx.message.author,total_seconds,reminder))
        else:
            await ctx.send("Hmm, that doesn't look valid. Ask for help if you need it!")

    @commands.command(hidden=True,aliases=["deletehist"])
    @commands.is_owner()
    async def removehist(self,ctx,num_to_delete:int):
        """Removes a specified number of previous messages by me"""
        bot_history = (message async for message in ctx.channel.history() if message.author == self.bot.user)
        to_delete = []
        for i in range(num_to_delete):
            try:
                to_delete.append(await bot_history.__anext__())
            except StopAsyncIteration:
                break
        await ctx.channel.delete_messages(to_delete)

    @commands.command()
    @commands.bot_has_permissions(manage_messages=True)
    async def opentxt(self,ctx):
        """Opens the most recent file for reading!!!"""
        async def displaytxt(extracted_text:str):
            text_block_size = 500
            button_emojis = left_arrow,right_arrow,stop_emote = "👈👉❌"
            text_blocks = [r"```{}```".format(extracted_text[i:i+text_block_size]) for i in range(0, len(extracted_text), text_block_size)]
            current_index = 0
            block_message = await ctx.send(text_blocks[current_index])
            def check(reaction,user):
                return user != self.bot.user and reaction.emoji in button_emojis and reaction.message.id == block_message.id

            while True:
                await block_message.edit(content=text_blocks[current_index])
                for emoji_to_add in button_emojis:
                    await block_message.add_reaction(emoji_to_add)
                res = await self.bot.wait_for('reaction_add',check=check)
                emoji_result = res[0].emoji
                try:
                    await block_message.remove_reaction(emoji_result,res[1])
                except:
                    pass
                if emoji_result == left_arrow:
                    current_index -= 1
                elif emoji_result == right_arrow:
                    current_index += 1
                else:
                    await block_message.clear_reactions()
                    await block_message.edit(content=r"```File closed.```")
                    break
        try:
            message_with_file = await ((message async for message in ctx.channel.history() if message.attachments)).__anext__()
            attachment = message_with_file.attachments[0]
            await attachment.save(r"working_directory/{}".format(attachment.filename))
            extracted_text = '\n'.join(open(r"working_directory/{}".format(attachment.filename),'r').readlines()).replace("```","'''")
        except UnicodeDecodeError:
            await ctx.send("It looks like you're trying to get me to read ```{}```, but that doesn't seem to be a text file, sorry! (Or I'm just bad) :<".format(attachment.filename))
        except StopAsyncIteration:
            await ctx.send("Ah, I couldn't find any text file, sorry!")
        else:
            asyncio.get_event_loop().create_task(displaytxt(extracted_text))
        finally:
            #Remove if you feel like it, or do whatever idc
            pass

    @commands.command()
    async def sayhitolily(self,ctx):
        """Says hi to Lilybot~"""
        await ctx.send("Hi Lily! I love you!" if ctx.guild and any(ctx.guild.get_member(id) is not None for id in commandutil.known_ids["lilybots"]) else "L-lily? Where are you? ;~;")

    @commands.command()
    async def whatis(self,ctx,*,query):
        """Searches Wikipedia to see what something is! Give it a try!"""
        closest_result = wikipedia.search(query)[0]
        try:
            description_result = ''.join(wikipedia.page(closest_result).summary)[:1500]
        except wikipedia.exceptions.DisambiguationError:
            await ctx.send("Sorry, you'll have to be more specific than that ;~;")
        else:
            await ctx.send('```{}...```\nhttps://en.wikipedia.org/wiki/{}'.format(description_result,closest_result))


    @commands.command(hidden=True)
    @commands.is_owner()
    async def sendto(self,ctx,channel:discord.TextChannel,*,message_text:str):
        await channel.send(message_text)

    @commands.command(hidden=True)
    @commands.is_owner()
    async def supereval(self,ctx,*,to_eval:str):
        old_stdout = sys.stdout
        sys.stdout = temp_output = StringIO()
        eval(to_eval)
        sys.stdout = old_stdout
        await ctx.send(temp_output.getvalue())

    @commands.command(hidden=True)
    @commands.is_owner()
    async def reloadcritical(self,ctx):
        """Reloads my critical commands"""
        logging.info("---Reloading criticalcommands---")
        ctx.bot.unload_extension('criticalcommands')
        try:
            ctx.bot.load_extension('criticalcommands')
            logging.info("Successfully reloaded criticalcommands")
            await ctx.send("Successfully reloaded!")
        except Exception as e:
            logging.info(r"Failed to reload criticalcommands:\n{}\n\n\n".format(commandutil.get_formatted_traceback(e)))
            await commandutil.send_formatted_message(ctx,commandutil.get_formatted_traceback(e))

    @commands.command(hidden=True)
    @commands.is_owner()
    async def clearshell(self,ctx):
        """Adds a few newlines to Maku's shell (for clean debugging)"""
        print("\n"*10)

    @commands.command()
    async def choose(self,ctx,*args):
        """
        Returns a random choice from the choices you provide!
        Separated  by spaces
        """
        await ctx.send("I choose {}!".format(random.choice(args)))


    #TODO
    # @commands.command()
    # async def reactionspeak(self,ctx,msg_id,*,text_to_add):
    #     try:
    #         target_message = await ctx.message.channel.get_message(msg_id)
    #     except discord.errors.HTTPException:
    #         await ctx.message.channel.send("That, uh, doesn't look like a valid message ID. Try again.")
    #     else:
    #         await








    async def load_free_reign_guilds(self):
        with open('free_reign.txt','r') as f:
            self.free_guilds = set(json.load(f))

    async def save_free_reign_guilds(self):
        with open('free_reign.txt','w') as f:
            json.dump(list(self.free_guilds),f)

    async def add_free_reign_guild(self,guild_id):
        self.free_guilds.add(guild_id)
        await self.save_free_reign_guilds()

    async def remove_free_reign_guild(self,guild_id):
        self.free_guilds.remove(guild_id)
        await self.save_free_reign_guilds()























    async def on_command_error(self,ctx,e:discord.ext.commands.errors.CommandError):
        if isinstance(e,discord.ext.commands.errors.CommandNotFound):
            if self.bot.user.mention in ctx.message.content:
                astevald = aeval(ctx.message.content.replace(self.bot.user.mention,"").strip(),return_error=False)
                if astevald:
                    await ctx.send(astevald)
        elif isinstance(e,discord.ext.commands.errors.NotOwner):
            await ctx.send("Sorry, only Maku can use that command :(")
        elif isinstance(e, discord.ext.commands.errors.CommandOnCooldown):
            await ctx.send("Slow down! You're going too fast for me ;a;\nI'm sorry that I'm not good enough to keep up with you :(")
        elif isinstance(e,(discord.ext.commands.errors.MissingPermissions,discord.ext.commands.errors.BotMissingPermissions,discord.ext.commands.errors.BadUnionArgument)):
            await ctx.send(str(e))
        else:
            await commandutil.send_formatted_message(self.bot.makusu,commandutil.get_formatted_traceback(e))
    async def on_error(self,ctx,e):
        await commandutil.send_formatted_message(self.bot.makusu,commandutil.get_formatted_traceback(e))


    async def on_message(self,message : discord.Message):
        if message.author != self.bot.user:
            if message.guild and message.guild.id in self.free_guilds and message.mention_everyone:
                await message.channel.send(message.author.mention+" grr")
            if message.guild and message.guild.id in self.free_guilds and "vore" in message.content.split():
                await message.pin()
            if message.guild and self.bot.user in message.mentions:
                await self.bot.change_presence(activity=discord.Game(name=message.author.name))
            if message.guild and message.guild.id == commandutil.known_ids["aagshit"] and message.channel.id != commandutil.known_ids["aagshit_lawgs"]:
                for attachment in message.attachments:
                    await attachment.save(r"saved_attachments/{}".format(attachment.filename))
                    await self.bot.get_channel(commandutil.known_ids["aagshit_lawgs"]).send(r"Posted by {} in {}:".format(message.author.name,message.channel.mention),file=discord.File(r"saved_attachments/{}".format(attachment.filename)))
        if message.author.id in commandutil.known_ids["lilybots"] and "Hi makubot!!!!! I love you a lot!!!!" in message.content:
            await message.channel.send("Hi Lily! You're amazing and I love you so much!!!!")



    async def move_message_attempt(self,message:discord.Message, channel:discord.TextChannel, move_request_user:discord.Member):
        member_can_manage_messages = channel.permissions_for(move_request_user).manage_messages
        if member_can_manage_messages or move_request_user == message.author or move_request_user.id == self.bot.makusu.id:
            [await attachment.save(r"saved_attachments/{}".format(attachment.filename)) for attachment in message.attachments]
            attachment_files = [discord.File(r"saved_attachments/{}".format(attachment.filename)) for attachment in message.attachments]
            new_message_content = "{} has moved this here from {}. OP was {}.\n{}".format(move_request_user.mention,message.channel.mention,message.author.mention,message.content)
            await channel.send(new_message_content,files=attachment_files)
            await message.delete()
        else:
            await message.channel.send("Looks like you don't have the manage messages role and you're not OP. sorry.")

    async def on_message_delete(self,message):
        last_deleted_message[message.channel.id] = deletion_message = "{}:A message from {} has been deleted in {} of {} with {} attachment(s): {}".format(message.created_at,message.author.name,message.channel.name,message.channel.guild.name,len(message.attachments),message.content)
        with codecs.open("deletionlog.txt","a","utf-8") as f:
            f.write(deletion_message+"\n")
        if message.guild and message.channel.guild.id == commandutil.known_ids["aagshit"] and message.channel.id != commandutil.known_ids["aagshit_lawgs"]:
            await self.bot.get_channel(commandutil.known_ids["aagshit_lawgs"]).send(r"```{}```".format(deletion_message))

    async def on_message_edit(self,before,after):
        pass

    async def on_member_join(self,member:discord.Member):
        """Called when a member joins to tell them that Maku loves them (because they do love them) <3 """
        if member.guild.id in self.free_guilds:
            await member.guild.system_channel.send("Hi {}! Maku loves you! <333333".format(member.mention))


    async def on_reaction_add(self,reaction,user):
        """Called when a user adds a reaction to a message which is in my cache. Currently only looks for the "move message" emoji."""
        if reaction.emoji == move_emote:
            await reaction.message.channel.send(user.mention+" Move to which channel?")
            while True:
                message = await self.bot.wait_for('message',check=lambda m: m.author == user)
                if message.content.lower().strip() == "cancel":
                    await message.channel.send("Cancelled")
                    return
                try:
                    channel_id = int(re.match(r"<#([0-9]+)>$",message.content).group(1))
                    channel_to_move_to = self.bot.get_channel(channel_id)
                    if channel_to_move_to is None:
                        raise ValueError("Channel to move to is none")
                except (ValueError,AttributeError):
                    await message.channel.send("That doesn't look like a tagged channel, try again. (You do not need to readd the reaction. Say 'cancel' to cancel the move request.)")
                except TypeError:
                    await message.channel.send("Hmmm, that looks like a channel but I can't figure out what it is. It's already been logged for Maku to debug.")
                    logging.error("Couldn't figure out what channel "+str(channel_id)+" was.")
                else:
                    await self.move_message_attempt(reaction.message,channel_to_move_to,message.author)
                    return

    async def on_reaction_clear(self,message:discord.Message,reactions):
        pass
    async def on_member_remove(self,member:discord.Member):
        pass
    async def on_member_update(self,before,after):
        pass
    async def on_guild_join(self,guild:discord.Guild):
        pass
    async def on_guild_remove(self,guild:discord.Guild):
        pass
    async def on_guild_role_create(self,role:discord.Role):
        pass
    async def on_guild_emojis_update(self,guild:discord.Guild,before,after):
        pass
    async def on_member_ban(self,guild:discord.Guild,user):
        pass
    async def on_voice_state_update(self,member:discord.Member,before,after):
        pass
    async def on_group_join(self,channel,user):
        pass


async def post_picture(channel,folder_name):
    file_to_send_name = random.choice(os.listdir(folder_name))
    file_to_send = r"{}/{}".format(folder_name,file_to_send_name)
    await channel.send(file=discord.File(file_to_send))

class FavePictures:
    def __init__(self,bot):
        self.bot = bot
        for folder_name in os.listdir("picture_associations"):
            folder_command = commands.Command(folder_name,lambda cog_ref,ctx: post_picture(ctx.channel,r"picture_associations/{}".format(ctx.invoked_with)),brief="Post one of {}'s favorite pictures~".format(folder_name))
            folder_command.instance = self
            folder_command.module = self.__module__
            self.bot.add_command(folder_command)

class ReactionImages:
    def __init__(self,bot):
        self.bot = bot
        for folder_name in os.listdir("picture_reactions"):
            folder_command = commands.Command(folder_name,lambda cog_ref,ctx: post_picture(ctx.channel,r"picture_reactions/{}".format(ctx.invoked_with)),brief=folder_name)
            folder_command.instance = self
            folder_command.module = self.__module__
            self.bot.add_command(folder_command)

def setup(bot):
    logging.info("makucomands starting setup")
    bot.add_cog(MakuCommands(bot))
    bot.add_cog(FavePictures(bot))
    bot.add_cog(ReactionImages(bot))
    logging.info("makucommands ending setup")
