BOT_NAME = "tweede_kamer"

SPIDER_MODULES = ["tweede_kamer.spiders"]
NEWSPIDER_MODULE = "tweede_kamer.spiders"

# Dit is een OData API, geen website -- er valt geen robots.txt te
# respecteren en de open-data-voorwaarden staan geautomatiseerde toegang
# expliciet toe.
ROBOTSTXT_OBEY = False

# De verslag-lookup is een sequentiële afhankelijkheidsketen (Activiteit ->
# Vergadering -> Verslag -> resource) waarbij we per topic de top-N meest
# recente debatten willen, in datumvolgorde, tot de limiet is bereikt.
# CONCURRENT_REQUESTS=1 houdt de verwerkingsvolgorde deterministisch gelijk
# aan die keten; dit is geen prestatiekritische crawler.
CONCURRENT_REQUESTS = 1
DOWNLOAD_DELAY = 0.25

USER_AGENT = "bipolariteit-tk-crawler/0.1 (contact: f.baart@gmail.com; onderzoeksproject)"

ITEM_PIPELINES = {
    "tweede_kamer.pipelines.RawFilePipeline": 300,
}

LOG_LEVEL = "INFO"
REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
