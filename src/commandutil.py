import traceback
import re
from pathlib import Path
import itertools
import logging
from datetime import datetime
import subprocess
try:
    import boto3
    import botocore
    S3 = boto3.client("s3")
except ImportError:
    pass  # Might just be running locally
import discord

logger = logging.getLogger()


def backup_db(backup_location):
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
                                s3_bucket=None):
    if s3_bucket:
        if not s3_object_exists(s3_bucket, candidate_filename):
            return candidate_filename
        try:
            filename_prefix, filename_suffix = candidate_filename.split(".", 1)
        except ValueError:
            raise("Filename was not valid (needs prefix and suffix")
        for addition in itertools.count():
            candidate_filename = (f"{filename_prefix}"
                                  f"{addition}."
                                  f"{filename_suffix}")
            if not s3_object_exists(s3_bucket, candidate_filename):
                return candidate_filename
        raise AssertionError("Shouldn't ever get here")
    else:
        if not (directory / candidate_filename).is_file():
            return candidate_filename
        try:
            filename_prefix, filename_suffix = candidate_filename.split(".", 1)
        except ValueError:
            raise("Filename was not valid (needs prefix and suffix")
        for addition in itertools.count():
            candidate_filename = (f"{filename_prefix}"
                                  f"{addition}."
                                  f"{filename_suffix}")
            if not (directory / candidate_filename).is_file():
                return candidate_filename
        raise AssertionError("Shouldn't ever get here")


def readable_timedelta(old, new=None):
    new = new or datetime.now()
    return str(new - old).split(".")[0]


async def clean(ctx, s):
    converter = discord.ext.commands.converter.clean_content()
    return await converter.convert(ctx, s)
