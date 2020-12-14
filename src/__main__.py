from . import runbot
import sys
import os
import asyncio
import time
import threading


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
    token = os.environ["DISCORD_BOT_TOKEN"]
    # Use local storage if S3_BUCKET isn't set in environment
    s3_bucket = os.environ.get("S3_BUCKET", None)
    google_api_key = os.environ.get("GOOGLE_API_KEY", None)
    db_host = os.environ["PGHOST"]
    db_pass = os.environ["PGPASSWORD"]
    db_port = os.environ["PGPORT"]
    db_user = os.environ["PGUSER"]
    db_name = os.environ["PGNAME"]

    makubot_bot = runbot.MakuBot(
        s3_bucket=s3_bucket,
        google_api_key=google_api_key,
        db_host=db_host,
        db_pass=db_pass,
        db_port=db_port,
        db_user=db_user,
        db_name=db_name,
    )

    if "profile" in sys.argv:
        profile_thread = threading.Thread(
            target=profile_bot, args=[makubot_bot])
        profile_thread.start()
    makubot_bot.run(token)


if __name__ == "__main__":
    main()
