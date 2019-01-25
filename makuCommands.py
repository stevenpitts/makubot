import discord
from discord.ext import commands
import random
import sys
import asyncio
import traceback


move_emote = "\U0001f232"

def freereign():
    """Use as a decorator to restrict certain commands to free reign guilds"""
    async def predicate(ctx):
        return ctx.message.guild.id in ctx.bot.free_guilds
    return commands.check(predicate)


class MakuCommands():
    def __init__(self,bot):
        self.bot = bot
        self.bot.description = """
Hey there! I'm Makubot!
I'm a dumb bot made by a person who codes stuff.
I'm currently running Python {}.
I'm pretty barebones on any server that I wasn't explicitly made to support, sorry!
        """.format(".".join(map(str, sys.version_info[:3])))
        
    @commands.command()
    async def ping(self,ctx):
        """Get ready to get PONG'D"""
        await ctx.send("pong")
            
    @commands.command()
    @freereign()
    async def reload(self,ctx): 
        """Reloads my command cogs"""
        #https://gist.github.com/EvieePy/d78c061a4798ae81be9825468fe146be
        try:
            compile(open("makucommands.py", 'r').read() + '\n', "makucommands.py", 'exec')
        except Exception:
            await self.bot.makusu.send(traceback.format_exc())
        else:
            self.bot.unload_extension('makucommands')
            try:
                self.bot.load_extension('makucommands')
            except Exception:
                await self.bot.makusu.send("Dang, didn't notice the error, now can't reload. ",traceback.format_exc())
        
    @commands.command()
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
        self.bot.close()
        
    @commands.command()
    async def move(self,ctx,msg_id,channel_to_move_to:discord.TextChannel):
        """
        move <message_id> <channel_mention>: move a message from the current channel to the channel specified (I need special permissions for this!) You can also add the reaction \U0001f232 to automate this process."""
        try:
            message_to_move = await ctx.message.channel.get_message(msg_id)
        except discord.errors.HTTPException:
            await ctx.message.channel.send("That, uh, doesn't look like a valid message ID. Try again.")
        else:
            await self.bot.move_message_attempt(message_to_move,channel_to_move_to,ctx.message.author)
            
    @commands.command()
    @commands.is_owner()
    async def gowild(self,ctx):
        """Add the current guild as a gowild guild; I do a bit more on these. Only Maku can add guilds though :("""
        await self.bot.add_free_reign_guild(ctx.message.guild.id)
            
    async def on_member_join(self,member:discord.Member):
        """Called when a member joins to tell them that Maku loves them (because they do love them) <3 """
        if member.guild.id in self.bot.free_guilds:
            await member.guild.system_channel.send(member.mention+" Hi! Maku loves you! <333333")
        
        
    async def on_reaction_add(self,reaction,user):
        """Called when a user adds a reaction to a message which is in my cache. Currently only looks for the "move message" emoji."""
        if reaction.emoji == move_emote:
            await reaction.message.channel.send(user.mention+" Move to which channel?")
            self.bot.move_requests_pending[user] = reaction.message
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
        
    
def setup(bot):
    bot.add_cog(MakuCommands(bot))