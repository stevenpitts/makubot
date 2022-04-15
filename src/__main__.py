from . import runbot
import os


def main():
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

    makubot_bot.run(token)


if __name__ == "__main__":
    main()
