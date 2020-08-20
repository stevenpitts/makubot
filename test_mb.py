from src.picturecommands_utils import (
    as_text,
    as_ids,
    suggest_audio_video_bitrate,
)
from src.util import (
    improve_url,
    url_from_s3_key,
    get_nonconflicting_filename,
)

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
        possible_keys_without_key = possible_keys - {possible_key}
        new_filename_without_key = get_nonconflicting_filename(
            possible_key,
            existing_keys=possible_keys_without_key)
        assert new_filename not in possible_keys
        assert new_filename_without_key == possible_key