import asyncio
import random

test_messages = r"""
mb.remindme 2s this should remind me in 2 seconds
mb.ping
mb.eval 2+2
mb.emojispam
mb.isgay
mb.bully
mb.yt hi
mb.fact
The following should only have ONE ping response:
mb.ping
mb.ping
mb.removehist 1
mb.whatis undertale
mb.choose one two three
mb.hey
mb.remindme 5s this one should be listed in list_commands
mb.listreminders
"""


async def send_tests(bot, channel):
    for test_message in test_messages:
        await channel.send(test_message)
        asyncio.sleep(1)
    move_test = await channel.send("This message will be moved")
    await channel.send(f"mb.move {move_test.id} {channel.id}")
    python_image_url = r"https://docs.python.org/3.7/_static/py.png"
    await channel.send(f"mb.addimage pythontest {python_image_url}")
    await channel.send(f"mb.addimage pythontest{int(random.random() * 100)} "
                       f"{python_image_url}")
    await channel.send(f"mb.aliasimage pythontest{int(random.random() * 100)} "
                       "pythontest")
