import discord
from discord.ext import commands
import random
import conf
import asyncio
from conf import *
import imp



class MakuBot(commands.Bot):
	#So, bot is a subclass of discord.Client, and this is a subclass of bot.
	
	def __init__(self,command_prefix='?',description="Makusu's bot"):
		commands.Bot.__init__(self,command_prefix=command_prefix,description=description)
		self.startupExtensions = ["makuCommands",]

	def printDebugInfo(self):
		print("Current servers:")
		for server in self.servers:
			print("   "+str(server))
		#for server in self.servers: print(str(server))
		print("Messages:")
		for message in self.messages:
			print("   "+message)
		#for message in self.messages: print(str(message))
		#print("Application info:")
		#print(str(list(self.application_info())))
		#for item in self.application_info():
		#	print(item)
	async def makePlaying(self,gameName):
		await self.change_presence(game=discord.Game(name=gameName))
	async def on_ready(self):
		"""Triggered when bot connects. Event."""
		print('Logged in as')
		print(self.user.name)
		print(self.user.id)
		print('------')
		await self.change_presence(game=discord.Game(name="Dick"))
		for extension in self.startupExtensions:
			try:
				self.load_extension(extension)
			except Exception as e:
				exc = '{}: {}'.format(type(e).__name__, e)
				print('Failed to load extension {}\n{}'.format(extension, exc))
		self.printDebugInfo()
		#self.command_prefix = self.user.mention
			
	async def on_message(self,message : discord.Message):
		if message.author != self.user:
			#print("on_message called. Author: "+message.author.name+". Message: "+message.content)
			if message.mention_everyone:
				await self.send_message(message.channel,content=message.author.mention+" did you just do the thing.")
			if "vore" in message.content:
				#await bot.add_reaction(message,364133071521447939
				await self.pin_message(message)
			if (message.author.bot or (message.author.name.lower() == "smugbot")):
				await self.send_message(message.channel,content="Wow, apparently I'm not a good enough bot for you guys")
			if self.user in message.mentions or message.server.me in message.mentions:
				await self.makePlaying(message.author.name)
		await bot.process_commands(message)
		#That's for some thing with the API, it's weird but don't remove it
	async def on_message_delete(self,message):
		print(getMessageString(message))
		await self.process_commands(message)
		#That's for some thing with the API, it's weird but don't remove it\
	async def on_message_edit(self,before,after):
		probMisspelledWord = getOriginalWord(before.content,after.content)
		if not probMisspelledWord is None:
			await self.send_message(before.channel,content="LOL nice going there with your '"+probMisspelledWord+"'")
	
	async def refresh(self):
		for extension in self.startupExtensions:
			self.unload_extension(extension)
			self.load_extension(extension)
		
	
bot = MakuBot()



def getMessageString(message):
	return str(message.timestamp)+" "+message.author.name+" in "+str(message.channel)+"   "+message.content
def getOriginalWord(before,after):
	"""Called for edited messages. Args of "Lol taht was funny" and "Lol that was funny" should return "taht" """
	beforeArray = before.split()
	afterArray = after.split()
	for word in beforeArray:
		if not (word in afterArray):
			return word

#add_reaction
#Fact command that makes bot print the first sentence of a random wikipedia article
#Make it correct people's grammar