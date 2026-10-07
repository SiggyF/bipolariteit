"""
Spider: zoekt Debat Direct's volledige transcriptie-index op één of meer
termen en downloadt/clipt per treffer het bijbehorende videofragment.

Dit is de porting van de oude "zoeken"-spider uit ~/src/echokamer
(debatgemist/spiders/zoeken.py), die destijds debatgemist.tweedekamer.nl's
server-rendered HTML scrapete. Debatgemist is Debat Direct geworden (JS-SPA,
niks meer te scrapen in de server-HTML), maar dezelfde doorzoekbare index
bestaat nu als JSON-API (zie debatdirect_fragments/debatdirect.py) --
geen HTML-parsing meer nodig, en de zoek-API geeft meteen een
`eventType`+`eventStart` terug waarmee Debat Direct's eigen paginalink
naar het exacte moment springt.

Eén detail-call per uniek debat (niet per treffer): meerdere treffers in
hetzelfde debat delen dezelfde events-tijdlijn en hetzelfde HLS-manifest.
De clipgrens per treffer is het eerstvolgende event in die tijdlijn (van
welk type dan ook), met `margin_seconds` extra ervoor/erachter -- dus
exact tot waar de volgende spreekbeurt begint, niet een geschatte vaste
duur zoals het oude echokamer-notebook deed.

Gebruik:
    cd crawlers/debatdirect_fragments
    uv run scrapy crawl fragments \\
        -a terms=modelwerkelijkheid,modellenwerkelijkheid \\
        -a margin_seconds=10

Schrijft naar data/raw/debatdirect-fragments/<terms-slug>/ (via
VideoFragmentPipeline): per treffer een .mp4 + metadata-JSON.
"""

from datetime import datetime
from urllib.parse import urlencode

import scrapy

from ..debatdirect import (
    DEBATE_DETAIL_URL,
    SEARCH_PAGE_SIZE,
    SEARCH_URL,
    build_debate_url,
    build_deep_link,
    build_manifest_url,
    event_timeline_seconds,
    find_clip_bounds,
    search_params,
)
from ..items import VideoFragmentItem


class FragmentsSpider(scrapy.Spider):
    name = "fragments"
    allowed_domains = ["debatdirect.tweedekamer.nl", "api.debatdirect.tweedekamer.nl", "livestreaming.b67v2.tweedekamer.nl"]

    def __init__(self, terms=None, margin_seconds=10, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not terms:
            raise ValueError(
                "--terms is verplicht (komma-gescheiden), bv. "
                "scrapy crawl fragments -a terms=modelwerkelijkheid,modellenwerkelijkheid"
            )
        self.terms = [t.strip() for t in terms.split(",") if t.strip()]
        self.margin_seconds = float(margin_seconds)
        self.seen_debate_ids = set()

    async def start(self):
        for term in self.terms:
            yield scrapy.Request(
                self._search_url(term, 0), callback=self.parse_search,
                cb_kwargs={"term": term, "offset": 0},
            )

    @staticmethod
    def _search_url(term, offset):
        return f"{SEARCH_URL}?{urlencode(search_params(term, offset))}"

    def parse_search(self, response, term, offset):
        data = response.json()
        total = data["hits"]["total"]["value"]
        hits = data["hits"]["hits"]
        self.logger.info(f"{term!r}: pagina vanaf={offset}, {len(hits)}/{total} debatten op deze pagina")

        for hit in hits:
            debate = hit["_source"]
            debate_id = debate["id"]
            matching_events = debate.get("events", [])
            if debate_id in self.seen_debate_ids or not matching_events:
                continue
            self.seen_debate_ids.add(debate_id)
            yield scrapy.Request(
                DEBATE_DETAIL_URL.format(id=debate_id),
                callback=self.parse_debate_detail,
                cb_kwargs={"debate": debate, "matching_events": matching_events},
            )

        next_offset = offset + SEARCH_PAGE_SIZE
        if next_offset < total:
            yield scrapy.Request(
                self._search_url(term, next_offset), callback=self.parse_search,
                cb_kwargs={"term": term, "offset": next_offset},
            )

    def parse_debate_detail(self, response, debate, matching_events):
        detail = response.json()
        vod_url = detail.get("video", {}).get("vodUrl")
        starts_at_raw, ends_at_raw = detail.get("startsAt"), detail.get("endsAt")
        if not vod_url or not starts_at_raw or not ends_at_raw:
            self.logger.warning(f"debat {debate['id']} mist video.vodUrl/startsAt/endsAt, overgeslagen")
            return

        starts_at = datetime.fromisoformat(starts_at_raw)
        ends_at = datetime.fromisoformat(ends_at_raw)
        total_seconds = (ends_at - starts_at).total_seconds()
        timeline_seconds = event_timeline_seconds(detail.get("events", []), starts_at)
        manifest_url = build_manifest_url(vod_url, starts_at_raw, ends_at_raw)
        debate_url = build_debate_url(debate)

        for event in matching_events:
            source = event["_source"]
            own_seconds = (datetime.fromisoformat(source["eventStart"]) - starts_at).total_seconds()
            clip_start, clip_duration = find_clip_bounds(timeline_seconds, total_seconds, own_seconds, self.margin_seconds)
            politician = source.get("politician") or {}
            highlight = (event.get("highlight") or {}).get("transcription") or [None]

            yield VideoFragmentItem(
                terms=self.terms,
                debate_id=debate["id"],
                debate_title=debate["name"],
                debate_date=debate["debateDate"],
                video_url=debate_url + "/video",
                deep_link_url=build_deep_link(debate_url, source["eventType"], source["eventStart"]),
                event_type=source["eventType"],
                event_start=source["eventStart"],
                object_id=source["objectId"],
                speaker=politician.get("name"),
                party=(politician.get("party") or {}).get("shorthand"),
                highlight=highlight[0],
                manifest_url=manifest_url,
                clip_start_seconds=clip_start,
                clip_duration_seconds=clip_duration,
            )
