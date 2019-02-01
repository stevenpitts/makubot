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

youtube = build('youtube', 'v3',developerKey=googleAPI)

def aeval(s,return_error=True):
    temp_string_io = StringIO()
    aeval_interpreter = asteval.Interpreter(writer=temp_string_io,err_writer=temp_string_io)
    result = aeval_interpreter(s) or "No result found."
    return "```{}```\nResult: {}".format(temp_string_io.getvalue(),result)
            
def youtube_search(search_term):
    search_response = youtube.search().list(q=search_term,part='id,snippet',maxResults=10).execute()
    for search_result in search_response.get('items', []):
        if search_result['id']['kind'] == 'youtube#video':
            return search_result['id']['videoId']




move_emote = "\U0001f232"
    





class MakuCommands():
    def __init__(self,bot,correct_typos=False,log_to_file=True):
        self.bot = bot
        self.bot.description = """
Hey there! I'm Makubot!
I'm a dumb bot made by a person who codes stuff.
I'm currently running Python {}.
I'm pretty barebones on any server that I wasn't explicitly made to support, sorry!
I can do some cool things like basic math if you tag me with a mathematical expression!
Also you can just ask Makusu2#2222 cuz they're never too busy to make a new friend <3
        """.format(".".join(map(str, sys.version_info[:3])))
        self.correct_typos = correct_typos
        self.log_to_file = log_to_file
        self.move_requests_pending = {}
        self.free_guilds = set()
        asyncio.get_event_loop().create_task(self.load_free_reign_guilds())
            
    async def send_maku_message(self,msg):
        for i in range(0, len(msg), 1500):
            await self.bot.makusu.send(msg[i:i+1500])
        
    async def send_reminder(self,channel,reminder_target:discord.member.Member,seconds:int,reminder_message:str):
        await asyncio.sleep(seconds)
        await channel.send("{}, you have a reminder from {} seconds ago:\n{}".format(reminder_target.mention,seconds,reminder_message))
    
    @commands.command()
    @commands.is_owner()
    async def getstatus(self,ctx):
        await send_maku_message("Current servers: ",{guild.name:guild.id for guild in self.bot.guilds})
        
    @commands.command()
    async def ping(self,ctx):
        """
        Pong was the first commercially successful video game, which helped to establish the video game industry along with the first home console, the Magnavox Odyssey. Soon after its release, several companies began producing games that copied its gameplay, and eventually released new types of games. As a result, Atari encouraged its staff to produce more innovative games. The company released several sequels which built upon the original's gameplay by adding new features. During the 1975 Christmas season, Atari released a home version of Pong exclusively through Sears retail stores. It also was a commercial success and led to numerous copies. The game has been remade on numerous home and portable platforms following its release. Pong is part of the permanent collection of the Smithsonian Institution in Washington, D.C. due to its cultural impact.
        """
        time_passed = (datetime.datetime.utcnow()-ctx.message.created_at).microseconds/1000
        await ctx.send("pong! It took me {} milliseconds to get the ping.".format(time_passed))
            
    
    @commands.command(aliases=["are you free","areyoufree?","are you free?",])
    async def areyoufree(self,ctx):
        """If I have free reign I'll tell you"""
        if ctx.guild.id in self.free_guilds:
            await ctx.send("Yes, I am free")
        else:
            await ctx.send("This is not a free reign guild.")
        
    @commands.command(aliases=["emoji spam",])
    async def emojispam(self,ctx):
        """Prepare to be spammed by the greatest emojis you've ever seen"""
        emoji_gen = iter(sorted(self.bot.emojis,key=lambda *args: random.random()))
        for emoji_to_add in emoji_gen:
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
    async def move(self,ctx,msg_id,channel_to_move_to:discord.TextChannel):
        """move <message_id> <channel_mention>: move a message from the current channel to the channel specified (I need special permissions for this!) You can also add the reaction \U0001f232 to automate this process."""
        try:
            message_to_move = await ctx.message.channel.get_message(msg_id)
        except discord.errors.HTTPException:
            await ctx.message.channel.send("That, uh, doesn't look like a valid message ID. Try again.")
        else:
            await self.move_message_attempt(message_to_move,channel_to_move_to,ctx.message.author)
            
    @commands.command(aliases=["is gay",])
    async def isgay(self,ctx):
        """Tells me I'm gay (CAUTION: May mirror the attack at the sender)"""
        await ctx.send("No u")
        
    @commands.command()
    async def bully(self,ctx):
        """Bullies me :("""
        if ctx.guild.get_member(self.bot.makusu.id) is not None:
            await ctx.send("{} HELP I'M BEING BULLIED ;a;".format(self.bot.makusu.mention))
        else:
            await ctx.send("M-makusu? W-where are you? Help!!!!")
            
    @commands.command(aliases=["hug me",])
    async def hugme(self,ctx):
        """Hugs you <3"""
        await ctx.send(r"*Hugs you* {}".format(ctx.message.author.mention))
            
    @commands.command(aliases=["go wild",])
    @commands.is_owner()
    async def gowild(self,ctx):
        """Add the current guild as a gowild guild; I do a bit more on these. Only Maku can add guilds though :("""
        if ctx.message.guild:
            await self.add_free_reign_guild(ctx.message.guild.id)
            await ctx.send("Ayaya~")
    
    @commands.command(aliases=["youtube",])
    async def yt(self,ctx,*,search_term:str):
        """Post a YouTube video based on a search phrase!"""
        search_result = youtube_search(search_term)
        if search_result is None:
            await ctx.send("Sowwy, I can't find it :(")
        else:
            await ctx.send(r"https://www.youtube.com/watch?v={}".format(search_result))
        
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
            astevald = aeval(to_eval)
            await ctx.send(astevald)
        except AttributeError:
            print("Couldn't get a match on {}. Weird.".format(ctx.message.content))
    
    @commands.command(aliases=["what was that","whatwasthat?","what was that?"])
    async def whatwasthat(self,ctx):
        """Tells you what that fleeting message was"""
        last_thing = last_deleted_message.pop(ctx.channel.id,None)
        if last_thing is None:
            await ctx.send("I can't find anything, sorry :(")
        else:
            await ctx.send(last_thing)
            
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
        timereg = re.compile(r"((?P<days>\d*)d)?((?P<hours>\d*)h)?((?P<minutes>\d*)m)?((?P<seconds>\d*)s)?")
        matches = re.search(timereg,timelength)
        if matches:
            days,hours,minutes,seconds = [int(val) if val else 0 for val in matches.group("days","hours","minutes","seconds")]
            total_seconds = days*86400 + hours*3600 + minutes*60 + seconds
            await ctx.send("Coolio I'll remind you in {} seconds".format(total_seconds))
            asyncio.get_event_loop().create_task(
            self.send_reminder(ctx.channel,ctx.message.author,total_seconds,reminder))
        else:
            await ctx.send("Hmm, that doesn't look valid. Ask for help if you need it!")
            
    @commands.command()
    async def cancel(self,ctx):
        """Cancel pending commands"""
        if self.move_requests_pending.pop(ctx.message.author,None):
            await ctx.send("Cancelled move command.")
            
            
            
            
            
            
            
    async def load_free_reign_guilds(self):
        with open('free_reign.txt','r') as f:
            self.free_guilds = set([int(element) for element in re.search('\{(.*)\}',f.readlines()[0].strip()).group(1).split(',') if element])
            
    async def save_free_reign_guilds(self):
        with open('free_reign.txt','w') as f:
            f.write(str(self.free_guilds))
            
    async def add_free_reign_guild(self,guild_id):
        self.free_guilds.add(guild_id)
        await self.save_free_reign_guilds()
        
    async def remove_free_reign_guild(self,guild_id):
        self.free_guilds.remove(guild_id)
        await self.save_free_reign_guilds()
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
    async def on_command_error(self,ctx,e:discord.ext.commands.errors.CommandError):
        if isinstance(e,discord.ext.commands.errors.CommandNotFound):
            astevald = aeval(ctx.message.content.replace(self.bot.user.mention,"").strip(),return_error=False)
            if astevald:
                await ctx.send(astevald)
        elif isinstance(e,discord.ext.commands.errors.NotOwner):
            await ctx.send("Sorry, only Maku can use that command :(")
        elif isinstance(e,discord.ext.commands.errors.CheckFailure):
            await ctx.send("Hmmm, there was a check failure but it wasn't accounted for. Maku did a mistake :(")
        else:
            await self.send_maku_message(r'```'+''.join(traceback.format_exception(type(e), e, e.__traceback__))+r'```')
    async def on_error(self,ctx,e):
        await self.send_maku_message(r'```'+''.join(traceback.format_exception(type(e), e, e.__traceback__))+r'```')
        
    
    async def on_message(self,message : discord.Message):
        if message.author != self.bot.user:
            if message.guild:
                if message.guild.id in self.free_guilds and message.mention_everyone:
                    await message.channel.send(message.author.mention+" grr")
                if message.guild.id in self.free_guilds and "vore" in message.content.split():
                    await message.pin()
                if self.bot.user in message.mentions:
                    await self.bot.change_presence(activity=discord.Game(name=message.author.name))
                if message.author in self.move_requests_pending:
                    try:
                        channel_id = int(message.content.strip().replace("<","").replace("#","").replace(">",""))
                        channel_to_move_to = self.bot.get_channel(channel_id)
                    except ValueError:
                        await message.channel.send("That doesn't look like a tagged channel, try again. (You do not need to readd the reaction. Use the 'cancel' command to cancel the move request.)")
                    except TypeError:
                        await message.channel.send("Hmmm, that looks like a channel but I can't figure out what it is. It's already been logged for Maku to debug.")
                        print("Couldn't figure out what channel "+str(channel_id)+" was.")
                    else:
                        message_to_move = self.move_requests_pending.pop(message.author)
                        asyncio.get_event_loop().create_task(self.move_message_attempt(message_to_move,channel_to_move_to,message.author))
                
    
    async def move_message_attempt(self,message:discord.Message, channel:discord.TextChannel, move_request_user:discord.member.Member):
        member_can_manage_messages = channel.permissions_for(move_request_user).manage_messages
        if member_can_manage_messages or move_request_user == message.author:
            if message.attachments:
                await message.channel.send("That guy has attachments which'd be deleted. Maku is adding support for that soon.")
            else:
                new_message_content = "{} has moved this here from {}. OP was {}.\n{}".format(move_request_user.mention,message.channel.mention,message.author.mention,message.content)
                await channel.send(new_message_content)
                await message.delete()
        else:
            await message.channel.send("Looks like you don't have the manage messages role and you're not OP. sorry.")
            
    async def on_message_delete(self,message):
        last_deleted_message[message.channel.id] = "From {}: {}".format(message.author.name,message.content)
        deletion_message = "A user has deleted a message. "+str(message.created_at)+" "+message.author.name+" in "+str(message.channel)+"   "+message.content
        for attachment in message.attachments:
            try:
                await attachment.save(r"saved_attachments\attch"+str(random.randint(0,100000000)))
            except discord.errors.Forbidden:
                deletion_message += "Could not save attachment from {} in {} due to it being deleted".format(message.author,message.channel)
        if self.log_to_file:
            with open("mylog01.txt","a") as f:
                for word in deletion_message.split():
                    try:
                        f.write(word+" ")
                    except UnicodeEncodeError:
                        f.write("?!?!?!"+" ")
                f.write("\n")
        else:
            print(deletion_message)
            
    async def on_message_edit(self,before,after):
        pass
                
    async def on_member_join(self,member:discord.Member):
        """Called when a member joins to tell them that Maku loves them (because they do love them) <3 """
        if member.guild.id in self.free_guilds:
            await member.guild.system_channel.send(member.mention+" Hi! Maku loves you! <333333")
        
        
    async def on_reaction_add(self,reaction,user):
        """Called when a user adds a reaction to a message which is in my cache. Currently only looks for the "move message" emoji."""
        if reaction.emoji == move_emote:
            await reaction.message.channel.send(user.mention+" Move to which channel?")
            self.move_requests_pending[user] = reaction.message
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
        
class FavePictures:
    def __init__(self,bot):
        self.bot = bot
        for folder_name in os.listdir("picture_associations"):
            folder_command = commands.Command(folder_name,lambda thing,ctx: thing.post_picture(ctx.channel,ctx.invoked_with,parent_dir="picture_associations"),brief="Post one of {}'s favorite pictures~".format(folder_name))
            folder_command.instance = self
            folder_command.module = self.__module__
            self.bot.add_command(folder_command)
        
    async def post_picture(self,channel,folder_name,parent_dir="picture_associations"):
        file_to_send = r"{}\{}\{}".format(parent_dir,folder_name,random.choice(os.listdir(r"{}\{}".format(parent_dir,folder_name))))
        await channel.send(file=discord.File(file_to_send))
class ReactionImages:
    def __init__(self,bot):
        self.bot = bot
        for folder_name in os.listdir("picture_reactions"):
            folder_command = commands.Command(folder_name,lambda thing,ctx: thing.post_picture(ctx.channel,ctx.invoked_with,parent_dir="picture_reactions"),brief=folder_name)
            folder_command.instance = self
            folder_command.module = self.__module__
            self.bot.add_command(folder_command)
        
    async def post_picture(self,channel,folder_name,parent_dir="picture_reactions"):
        file_to_send = r"{}\{}\{}".format(parent_dir,folder_name,random.choice(os.listdir(r"{}\{}".format(parent_dir,folder_name))))
        await channel.send(file=discord.File(file_to_send))
    
def setup(bot):
    bot.add_cog(MakuCommands(bot))
    bot.add_cog(FavePictures(bot))
    bot.add_cog(ReactionImages(bot))
    
    
    

#Fact command that makes bot print the first sentence of a random wikipedia article