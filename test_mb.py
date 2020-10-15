from src.picturecommands_utils import (
    as_text,
    as_ids,
    suggest_audio_video_bitrate,
)
from src.util import (
    improve_url,
    url_from_s3_key,
    get_nonconflicting_filename,
    split_text_to_chunks,
)
from src import ctxhelpers


id_text_pairs = [
    ["1", "1"],
    ["hi", "hi"],
    [203285581004931072, "203285581004931072"],
    [3, 3],
    [
        {"Hello": 203285581004931072},
        {"Hello": "203285581004931072"}
    ],
    [None, None]
]


def test_as_text():
    for id_val, text_val in id_text_pairs:
        assert as_text(id_val) == text_val


def test_as_ids():
    for id_val, text_val in id_text_pairs:
        assert as_ids(text_val) == id_val


def test_suggest_audio_video_bitrate():
    assert suggest_audio_video_bitrate(1) == (64000, 31936000)
    assert suggest_audio_video_bitrate(60) == (64000, 469333)


def test_improve_url():
    assert improve_url("google.com") == "google.com"
    assert improve_url("hi there.com") == "hi+there.com"


def test_url_from_s3_key():
    assert url_from_s3_key(
        s3_bucket="makumistake",
        s3_bucket_location="us-east-2",
        s3_key="mykey.txt"
    ) == "https://makumistake.s3.us-east-2.amazonaws.com/mykey.txt"


def test_get_nonconflicting_filename():
    possible_keys = {
        "hithere.jpg",
        "unknown.png",
        "unknown0.png",
        "image.png",
        "image.jpg",
        "image2.png",
        "image.jpg.jpg",
    }

    for possible_key in possible_keys:
        new_filename = get_nonconflicting_filename(
            possible_key,
            existing_keys=possible_keys)
        assert new_filename not in possible_keys


class objectview(object):
    def __init__(self, d):
        self.__dict__ = d


def get_example_ctx():
    content_example = objectview({"content": "mb.lupo what's up?"})
    ctx_example = {
        "prefix": "mb.",
        "invoked_with": "lupo",
        "message": content_example,
    }
    return objectview(ctx_example)


def test_get_invocation():
    assert ctxhelpers.get_invocation(get_example_ctx()) == "mb.lupo"


def test_get_content_without_invocation():
    ctx = get_example_ctx()
    assert ctxhelpers.get_content_without_invocation(ctx) == "what's up?"


def test_get_invoked_command():
    assert ctxhelpers.get_invoked_command(get_example_ctx()) == "lupo"


def test_split_text_to_chunks():
    text = "1 1 1 1234 12345 12 123456 1234 123 1 12 12345678"
    assert tuple(split_text_to_chunks(text, block_size=4)) == (
        "1 1",
        "1",
        "1234",
        "1234",
        "5 12",
        "1234",
        "56",
        "1234",
        "123",
        "1 12",
        "1234",
        "5678"
    )
