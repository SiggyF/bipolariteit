"""
Spider: haal Tweede Kamer Verslagen op voor een datumperiode, zonder
topic-trefwoordfilter (alle Activiteiten van die dag worden later door
pipeline.ingest.ingest_tk.ingest_plenair() geselecteerd, niet hier).

Gebruik:
    cd crawlers/tweede_kamer
    uv run scrapy crawl verslagen_periode -a start=2024-09-01 -a end=2025-08-31 \
        -a topic_keyword=_plenair_2024-2025 -a limit=10 \
        -s CONCURRENT_REQUESTS=8 -s DOWNLOAD_DELAY=0.05

    # Commissiedebatten i.p.v. plenair (issue #215: bredere dekking dan de
    # topic-gerichte trefwoordcrawls, voor de plenaire/debattenkaart):
    uv run scrapy crawl verslagen_periode -a start=2025-11-12 -a end=2026-08-29 \
        -a soort=Commissie -a topic_keyword=_commissie_2025-heden -a limit=20

Schrijft, net als de bestaande `verslagen`-spider, per gevonden Verslag een
ruw XML-bestand + metadata-JSON naar data/raw/tweede_kamer/<topic_keyword>/
(via RawFilePipeline) -- topic_keyword is hier een pseudo-waarde (geen
inhoudelijk topic) die alleen als mapnaam dient, zodat deze ruwe data apart
blijft van de topic-crawls.

Volgt de kortere keten Vergadering -> Verslag -> resource-download
(geen Activiteit-omweg, zie odata.vergaderingen_url), sequentieel per
Vergadering net als de bestaande spider (settings.CONCURRENT_REQUESTS).
"""

import json

import scrapy

from .. import odata
from ..items import VerslagItem
from ..paths import RAW_DIR


class VerslagenPeriodeSpider(scrapy.Spider):
    name = "verslagen_periode"

    def __init__(self, start=None, end=None, soort="Plenair", topic_keyword=None, limit=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not start or not end:
            raise ValueError(
                "--start en --end zijn verplicht (ISO-datums), bv. "
                "scrapy crawl verslagen_periode -a start=2024-09-01 -a end=2025-08-31"
            )
        if soort not in ("Plenair", "Commissie"):
            raise ValueError(f"soort moet 'Plenair' of 'Commissie' zijn, niet {soort!r}")
        self.start_date = start
        self.end_date = end
        self.soort = soort
        default_prefix = "_plenair_" if soort == "Plenair" else "_commissie_"
        self.topic_keyword = topic_keyword or f"{default_prefix}{start}_{end}"
        self.limit = int(limit) if limit is not None else None
        self.fetched = 0

    async def start(self):
        url = odata.vergaderingen_url(self.start_date, self.end_date, top=odata.MAX_TOP, soort=self.soort)
        yield scrapy.Request(url, callback=self.parse_vergaderingen, cb_kwargs={"buffer": []})

    def parse_vergaderingen(self, response, buffer):
        body = json.loads(response.text)
        page = body.get("value", [])
        buffer = buffer + page
        under_limit = self.limit is None or len(buffer) < self.limit

        next_link = body.get("@odata.nextLink")
        if next_link and under_limit:
            yield scrapy.Request(next_link, callback=self.parse_vergaderingen, cb_kwargs={"buffer": buffer})
            return

        # Deze $filter+$orderby-combinatie op Vergadering geeft geen
        # @odata.nextLink terug, ook niet als er meer dan MAX_TOP rijen
        # bestaan (zie odata.vergaderingen_url's docstring) -- een volle
        # pagina (len(page) == MAX_TOP) is dan het enige signaal dat er
        # nog meer is. Zelf doorpagineren met $skip totdat een pagina
        # niet meer vol is.
        if not next_link and len(page) == odata.MAX_TOP and under_limit:
            next_url = odata.vergaderingen_url(
                self.start_date, self.end_date, top=odata.MAX_TOP, soort=self.soort, skip=len(buffer),
            )
            yield scrapy.Request(next_url, callback=self.parse_vergaderingen, cb_kwargs={"buffer": buffer})
            return

        vergaderingen = buffer[: self.limit] if self.limit is not None else buffer
        self.logger.info(f"{len(vergaderingen)} {self.soort}-Vergaderingen gevonden ({self.start_date}..{self.end_date})")
        yield from self.process_next_vergadering(vergaderingen, 0)

    def process_next_vergadering(self, vergaderingen, index):
        if (self.limit is not None and self.fetched >= self.limit) or index >= len(vergaderingen):
            return

        vergadering = vergaderingen[index]
        url = odata.verslagen_url_for_vergadering(vergadering["Id"])
        yield scrapy.Request(
            url,
            callback=self.parse_verslag,
            cb_kwargs={"vergadering": vergadering, "vergaderingen": vergaderingen, "index": index},
        )

    def parse_verslag(self, response, vergadering, vergaderingen, index):
        body = json.loads(response.text)
        verslag = odata.best_verslag(body.get("value", []))
        if not verslag:
            self.logger.info(f"overslaan (geen verslag gevonden): {vergadering['Titel']}")
            yield from self.process_next_vergadering(vergaderingen, index + 1)
            return

        out_path = RAW_DIR / self.topic_keyword / f"{verslag['Id']}.xml"
        if out_path.exists():
            self.logger.info(f"al aanwezig: {out_path.name}")
            self.fetched += 1
            yield from self.process_next_vergadering(vergaderingen, index + 1)
            return

        url = odata.resource_url("Verslag", verslag["Id"])
        yield scrapy.Request(
            url,
            callback=self.parse_resource,
            cb_kwargs={"vergadering": vergadering, "verslag": verslag, "vergaderingen": vergaderingen, "index": index},
        )

    def parse_resource(self, response, vergadering, verslag, vergaderingen, index):
        item = VerslagItem(
            topic_keyword=self.topic_keyword,
            activiteit_id=None,
            activiteit_onderwerp=vergadering["Titel"],
            activiteit_datum=vergadering["Datum"],
            activiteit_nummer=None,
            activiteit_soort_odata=None,
            vergadering_id=vergadering["Id"],
            vergadering_titel=vergadering["Titel"],
            verslag_id=verslag["Id"],
            verslag_soort=verslag["Soort"],
            verslag_status=verslag["Status"],
            source_resource_url=odata.resource_url("Verslag", verslag["Id"]),
            xml_content=response.body,
        )
        self.fetched += 1
        yield item
        yield from self.process_next_vergadering(vergaderingen, index + 1)
