from pipeline.build_static_data import _speaker_event_url


def test_speaker_event_url_strips_video_suffix_and_encodes_timestamp():
    video_url = "https://debatdirect.tweedekamer.nl/2026-07-01/landbouw/plenaire-zaal/stikstof-13-30/video"
    url = _speaker_event_url(video_url, "2026-07-01T17:12:59")
    assert url == (
        "https://debatdirect.tweedekamer.nl/2026-07-01/landbouw/plenaire-zaal/stikstof-13-30"
        "?event=speaker2026-07-01T17%3A12%3A59%2B0200"
    )


def test_speaker_event_url_uses_winter_offset_for_cet_dates():
    video_url = "https://debatdirect.tweedekamer.nl/2025-02-20/huisvesting/plenaire-zaal/stikstofontwikkelingen-15-00/video"
    url = _speaker_event_url(video_url, "2025-02-20T16:04:53")
    assert "%2B0100" in url  # CET (winter), niet CEST


def test_speaker_event_url_returns_none_without_video_url():
    assert _speaker_event_url(None, "2026-07-01T17:12:59") is None


def test_speaker_event_url_returns_none_without_published_at():
    assert _speaker_event_url("https://debatdirect.tweedekamer.nl/x/video", None) is None
