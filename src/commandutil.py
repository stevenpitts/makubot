import traceback
import re
from pathlib import Path
import itertools
import asyncio
from datetime import datetime
try:
    import boto3
    import botocore
    S3 = boto3.client("s3")
except ImportError:
    pass  # Might just be running locally
import discord


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


class SubprocessFailed(Exception):
    pass


async def backup_db(s3_bucket, db_connection):
    if not s3_bucket:
        return
    filename = datetime.now().strftime("%Y/%m/%d/%H/%M/%S")
    command = f"pg_dump | aws s3 cp - {s3_bucket}/backups/{filename}"
    proc = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
        )
    await proc.communicate()
    if proc.returncode != 0:
        stderr_text = await proc.stderr.read()
        stdout_text = await proc.stdout.read()
        raise SubprocessFailed(
            f"backup_db failed with exit code {proc.returncode}, "
            f"stderr {stderr_text}\nand stdout {stdout_text}"
            )


async def clean(ctx, s):
    converter = discord.ext.commands.converter.clean_content()
    return await converter.convert(ctx, s)
