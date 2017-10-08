import discord
from discord.ext import commands

class MakuCommands():
	def __init__(self,bot):
		self.bot = bot
	@commands.command()
	async def ping(self):
		await self.bot.say("pong")
	@commands.command()
	async def fact(self):
		raise NotImplementedError
	@commands.command()
	async def refresh(self):
		await self.bot.refresh()
def setup(bot):
	bot.add_cog(MakuCommands(bot))
	