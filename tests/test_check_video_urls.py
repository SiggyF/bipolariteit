from pipeline.check_video_urls import first_video_level_uri

MASTER_PLAYLIST = """#EXTM3U
#EXT-X-VERSION:7
#EXT-X-MEDIA:TYPE=AUDIO,GROUP-ID="audio",NAME="Original Audio",URI="Stream(06)/prog_index.m3u8"
#EXT-X-STREAM-INF:PROGRAM-ID=1,BANDWIDTH=408322,RESOLUTION=320x180,AUDIO="audio"
Stream(01)/prog_index.m3u8?start=2026-07-01T13%3A35%3A26.0000000%2B02%3A00
#EXT-X-STREAM-INF:PROGRAM-ID=1,BANDWIDTH=504260,RESOLUTION=640x360,AUDIO="audio"
Stream(02)/prog_index.m3u8?start=2026-07-01T13%3A35%3A26.0000000%2B02%3A00
"""


def test_first_video_level_uri_picks_first_stream_inf_target():
    assert first_video_level_uri(MASTER_PLAYLIST) == (
        "Stream(01)/prog_index.m3u8?start=2026-07-01T13%3A35%3A26.0000000%2B02%3A00"
    )


def test_first_video_level_uri_returns_none_without_stream_inf():
    assert first_video_level_uri("#EXTM3U\n#EXT-X-VERSION:7\n") is None
