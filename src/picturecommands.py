import discord
from discord.ext import commands
import logging
import random
import aiohttp
import asyncio
import concurrent
import youtube_dl
import hashlib
from datetime import datetime
import mimetypes
import boto3
from . import util
from .picturecommands_utils import (
    YES_EMOJI,
    NO_EMOJI,
    cmd_has_hash,
    get_all_true_cmds_from_db,
    get_all_cmd_images_from_db,
    command_exists_in_db,
    add_cmd_to_db,
    image_exists_in_cmd,
    add_image_to_db,
    get_cmd_from_alias,
    add_alias_to_db,
    get_media_bytes_and_name,
    cascade_deleted_referenced_aliases,
    get_starting_keys_hashes,
    delete_cmd_and_all_images,
    delete_image_from_db,
    get_random_image,
    generate_image_embed,
    get_cmd_uid,
    add_server_command_association,
    get_user_sids,
    get_user_origin_server_intersection,
    get_appropriate_images,
    img_sid_should_be_set,
    set_img_sid,
    get_all_cmds_aliases_from_db,
    get_cmd_sizes,
    cmd_info,
    image_info,
    set_cmd_images_owner_on_db,
    set_cmd_images_server_on_db,
    get_all_user_cmds,
    get_all_user_images,
    get_cmd_aliases_from_db,
    get_cmd_size_server_user,
    add_blacklist_association,
    get_user_blacklist,
    remove_blacklist_association,
)

logger = logging.getLogger()

S3 = boto3.client("s3")


def sync_s3_db(db_connection, collection_keys, collection_hashes):
    missing_cmds = [
        cmd for cmd in collection_keys
        if not command_exists_in_db(db_connection, cmd)]
    if missing_cmds:
        logger.info(f"DB didn't have cmds, adding: {missing_cmds=}")
    for cmd in missing_cmds:
        add_cmd_to_db(db_connection, cmd, uid=None, sid=None)
    for cmd in collection_keys:
        assert (len(collection_keys[cmd])
                == len(collection_hashes[cmd]))
        missing_key_hash_pairs = [
            (image_key, image_hash)
            for (image_key, image_hash)
            in zip(collection_keys[cmd], collection_hashes[cmd])
            if not image_exists_in_cmd(db_connection, image_key, cmd)
        ]
        if missing_key_hash_pairs:
            logger.info(f"Adding to DB {missing_key_hash_pairs=}")
        for image_key, image_hash in missing_key_hash_pairs:
            add_image_to_db(
                db_connection, image_key, cmd, uid=None,
                sid=None, md5=image_hash)

    for cmd in get_all_true_cmds_from_db(db_connection):
        if cmd not in collection_keys:
            logger.warning(f"{cmd} wasn't in S3, so it's being removed "
                           f"from the database.")
            delete_cmd_and_all_images(db_connection, cmd)
            continue
        cmd_image_keys = (
            get_all_cmd_images_from_db(db_connection, cmd))
        for image_key in cmd_image_keys:
            if image_key not in collection_keys[cmd]:
                delete_image_from_db(
                    db_connection, cmd, image_key)


def collection_has_image_bytes(
        db_connection, collection: str, image_bytes):
    image_hash = hashlib.md5(image_bytes).hexdigest()
    return cmd_has_hash(db_connection, collection, image_hash)


class PictureAdder(discord.ext.commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.pending_approval_message_ids = []

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

    async def image_suggestion(self, image_collection, filepath, requestor,
                               image_bytes=None, status_message=None,
                               temp_dir=None):
        if filepath is None or temp_dir is None or image_bytes is None:
            raise ValueError("filepath, temp_dir, and image_bytes must be set")
        filename = filepath.split("/")[-1]
        try:
            with open(filepath, "rb") as f:
                image_bytes = f.read()
            if collection_has_image_bytes(
                    self.bot.db_connection, image_collection, image_bytes,):
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
                get_all_true_cmds_from_db(self.bot.db_connection))
            new_addition = "***NEW*** " if is_new else ""
            proposal = (f"Add image {filename} to {new_addition}"
                        f"{image_collection}? Requested by {requestor.name}")
            try:
                request = await self.bot.makusu.send(
                    proposal, file=discord.File(filepath))
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
                    content="Waiting for Maku's approval...")
            except discord.errors.NotFound:
                pass
            approval_start_time = datetime.now()
            approved = await self.get_approval(request.id)
            approval_time = datetime.now() - approval_start_time
            logger.info(f"{filename} took {approval_time} to get approved")
            await request.delete()
            if collection_has_image_bytes(
                    self.bot.db_connection, image_collection, image_bytes):
                response = (
                    f"The image {filename} appears already in the collection!")
                await requestor.send(response)
                try:
                    await status_message.edit(content=response)
                except discord.errors.NotFound:
                    pass
                return
            if not approved:
                response = (f"Your image `{filename}` was not approved. "
                            "Feel free to ask Maku why ^_^")
                try:
                    await status_message.edit(content=response)
                except discord.errors.NotFound:
                    pass
                if status_message.channel != requestor.dm_channel:
                    await requestor.send(response)
                return
            return await self.apply_image_approved(
                filepath,
                image_collection,
                requestor,
                status_message,
                image_bytes)
        except (concurrent.futures._base.CancelledError,
                asyncio.exceptions.CancelledError):
            logger.error(f"Cancelled error on {filename}")
        except BaseException as e:
            formatted_tb = util.get_formatted_traceback(e)
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

    async def apply_image_approved(
            self, filepath, cmd, requestor, status_message, image_bytes):
        filename = filepath.split("/")[-1]
        existing_keys = get_all_cmd_images_from_db(self.bot.db_connection, cmd)
        image_key = util.get_nonconflicting_filename(
            filename, existing_keys=existing_keys)
        full_image_key = f"pictures/{cmd}/{image_key}"

        def upload_image_func():
            mimetype, _ = mimetypes.guess_type(filepath)
            mimetype = mimetype or "binary/octet-steam"
            return S3.upload_file(
                str(filepath),
                self.bot.s3_bucket,
                full_image_key,
                ExtraArgs={
                    "ACL": "public-read",
                    "ContentType": mimetype
                }
            )
        with concurrent.futures.ThreadPoolExecutor() as pool:
            await asyncio.get_running_loop().run_in_executor(
                pool, upload_image_func)
        md5 = hashlib.md5(image_bytes).hexdigest()

        try:
            sid = status_message.guild.id
        except (discord.errors.NotFound, AttributeError):
            sid = None
        uid = requestor.id

        if not command_exists_in_db(self.bot.db_connection, cmd):
            add_cmd_to_db(self.bot.db_connection, cmd, uid=uid, sid=sid)
            self.bot.get_command("send_image_func").aliases.append(cmd)
            self.bot.all_commands[cmd] = self.bot.all_commands[
                "send_image_func"]

        if not image_exists_in_cmd(self.bot.db_connection, image_key, cmd):
            add_image_to_db(
                self.bot.db_connection, image_key, cmd,
                uid=uid, sid=sid, md5=md5)

        response = f"Your image `{image_key}` was approved!"
        await requestor.send(response)
        try:
            await status_message.edit(content=response)
        except discord.errors.NotFound:
            pass

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
        add_alias_to_db(self.bot.db_connection, alias, real)
        send_image_cmd.aliases.append(alias)
        self.bot.all_commands[alias] = self.bot.all_commands["send_image_func"]
        await ctx.send("Added!")

    @commands.command(aliases=["mycmds"])
    async def mycommands(self, ctx):
        """Shows you all your commands!"""
        all_cmds = get_all_user_cmds(self.bot.db_connection, ctx.author.id)
        all_cmds_str = ", ".join(all_cmds)
        if all_cmds:
            await ctx.send(f"All your commands: {all_cmds_str}")
        else:
            await ctx.send("You don't have any owned commands!")

    @commands.command()
    async def myimagecount(self, ctx):
        """Shows you how many images you've added!"""
        all_images = get_all_user_images(self.bot.db_connection, ctx.author.id)
        await ctx.send(f"You have {len(all_images)} owned images!")

    @commands.command()
    async def addimage(self, ctx, *, image_collection_and_urls: str = ""):
        """Requests an image be added to an image collection.
        For example, to add an image to mb.nao:
        mb.addimage nao http://static.zerochan.net/Tomori.Nao.full.1901643.jpg
        Alternatively, you can use mb.addimage nao, and attach an image to \
the message!
        Then, it'll be sent to Maku for approval!
        If you want to start a new image command, \
you just need to add an image to it!"""
        image_collection_and_urls_separated = image_collection_and_urls.split()
        if not image_collection_and_urls_separated:
            await ctx.send(f"`mb.addimage`: {ctx.command.help}")
            return
        image_collection = image_collection_and_urls_separated[0]
        urls = " ".join(image_collection_and_urls_separated[1:])
        logger.info(
            f"Called add_image with ctx {ctx.__dict__}, "
            f"image_collection {image_collection}, and urls {urls}.")
        if " " in image_collection:
            await ctx.send("Spaces replaced with underscores")
        image_collection = image_collection.strip().lower().replace(" ", "_")
        if not image_collection.isalnum() or not image_collection.isascii():
            await ctx.send("Please only include ascii letters and numbers.")
            return
        image_collection = get_cmd_from_alias(
            self.bot.db_connection, image_collection
        ) or image_collection
        existing_command = (
            self.bot.all_commands.get(image_collection, None)
            if image_collection else None)
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
                data, filepath, temp_dir = await get_media_bytes_and_name(
                    url, status_message=status_message,
                    loading_emoji=loading_emoji)
            except(youtube_dl.utils.DownloadError,
                   aiohttp.client_exceptions.ClientConnectorError,
                   aiohttp.client_exceptions.InvalidURL,
                   discord.errors.HTTPException,
                   FileNotFoundError) as e:
                traceback = util.get_formatted_traceback(e)
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
                formatted_tb = util.get_formatted_traceback(e)
                await status_message.edit(content="Something went wrong ;a;")
                await self.bot.makusu.send(
                    f"Something went wrong in addimage\n```{formatted_tb}```")
                raise
            else:
                await status_message.edit(content="Sent to Maku for approval!")
                image_suggestion_coros.append(self.image_suggestion(
                    image_collection, filepath, ctx.author,
                    image_bytes=data, status_message=status_message,
                    temp_dir=temp_dir))
        all_suggestion_coros = asyncio.gather(*image_suggestion_coros)
        try:
            await all_suggestion_coros
        except BaseException:
            logger.error("Got exception in addimage: ", exc_info=True)
            all_suggestion_coros.cancel()


class ReactionImages(discord.ext.commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        cursor = self.bot.db_connection.cursor()
        cursor.execute(
            """
            CREATE SCHEMA IF NOT EXISTS media;
            CREATE TABLE IF NOT EXISTS media.commands (
                cmd TEXT PRIMARY KEY,
                uid CHARACTER(18));
            CREATE TABLE IF NOT EXISTS media.images (
                cmd TEXT REFERENCES media.commands(cmd) ON DELETE CASCADE,
                image_key TEXT,
                uid CHARACTER(18),
                sid CHARACTER(18),
                md5 TEXT,
                PRIMARY KEY (cmd, image_key));
            CREATE TABLE IF NOT EXISTS media.server_command_associations (
                sid CHARACTER(18),
                cmd TEXT REFERENCES media.commands(cmd) ON DELETE CASCADE,
                PRIMARY KEY (sid, cmd));
            CREATE TABLE IF NOT EXISTS media.aliases (
                alias TEXT PRIMARY KEY,
                real TEXT);
            CREATE TABLE IF NOT EXISTS media.blacklist_associations (
                cmd TEXT REFERENCES media.commands(cmd) ON DELETE CASCADE,
                image_key TEXT,
                uid CHARACTER(18),
                PRIMARY KEY (cmd, image_key, uid));
            """
        )
        self.bot.db_connection.commit()

        collection_keys, collection_hashes = (
            get_starting_keys_hashes(self.bot.s3_bucket)
        )
        sync_s3_db(self.bot.db_connection, collection_keys, collection_hashes)

        cascade_deleted_referenced_aliases(self.bot.db_connection)

        self.sent_messages_image_urls = dict()

    @commands.command(aliases=["yo", "hey", "makubot"])
    async def randomimage(self, ctx):
        """Get a totally random image!"""
        chosen_path = get_random_image(self.bot.db_connection)
        chosen_url = util.url_from_s3_key(
            self.bot.s3_bucket,
            self.bot.s3_bucket_location,
            chosen_path,
            improve=True)
        logging.info(f"Sending url in randomimage func: {chosen_url}")
        image_embed = await generate_image_embed(
            ctx, chosen_url, call_bot_name=True)
        sent_message = await ctx.send(embed=image_embed)
        self.sent_messages_image_urls[sent_message.id] = chosen_url
        if not await util.url_is_image(chosen_url):
            new_url = util.improve_url(chosen_url)
            logger.info(
                "URL wasn't image, so turned to text URL. "
                f"{chosen_url} -> {new_url}")
            await sent_message.edit(embed=None, content=new_url)

    @commands.command(hidden=True)
    async def send_image_func(self, ctx):
        if ctx.invoked_with == "send_image_func":
            await ctx.send("Nice try, fucker")
            return
        invoked_command = ctx.invoked_with.lower()
        cmd = get_cmd_from_alias(ctx.bot.db_connection, invoked_command)
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
        chosen_path = f"pictures/{cmd}/{chosen_key}"
        chosen_url = util.url_from_s3_key(
            ctx.bot.s3_bucket, ctx.bot.s3_bucket_location, chosen_path,
            improve=True)
        logging.info(f"Sending url in send_image func: {chosen_url}")
        image_embed = await generate_image_embed(ctx, chosen_url)
        sent_message = await ctx.send(embed=image_embed)
        self.sent_messages_image_urls[sent_message.id] = chosen_url
        if not await util.url_is_image(chosen_url):
            new_url = util.improve_url(chosen_url)
            logger.info(
                "URL wasn't image, so turned to text URL. "
                f"{chosen_url} -> {new_url}")
            await sent_message.edit(embed=None, content=new_url)

    @commands.command()
    async def showimage(self, ctx, cmdimgpath):
        """Shows an image as though you got it randomly! Cheater."""
        try:
            cmd, image_key = cmdimgpath.split("/")
        except (AttributeError, ValueError):
            await ctx.send(
                "Please use the form cmd/img, eg lupo/happy.jpg")
            return
        cmd = get_cmd_from_alias(self.bot.db_connection, cmd)
        if not cmd:
            await ctx.send("That isn't an image command :?")
            return
        if not image_exists_in_cmd(self.bot.db_connection, image_key, cmd):
            await ctx.send("I can't find that image :?")
            return
        chosen_path = f"pictures/{cmd}/{image_key}"
        chosen_url = util.url_from_s3_key(
            ctx.bot.s3_bucket, ctx.bot.s3_bucket_location, chosen_path,
            improve=True)
        logging.info(f"Sending url in showimage func: {chosen_url}")
        image_embed = await generate_image_embed(ctx, chosen_url)
        sent_message = await ctx.send(embed=image_embed)
        self.sent_messages_image_urls[sent_message.id] = chosen_url
        if not await util.url_is_image(chosen_url):
            new_url = util.improve_url(chosen_url)
            logger.info(
                "URL wasn't image, so turned to text URL. "
                f"{chosen_url} -> {new_url}")
            await sent_message.edit(embed=None, content=new_url)

    @commands.command(hidden=True)
    async def whatwassentin(self, ctx, message: discord.Message):
        message_id = message.id
        if message_id not in self.sent_messages_image_urls:
            await ctx.send("idk man")
            return
        await ctx.send(self.sent_messages_image_urls[message_id])

    @commands.command(aliases=["listimagecommands"])
    async def listreactions(self, ctx):
        """List all my reactions (image commands)"""
        all_invocations = get_all_cmds_aliases_from_db(self.bot.db_connection)
        all_invocations_alphabetized = sorted(all_invocations)
        pictures_desc = ", ".join(all_invocations_alphabetized)
        await util.displaytxt(ctx, pictures_desc)

    @commands.command(hidden=True, aliases=["realinvocation"])
    async def real_invocation(self, ctx, alias):
        real_cmd = get_cmd_from_alias(
            self.bot.db_connection, alias)
        if real_cmd == alias:
            await ctx.send(f"{real_cmd} is the actual function!")
        if real_cmd:
            await ctx.send(f"{alias} is an alias for {real_cmd}!")
        else:
            await ctx.send(f"Hmm, I don't think {alias} is an alias...")

    @commands.command()
    async def howbig(self, ctx, cmd):
        """Tells you how many images are in a command"""
        real_cmd = get_cmd_from_alias(self.bot.db_connection, cmd)
        if not real_cmd:
            await ctx.send(f"{cmd} isn't an image command :o")
            return
        cmd_sizes = get_cmd_sizes(self.bot.db_connection)
        cmd_size = cmd_sizes[real_cmd]
        image_plurality = "image" if cmd_size == 1 else "images"
        base_size_msg = f"{cmd} has {cmd_size} {image_plurality}!"
        if not ctx.guild:
            await ctx.send(base_size_msg)
            return
        uid = ctx.author.id
        user_sids = get_user_sids(self.bot, uid)
        sid = ctx.guild.id
        cmd_size_server, cmd_size_user = get_cmd_size_server_user(
            self.bot.db_connection, real_cmd, uid, sid, user_sids)
        server_size_msg = (
            f"Anyone on the server can pull {cmd_size_server} of them!")
        user_size_msg = (
            f"You can personally pull {cmd_size_user} of them here!")
        if cmd_size == cmd_size_server:
            await ctx.send(base_size_msg)
        elif cmd_size_server == cmd_size_user:
            await ctx.send(f"{base_size_msg} {server_size_msg}")
        else:
            await ctx.send(
                f"{base_size_msg} {server_size_msg} {user_size_msg}")

    @commands.is_owner()
    @commands.command()
    async def deletecmd(self, ctx, cmd):
        cmd = get_cmd_from_alias(self.bot.db_connection, cmd)
        if not cmd:
            await ctx.send("That isn't an image command :?")
            return
        cmd_info_dict = cmd_info(self.bot.db_connection, cmd)
        uid = cmd_info_dict["uid"]
        origin_sids = cmd_info_dict["origin_sids"]
        uid_user = self.bot.get_user(uid) if uid else None
        uid_user_str = (
            f"{uid_user.name}#{uid_user.discriminator}"
            if uid_user else f"Unknown ({uid})")
        origin_servers = [self.bot.get_guild(sid) for sid in origin_sids]

        logger.info(
            f"Deleting {cmd}."
            f"Was at pictures/{cmd} "
            f"{uid_user_str=}, {origin_servers=}.")

        cmd_aliases = get_cmd_aliases_from_db(self.bot.db_connection, cmd)
        cmd_aliases.add(cmd)
        delete_cmd_and_all_images(self.bot.db_connection, cmd)
        cascade_deleted_referenced_aliases(self.bot.db_connection)
        cmd_bucket = boto3.resource('s3').Bucket(self.bot.s3_bucket)
        cmd_bucket.objects.filter(Prefix=f"pictures/{cmd}").delete()
        send_image_func_ref = self.bot.get_command("send_image_func")
        self.bot.get_command("send_image_func").aliases = [
            alias for alias in send_image_func_ref.aliases
            if alias not in cmd_aliases
        ]
        for alias in cmd_aliases:
            logger.info(f"Removing alias {alias}...")
            self.bot.all_commands.pop(alias)

        await ctx.send(f"Command {cmd} deleted!")

    @commands.is_owner()
    @commands.command()
    async def deleteimage(self, ctx, cmdimgpath):
        try:
            cmd, image_key = cmdimgpath.split("/")
        except (AttributeError, ValueError):
            await ctx.send(
                "Please use the form cmd/img, eg lupo/happy.jpg")
            return
        cmd = get_cmd_from_alias(self.bot.db_connection, cmd)
        if not cmd:
            await ctx.send("That isn't an image command :?")
            return
        image_info_dict = image_info(
            self.bot.db_connection, cmd, image_key)
        if not image_info_dict:
            await ctx.send("I can't find that image :?")
            return
        uid = image_info_dict["uid"]
        sid = image_info_dict["sid"]
        md5 = image_info_dict["md5"]
        uid_user = self.bot.get_user(uid) if uid else None
        uid_user_str = (
            f"{uid_user.name}#{uid_user.discriminator}"
            if uid_user else f"Unknown ({uid})")
        sid_server = self.bot.get_guild(sid) if sid else None
        sid_server_str = sid_server.name if sid_server else f"Unknown ({sid})"
        logger.info(
            f"Deleting {cmd}/{image_key}. "
            f"Was at pictures/{cmd}/{image_key}. "
            f"{uid_user_str=}, {sid_server_str=}, {md5=}.")
        full_image_key = f"pictures/{cmd}/{image_key}"

        delete_image_from_db(self.bot.db_connection, cmd, image_key)

        S3.delete_object(
            Bucket=self.bot.s3_bucket,
            Key=full_image_key
        )
        await ctx.send("Image deleted!")

        images_remaining = get_all_cmd_images_from_db(
            self.bot.db_connection, cmd)
        if not images_remaining:
            cmd_aliases = get_cmd_aliases_from_db(self.bot.db_connection, cmd)
            cmd_aliases.add(cmd)
            delete_cmd_and_all_images(self.bot.db_connection, cmd)
            cascade_deleted_referenced_aliases(self.bot.db_connection)
            send_image_func_ref = self.bot.get_command("send_image_func")
            self.bot.get_command("send_image_func").aliases = [
                alias for alias in send_image_func_ref.aliases
                if alias not in cmd_aliases
            ]
            for alias in cmd_aliases:
                logger.info(f"Removing alias {alias}...")
                self.bot.all_commands.pop(alias)
            await ctx.send("Also deleted command, as it is now empty.")

    @commands.command(aliases=["topten"])
    async def bigten(self, ctx):
        """List my ten biggest image commands!"""
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

    @commands.command(hidden=True, aliases=["getcmdinfo"])
    async def get_cmd_info(self, ctx, cmd):
        real_cmd = get_cmd_from_alias(self.bot.db_connection, cmd)
        if not real_cmd:
            await ctx.send("That's not an image command :?")
            return
        cmd_info_dict = cmd_info(self.bot.db_connection, real_cmd)
        uid = cmd_info_dict["uid"]
        origin_sids = cmd_info_dict["origin_sids"]
        uid_user = self.bot.get_user(uid)
        uid_user_str = (
            f"{uid_user.name}#{uid_user.discriminator}"
            if uid_user else f"Unknown ({uid})")
        origin_sid_servers = [self.bot.get_guild(sid) for sid in origin_sids]
        origin_sid_server_strs = [
            origin_sid_servers[i].name if origin_sid_servers[i]
            else f"Unknown ({origin_sids[i]})"
            for i in range(len(origin_sid_servers))]
        await ctx.send(
            f"{cmd} is at pictures/{real_cmd}. {uid_user_str=}, "
            f"{origin_sid_server_strs=}.")

    @commands.command(hidden=True, aliases=["getimageinfo", "getimginfo"])
    async def get_image_info(self, ctx, cmdimgpath):
        try:
            cmd, image_key = cmdimgpath.split("/")
        except (AttributeError, ValueError):
            await ctx.send(
                "Please use the form cmd/img, eg lupo/happy.jpg")
            return
        real_cmd = get_cmd_from_alias(self.bot.db_connection, cmd)
        if not real_cmd:
            await ctx.send("That isn't an image command :?")
            return
        image_info_dict = image_info(
            self.bot.db_connection, real_cmd, image_key)
        if not image_info_dict:
            await ctx.send("I can't find that image :?")
            return
        uid = image_info_dict["uid"]
        sid = image_info_dict["sid"]
        md5 = image_info_dict["md5"]
        uid_user = self.bot.get_user(uid) if uid else None
        uid_user_str = (
            f"{uid_user.name}#{uid_user.discriminator}"
            if uid_user else f"Unknown ({uid})")
        sid_server = self.bot.get_guild(sid) if sid else None
        sid_server_str = sid_server.name if sid_server else f"Unknown ({sid})"
        await ctx.send(
            f"{cmd}/{image_key} is at pictures/{real_cmd}/{image_key}. "
            f"{uid_user_str=}, {sid_server_str=}, {md5=}.")

    @commands.is_owner()
    @commands.command(hidden=True, aliases=["setcmdowner"])
    async def set_cmd_images_owner(self, ctx, cmd, user: discord.User):
        uid = user.id
        cmd = get_cmd_from_alias(self.bot.db_connection, cmd)
        if not cmd:
            await ctx.send("That's not an image command :?")
            return
        set_cmd_images_owner_on_db(self.bot.db_connection, cmd, uid)
        await ctx.send("Done!")

    @commands.is_owner()
    @commands.command(hidden=True, aliases=["setcmdserver"])
    async def set_cmd_images_server(self, ctx, cmd, sid):
        assert len(sid) == 18
        cmd = get_cmd_from_alias(self.bot.db_connection, cmd)
        if not cmd:
            await ctx.send("That's not an image command :?")
            return
        set_cmd_images_server_on_db(self.bot.db_connection, cmd, sid)
        await ctx.send("Done!")

    @commands.command(hidden=True)
    async def imagesin(self, ctx, cmd):
        """Shows you all images in a command. Extremely spammy."""
        cmd = get_cmd_from_alias(self.bot.db_connection, cmd)
        if not cmd:
            await ctx.send("That's not an image command :?")
            return
        images = get_all_cmd_images_from_db(
            self.bot.db_connection, cmd)
        image_paths = [f"pictures/{cmd}/{image_key}" for image_key in images]
        image_urls = [
            util.url_from_s3_key(
                ctx.bot.s3_bucket, ctx.bot.s3_bucket_location, path,
                improve=True)
            for path in image_paths]
        image_urls_str = "\n".join(image_urls)
        await util.displaytxt(ctx, image_urls_str, separator="\n")

    @commands.group(aliases=["imgbl", "imgblacklist", "imagebl"])
    async def imageblacklist(self, ctx):
        """
        See, add to, or remove from your blacklisted images!
        mb.imageblacklist
        mb.imageblacklist add imagecommand/image01.png
        mb.imageblacklist remove imagecommand/image01.png
        """
        if ctx.invoked_subcommand is not None:
            return
        cmd_image_pairs = get_user_blacklist(
            self.bot.db_connection, ctx.author.id)
        if not cmd_image_pairs:
            await ctx.send("Looks like you haven't blacklisted any images!")
            return
        cmd_image_pairs_text = ", ".join([
            f"{cmd}/{image_key}" for cmd, image_key in cmd_image_pairs])
        await ctx.send(f"Your blacklisted images: {cmd_image_pairs_text}")

    @imageblacklist.command()
    async def add(self, ctx, cmd_and_key: str):
        """
        Add an image to a list of images that you don't want to see
        mb.imageblacklist add imagecommand/image01.png
        """
        uid = ctx.author.id
        try:
            cmd, image_key = cmd_and_key.split("/")
        except ValueError:
            await ctx.send(
                "Hmm, I can't tell what the command/key combination is!")
            return
        cmd = get_cmd_from_alias(self.bot.db_connection, cmd)
        if not cmd:
            await ctx.send("That's not an image command :?")
            return
        if not image_exists_in_cmd(self.bot.db_connection, image_key, cmd):
            await ctx.send("I can't find that image :?")
            return
        add_blacklist_association(self.bot.db_connection, cmd, image_key, uid)
        await ctx.send("Done!")

    @imageblacklist.command()
    async def remove(self, ctx, cmd_and_key: str):
        """
        Undo a mb.imageblacklist add command
        mb.imageblacklist remove imagecommand/image01.png
        """
        uid = ctx.author.id
        try:
            cmd, image_key = cmd_and_key.split("/")
        except ValueError:
            await ctx.send(
                "Hmm, I can't tell what the command/key combination is!")
            return
        cmd = get_cmd_from_alias(self.bot.db_connection, cmd)
        if not cmd:
            await ctx.send("That's not an image command :?")
            return
        if not image_exists_in_cmd(self.bot.db_connection, image_key, cmd):
            await ctx.send("I can't find that image :?")
            return
        remove_blacklist_association(
            self.bot.db_connection, cmd, image_key, uid)
        await ctx.send("Sure!")

    @commands.command(hidden=True)
    async def nolike(self, ctx, cmd_and_key: str):
        await self.add_to_blacklist(ctx, cmd_and_key)

    @commands.command(hidden=True)
    async def relike(self, ctx, cmd_and_key: str):
        await self.remove_from_blacklist(ctx, cmd_and_key)


def setup(bot):
    logger.info("picturecommands starting setup")
    bot.add_cog(ReactionImages(bot))
    bot.add_cog(PictureAdder(bot))
    image_command_invocations = list(
        get_all_cmds_aliases_from_db(bot.db_connection))

    bot.get_command("send_image_func").aliases += image_command_invocations
    for invocation in image_command_invocations:
        bot.all_commands[invocation] = bot.all_commands["send_image_func"]

    logger.info("picturecommands ending setup")
