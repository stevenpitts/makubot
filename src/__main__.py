from . import makubot
import sys
import os
from pathlib import Path
import asyncio
import time
import threading

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

    token = os.environ['DISCORD_BOT_TOKEN']
    # Use local storage if S3_BUCKET isn't set in environment
    s3_bucket = os.environ.get('S3_BUCKET', None)
    google_api_key = os.environ.get('GOOGLE_API_KEY', None)

    makubot_bot = makubot.MakuBot(
        s3_bucket=s3_bucket,
        google_api_key=google_api_key
        )

    if "profile" in sys.argv:
        profile_thread = threading.Thread(
            target=profile_bot, args=[makubot_bot])
        profile_thread.start()
    makubot_bot.run(token)


if __name__ == "__main__":
    main()
