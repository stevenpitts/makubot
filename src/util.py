import traceback
import itertools
import logging
from datetime import datetime
import urllib
import aiohttp
import subprocess
from psycopg2.extras import RealDictCursor
import boto3
import botocore
import time
import discord
import os
import psutil

logger = logging.getLogger()

S3 = boto3.client("s3")


def improve_url(url):
    return url.replace(" ", "+")


def extract_args_setting(args, setting_prefix="NUMVOTES"):
    for arg in args:
        if not arg.startswith(f"{setting_prefix}="):
            continue
        remainder = arg[len(setting_prefix)+1:]
        try:
            other_args = [
                other_arg for other_arg in args if other_arg != arg]
            return other_args, int(remainder)
        except ValueError:
            continue  # Silently fail
    return args, None


def fnlog(func):
    # Logger that logs inputs, outputs, and time.
    def inner(*args, **kwargs):
        name_part = func.__name__
        args_reprd = ", ".join([repr(arg) for arg in args])
        kwargs_reprd = ", ".join([
            f"{kwarg}={repr(val)}" for kwarg, val in kwargs.items()])
        parts = [args_reprd, kwargs_reprd]
        joined_parts = ", ".join([part for part in parts if part])
        arg_part = f"({joined_parts})"
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
        except Exception:
            end_time = time.time()
            time_part = f"{end_time-start_time:.4f} seconds"
            logger.exception(
                f"{name_part}{arg_part} raised exception (took {time_part})")
            raise
        else:
            end_time = time.time()
            time_part = f"{end_time-start_time:.4f} seconds"
            logger.info(
                f"{name_part}{arg_part} -> {result} (took {time_part})")
            return result
    return inner


def url_from_s3_key(s3_bucket,
                    s3_bucket_location,
                    s3_key,
                    validate=False,
                    improve=False):
    url = (f"https://{s3_bucket}.s3.{s3_bucket_location}"
           f".amazonaws.com/{s3_key}")
    if improve:
        url = improve_url(url)
    if validate:
        # Raise HTTPError if url 404s or whatever
        try:
            urllib.request.urlopen(url)
        except urllib.error.HTTPError as e:
            logger.error(f"URL {url} failed due to {e.code} {e.reason}")
            raise
    return url


def s3_keys_hashes(bucket, prefix="/", delimiter="/", start_after=""):
    s3_paginator = boto3.client("s3").get_paginator("list_objects_v2")
    prefix = prefix[1:] if prefix.startswith(delimiter) else prefix
    start_after = ((start_after or prefix) if prefix.endswith(delimiter)
                   else start_after)
    keys = []
    hashes = []
    for page in s3_paginator.paginate(Bucket=bucket,
                                      Prefix=prefix,
                                      StartAfter=start_after):
        for content in page.get("Contents", ()):
            keys.append(content["Key"])
            hashes.append(content["ETag"][1:-1])
    return keys, hashes


def s3_keys(bucket, prefix="/", delimiter="/", start_after=""):
    return s3_keys_hashes(bucket, prefix, delimiter, start_after)[0]


def s3_hashes(bucket, prefix="/", delimiter="/", start_after=""):
    return s3_keys_hashes(bucket, prefix, delimiter, start_after)[1]


def get_most_recent_backup_key(s3_bucket):
    backup_keys = s3_keys(s3_bucket, prefix="/backups")
    if not backup_keys:
        logger.info("No backups were present when db restore was attempted")
        return
    keys_by_date = sorted(backup_keys, reverse=True)
    return keys_by_date[0]


def get_num_tables(db_connection):
    cursor = db_connection.cursor(cursor_factory=RealDictCursor)
    cursor.execute(
        """
        SELECT COUNT(*) FROM pg_stat_user_tables;
        """
    )
    results = cursor.fetchall()
    num_tables_result = results[0]["count"]
    num_tables = int(num_tables_result)
    return num_tables


def drop_all_tables(db_connection):
    cursor = db_connection.cursor()
    cursor.execute(
        """
        DROP SCHEMA public CASCADE;
        CREATE SCHEMA public;
        GRANT ALL ON SCHEMA public TO postgres;
        GRANT ALL ON SCHEMA public TO public;
        COMMENT ON SCHEMA public IS 'standard public schema';
        """
    )
    db_connection.commit()


def backup_and_drop_all(db_connection, s3_bucket):
    num_tables = get_num_tables(db_connection)
    logger.info(f"Started with {num_tables} tables")
    if num_tables:
        logger.info("Backing up existing database")
        backup_db(s3_bucket)
        logger.info("Backed up existing database")
    logger.info("Dropping all tables")
    drop_all_tables(db_connection)
    logger.info("Dropped all tables")


def restore_db(s3_bucket, most_recent_key=None):
    if most_recent_key is None:
        most_recent_key = get_most_recent_backup_key(s3_bucket)
    if most_recent_key is None:
        return  # No backups present
    logger.info(f"Restoring most recent key: {most_recent_key}")
    backup_location = f"s3://{s3_bucket}/{most_recent_key}"
    file_location = f"/tmp/{most_recent_key}"
    logger.info(f"Restoring {backup_location}")
    cmd = (f"aws s3 cp {backup_location} {file_location} "
           f"&& psql -f {file_location} && rm {file_location}")
    logger.info(f"Preparing to run {cmd}")
    try:
        subprocess.run(
            cmd, shell=True, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        logger.info(f"Failed backup output: {e.stdout}")
        logger.error(
            f"Backup failed with exit code {e.returncode} and err {e.stderr}."
        )
        raise
    logger.info("Successfully restored database")


def backup_db(s3_bucket):
    now_formatted = datetime.now().strftime("%Y.%m.%d.%H.%M.%S")
    backups_dir = f"s3://{s3_bucket}/backups"
    backup_location = f"{backups_dir}/{now_formatted}.pgdump"
    logger.info(f"Backing up database to {backup_location}")

    cmd = f"pg_dump | aws s3 cp - {backup_location}"
    try:
        subprocess.run(
            cmd, shell=True, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        logger.info(f"Failed backup output: {e.stdout}")
        logger.error(
            f"Backup failed with exit code {e.returncode} and err {e.stderr}."
        )
        raise


def s3_object_exists(s3_bucket, key):
    try:
        S3.head_object(Bucket=s3_bucket,
                       Key=key)
    except botocore.exceptions.ClientError:
        return False
    else:
        return True


def get_formatted_traceback(e):
    return "".join(traceback.format_exception(type(e), e, e.__traceback__))


@fnlog
def get_nonconflicting_filename(candidate_filename: str, existing_keys=None):
    existing_keys = {key.split("/")[-1] for key in existing_keys}
    if candidate_filename not in existing_keys:
        return candidate_filename
    try:
        filename_prefix, filename_suffix = candidate_filename.split(".", 1)
    except ValueError:
        raise("Filename was not valid (needs prefix and suffix")
    for addition in itertools.count():
        candidate_filename = f"{filename_prefix}{addition}.{filename_suffix}"
        if candidate_filename not in existing_keys:
            return candidate_filename
    raise AssertionError("Shouldn't ever get here")


def readable_timedelta(old, new=None):
    new = new or datetime.now()
    return str(new - old).split(".")[0]


async def clean(ctx, s):
    converter = discord.ext.commands.converter.clean_content()
    return await converter.convert(ctx, s)


async def url_media_type(url):
    async with aiohttp.request("HEAD", url) as response:
        return response.content_type


async def url_is_image(url):
    media_type = await url_media_type(url)
    return media_type.split("/")[0].lower() == "image"


def db_size(db_connection):
    cursor = db_connection.cursor()
    cursor.execute(
        """
        SELECT pg_size_pretty(pg_database_size(current_database()));
        """
    )
    result = cursor.fetchall()
    return result[0][0]


def hardware_usage():
    process = psutil.Process(os.getpid())
    with process.oneshot():
        return (
            f"{process.cpu_percent():.2f}% cpu, "
            f"{process.memory_percent():.2f}% RAM"
        )


async def displaytxt(ctx, text: str, blockify=False):
    block_size = 500
    surrounder = "```" if blockify else ""
    button_emojis = left_arrow, right_arrow, stop_emote = ["👈", "👉", "❌"]
    text_blocks = [
        f"{text[i:i+block_size]}"
        for i in range(0, len(text), block_size)]
    text_blocks = [
        f"{surrounder}{text_block}{surrounder}"
        for text_block in text_blocks]
    current_index = 0
    block_message = await ctx.send(text_blocks[current_index])

    def check(reaction, user):
        return (user != ctx.bot.user
                and reaction.emoji in button_emojis
                and reaction.message.id == block_message.id)

    while current_index is not None:
        current_index = current_index % len(text_blocks)
        await block_message.edit(content=text_blocks[current_index])
        for emoji_to_add in button_emojis:
            await block_message.add_reaction(emoji_to_add)
        res = await ctx.bot.wait_for("reaction_add", check=check)
        emoji_result = res[0].emoji
        try:
            await block_message.remove_reaction(emoji_result, res[1])
        except discord.errors.Forbidden:
            pass
        if emoji_result == left_arrow:
            current_index -= 1
        elif emoji_result == right_arrow:
            current_index += 1
        else:
            try:
                await block_message.clear_reactions()
            except discord.errors.Forbidden:
                pass
            await block_message.edit(content=r"```Closed.```")
            current_index = None
