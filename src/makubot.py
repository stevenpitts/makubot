"""
Main module for makubot.
This module should never have to be reloaded.
All reloading should take place in makucommands and commandutil.
"""
import logging
import discord
import tempfile
import sys
from datetime import datetime
from discord.ext import commands
from pathlib import Path
import time
import psycopg2
from . import commandutil
import boto3

LOGGING_FORMAT = ("%(asctime)-15s %(levelname)s in %(funcName)s "
                  "at %(pathname)s:%(lineno)d: %(message)s")
logging.basicConfig(
    stream=sys.stderr, level=logging.INFO, format=LOGGING_FORMAT)

logger = logging.getLogger()

logger.info("\n\nEntering makubot.py\n\n")

DATABASE_CONNECT_MAX_RETRIES = 10

S3 = boto3.client("s3")


class MakuBot(commands.Bot):
    def __init__(self,
                 s3_bucket=False,
                 google_api_key=None,
                 db_host=None,
                 db_pass=None,
                 db_port=None,
                 db_user=None,
                 ):
        commands.Bot.__init__(self,
                              command_prefix=commands.when_mentioned,
                              case_insensitive=True,
                              owner_id=203285581004931072)
        logger.info("Bot entering setup")
        self.makusu = None
        self.shared = {}
        self.temp_dir_pointer = tempfile.TemporaryDirectory()
        self.shared["temp_dir"] = Path(self.temp_dir_pointer.name)
        self.shared["default_extensions"] = ["makucommands",
                                             "reminders",
                                             "picturecommands",
                                             "serverlogging",
                                             "movement",
                                             "evaluations",
                                             "listeners",
                                             "wikisearch",
                                             "ytsearch",
                                             "fun",
                                             "debugging",
                                             "rolegiver"
                                             ]
        self.s3_bucket = s3_bucket
        if self.s3_bucket:
            self.s3_bucket_location = S3.get_bucket_location(
                Bucket=self.s3_bucket
            )["LocationConstraint"]
        self.google_api_key = google_api_key
        self.db_host = db_host
        self.db_pass = db_pass
        self.db_port = db_port
        self.db_user = db_user
        self.loop.set_debug(True)

        for database_connect_attempt in range(DATABASE_CONNECT_MAX_RETRIES):
            try:
                self.db_connection = psycopg2.connect(
                    host=self.db_host,
                    password=self.db_pass,
                    port=self.db_port,
                    user=self.db_user,
                )
            except psycopg2.OperationalError:
                logger.info(
                    "Couldn't connect to mbdb, retrying in a few seconds")
                time.sleep(5)
                continue
            else:
                break
        else:
            raise psycopg2.OperationalError("Couldn't connect after retries")
        commandutil.backup_and_drop_all(self.db_connection, self.s3_bucket)
        commandutil.restore_db(self.s3_bucket)

        for extension in self.shared["default_extensions"]:
            self.load_extension(f"src.{extension}")

    async def on_ready(self):
        """
        Called when MakuBot has logged in and is ready to accept commands
        """
        self.makusu = await self.fetch_user(self.owner_id)
        logger.info(
            f"\n\n\nLogged in at {datetime.now()} as {self.user.name} "
            f"with ID {self.user.id}\n\n\n"
        )
        await self.change_presence(activity=discord.Game(
            name=r"Nao is being tsun to me :<"))
