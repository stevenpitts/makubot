from src.picturecommands_utils import (
    as_text,
    as_ids,
    suggest_audio_video_bitrate,
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
