import json

from .paths import RAW_DIR


class RawFilePipeline:
    """Schrijft elk item als ruw XML-bestand + metadata-JSON naar
    data/raw/tweede_kamer/, in hetzelfde formaat als de oorspronkelijke
    fetch_tk.py CLI."""

    def open_spider(self, spider):
        RAW_DIR.mkdir(parents=True, exist_ok=True)

    def process_item(self, item, spider):
        out_path = RAW_DIR / f"{item['verslag_id']}.xml"
        meta_path = RAW_DIR / f"{item['verslag_id']}.json"

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
                    # Officiële, verifieerbare bronlink (open data resource).
                    # TODO: vervangen door de publieke tweedekamer.nl debat-URL
                    # zodra het exacte URL-patroon is uitgezocht (niet gegokt).
                    "source_resource_url": item["source_resource_url"],
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        spider.logger.info(f"opgehaald: {item['activiteit_onderwerp']} -> {out_path.name}")
        return item
