import traceback
import re
from pathlib import Path
import itertools
import logging
from datetime import datetime
import urllib
import aiohttp
import subprocess
try:
    import boto3
    import botocore
    S3 = boto3.client("s3")
except ImportError:
    pass  # Might just be running locally
import discord

logger = logging.getLogger()


def obfuscate_amazon(url):
    # Amazon doesn't need free advertising
    return url.replace("amazon", "%61%6d%61%7a%6f%6e")


def improve_url(url, obfuscate=False):
    if obfuscate:
        url = obfuscate_amazon(url)
    url = url.replace(" ", "+")
    return url


def url_from_s3_key(s3_bucket,
                    s3_bucket_location,
                    s3_key,
                    validate=False,
                    improve=False,
                    obfuscate=False):
    url = (f"https://{s3_bucket}.s3.{s3_bucket_location}"
           f".amazonaws.com/{s3_key}")
    if improve:
        url = improve_url(url)
    if obfuscate:
        url = obfuscate_amazon(url)
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


def slugify(candidate_filename: str):
    slugified = candidate_filename.replace(" ", "_")
    slugified = re.sub(r"(?u)[^-\w.]", "", slugified)
    slugified = slugified.strip(" .")
    if "." not in slugified:
        slugified += ".unknown"
    return slugified


def get_nonconflicting_filename(candidate_filename: str,
                                directory: Path,
                                collection_keys=None):
    def candidate_filename_exists(candidate_filename):
        if collection_keys:
            return candidate_filename in collection_keys
        return (directory / candidate_filename).is_file()
    if not candidate_filename_exists(candidate_filename):
        return candidate_filename
    try:
        filename_prefix, filename_suffix = candidate_filename.split(".", 1)
    except ValueError:
        raise("Filename was not valid (needs prefix and suffix")
    for addition in itertools.count():
        candidate_filename = (f"{filename_prefix}"
                              f"{addition}."
                              f"{filename_suffix}")
        if not candidate_filename_exists(candidate_filename):
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
