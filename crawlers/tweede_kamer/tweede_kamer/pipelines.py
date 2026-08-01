import json

from . import odata
from .paths import RAW_DIR


class RawFilePipeline:
    """Schrijft elk item als ruw XML-bestand + metadata-JSON naar
    data/raw/tweede_kamer/<topic_keyword>/, in hetzelfde formaat als de
    oorspronkelijke fetch_tk.py CLI. Namespacing per crawl-keyword houdt
    de ruwe data van verschillende topics uit elkaar -- ingest_tk.py scant
    per topic standaard alleen de eigen map, zodat een debat dat toevallig
    een ander topic-woord noemt (bv. een motie over abortuscijfers in een
    stikstofdebat) niet stilzwijgend meegenomen wordt."""

    def open_spider(self, spider):
        RAW_DIR.mkdir(parents=True, exist_ok=True)

    def process_item(self, item, spider):
        topic_dir = RAW_DIR / item["topic_keyword"]
        topic_dir.mkdir(parents=True, exist_ok=True)
        out_path = topic_dir / f"{item['verslag_id']}.xml"
        meta_path = topic_dir / f"{item['verslag_id']}.json"

        out_path.write_bytes(item["xml_content"])
        meta_path.write_text(
            json.dumps(
                {
                    "topic_keyword": item["topic_keyword"],
                    "activiteit_id": item["activiteit_id"],
                    "activiteit_onderwerp": item["activiteit_onderwerp"],
                    "activiteit_datum": item["activiteit_datum"],
                    "vergadering_id": item["vergadering_id"],
                    "vergadering_titel": item["vergadering_titel"],
                    "verslag_id": item["verslag_id"],
                    "verslag_soort": item["verslag_soort"],
                    "verslag_status": item["verslag_status"],
                    # Officiële, verifieerbare bronlink (open data resource) --
                    # machine-leesbare XML, geen leesbare pagina.
                    "source_resource_url": item["source_resource_url"],
                    # Publieke, mens-leesbare tweedekamer.nl-pagina (zie
                    # docs/tk-data-sources-overview.md sectie 11). None als
                    # Activiteit.Soort geen plenair/commissie-variant is
                    # (bv. e-mailprocedures) waarvoor geen detailpagina bestaat.
                    "tweedekamer_activiteit_url": odata.activiteit_website_url(
                        item.get("activiteit_nummer"), item.get("activiteit_soort_odata")
                    ),
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        spider.logger.info(f"opgehaald: {item['activiteit_onderwerp']} -> {out_path.name}")
        return item
