"""
Kale, dependency-vrije helpers voor Debat Direct's publieke JSON-API's --
los van scrapy zodat ze ook zonder draaiende spider getest kunnen worden.
Geen HTTP hierin; de spider doet het ophalen, dit bestand alleen het
URL's bouwen en de respons-JSON interpreteren.

Bronnen (zie ook docs/tk-data-sources-overview.md in de hoofdrepo):
- Zoek-API (`SEARCH_URL`): doorzoekt transcripties van alle Kamerdebatten,
  geeft per debat de matchende spreekbeurten terug incl. een highlight-
  snippet. Vervangt de oude debatgemist.tweedekamer.nl-HTML-scrape
  (~/src/echokamer, debatgemist/spiders/zoeken.py) -- dezelfde index,
  nu als JSON i.p.v. server-rendered HTML.
- Detail-API (`DEBATE_DETAIL_URL`): per debat het ruwe HLS-manifest
  (video.vodUrl) + de volledige events-tijdlijn (eventStart/eventType/
  objectId per beurtwisseling), nodig om de exacte clipgrenzen te bepalen.
"""

import re
from datetime import datetime
from urllib.parse import quote

SEARCH_URL = "https://cdn.debatdirect.tweedekamer.nl/search"
DEBATE_DETAIL_URL = "https://api.debatdirect.tweedekamer.nl/debates/{id}"
SEARCH_PAGE_SIZE = 20
SEARCH_APP_VERSION = "11.22.8"

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(text):
    return _SLUG_RE.sub("-", text.lower()).strip("-")


def search_params(term, offset):
    return {
        "q": term, "sortering": "relevant", "vanaf": offset,
        "appVersion": SEARCH_APP_VERSION, "platform": "web", "totalFormat": "new",
    }


def build_debate_url(debate):
    """Mens-leesbare Debat Direct-paginalink, zie
    docs/tk-data-sources-overview.md punt 48 in de hoofdrepo voor de
    URL-opbouw."""
    category_id = debate["categoryIds"][0] if debate.get("categoryIds") else "overig"
    return f"https://debatdirect.tweedekamer.nl/{debate['debateDate']}/{category_id}/{debate['locationId']}/{debate['slug']}"


def build_deep_link(debate_url, event_type, event_start):
    """Debat Direct's eigen `?event={eventType}{eventStart}`-diepe-link,
    die de pagina zelf naar het juiste moment laat springen (bevestigd met
    een door de gebruiker aangeleverde link, zie docs/handoff.md)."""
    return f"{debate_url}?event={event_type}{quote(event_start, safe='')}"


def build_manifest_url(vod_url, starts_at, ends_at):
    """Het afspeelbare HLS-manifest voor één debat (zelfde constructie als
    pipeline/fetch_subtitles.py in de hoofdrepo: zonder start/end-params
    ontbreekt de ondertitel-track stilzwijgend, niet relevant hier maar de
    url-vorm is identiek)."""
    return f"{vod_url}&start={quote(starts_at, safe='')}&end={quote(ends_at, safe='')}"


def event_timeline_seconds(events, starts_at):
    """Alle `eventStart`-tijden uit een debat's volle events-array, omgezet
    naar seconden t.o.v. `starts_at` (t=0 in de video) en oplopend
    gesorteerd. Events zonder eventStart (zou niet moeten voorkomen) worden
    overgeslagen."""
    seconds = [
        (datetime.fromisoformat(e["eventStart"]) - starts_at).total_seconds()
        for e in events if e.get("eventStart")
    ]
    seconds.sort()
    return seconds


def find_clip_bounds(timeline_seconds, total_seconds, own_seconds, margin_seconds):
    """(clip_start, clip_duration) voor een spreekbeurt die begint op
    `own_seconds`: van dit moment tot het eerstvolgende event in
    `timeline_seconds` (van welk type dan ook), elk met `margin_seconds`
    extra ervoor/erachter. Zonder een volgend event (laatste spreekbeurt
    van het debat) is `total_seconds` (einde vergadering) de grens."""
    next_times = [t for t in timeline_seconds if t > own_seconds + 0.5]
    end_seconds = min(next_times) if next_times else total_seconds
    clip_start = max(0.0, own_seconds - margin_seconds)
    clip_end = min(total_seconds, end_seconds + margin_seconds)
    return clip_start, max(1.0, clip_end - clip_start)
