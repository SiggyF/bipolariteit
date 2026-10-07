BOT_NAME = "debatdirect_fragments"

SPIDER_MODULES = ["debatdirect_fragments.spiders"]
NEWSPIDER_MODULE = "debatdirect_fragments.spiders"

# Publieke JSON-API's (zoek- en detail-endpoint van Debat Direct), geen
# website met een robots.txt om te respecteren.
ROBOTSTXT_OBEY = False

# Sequentieel: de detail-call per debat hergebruikt de events-tijdlijn voor
# alle treffers in dat debat (zie spiders/fragments.py), en het ffmpeg-
# clippen in de pipeline is toch al een blokkerende, I/O-zware stap per
# item. Geen prestatiekritische crawler.
CONCURRENT_REQUESTS = 1
DOWNLOAD_DELAY = 0.3

USER_AGENT = "bipolariteit-debatdirect-crawler/0.1 (contact: f.baart@gmail.com; onderzoeksproject)"

ITEM_PIPELINES = {
    "debatdirect_fragments.pipelines.VideoFragmentPipeline": 300,
}

LOG_LEVEL = "INFO"
REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
