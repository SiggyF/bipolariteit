from pipeline.fetch_subtitles import build_manifest_url, find_subtitle_manifest_url, find_vtt_url

MANIFEST_URL = "https://livestreaming.b67v2.tweedekamer.nl/2026-07-01/plenairezaal/index.m3u8?hd=1&start=2026-07-01T13%3A35%3A26%2B0200"

MASTER_PLAYLIST = """#EXTM3U
#EXT-X-VERSION:7
#EXT-X-STREAM-INF:PROGRAM-ID=1,BANDWIDTH=428000,RESOLUTION=320x180,AUDIO="audio1",SUBTITLES="subs"
Stream(01)/prog_index.m3u8
#EXT-X-MEDIA:TYPE=SUBTITLES,GROUP-ID="subs",NAME="Nederlands",DEFAULT=NO,FORCED=NO,URI="subtitles/nl-pol_VOD.m3u8?start=2026-07-01T13%3A35%3A26.0000000%2B02%3A00",LANGUAGE="nl-pol"
"""

SUBTITLE_PLAYLIST_URL = "https://livestreaming.b67v2.tweedekamer.nl/2026-07-01/plenairezaal/subtitles/nl-pol_VOD.m3u8?start=2026-07-01T13%3A35%3A26.0000000%2B02%3A00"

SUBTITLE_PLAYLIST = """#EXTM3U
#EXT-X-VERSION:4
#EXT-X-PLAYLIST-TYPE:VOD
#EXTINF:41968
nl-pol/vod.vtt?start=2026-07-01T13%3A35%3A26.0000000%2B02%3A00
#EXT-X-ENDLIST
"""


def test_find_subtitle_manifest_url_resolves_relative_uri():
    assert find_subtitle_manifest_url(MASTER_PLAYLIST, MANIFEST_URL) == (
        "https://livestreaming.b67v2.tweedekamer.nl/2026-07-01/plenairezaal/"
        "subtitles/nl-pol_VOD.m3u8?start=2026-07-01T13%3A35%3A26.0000000%2B02%3A00"
    )


def test_find_subtitle_manifest_url_returns_none_without_subtitles_track():
    assert find_subtitle_manifest_url("#EXTM3U\n#EXT-X-VERSION:7\n", MANIFEST_URL) is None


def test_find_vtt_url_resolves_relative_uri_against_playlist_url():
    assert find_vtt_url(SUBTITLE_PLAYLIST, SUBTITLE_PLAYLIST_URL) == (
        "https://livestreaming.b67v2.tweedekamer.nl/2026-07-01/plenairezaal/"
        "subtitles/nl-pol/vod.vtt?start=2026-07-01T13%3A35%3A26.0000000%2B02%3A00"
    )


def test_find_vtt_url_returns_none_without_media_segment():
    assert find_vtt_url("#EXTM3U\n#EXT-X-ENDLIST\n", SUBTITLE_PLAYLIST_URL) is None


def test_build_manifest_url_appends_url_encoded_start_and_end():
    assert build_manifest_url(
        "https://livestreaming.b67v2.tweedekamer.nl/2026-07-01/plenairezaal/index.m3u8?hd=1",
        "2026-07-01T13:35:26+0200",
        "2026-07-02T01:14:54+0200",
    ) == (
        "https://livestreaming.b67v2.tweedekamer.nl/2026-07-01/plenairezaal/index.m3u8?hd=1"
        "&start=2026-07-01T13%3A35%3A26%2B0200&end=2026-07-02T01%3A14%3A54%2B0200"
    )
