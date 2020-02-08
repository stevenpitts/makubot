import traceback
import re
from pathlib import Path
import itertools
from datetime import datetime
import discord


def get_formatted_traceback(e):
    return ''.join(traceback.format_exception(type(e), e, e.__traceback__))


def slugify(candidate_filename: str):
    slugified = candidate_filename.replace(" ", "_")
    slugified = re.sub(r'(?u)[^-\w.]', '', slugified)
    slugified = slugified.strip(" .")
    if "." not in slugified:
        slugified += ".unknown"
    return slugified


def get_nonconflicting_filename(candidate_filename: str, directory: Path):
    if not (directory / candidate_filename).is_file():
        return candidate_filename
    try:
        filename_prefix, filename_suffix = candidate_filename.split(".", 1)
    except ValueError:
        raise("Filename was not valid (needs prefix and suffix")
    for addition in itertools.count():
        candidate_filename = f"{filename_prefix}{addition}.{filename_suffix}"
        if not (directory / candidate_filename).is_file():
            return candidate_filename
    raise AssertionError("Shouldn't ever get here")


def readable_timedelta(old, new=None):
    new = new or datetime.now()
    return str(new - old).split('.')[0]


async def clean(ctx, s):
    converter = discord.ext.commands.converter.clean_content()
    return await converter.convert(ctx, s)
