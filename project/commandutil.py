import traceback
import re
from pathlib import Path
import asyncio
import itertools
import concurrent
from datetime import datetime


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


async def keep_updating_message_timedelta(message, message_format):
    try:
        start_time = datetime.now()
        for shift in itertools.count():
            timedelta_str = readable_timedelta(start_time)
            message_formatted = message_format.format(timedelta_str)
            await message.edit(content=message_formatted)
            await asyncio.sleep(1 << shift)
    except (concurrent.futures._base.CancelledError,
            asyncio.exceptions.CancelledError):
        return
    except BaseException as e:
        await message.edit(
            content=f"Something borked after {readable_timedelta(start_time)}")
        print(get_formatted_traceback(e))
