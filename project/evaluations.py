import discord
from discord.ext import commands
import aiohttp
from pathlib import Path
import json
import logging


SCRIPT_DIR = Path(__file__).parent
PARENT_DIR = SCRIPT_DIR.parent
DATA_DIR = PARENT_DIR / 'data'


class Evaluations(discord.ext.commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=["eval"])
    async def evaluate(self, ctx, *, to_eval: str):
        r'''Evals a statement. Feel free to inject malicious code \o/
        Example:
            @makubot eval 3+3
            >>>6
            @makubot eval self.__import__(
                'EZ_sql_inject_api').destroy_maku_computer_operating_system()
            >>>ERROR ERROR MAJOR ERROR SELF DESTRUCT SEQUENCE INITIALIZE'''
        to_eval = to_eval.strip().strip('`').strip()
        to_eval = (f"result=eval(\"\"\"\n{to_eval}\n\"\"\"); "
                   "print(result or 'No Result')")
        eval_path = r"http://0.0.0.0:8060/eval"
        eval_data = {"input": to_eval}
        async with aiohttp.ClientSession() as session:
            async with session.post(eval_path, json=eval_data) as resp:
                result_text = await resp.text()
        result_dict = json.loads(result_text)
        if result_dict.get("stdout", ""):
            await ctx.send(f"```{result_dict['stdout']}```")
        else:
            returncode = result_dict.get("returncode", None)
            if returncode in (137, 139):
                await ctx.send("That looks way too difficult NGL")
            else:
                print("Eval didn't have stdout: ", to_eval, result_dict)
                await ctx.send("Something went wrong, sorry!")


def setup(bot):
    logging.info('evaluations starting setup')
    bot.add_cog(Evaluations(bot))
    logging.info('evaluations ending setup')
