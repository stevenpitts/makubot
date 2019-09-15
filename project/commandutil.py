import traceback
import re
from pathlib import Path
import asteval
import asyncio
from io import StringIO
import itertools
import concurrent
from datetime import datetime
from discord.utils import escape_markdown


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


def aeval(to_evaluate, return_error=True) -> str:
    is_dangerous_input = (any([char.isalpha() and char not in 'eE'
                               for char in to_evaluate])
                          or "**" in to_evaluate
                          or "=" in to_evaluate)
    if is_dangerous_input:
        return "Sorry, that looks dangerous; please use me for simple math!"
    temp_string_io = StringIO()
    aeval_interpreter = asteval.Interpreter(writer=temp_string_io,
                                            err_writer=temp_string_io)
    result = aeval_interpreter(to_evaluate)
    output = temp_string_io.getvalue()
    output = output and escape_markdown(str(output))
    result = result and escape_markdown(str(result))
    if result or output:
        output_str = f'```{output}```\n' if output else ''
        result_str = f'```Result: {result}```' if result else 'No Result.'
        return f'{output_str}{result_str}'
    elif return_error:
        return 'No result'


def readable_timedelta(old, new):
    return str(new - old).split('.')[0]


async def keep_updating_message_timedelta(message, message_format, delay=5):
    try:
        start_time = datetime.now()
        while True:
            timedelta_str = readable_timedelta(start_time, datetime.now())
            message_formatted = message_format.format(timedelta_str)
            await message.edit(content=message_formatted)
            await asyncio.sleep(delay)
    except concurrent.futures._base.CancelledError:
        raise
    except BaseException as e:
        print(get_formatted_traceback(e))
