import discord
from discord.ext import commands
from discord.utils import escape_markdown
import logging
import os
import random
import aiohttp
import asyncio
import concurrent
import subprocess
import youtube_dl
import tempfile
from psycopg2.extras import RealDictCursor
import hashlib
from datetime import datetime
import mimetypes
import boto3
from . import commandutil

logger = logging.getLogger()

NO_EMOJI, YES_EMOJI = "❌", "✅"

S3 = boto3.client("s3")


class NotVideo(Exception):
    pass


def add_new_alias_to_db(db_connection, alias, real):
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
        (cmd, image_key, str(uid).zfill(18), str(sid).zfill(18), md5)
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


def add_cmd_to_db(db_connection, cmd, invoking_uid=None, invoking_sid=None):
    cursor = db_connection.cursor()
    cursor.execute(
        """
        INSERT INTO media.commands (
        cmd,
        uid)
        VALUES (%s, %s);
        """,
        (cmd, str(invoking_uid).zfill(18))
    )
    cursor.execute(
        """
        INSERT INTO media.server_command_associations (
        cmd,
        sid)
        VALUES (%s, %s);
        """,
        (cmd, str(invoking_sid).zfill(18))
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


def get_all_true_image_commands_from_db(db_connection):
    cursor = db_connection.cursor(cursor_factory=RealDictCursor)
    cursor.execute(
        """
        SELECT * FROM media.commands
        """
    )
    results = cursor.fetchall()
    normal_commands = {result["cmd"] for result in results}
    return normal_commands


def get_all_image_commands_aliases_from_db(db_connection):
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


def get_all_command_images(db_connection, cmd):
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


def get_cmd_from_alias(db_connection, alias_cmd, none_if_not_exist=False):
    cursor = db_connection.cursor(cursor_factory=RealDictCursor)
    cursor.execute(
        """
        SELECT * FROM media.aliases
        WHERE alias = %s;
        """,
        (alias_cmd,)
    )
    results = cursor.fetchall()
    if not results:
        if none_if_not_exist:
            return None
        return alias_cmd
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
    cursor = db_connection.cursor()
    cursor.execute(
        """
        INSERT INTO media.server_command_associations (
        sid,
        cmd)
        VALUES (%s, %s);
        """,
        (str(sid).zfill(18), cmd)
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
    cursor = db_connection.cursor(cursor_factory=RealDictCursor)
    cursor.execute(
        """
        UPDATE media.images
        SET sid = %s
        WHERE cmd = %s
        AND image_key = %s;
        """,
        (str(sid).zfill(18), cmd, image_key)
    )
    db_connection.commit()


def get_appropriate_images(db_connection, cmd, uid, sid=None, user_sids=[]):
    user_sids = [str(sid).zfill(18) for sid in user_sids]
    cursor = db_connection.cursor(cursor_factory=RealDictCursor)
    cursor.execute(
        """
        SELECT * FROM media.images
        WHERE cmd = %s
        AND (uid IS NULL OR uid = %s OR sid = %s OR sid = ANY(%s));
        """,
        (cmd, str(uid).zfill(18), str(sid).zfill(18), user_sids)
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


class PictureAdder(discord.ext.commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.temp_save_dir = self.bot.shared["temp_dir"]
        self.pending_approval_message_ids = []

    async def collection_has_image_bytes(self,
                                         collection: str,
                                         image_bytes):
        image_hash = hashlib.md5(image_bytes).hexdigest()
        return cmd_has_hash(self.bot.db_connection, collection, image_hash)

    async def get_approval(self, request_id, peek_count=3):
        assert request_id not in self.pending_approval_message_ids
        self.pending_approval_message_ids.append(request_id)
        try:
            while True:
                newest_ids = self.pending_approval_message_ids[-peek_count:]
                if request_id not in newest_ids:
                    await asyncio.sleep(0.1)
                    continue
                try:
                    request = await self.bot.makusu.fetch_message(
                        request_id)
                except (aiohttp.client_exceptions.ServerDisconnectedError,
                        aiohttp.client_exceptions.ClientOSError,
                        discord.errors.HTTPException):
                    logger.warning(f"Got error on {request_id}", exc_info=True)
                    await asyncio.sleep(1)
                reactions_from_maku = [
                    reaction.emoji for reaction in request.reactions
                    if reaction.count == 2
                    and reaction.emoji in (NO_EMOJI, YES_EMOJI)]
                if len(reactions_from_maku) > 1:
                    await self.bot.makusu.send("You reacted twice...")
                elif len(reactions_from_maku) == 1:
                    assert reactions_from_maku[0] in (YES_EMOJI, NO_EMOJI)
                    return reactions_from_maku[0] == YES_EMOJI
                await asyncio.sleep(0.1)
        finally:
            self.pending_approval_message_ids.remove(request_id)

    async def image_suggestion(self, image_collection, filename, requestor,
                               image_bytes=None, status_message=None):
        try:
            if image_bytes is None:
                with open(self.temp_save_dir / filename, "rb") as f:
                    image_bytes = f.read()
            else:
                existing_keys = {
                    str(path) for path in self.temp_save_dir.iterdir()}
                filename = commandutil.get_nonconflicting_filename(
                    filename, existing_keys=existing_keys)
                with open(self.temp_save_dir / filename, "wb") as f:
                    f.write(image_bytes)
            if await self.collection_has_image_bytes(image_collection,
                                                     image_bytes,):
                response = (
                    f"The image {filename} appears already in the collection!")
                await requestor.send(response)
                try:
                    await status_message.edit(content=response)
                except discord.errors.NotFound:
                    pass
                return
            is_new = (
                image_collection not in
                get_all_true_image_commands_from_db(self.bot.db_connection))
            new_addition = "***NEW*** " if is_new else ""
            proposal = (f"Add image {filename} to {new_addition}"
                        f"{image_collection}? Requested by {requestor.name}")
            try:
                request = await self.bot.makusu.send(
                    proposal, file=discord.File(self.temp_save_dir
                                                / filename))
                try:
                    await status_message.edit(content="Sent to Maku!")
                except discord.errors.NotFound:
                    pass
            except discord.errors.HTTPException:
                response = f"Sorry, {filename} is too large ;~;"
                await requestor.send(response)
                try:
                    await status_message.edit(content=response)
                except discord.errors.NotFound:
                    pass
                return

            await request.add_reaction(NO_EMOJI)
            await request.add_reaction(YES_EMOJI)

            try:
                await status_message.edit(
                    content="Waiting for maku approval...")
            except discord.errors.NotFound:
                pass
            approval_start_time = datetime.now()
            approved = await self.get_approval(request.id)
            approval_time = datetime.now() - approval_start_time
            logger.info(f"{filename} took {approval_time} to get approved")
            await request.delete()
            if await self.collection_has_image_bytes(image_collection,
                                                     image_bytes):
                response = (
                    f"The image {filename} appears already in the collection!")
                await requestor.send(response)
                try:
                    await status_message.edit(content=response)
                except discord.errors.NotFound:
                    pass
                return
            if not approved:
                response = (f"Your image {filename} was not approved. "
                            "Feel free to ask Maku why ^_^")
                try:
                    await status_message.edit(content=response)
                except discord.errors.NotFound:
                    pass
                if status_message.channel != requestor.dm_channel:
                    await requestor.send(response)
                return
            return await self.apply_image_approved(
                filename,
                image_collection,
                requestor,
                status_message,
                image_bytes)
        except (concurrent.futures._base.CancelledError,
                asyncio.exceptions.CancelledError):
            logger.error(f"Cancelled error on {filename}")
        except BaseException as e:
            formatted_tb = commandutil.get_formatted_traceback(e)
            logger.error(formatted_tb)
            response = f"Something went wrong with {filename}, sorry!"
            await requestor.send(response)
            try:
                await status_message.edit(content=response)
            except discord.errors.NotFound:
                pass
            await self.bot.makusu.send(
                "Something went wrong in image_suggestion"
                f"\n```{formatted_tb}```")

    async def apply_image_approved(self,
                                   filename,
                                   cmd,
                                   requestor,
                                   status_message,
                                   image_bytes):
        existing_keys = get_all_command_images(self.bot.db_connection, cmd)
        new_filename = commandutil.get_nonconflicting_filename(
            filename, existing_keys=existing_keys)
        image_key = f"pictures/{cmd}/{new_filename}"

        def upload_image_func():
            local_path = self.temp_save_dir / filename
            mimetype, _ = mimetypes.guess_type(local_path)
            mimetype = mimetype or "binary/octet-steam"
            return S3.upload_file(
                str(local_path),
                self.bot.s3_bucket,
                image_key,
                ExtraArgs={
                    "ACL": "public-read",
                    "ContentType": mimetype
                }
            )
        with concurrent.futures.ThreadPoolExecutor() as pool:
            await asyncio.get_running_loop().run_in_executor(
                pool,
                upload_image_func
            )
        image_hash = hashlib.md5(image_bytes).hexdigest()
        self.bot.get_command("send_image_func").aliases.append(cmd)
        self.bot.all_commands["cmd"] = self.bot.all_commands["send_image_func"]

        try:
            sid = status_message.guild.id
        except (discord.errors.NotFound, AttributeError):
            sid = None

        if not image_exists_in_cmd(self.bot.db_connection, image_key, cmd):
            add_image_to_db(
                self.bot.db_connection, image_key, cmd,
                uid=requestor.id, sid=sid, md5=image_hash)

        response = f"Your image {new_filename} was approved!"
        await requestor.send(response)
        try:
            await status_message.edit(content=response)
        except discord.errors.NotFound:
            pass

    def get_aliases_of_cmd(self, real_cmd):
        cursor = self.bot.db_connection.cursor(cursor_factory=RealDictCursor)
        cursor.execute(
            """
            SELECT * FROM media.aliases
            WHERE real = %s;
            """,
            (real_cmd,)
        )
        results = cursor.fetchall()
        return [result["alias"] for result in results]

    @commands.command(hidden=True, aliases=["aliasimage", "aliaspicture"])
    @commands.is_owner()
    async def add_picture_alias(self, ctx, alias, real):
        send_image_cmd = self.bot.get_command("send_image_func")
        if not alias.isalnum() or not real.isalnum():
            await ctx.send("Please only include letters and numbers.")
            return
        elif self.bot.get_command(alias):
            await ctx.send(f"{alias} is already a command :<")
            return
        elif real not in send_image_cmd.aliases:
            await ctx.send(
                f"{real} isn't an image command, though :<")
            return
        real = get_cmd_from_alias(self.bot.db_connection, real)
        add_new_alias_to_db(self.bot.db_connection, alias, real)
        send_image_cmd.aliases.append(alias)
        self.bot.all_commands[alias] = self.bot.all_commands["send_image_func"]
        await ctx.send("Added!")

    @commands.command(aliases=["addimage", "addimageraw"])
    async def add_image(self, ctx, image_collection: str, *, urls: str = ""):
        """Requests an image be added.
        mb.addimage nao http://static.zerochan.net/Tomori.Nao.full.1901643.jpg
        Then, it'll be sent to maku for approval!"""
        logger.info(
            f"Called add_image with ctx {ctx.__dict__}, "
            f"image_collection {image_collection}, and urls {urls}.")
        do_raw = ctx.invoked_with == "addimageraw"
        if " " in image_collection:
            await ctx.send("Spaces replaced with underscores")
        image_collection = image_collection.strip().lower().replace(" ", "_")
        if not image_collection.isalnum():
            await ctx.send("Please only include letters and numbers.")
            return
        image_collection = get_cmd_from_alias(self.bot.db_connection,
                                              image_collection)
        existing_command = self.bot.all_commands.get(image_collection, None)
        send_image_command = self.bot.all_commands["send_image_func"]
        if existing_command and (existing_command != send_image_command):
            await ctx.send("That is already a non-image command name.")
            return
        if not urls and not ctx.message.attachments:
            await ctx.send("You must include a URL at the end of your "
                           "message or attach image(s).")
            return
        urls = urls.split() + [attachment.url for attachment
                               in ctx.message.attachments]
        image_suggestion_coros = []
        loading_emoji = discord.utils.get(self.bot.emojis,
                                          name="makubot_loading")
        for url in urls:
            try:
                status_message = await ctx.send(f"Querying... {loading_emoji}")
                data, filename = await get_media_bytes_and_name(
                    url, status_message=status_message, do_raw=do_raw,
                    loading_emoji=loading_emoji)
            except(youtube_dl.utils.DownloadError,
                   aiohttp.client_exceptions.ClientConnectorError,
                   aiohttp.client_exceptions.InvalidURL,
                   discord.errors.HTTPException,
                   FileNotFoundError) as e:
                traceback = commandutil.get_formatted_traceback(e)
                logger.warning(f"Couldn't download image: {traceback}")
                await asyncio.sleep(1)  # TODO fix race condition, added to
                # counter status message update from separate thread
                await status_message.edit(content="I can't download that ;a;")
            except (concurrent.futures._base.CancelledError,
                    asyncio.exceptions.CancelledError):
                await status_message.edit(
                    content="Sorry, the download messed up; please try again!")
                return
            except BaseException as e:
                formatted_tb = commandutil.get_formatted_traceback(e)
                await status_message.edit(content="Something went wrong ;a;")
                await self.bot.makusu.send(
                    f"Something went wrong in add_image\n```{formatted_tb}```")
                raise
            else:
                await status_message.edit(content="Sent to Maku for approval!")
                image_suggestion_coros.append(self.image_suggestion(
                    image_collection, filename, ctx.author,
                    image_bytes=data, status_message=status_message))
        all_suggestion_coros = asyncio.gather(*image_suggestion_coros)
        try:
            await all_suggestion_coros
        except BaseException:
            logger.error("Got exception in add_image: ", exc_info=True)
            all_suggestion_coros.cancel()


class ReactionImages(discord.ext.commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        cursor = self.bot.db_connection.cursor()
        cursor.execute(
            """
            CREATE SCHEMA IF NOT EXISTS media;
            ALTER TABLE IF EXISTS alias_images
                RENAME TO aliases;
            ALTER TABLE IF EXISTS aliases
                SET SCHEMA media;
            CREATE TABLE IF NOT EXISTS media.commands (
                cmd TEXT PRIMARY KEY,
                uid CHARACTER(18));
            CREATE TABLE IF NOT EXISTS media.images (
                cmd TEXT REFERENCES media.commands(cmd),
                image_key TEXT,
                uid CHARACTER(18),
                sid CHARACTER(18),
                md5 TEXT,
                PRIMARY KEY (cmd, image_key));
            CREATE TABLE IF NOT EXISTS media.server_command_associations (
                sid CHARACTER(18),
                cmd TEXT REFERENCES media.commands(cmd));
            CREATE TABLE IF NOT EXISTS media.aliases (
                alias TEXT PRIMARY KEY,
                real TEXT);
            """
        )
        self.bot.db_connection.commit()

        cursor = self.bot.db_connection.cursor(cursor_factory=RealDictCursor)
        cursor.execute(
            """
            SELECT * FROM media.aliases
            """
        )
        alias_pictures_results = cursor.fetchall()

        self.image_aliases = {}
        for alias_pictures_result in alias_pictures_results:
            alias_cmd = alias_pictures_result["alias"]
            real_cmd = alias_pictures_result["real"]
            self.image_aliases[real_cmd] = (
                self.image_aliases.get(real_cmd, []) + [alias_cmd])

        collection_keys, collection_hashes = (
            get_starting_keys_hashes(self.bot.s3_bucket)
        )
        self.sync_s3_db(collection_keys, collection_hashes)

    def sync_s3_db(self, collection_keys, collection_hashes):
        for cmd in collection_keys:
            if not command_exists_in_db(self.bot.db_connection, cmd):
                logger.info(f"DB didn't have {cmd=}, adding")
                add_cmd_to_db(
                    self.bot.db_connection, cmd, invoking_uid=None,
                    invoking_sid=None)
            assert (len(collection_keys[cmd])
                    == len(collection_hashes[cmd]))
            key_hash_pairs = zip(collection_keys[cmd], collection_hashes[cmd])
            for image_key, image_hash in key_hash_pairs:
                if image_exists_in_cmd(self.bot.db_connection, image_key, cmd):
                    continue
                logger.info(f"DB didn't have {image_key} in {cmd}, adding "
                            f"with {image_hash=}.")
                add_image_to_db(
                    self.bot.db_connection, image_key, cmd, uid=None,
                    sid=None, md5=image_hash)

        for cmd in get_all_true_image_commands_from_db(self.bot.db_connection):
            if cmd not in collection_keys:
                logger.warning(f"{cmd} wasn't in S3, so it's being removed "
                               f"from the database.")
                delete_cmd_and_all_images(self.bot.db_connection, cmd)
                continue
            cmd_image_keys = (
                get_all_command_images(self.bot.db_connection, cmd))
            for image_key in cmd_image_keys:
                if image_key not in collection_keys[cmd]:
                    delete_image_from_db(
                        self.bot.db_connection, cmd, image_key)

    @commands.command(aliases=["randomimage", "yo", "hey", "makubot"])
    async def random_image(self, ctx):
        """For true shitposting."""
        chosen_key = get_random_image(self.bot.db_connection)
        chosen_url = commandutil.url_from_s3_key(
            self.bot.s3_bucket,
            self.bot.s3_bucket_location,
            chosen_key,
            improve=True)
        logging.info(f"Sending url in random_image func: {chosen_url}")
        image_embed = await generate_image_embed(
            ctx, chosen_url, call_bot_name=True)
        sent_message = await ctx.send(embed=image_embed)
        if sent_message.embeds[0].image.url == discord.Embed.Empty:
            new_url = commandutil.improve_url(chosen_url)
            sent_message.edit(embed=None, content=new_url)

    @commands.command(hidden=True)
    async def send_image_func(self, ctx):
        cmd = get_cmd_from_alias(ctx.bot.db_connection, ctx.invoked_with)
        uid = ctx.author.id
        try:
            sid = ctx.guild.id
        except AttributeError:
            sid = None
        cmd_uid = get_cmd_uid(ctx.bot.db_connection, cmd)
        if cmd_uid == uid and sid:
            add_server_command_association(ctx.bot.db_connection, sid, cmd)
        user_sids = get_user_sids(ctx.bot, uid)
        user_origin_server_intersection = get_user_origin_server_intersection(
            ctx.bot.db_connection, user_sids, cmd)
        candidate_images = get_appropriate_images(
            ctx.bot.db_connection, cmd, uid, sid,
            user_origin_server_intersection)
        logger.info(f"From {cmd=}, {uid=}, {sid=}, "
                    f"{user_origin_server_intersection=}, got "
                    f"{candidate_images=}")
        chosen_key = random.choice(candidate_images)
        if img_sid_should_be_set(ctx.bot.db_connection, cmd, chosen_key, uid):
            logger.info(f"{cmd}'s sid will be set to {sid}")
            set_img_sid(ctx.bot.db_connection, cmd, chosen_key, sid)
        chosen_url = commandutil.url_from_s3_key(
            ctx.bot.s3_bucket,
            ctx.bot.s3_bucket_location,
            chosen_key,
            improve=True)
        logging.info(f"Sending url in send_image func: {chosen_url}")
        image_embed = await generate_image_embed(ctx, chosen_url)
        sent_message = await ctx.send(embed=image_embed)
        if not await commandutil.url_is_image(chosen_url):
            new_url = commandutil.improve_url(
                chosen_url)
            logger.info(
                "URL wasn't image, so turned to text URL. "
                f"{chosen_url} -> {new_url}")
            await sent_message.edit(embed=None, content=new_url)

    @commands.command(aliases=["listreactions"])
    async def list_reactions(self, ctx):
        """List all my reactions"""
        pictures_desc = ", ".join(get_all_image_commands_aliases_from_db(
            self.bot.db_connection))
        block_size = 1500
        text_blocks = [f"{pictures_desc[i:i+block_size]}"
                       for i in range(0, len(pictures_desc), block_size)]
        for text_block in text_blocks:
            await ctx.send(f"```{escape_markdown(text_block)}```")

    @commands.command(aliases=["realinvocation"])
    async def real_invocation(self, ctx, alias):
        real_cmd = get_cmd_from_alias(
            self.bot.db_connection, alias, none_if_not_exist=True)
        if real_cmd:
            await ctx.send(f"{alias} is an alias for {real_cmd}!")
        else:
            await ctx.send(f"Hmm, I don't think {alias} is an alias...")

    @commands.command(aliases=["howbig"])
    async def how_big(self, ctx, cmd):
        real_cmd = get_cmd_from_alias(
            self.bot.db_connection, cmd, none_if_not_exist=True)
        try:
            command_size = get_single_cmd_size(
                self.bot.db_connection, real_cmd)
        except KeyError:
            await ctx.send("That's not an image command :o")
            return
        image_plurality = "image" if command_size == 1 else "images"
        await ctx.send(f"{cmd} has {command_size} {image_plurality}!")

    @commands.command(aliases=["bigten"])
    async def big_ten(self, ctx):
        """List ten biggest image commands!"""
        command_sizes = get_cmd_sizes(self.bot.db_connection)
        commands_sorted = sorted(
            command_sizes.keys(),
            key=lambda command: command_sizes[command],
            reverse=True
        )
        top_ten_commands = commands_sorted[:10]
        message = "\n".join([
            f"{command}: {command_sizes[command]}"
            for command in top_ten_commands])
        await ctx.send(message)


def setup(bot):
    logger.info("picturecommands starting setup")
    bot.add_cog(ReactionImages(bot))
    bot.add_cog(PictureAdder(bot))
    image_command_invocations = list(
        get_all_image_commands_aliases_from_db(bot.db_connection))

    bot.get_command("send_image_func").aliases += image_command_invocations
    for invocation in image_command_invocations:
        bot.all_commands[invocation] = bot.all_commands["send_image_func"]

    logger.info("picturecommands ending setup")
