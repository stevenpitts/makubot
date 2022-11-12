from . import runbot
import asyncio
import os


async def main():
    token = os.environ["DISCORD_BOT_TOKEN"]

    makubot_bot = runbot.MakuBot(
        s3_bucket=os.environ.get("S3_BUCKET", None),
        google_api_key=os.environ.get("GOOGLE_API_KEY", None),
        db_host=os.environ["PGHOST"],
        db_pass=os.environ["PGPASSWORD"],
        db_port=os.environ["PGPORT"],
        db_user=os.environ["PGUSER"],
        db_name=os.environ["PGNAME"],
    )

    async with makubot_bot:
        await makubot_bot.start(token)


if __name__ == "__main__":
    asyncio.run(main())
