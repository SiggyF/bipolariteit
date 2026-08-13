from pipeline.enrich_video_url import build_video_url, find_best_match, search_dates_for


def _candidate(starts_at, ends_at, **extra):
    return {
        "startsAt": starts_at,
        "endsAt": ends_at,
        "debateDate": "2026-07-01",
        "categoryIds": ["landbouw"],
        "locationId": "plenaire-zaal",
        "slug": "stikstof-debat-13-30",
        **extra,
    }


def test_find_best_match_picks_closest_start_within_window():
    our_start, our_end = "2026-07-01T13:35:26", "2026-07-01T18:00:00"
    far = _candidate("2026-07-01T10:00:00+0200", "2026-07-01T18:00:00+0200")
    close = _candidate("2026-07-01T13:35:30+0200", "2026-07-01T18:00:04+0200")
    assert find_best_match([far, close], our_start, our_end) is close


def test_find_best_match_rejects_candidate_outside_start_window():
    our_start, our_end = "2026-07-01T13:35:26", "2026-07-01T18:00:00"
    too_far = _candidate("2026-07-01T09:00:00+0200", "2026-07-01T13:30:00+0200")
    assert find_best_match([too_far], our_start, our_end) is None


def test_find_best_match_rejects_candidate_failing_duration_ratio_sanitycheck():
    # zelfde starttijd, maar kandidaat duurt 10x zo lang -- vermoedelijk het
    # verkeerde debat ondanks de exacte starttijd-match (zie MAX_DURATION_RATIO)
    our_start, our_end = "2026-07-01T13:35:26", "2026-07-01T14:05:26"  # 30 min
    wrong_duration = _candidate("2026-07-01T13:35:26+0200", "2026-07-01T18:35:26+0200")  # 5 uur
    assert find_best_match([wrong_duration], our_start, our_end) is None


def test_find_best_match_returns_none_without_candidates():
    assert find_best_match([], "2026-07-01T13:35:26", "2026-07-01T18:00:00") is None


def test_build_video_url_composes_expected_shape():
    candidate = _candidate("2026-07-01T13:35:26+0200", "2026-07-01T18:00:00+0200")
    assert build_video_url(candidate) == (
        "https://debatdirect.tweedekamer.nl/2026-07-01/landbouw/plenaire-zaal/stikstof-debat-13-30/video"
    )


def test_build_video_url_returns_none_when_fields_missing():
    candidate = _candidate("2026-07-01T13:35:26+0200", "2026-07-01T18:00:00+0200", categoryIds=[])
    assert build_video_url(candidate) is None


def test_search_dates_for_regular_evening_start_is_single_day():
    assert search_dates_for("2026-07-01T20:35:26") == ["2026-07-01"]


def test_search_dates_for_over_midnight_start_includes_previous_day():
    # Debat Direct indexeert een over-middernacht-vergadering (bv. late
    # stemmingen) onder de dag waarop ze begon, niet de dag van dit tijdstip
    # zelf -- zie issue #83.
    assert search_dates_for("2023-07-07T01:04:12") == ["2023-07-06", "2023-07-07"]


def test_search_dates_for_handles_month_boundary():
    assert search_dates_for("2024-12-01T00:58:40") == ["2024-11-30", "2024-12-01"]
