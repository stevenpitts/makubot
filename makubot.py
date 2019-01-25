import discord
from discord.ext import commands
import random
import asyncio
import time
import tokens
from tokens import *
import re
import sys

#TODO switch superclass from bot to client cuz bot is stupid
#Actually maybe don't?





class MakuBot(commands.Bot):
    #So, bot is a subclass of discord.Client, and this is a subclass of bot.

    def __init__(self,correct_typos=False,log_to_file=True):
        self.correct_typos = correct_typos
        self.log_to_file = log_to_file
        commands.Bot.__init__(self,command_prefix=commands.when_mentioned,description="Makusu's bot",case_insensitive=True,owner_id=203285581004931072)
        self.move_requests_pending = {}
        self.lastTime = time.time()
        self.makusu = None
        self.free_guilds = []

    def printDebugInfo(self):
        print("Current servers: ",{guild.name:guild.id for guild in self.guilds})
        

    async def on_ready(self):
        """Triggered when bot connects. Event."""
        print('Logged in as ',self.user.name,' with ID ',self.user.id)
        self.makusu = await self.get_user_info(self.owner_id)
        await self.change_presence(activity=discord.Game(name=r"SmugBot is being tsun to me :<"))
        self.load_extension('makucommands')
        await self.load_free_reign_guilds()
        self.printDebugInfo()

    async def on_message(self,message : discord.Message):
        if message.author != self.user:
             if message.guild.id in self.free_guilds and message.mention_everyone:
                 await message.channel.send(message.author.mention+" grr")
             if message.guild.id in self.free_guilds and "vore" in message.content.split():
                 await message.pin()
             if self.user in message.mentions:
                 await self.change_presence(activity=discord.Game(name=message.author.name))
             if "maku" in message.content.lower() and r"@ma" not in message.content.lower() and "makubot" not in message.content.lower():
                 await message.channel.send(r"<@!203285581004931072>")
             
             if message.author in self.move_requests_pending:
                 try:
                     channel_id = int(message.content.strip().replace("<","").replace("#","").replace(">",""))
                     channel_to_move_to = self.get_channel(channel_id)
                 except ValueError:
                     await message.channel.send("That doesn't look like a tagged channel, try again. (You do not need to readd the reaction. Type \"cancel\" to cancel the move request.)")
                 except TypeError:
                    await message.channel.send("Hmmm, that looks like a channel but I can't figure out what it is. It's already been logged for Maku to debug.")
                    print("Couldn't figure out what channel "+str(channel_id)+" was.")
                 else:
                    message_to_move = self.move_requests_pending.pop(message.author)
                    asyncio.get_event_loop().create_task(self.move_message_attempt(message_to_move,channel_to_move_to,message.author))
                     

        await self.process_commands(message) #That's for some thing with the API, it's weird but don't remove it
        
    async def on_message_delete(self,message):
        deletion_message = "A user has deleted a message. "+str(getMessageString(message))
        for attachment in message.attachments:
            try:
                await attachment.save(r"saved_attachments\attch"+str(random.randint(0,100000000)))
            except discord.errors.Forbidden:
                deletion_message += "Could not save attachment from {} in {} due to it being deleted".format(message.author,message.channel)
        if self.log_to_file:
            with open("mylog01.txt","a") as f:
                f.write(deletion_message+"\n")
        else:
            print(deletion_message)
        await self.process_commands(message)
        #That's for some thing with the API, it's weird but don't remove it
    async def on_message_edit(self,before,after):
        if self.correct_typos:
            probMisspelledWord = getOriginalWord(before.content,after.content)
            if not probMisspelledWord is None:
                if (time.time() - self.lastTime > 100):
                    await before.channel.send("LOL nice going there with your '"+probMisspelledWord+"'")
                    self.lastTime = time.time()
                
    
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
        
    async def load_free_reign_guilds(self):
        self.free_guilds = []
        with open('free_reign.txt','r') as f:
            for line in f:
                try:
                    self.free_guilds.append(int(line))
                except ValueError:
                    pass
    async def save_free_reign_guilds(self):
        with open('free_reign.txt','w') as f:
            for guild_id in self.free_guilds:
                f.write("{}\n".format(guild_id))
    async def add_free_reign_guild(self,guild_id):
        self.free_guilds.append(guild_id)
        with open('free_reign.txt','a') as f:
            f.write("{}\n".format(guild_id))
    async def remove_free_reign_guild(self,guild_id):
        self.free_guilds.remove(guild_id)
        await self.save_free_reign_guilds()
    
        
makubot = MakuBot()
def getMessageString(message):
    return str(message.created_at)+" "+message.author.name+" in "+str(message.channel)+"   "+message.content
def getOriginalWord(before,after):
    """Called for edited messages. Args of "Lol taht was funny" and "Lol that was funny" should return "taht" """
    return [word for word in before.split() if word not in after.split()][0]

def main():
	makubot.run(makubotToken)

if __name__=="__main__":
    main()


#add_reaction
#Fact command that makes bot print the first sentence of a random wikipedia article
