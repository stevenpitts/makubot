from . import makubot
import sys
import os
from pathlib import Path
import asyncio
import time
import threading
try:
    from . import tokens
except ImportError:
    if not os.path.isfile(str(Path(__file__).parent / 'tokens.py')):
        with open(str(Path(__file__).parent / 'tokens.py'), 'w') as f:
            f.write('realToken = None\ntestToken = None\ngoogleAPI = None\n')
    from . import tokens
SCRIPT_DIR = Path(__file__).parent
PARENT_DIR = SCRIPT_DIR.parent
DATA_DIR = PARENT_DIR / 'data'


def profile_bot(bot):
    while True:
        time.sleep(1)
        current_task = asyncio.current_task(loop=bot.loop)
        if current_task:
            print("Current task: ")
            current_task.print_stack()
            print("\n")
        print("All tasks: ")
        for task in asyncio.all_tasks(loop=bot.loop):
            task.print_stack(limit=3)
        print("\n\n\n\n")


def main():
    os.makedirs(str(DATA_DIR / 'pictures'), exist_ok=True)

    default_text = {'makubot.log': '',
                    'data.json': '{}',
                    'deletion_log.txt': ''}
    for filename, to_write in default_text.items():
        if not os.path.isfile(str(DATA_DIR / filename)):
            with open(str(DATA_DIR / filename), 'w') as f:
                f.write(to_write)

    if bool('test' in sys.argv) == bool('real' in sys.argv):
        raise ValueError('You must pass only one of "test" or "real" in args.')
    if 'test' in sys.argv and tokens.testToken is None:
        raise ValueError('You must replace testToken in tokens.py '
                         'with your own test token first.')
    elif 'real' in sys.argv and tokens.realToken is None:
        raise ValueError('You must replace realToken in tokens.py '
                         'with your own token first.')
    token = tokens.testToken if 'test' in sys.argv else tokens.realToken
    # Use local storage if s3_bucket isn't set in environment
    s3_bucket = os.environ.get('S3_BUCKET', None)
    makubot_bot = makubot.MakuBot(s3_bucket=s3_bucket)
    if "profile" in sys.argv:
        profile_thread = threading.Thread(
            target=profile_bot, args=[makubot_bot])
        profile_thread.start()
    makubot_bot.run(token)


if __name__ == "__main__":
    main()
