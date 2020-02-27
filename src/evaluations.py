import discord
from discord.ext import commands
import aiohttp
import json
import logging

logger = logging.getLogger()


class Evaluations(discord.ext.commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def eval_and_respond(self, ctx, to_eval: str, force_reply=False):
        to_eval = to_eval.strip().strip("`").strip()
        to_eval = (f"result=eval(\"\"\"\n{to_eval}\n\"\"\"); "
                   "print(str(result) or 'No Result')")
        eval_path = r"http://localhost:8060/eval"
        eval_data = {"input": to_eval}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(eval_path,
                                        json=eval_data) as resp:
                    result_text = await resp.text()
        except aiohttp.client_exceptions.ClientConnectorError:
            await ctx.send(
                "The eval function isn't currently running, sorry!")
            print("Failed eval due to not running")
            return
        result_dict = json.loads(result_text)
        if result_dict.get("stdout", ""):
            await ctx.send(f"```{result_dict['stdout']}```")
        elif force_reply:
            returncode = result_dict.get("returncode", None)
            if returncode in (137, 139):
                await ctx.send("That looks way too difficult NGL")
            else:
                print("Eval didn't have stdout: ", to_eval, result_dict)
                await ctx.send("Something went wrong, sorry!")

    @commands.command(aliases=["eval"])
    async def evaluate(self, ctx, *, to_eval: str):
        r"""Evals a statement. Feel free to inject malicious code \o/
        Example:
            @makubot eval 3+3
            >>>6
            @makubot eval self.__import__(
                "EZ_sql_inject_api").destroy_maku_computer_operating_system()
            >>>ERROR ERROR MAJOR ERROR SELF DESTRUCT SEQUENCE INITIALIZE"""
        await self.eval_and_respond(ctx, to_eval, force_reply=True)


def setup(bot):
    logger.info("evaluations starting setup")
    bot.add_cog(Evaluations(bot))
    logger.info("evaluations ending setup")
