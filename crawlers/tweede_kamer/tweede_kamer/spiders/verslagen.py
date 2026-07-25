"""
Spider: haal Tweede Kamer plenaire debat-Verslagen op voor een topic.

Gebruik:
    cd crawlers/tweede_kamer
    uv run scrapy crawl verslagen -a topic=stikstof -a limit=10

Schrijft per gevonden debat een ruw XML-bestand + metadata-JSON naar
data/raw/tweede_kamer/ (via RawFilePipeline).

Volgt de keten Activiteit -> Vergadering -> Verslag -> resource-download
sequentieel per activiteit (zie settings.CONCURRENT_REQUESTS), zodat de
top-N meest recente debatten in datumvolgorde verwerkt worden tot de
limiet is bereikt -- zelfde semantiek als de oorspronkelijke fetch_tk.py
for-loop.
"""

import json

import scrapy

from .. import odata
from ..items import VerslagItem
from ..paths import RAW_DIR


class VerslagenSpider(scrapy.Spider):
    name = "verslagen"

    def __init__(self, topic=None, limit=10, soort="Plenair debat (debat)", *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not topic:
            raise ValueError("--topic is verplicht, bv. scrapy crawl verslagen -a topic=stikstof")
        self.topic = topic
        self.limit = int(limit)
        self.soort = soort
        self.fetched = 0

    async def start(self):
        top = self.limit * 3
        url = odata.activiteiten_url(self.topic, self.soort, top=top)
        yield scrapy.Request(url, callback=self.parse_activiteiten, cb_kwargs={"buffer": [], "top": top})

    def parse_activiteiten(self, response, buffer, top):
        body = json.loads(response.text)
        buffer = buffer + body.get("value", [])
        next_link = body.get("@odata.nextLink")
        if next_link and len(buffer) < top:
            yield scrapy.Request(next_link, callback=self.parse_activiteiten, cb_kwargs={"buffer": buffer, "top": top})
            return

        activiteiten = buffer[:top]
        yield from self.process_next_activiteit(activiteiten, 0)

    def process_next_activiteit(self, activiteiten, index):
        if self.fetched >= self.limit or index >= len(activiteiten):
            return

        activiteit = activiteiten[index]
        datum = activiteit.get("Datum")
        if not datum:
            yield from self.process_next_activiteit(activiteiten, index + 1)
            return

        url = odata.vergadering_url_for_activiteit(datum)
        yield scrapy.Request(
            url,
            callback=self.parse_vergadering,
            cb_kwargs={"activiteit": activiteit, "activiteiten": activiteiten, "index": index},
        )

    def parse_vergadering(self, response, activiteit, activiteiten, index):
        body = json.loads(response.text)
        vergadering = odata.pick_closest_vergadering(body.get("value", []), activiteit["Datum"])
        if not vergadering:
            self.logger.info(f"overslaan (geen vergadering gevonden): {activiteit['Onderwerp']}")
            yield from self.process_next_activiteit(activiteiten, index + 1)
            return

        url = odata.verslagen_url_for_vergadering(vergadering["Id"])
        yield scrapy.Request(
            url,
            callback=self.parse_verslag,
            cb_kwargs={"activiteit": activiteit, "vergadering": vergadering, "activiteiten": activiteiten, "index": index},
        )

    def parse_verslag(self, response, activiteit, vergadering, activiteiten, index):
        body = json.loads(response.text)
        verslag = odata.best_verslag(body.get("value", []))
        if not verslag:
            self.logger.info(f"overslaan (geen verslag gevonden): {activiteit['Onderwerp']}")
            yield from self.process_next_activiteit(activiteiten, index + 1)
            return

        out_path = RAW_DIR / f"{verslag['Id']}.xml"
        if out_path.exists():
            self.logger.info(f"al aanwezig: {out_path.name}")
            self.fetched += 1
            yield from self.process_next_activiteit(activiteiten, index + 1)
            return

        url = odata.resource_url("Verslag", verslag["Id"])
        yield scrapy.Request(
            url,
            callback=self.parse_resource,
            cb_kwargs={
                "activiteit": activiteit,
                "vergadering": vergadering,
                "verslag": verslag,
                "activiteiten": activiteiten,
                "index": index,
            },
        )

    def parse_resource(self, response, activiteit, vergadering, verslag, activiteiten, index):
        item = VerslagItem(
            topic_keyword=self.topic,
            activiteit_id=activiteit["Id"],
            activiteit_onderwerp=activiteit["Onderwerp"],
            activiteit_datum=activiteit["Datum"],
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
        yield from self.process_next_activiteit(activiteiten, index + 1)
