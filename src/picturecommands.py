import discord
from discord.ext import commands
from discord.utils import escape_markdown
import logging
from pathlib import Path
import os
import random
import aiohttp
import asyncio
import shutil
import concurrent
import subprocess
import youtube_dl
import tempfile
import urllib
import hashlib
from datetime import datetime
try:
    import boto3
    S3 = boto3.client("s3")
except ImportError:
    pass  # Let the exception get raised later, they might be running locally
from . import commandutil

SCRIPT_DIR = Path(__file__).parent
PARENT_DIR = SCRIPT_DIR.parent
DATA_DIR = PARENT_DIR / 'data'
PICTURES_DIR = DATA_DIR / 'pictures'

logger = logging.getLogger()


class NotVideo(Exception):
    pass


async def s3_keys(Bucket, Prefix='/', Delimiter='/', start_after=''):
    s3_paginator = boto3.client('s3').get_paginator('list_objects_v2')
    Prefix = Prefix[1:] if Prefix.startswith(Delimiter) else Prefix
    start_after = ((start_after or Prefix) if Prefix.endswith(Delimiter)
                   else start_after)
    keys = []
    for page in s3_paginator.paginate(Bucket=Bucket,
                                      Prefix=Prefix,
                                      StartAfter=start_after):
        for content in page.get('Contents', ()):
            keys.append(content['Key'])
        await asyncio.sleep(0)
    return keys


async def s3_hashes(Bucket, Prefix='/', Delimiter='/', start_after=''):
    s3_paginator = boto3.client('s3').get_paginator('list_objects_v2')
    Prefix = Prefix[1:] if Prefix.startswith(Delimiter) else Prefix
    start_after = ((start_after or Prefix) if Prefix.endswith(Delimiter)
                   else start_after)
    hashes = []
    for page in s3_paginator.paginate(Bucket=Bucket,
                                      Prefix=Prefix,
                                      StartAfter=start_after):
        for content in page.get('Contents', ()):
            hashes.append(content['ETag'].strip('"').strip("'"))
        await asyncio.sleep(0)
    return hashes


def url_from_s3_key(s3_bucket, s3_key, validate=True):
    bucket_location = S3.get_bucket_location(Bucket=s3_bucket)
    bucket_location = bucket_location['LocationConstraint']
    url = (f"https://{s3_bucket}.s3.{bucket_location}"
           f".amazonaws.com/{s3_key}")
    if validate:
        # Raise HTTPError if url 404s or whatever
        try:
            urllib.request.urlopen(url)
        except urllib.error.HTTPError as e:
            print(f"URL {url} failed due to {e.code} {e.reason}")
            raise
    return url


async def generate_image_embed(ctx,
                               url,
                               call_bot_name=False):
    bot_nick = ctx.me.nick or ctx.me.name
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
        quality_format = 'best' if do_raw else 'best[filesize<8M]/worst'
        ydl_options = {
            # 'logger': logger,
            'quiet': True,
            'no_warnings': True,
            'format': quality_format,
            "outtmpl": f"{temp_dir}/%(title)s-%(id)s.%(ext)s"
            }
        with youtube_dl.YoutubeDL(ydl_options) as ydl:
            await status_message.edit(content=f"Downloading...{loading_emoji}")
            download_start_time = datetime.now()
            await asyncio.get_running_loop().run_in_executor(
                None, ydl.extract_info, url)
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
    cmds = ['ffprobe',
            '-v', 'error',
            '-show_entries',
            'format=duration',
            '-of',
            'default=noprint_wrappers=1:nokey=1',
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
    cmds = ['ffmpeg',
            '-y',
            '-i', video_input,
            # '-vf', "scale=300:200",
            '-b:v', str(video_bitrate),
            '-b:a', str(audio_bitrate),
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


async def collection_has_image_bytes(collection: str,
                                     image_bytes,
                                     s3_bucket=False):
    image_hash = hashlib.md5(image_bytes).hexdigest()
    if s3_bucket:
        existing_checksums = await s3_hashes(Bucket=s3_bucket,
                                             Prefix=f"pictures/{collection}/"
                                             )
        return image_hash in existing_checksums
    else:
        collection_dir = PICTURES_DIR / collection
        if not collection_dir.exists():
            return False
        existing_files = (collection_dir / picture_filename
                          for picture_filename in os.listdir(collection_dir))
        existing_bytes = (file.read_bytes() for file in existing_files)
        existing_checksums = (hashlib.md5(bytes).hexdigest()
                              for bytes in existing_bytes)
        return image_hash in existing_checksums


class PictureAdder(discord.ext.commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.temp_save_dir = self.bot.shared['temp_dir']

    async def image_suggestion(self, image_collection, filename, requestor,
                               image_bytes=None, status_message=None):
        image_dir = PICTURES_DIR / image_collection
        try:
            if image_bytes is None:
                with open(self.temp_save_dir / filename, "rb") as f:
                    image_bytes = f.read()
            else:
                filename = commandutil.get_nonconflicting_filename(
                    filename, self.temp_save_dir)
                with open(self.temp_save_dir / filename, "wb") as f:
                    f.write(image_bytes)
            if await collection_has_image_bytes(image_collection,
                                                image_bytes,
                                                self.bot.s3_bucket):
                response = (
                    f"The image {filename} appears already in the collection!")
                await requestor.send(response)
                if status_message:
                    await status_message.edit(content=response)
                return
            if self.bot.s3_bucket:
                list_query = S3.list_objects_v2(
                    Bucket=self.bot.s3_bucket,
                    Prefix=(f"pictures/{image_collection}"))
                is_new = list_query["KeyCount"] == 0
            else:
                is_new = image_dir.exists()
            new_addition = '' if is_new else '***NEW*** '
            proposal = (f"Add image {filename} to {new_addition}"
                        f"{image_collection}? Requested by {requestor.name}")
            try:
                request = await self.bot.makusu.send(
                    proposal, file=discord.File(self.temp_save_dir
                                                / filename))
                if status_message:
                    await status_message.edit(content="Sent to Maku!")
            except discord.errors.HTTPException:
                response = f"Sorry, {filename} is too large ;~;"
                await requestor.send(response)
                if status_message:
                    await status_message.edit(content=response)
                return
            no_emoji, yes_emoji = "❌", "✅"
            await request.add_reaction(no_emoji)
            await request.add_reaction(yes_emoji)

            async def get_approval(request_id):
                while True:
                    try:
                        request = await self.bot.makusu.fetch_message(
                            request_id)
                    except (aiohttp.client_exceptions.ServerDisconnectedError,
                            aiohttp.client_exceptions.ClientOSError,
                            discord.errors.HTTPException):
                        logger.warning(
                            f"Got error on {request_id}")
                        await asyncio.sleep(10)
                    reactions_from_maku = [
                        reaction.emoji for reaction in request.reactions
                        if reaction.count == 2 and reaction.emoji in (
                            no_emoji, yes_emoji)]
                    if len(reactions_from_maku) > 1:
                        await self.bot.makusu.send("You reacted twice...")
                    elif len(reactions_from_maku) == 1:
                        assert reactions_from_maku[0] in (yes_emoji, no_emoji)
                        return reactions_from_maku[0] == yes_emoji
                    await asyncio.sleep(0)

            await status_message.edit(content="Waiting for maku approval...")
            approval_start_time = datetime.now()
            approved = await get_approval(request.id)
            approval_time = datetime.now() - approval_start_time
            logger.info(f"{filename} took {approval_time} to get approved")
            await request.delete()
            if await collection_has_image_bytes(image_collection,
                                                image_bytes,
                                                self.bot.s3_bucket):
                response = (
                    f"The image {filename} appears already in the collection!")
                await requestor.send(response)
                if status_message:
                    await status_message.edit(content=response)
            elif approved:
                if self.bot.s3_bucket:
                    new_filename = commandutil.get_nonconflicting_filename(
                        filename, image_dir, s3_bucket=self.bot.s3_bucket)
                    S3.upload_file(
                        str(self.temp_save_dir / filename),
                        self.bot.s3_bucket,
                        f"pictures/{image_collection}/{new_filename}",
                        ExtraArgs={'ACL': 'public-read'})
                else:
                    image_dir.mkdir(parents=True, exist_ok=True)
                    new_filename = commandutil.get_nonconflicting_filename(
                        filename, image_dir)
                    shutil.move(self.temp_save_dir / filename,
                                image_dir / new_filename)
                self.bot.get_cog("ReactionImages").add_pictures_dir(
                    image_collection)
                response = f"Your image {new_filename} was approved!"
                await requestor.send(response)
                if status_message:
                    try:
                        await status_message.edit(content=response)
                    except discord.errors.NotFound:
                        print(f"{new_filename}, {request.id}, "
                              f"{requestor.name}")

            else:
                response = (f"Your image {filename} was not approved. "
                            "Feel free to ask Maku why ^_^")
                await status_message.edit(content=response)
                if status_message.channel != requestor.dm_channel:
                    await requestor.send(response)
        except (concurrent.futures._base.CancelledError,
                asyncio.exceptions.CancelledError):
            print(f"Cancelled error on {filename}")
        except BaseException as e:
            print(commandutil.get_formatted_traceback(e))
            response = f"Something went wrong with {filename}, sorry!"
            await requestor.send(response)
            if status_message:
                await status_message.edit(response)

    @commands.command(hidden=True, aliases=["aliasimage", "aliaspicture"])
    @commands.is_owner()
    async def add_picture_alias(self, ctx, ref_invocation, true_invocation):
        if not ref_invocation.isalnum() or not true_invocation.isalnum():
            await ctx.send("Please only include letters and numbers.")
            return
        elif self.bot.get_command(ref_invocation):
            await ctx.send(f"{ref_invocation} is already a command :<")
        elif not self.bot.get_command(true_invocation):
            await ctx.send(f"{true_invocation} isn't a command, though :<")
        else:
            aliases = self.bot.shared['data']['alias_pictures']
            if true_invocation in aliases:
                # true_invocation was in turn referencing another invocation
                true_invocation = aliases[true_invocation]
            true_command = self.bot.get_command(true_invocation)
            maps_to_image = (hasattr(true_command, "instance")
                             and isinstance(true_command.instance,
                                            ReactionImages))
            if maps_to_image:
                aliases[ref_invocation] = true_invocation
                true_command.aliases += [ref_invocation]
                self.bot.shared['pictures_commands'] += [ref_invocation]
                self.bot.all_commands[ref_invocation] = true_command
                await ctx.send("Added!")
            else:
                await ctx.send(f"{true_invocation} is not an image command :?")

    @commands.command(aliases=["randomimage", "yo", "hey", "makubot"])
    async def random_image(self, ctx):
        """For true shitposting."""
        if self.bot.s3_bucket:
            keys = await s3_keys(Bucket=self.bot.s3_bucket,
                                 Prefix="pictures/")
            chosen_key = random.choice(keys)
            chosen_url = url_from_s3_key(self.bot.s3_bucket, chosen_key)
            image_embed = await generate_image_embed(ctx,
                                                     chosen_url,
                                                     call_bot_name=True)
            await ctx.send(embed=image_embed)
        else:
            files = [Path(dirpath) / Path(filename)
                     for dirpath, dirnames, filenames in os.walk(PICTURES_DIR)
                     for filename in filenames]
            chosen_file = random.choice(files)
            await ctx.send(file=discord.File(chosen_file))

    @commands.command(aliases=["addimage", "addimageraw"])
    async def add_image(self, ctx, image_collection: str, *, urls: str = ""):
        """Requests an image be added.
        mb.addimage nao http://static.zerochan.net/Tomori.Nao.full.1901643.jpg
        Then, it'll be sent to maku for approval!"""
        do_raw = ctx.invoked_with == "addimageraw"
        if ' ' in image_collection:
            await ctx.send("Spaces replaced with underscores")
        image_collection = image_collection.strip().lower().replace(' ', '_')
        if not image_collection.isalnum():
            await ctx.send("Please only include letters and numbers.")
            return
        image_collection = self.bot.shared['data']['alias_pictures'].get(
            image_collection, image_collection)
        existing_command = self.bot.get_command(image_collection)
        command_taken = (existing_command is not None
                         and (not hasattr(existing_command, "instance")
                              or not isinstance(existing_command.instance,
                                                ReactionImages)))
        if command_taken:
            await ctx.send("That is already a command name.")
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
            except BaseException:
                await status_message.edit(content="Something went wrong ;a;")
                raise
            else:
                await status_message.edit(content="Sent to Maku for approval!")
                image_suggestion_coros.append(self.image_suggestion(
                    image_collection, filename, ctx.author,
                    image_bytes=data, status_message=status_message))
        all_suggestion_coros = asyncio.gather(*image_suggestion_coros)
        try:
            await all_suggestion_coros
        except BaseException as e:
            print(commandutil.get_formatted_traceback(e))
            all_suggestion_coros.cancel()


class ReactionImages(discord.ext.commands.Cog):

    async def send_image_func(ctx):
        if ctx.bot.s3_bucket:
            keys = await s3_keys(Bucket=ctx.bot.s3_bucket,
                                 Prefix=(f"pictures/{ctx.command.name}")
                                 )
            # s3_objects = s3_response["Contents"]
            # chosen_object = random.choice(s3_objects)
            # chosen_key = chosen_object["Key"]
            chosen_key = random.choice(keys)
            chosen_url = url_from_s3_key(ctx.bot.s3_bucket, chosen_key)
            image_embed = await generate_image_embed(ctx, chosen_url)
            await ctx.send(embed=image_embed)
        else:
            true_path = PICTURES_DIR / ctx.command.name
            file_to_send = true_path / random.choice(os.listdir(true_path))
            async with ctx.typing():
                await ctx.channel.send(file=discord.File(file_to_send))

    def __init__(self, bot):
        self.bot = bot
        self.bot.shared['pictures_commands'] = []
        self.image_aliases = {}
        for key, val in self.bot.shared['data']['alias_pictures'].items():
            self.image_aliases[val] = self.image_aliases.get(val, []) + [key]
        if bot.s3_bucket:
            toplevel_query = S3.list_objects_v2(Bucket=bot.s3_bucket,
                                                Prefix="pictures/",
                                                Delimiter="/")
            toplevel_dirs = [prefix['Prefix'].split("/")[-2]
                             for prefix
                             in toplevel_query.get("CommonPrefixes", [])]
            for folder_name in toplevel_dirs:
                self.add_pictures_dir(folder_name)
        else:
            for folder_name in os.listdir(PICTURES_DIR):
                self.add_pictures_dir(folder_name)

    def add_pictures_dir(self, folder_name: str):
        if folder_name in self.bot.shared['pictures_commands']:
            return
        self.bot.shared['pictures_commands'].append(folder_name)
        collection_aliases = self.image_aliases.get(folder_name, [])
        folder_command = commands.Command(
            ReactionImages.send_image_func,
            name=folder_name,
            brief=folder_name,
            aliases=collection_aliases,
            hidden=True)
        folder_command.instance = self
        folder_command.module = self.__module__
        self.bot.add_command(folder_command)
        for collection_alias in collection_aliases:
            self.bot.shared['pictures_commands'].append(collection_alias)

    @commands.command(aliases=["listreactions"])
    async def list_reactions(self, ctx):
        """List all my reactions"""
        pictures_desc = ', '.join(self.bot.shared['pictures_commands'])
        block_size = 1500
        text_blocks = [f'{pictures_desc[i:i+block_size]}'
                       for i in range(0, len(pictures_desc), block_size)]
        for text_block in text_blocks:
            await ctx.send(f"```{escape_markdown(text_block)}```")


def setup(bot):
    logger.info('picturecommands starting setup')
    bot.add_cog(ReactionImages(bot))
    bot.add_cog(PictureAdder(bot))
    logger.info('picturecommands ending setup')
