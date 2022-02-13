from . import runbot
import os

def main():
    token = os.environ["DISCORD_BOT_TOKEN"]
    dev_id_string = os.environ["DEVELOPERS"].split(" ")
    dev_ids = []
    for id in dev_id_string: dev_ids.append(int(id))
    makubot_bot = runbot.MakuBot(
        s3_bucket=os.environ.get("S3_BUCKET", None),
        google_api_key=os.environ.get("GOOGLE_API_KEY", None),
        db_host=os.environ["PGHOST"],
        db_pass=os.environ["PGPASSWORD"],
        db_port=os.environ["PGPORT"],
        db_user=os.environ["PGUSER"],
        db_name=os.environ["PGNAME"],
        bot_owner=int(os.environ["OWNER"]),
        bot_devs=dev_ids,
    )
    makubot_bot.run(token)


if __name__ == "__main__":
    main()
