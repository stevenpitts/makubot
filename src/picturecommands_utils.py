import discord
import logging
import os
import asyncio
import concurrent
import subprocess
import youtube_dl
import tempfile
from psycopg2.extras import RealDictCursor
from datetime import datetime
import boto3
from . import commandutil

logger = logging.getLogger()

NO_EMOJI, YES_EMOJI = "❌", "✅"

S3 = boto3.client("s3")


class NotVideo(Exception):
    pass


def set_cmd_images_owner_on_db(db_connection, cmd, uid):
    uid = str(uid).zfill(18)
    cursor = db_connection.cursor(cursor_factory=RealDictCursor)
    cursor.execute(
        """
        UPDATE media.images
        SET uid = %s
        WHERE cmd = %s
        """,
        (uid, cmd)
    )
    cursor.execute(
        """
        UPDATE media.commands
        SET uid = %s
        WHERE cmd = %s
        """,
        (uid, cmd)
    )
    db_connection.commit()


def add_alias_to_db(db_connection, alias, real):
    cursor = db_connection.cursor()
    cursor.execute(
        """
            INSERT INTO media.aliases (
            alias,
            real)
            VALUES (%s, %s);
            """,
        (alias, real)
    )
    db_connection.commit()


def cmd_info(db_connection, cmd):
    cursor = db_connection.cursor(cursor_factory=RealDictCursor)
    cursor.execute(
        """
        SELECT * FROM media.commands
        WHERE cmd = %s
        """,
        (cmd,)
    )
    results = cursor.fetchall()
    if not results:
        return None
    assert len(results) == 1
    basic_cmd_info = results[0]
    cursor.execute(
        """
        SELECT * FROM media.server_command_associations
        WHERE cmd = %s
        """,
        (cmd,)
    )
    results = cursor.fetchall()
    sids = [result["sid"] for result in results]
    basic_cmd_info["origin_sids"] = sids
    return basic_cmd_info


def image_info(db_connection, cmd, image_key):
    cursor = db_connection.cursor(cursor_factory=RealDictCursor)
    cursor.execute(
        """
        SELECT * FROM media.images
        WHERE cmd = %s
        AND image_key = %s
        """,
        (cmd, image_key)
    )
    results = cursor.fetchall()
    if not results:
        return None
    assert len(results) == 1
    return results[0]


def image_exists_in_cmd(db_connection, image_key, cmd):
    cursor = db_connection.cursor(cursor_factory=RealDictCursor)
    cursor.execute(
        """
        SELECT * FROM media.images
        WHERE cmd = %s
        AND image_key = %s
        """,
        (cmd, image_key)
    )
    results = cursor.fetchall()
    return bool(results)


def add_image_to_db(
        db_connection, image_key, cmd, uid=None, sid=None, md5=None):
    if uid:
        uid = str(uid).zfill(18)
    if sid:
        sid = str(sid).zfill(18)
    cursor = db_connection.cursor()
    cursor.execute(
        """
        INSERT INTO media.images (
        cmd,
        image_key,
        uid,
        sid,
        md5)
        VALUES (%s, %s, %s, %s, %s);
        """,
        (cmd, image_key, uid, sid, md5)
    )


def command_exists_in_db(db_connection, cmd):
    cursor = db_connection.cursor(cursor_factory=RealDictCursor)
    cursor.execute(
        """
        SELECT * FROM media.commands
        WHERE cmd = %s;
        """,
        (cmd,)
    )
    results = cursor.fetchall()
    return bool(results)


def add_cmd_to_db(db_connection, cmd, uid=None, sid=None):
    if uid:
        uid = str(uid).zfill(18)
    if sid:
        sid = str(sid).zfill(18)
    cursor = db_connection.cursor()
    cursor.execute(
        """
        INSERT INTO media.commands (
        cmd,
        uid)
        VALUES (%s, %s);
        """,
        (cmd, uid)
    )
    if sid:
        cursor.execute(
            """
            INSERT INTO media.server_command_associations (
            cmd,
            sid)
            VALUES (%s, %s);
            """,
            (cmd, sid)
        )


def delete_image_from_db(db_connection, cmd, image_key):
    logging.info(f"Deleting {cmd}/{image_key} from DB")
    cursor = db_connection.cursor(cursor_factory=RealDictCursor)
    cursor.execute(
        """
        DELETE FROM media.images
        WHERE cmd = %s
        AND image_key = %s
        """,
        (cmd, image_key)
    )


def cascade_deleted_referenced_aliases(db_connection):
    cursor = db_connection.cursor()
    cursor.execute(
        """
        DELETE FROM media.aliases
        WHERE real NOT IN (
            SELECT image_key
            FROM media.images
        )
        RETURNING *
        """
    )
    results = cursor.fetchall()
    logger.info(f"Deleted old aliases: {results}")


def delete_cmd_and_all_images(db_connection, cmd):
    logging.info(f"Deleting {cmd} and all its images from DB")
    cursor = db_connection.cursor(cursor_factory=RealDictCursor)
    cursor.execute(
        """
        DELETE FROM media.images
        WHERE cmd = %s
        """,
        (cmd,)
    )
    cursor.execute(
        """
        DELETE FROM media.commands
        WHERE cmd = %s
        """,
        (cmd,)
    )


def get_random_image(db_connection):
    cursor = db_connection.cursor(cursor_factory=RealDictCursor)
    cursor.execute(
        """
        SELECT * FROM media.images
        ORDER BY RANDOM()
        LIMIT 1
        """
    )
    result = cursor.fetchone()
    return result["image_key"]


def get_cmd_sizes(db_connection):
    cursor = db_connection.cursor(cursor_factory=RealDictCursor)
    cursor.execute(
        """
        SELECT cmd, COUNT(*) AS cmd_size FROM media.images
        GROUP BY cmd
        """
    )
    results = cursor.fetchall()
    return {result["cmd"]: result["cmd_size"] for result in results}


def get_single_cmd_size(db_connection, cmd):
    return get_cmd_sizes(db_connection)[cmd]


def get_all_true_cmds_from_db(db_connection):
    cursor = db_connection.cursor(cursor_factory=RealDictCursor)
    cursor.execute(
        """
        SELECT * FROM media.commands
        """
    )
    results = cursor.fetchall()
    normal_commands = {result["cmd"] for result in results}
    return normal_commands


def get_all_cmds_aliases_from_db(db_connection):
    cursor = db_connection.cursor(cursor_factory=RealDictCursor)
    cursor.execute(
        """
        SELECT * FROM media.commands
        """
    )
    results = cursor.fetchall()
    normal_commands = {result["cmd"] for result in results}
    cursor.execute(
        """
        SELECT * FROM media.aliases
        """
    )
    results = cursor.fetchall()
    alias_commands = {result["alias"] for result in results}
    return normal_commands | alias_commands


def cmd_has_hash(db_connection, cmd, md5):
    cursor = db_connection.cursor(cursor_factory=RealDictCursor)
    cursor.execute(
        """
        SELECT * FROM media.images
        WHERE cmd = %s
        AND md5 = %s
        """,
        (cmd, str(md5))
    )
    results = cursor.fetchall()
    return bool(results)


def get_all_cmd_images_from_db(db_connection, cmd):
    cursor = db_connection.cursor(cursor_factory=RealDictCursor)
    cursor.execute(
        """
        SELECT * FROM media.images
        WHERE cmd = %s
        """,
        (cmd,)
    )
    results = cursor.fetchall()
    return [result["image_key"] for result in results]


def get_cmd_from_alias(db_connection, alias_cmd):
    cursor = db_connection.cursor(cursor_factory=RealDictCursor)
    cursor.execute(
        """
        SELECT * FROM media.commands
        WHERE cmd = %s
        """,
        (alias_cmd,)
    )
    results = cursor.fetchall()
    if results:
        assert len(results) == 1
        return results[0]["cmd"]
    cursor.execute(
        """
        SELECT * FROM media.aliases
        WHERE alias = %s
        """,
        (alias_cmd,)
    )
    results = cursor.fetchall()
    if not results:
        logger.info(f"{alias_cmd} wasn't an alias or real, returning None")
        return None
    assert len(results) == 1
    true_invocation = results[0]["real"]
    logger.info(f"Resolved alias {alias_cmd} -> {true_invocation}")
    return true_invocation


def get_cmd_uid(db_connection, cmd):
    cursor = db_connection.cursor(cursor_factory=RealDictCursor)
    cursor.execute(
        """
        SELECT * FROM media.commands
        WHERE cmd = %s;
        """,
        (cmd,)
    )
    results = cursor.fetchall()
    assert len(results) == 1, f"{cmd=}, {len(results) =}"
    return results[0]["uid"]


def add_server_command_association(db_connection, sid, cmd):
    if sid:
        sid = str(sid).zfill(18)
    cursor = db_connection.cursor()
    cursor.execute(
        """
        INSERT INTO media.server_command_associations (
        sid,
        cmd)
        VALUES (%s, %s);
        """,
        (sid, cmd)
    )
    db_connection.commit()


def get_user_sids(bot, uid):
    """Returns a set of servers that the user and the bot share"""
    # TODO improve this
    shared_servers = {bot_server for bot_server in bot.guilds
                      if bot_server.get_member(uid)}
    shared_sids = {shared_server.id for shared_server in shared_servers}
    return shared_sids


def get_user_origin_server_intersection(db_connection, user_sids, cmd):
    user_sids = [str(sid).zfill(18) for sid in user_sids]
    cursor = db_connection.cursor(cursor_factory=RealDictCursor)
    cursor.execute(
        """
        SELECT * FROM media.server_command_associations
        WHERE cmd = %s
        AND sid = ANY(%s);
        """,
        (cmd, user_sids)
    )
    results = cursor.fetchall()
    intersecting_sids = [result["sid"] for result in results]
    return intersecting_sids


def img_sid_should_be_set(db_connection, cmd, image_key, uid):
    cursor = db_connection.cursor(cursor_factory=RealDictCursor)
    cursor.execute(
        """
        SELECT * FROM media.images
        WHERE cmd = %s
        AND image_key = %s;
        """,
        (cmd, image_key)
    )
    results = cursor.fetchall()
    assert len(results) == 1
    result = results[0]
    img_uid = result["uid"]
    img_sid = result["sid"]
    should_set = (img_uid == uid) and img_sid is None
    logger.info(
        f"For {cmd=} {image_key=}, got {img_uid=}, {img_sid=}, {should_set=}")
    return should_set


def set_img_sid(db_connection, cmd, image_key, sid):
    if sid:
        sid = str(sid).zfill(18)
    cursor = db_connection.cursor(cursor_factory=RealDictCursor)
    cursor.execute(
        """
        UPDATE media.images
        SET sid = %s
        WHERE cmd = %s
        AND image_key = %s;
        """,
        (sid, cmd, image_key)
    )
    db_connection.commit()


def get_appropriate_images(db_connection, cmd, uid, sid=None, user_sids=[]):
    if uid:
        uid = str(uid).zfill(18)
    if sid:
        sid = str(sid).zfill(18)
    user_sids = [str(sid).zfill(18) for sid in user_sids]
    cursor = db_connection.cursor(cursor_factory=RealDictCursor)
    cursor.execute(
        """
        SELECT * FROM media.images
        WHERE cmd = %s
        AND (uid IS NULL OR uid = %s OR sid = %s OR sid = ANY(%s));
        """,
        (cmd, uid, sid, user_sids)
    )
    results = cursor.fetchall()
    if results:
        return [result["image_key"] for result in results]
    logger.info(
        f"Couldn't get any appropriate images for {cmd=} {uid=} {sid=} "
        f"{user_sids=}, so pulling from the entire collection")
    cursor.execute(
        """
        SELECT * FROM media.images
        WHERE cmd = %s;
        """,
        (cmd,)
    )
    results = cursor.fetchall()
    return [result["image_key"] for result in results]


def get_starting_keys_hashes(bucket):
    keys, hashes = commandutil.s3_keys_hashes(bucket, prefix="pictures/")
    toplevel_dirs = set(key.split("/")[1] for key in keys)
    collection_keys = {}
    collection_hashes = {}
    for collection in toplevel_dirs:
        matching_indeces = [i for i, key in enumerate(keys)
                            if key.split("/")[1] == collection]
        collection_keys[collection] = [
            keys[i] for i in matching_indeces]
        collection_hashes[collection] = [
            hashes[i] for i in matching_indeces]

    assert len(collection_keys) == len(collection_hashes), (
        f"{len(collection_keys)=}, {len(collection_hashes)=}")
    for cmd in collection_keys:
        assert len(collection_keys[cmd]) == len(collection_hashes[cmd]), (
            f"{cmd=}: {len(collection_keys[cmd])=}, "
            f"{len(collection_hashes[cmd])=}")

    return collection_keys, collection_hashes


async def generate_image_embed(ctx,
                               url,
                               call_bot_name=False):
    url = commandutil.improve_url(url)
    if getattr(ctx.me, "nick", None):
        bot_nick = ctx.me.nick
    else:
        bot_nick = ctx.me.name
    invocation = f"{ctx.prefix}{ctx.invoked_with}"
    content_without_invocation = ctx.message.content[len(invocation):]
    has_content = bool(content_without_invocation.strip())
    query = f"{content_without_invocation}"
    cleaned_query = await commandutil.clean(ctx, query)
    call_beginning = ("" if not has_content else
                      f"{bot_nick}, " if call_bot_name else
                      f"{ctx.invoked_with}, "
                      )
    embed_description = (
        f"{call_beginning}{cleaned_query}" if has_content else ""
    )
    image_embed_dict = {
        "description": embed_description,
        "author": {"name": ctx.author.name,
                   "icon_url": str(ctx.author.avatar_url)
                   } if has_content else {},
        "image": {"url": url},
        "footer": {"text": f"-{bot_nick}", "icon_url": str(ctx.me.avatar_url)},
    }
    image_embed = discord.Embed.from_dict(image_embed_dict)
    return image_embed


async def get_media_bytes_and_name(url, status_message=None, do_raw=False,
                                   loading_emoji=""):
    with tempfile.TemporaryDirectory() as temp_dir:
        quality_format = "best" if do_raw else "best[filesize<8M]/worst"
        ydl_options = {
            # "logger": logger,
            "quiet": True,
            "no_warnings": True,
            "format": quality_format,
            "outtmpl": f"{temp_dir}/%(title)s.%(ext)s"
        }
        with youtube_dl.YoutubeDL(ydl_options) as ydl:
            await status_message.edit(content=f"Downloading...{loading_emoji}")
            download_start_time = datetime.now()
            with concurrent.futures.ThreadPoolExecutor() as pool:
                await asyncio.get_running_loop().run_in_executor(
                    pool, ydl.extract_info, url)  # This guy takes a while
            download_time = datetime.now() - download_start_time
            logger.info(f"{url} took {download_time} to download")
            files_in_dir = os.listdir(temp_dir)
            if len(files_in_dir) == 0:
                raise youtube_dl.utils.DownloadError("No file found")
            elif len(files_in_dir) > 1:
                logger.warning(
                    f"youtube_dl got more than one file: {files_in_dir}")
                raise youtube_dl.utils.DownloadError(
                    "Multiple files received")
            filename = files_in_dir[0]
            filepath = f"{temp_dir}/{filename}"
            # Fix bad extension
            temp_filepath = f"{filepath}2"
            os.rename(filepath, temp_filepath)
            if filepath.endswith(".mkv"):
                filepath += ".webm"
                filename += ".webm"
            await status_message.edit(content=f"Processing...{loading_emoji}")
            processing_start_time = datetime.now()
            if do_raw:
                os.rename(temp_filepath, filepath)
            else:
                try:
                    await convert_video(temp_filepath, filepath)
                except NotVideo:
                    os.rename(temp_filepath, filepath)
            processing_time = datetime.now() - processing_start_time
            logger.info(f"{url} took {processing_time} to process")
            with open(filepath, "rb") as downloaded_file:
                data = downloaded_file.read()
            return data, filename


async def get_video_length(video_input):
    cmds = ["ffprobe",
            "-v", "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            video_input
            ]
    p = subprocess.Popen(cmds, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    while p.poll() is None:
        await asyncio.sleep(0)
    output, err = p.communicate()
    try:
        video_length = float(output)
    except ValueError:
        raise NotVideo()
    return video_length


async def suggest_audio_video_bitrate(video_input):
    audio_bitrate = 64e3  # bits
    video_length = await get_video_length(video_input)
    max_size = 32e6  # bits. Technically 64e6 but there's some error.
    video_bitrate = (max_size / video_length) - audio_bitrate
    video_bitrate = max(int(video_bitrate), 1e3)
    return audio_bitrate, video_bitrate


async def convert_video(video_input, video_output, log=False):
    audio_bitrate, video_bitrate = await suggest_audio_video_bitrate(
        video_input)
    cmds = ["ffmpeg",
            "-y",
            "-i", video_input,
            # "-vf", "scale=300:200",
            "-b:v", str(video_bitrate),
            "-b:a", str(audio_bitrate),
            video_output
            ]
    p = subprocess.Popen(cmds, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    while p.poll() is None:
        await asyncio.sleep(0)
    output, err = p.communicate()
    if log:
        logger.info(f"ffmpeg output: {output}")
        logger.info(f"ffmpeg err: {err}")
    if not os.path.isfile(video_output):
        raise FileNotFoundError(
            f"ffmpeg failed to convert {video_input} to {video_output}")
