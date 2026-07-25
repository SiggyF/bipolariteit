import scrapy


class VerslagItem(scrapy.Item):
    topic_keyword = scrapy.Field()
    activiteit_id = scrapy.Field()
    activiteit_onderwerp = scrapy.Field()
    activiteit_datum = scrapy.Field()
    vergadering_id = scrapy.Field()
    vergadering_titel = scrapy.Field()
    verslag_id = scrapy.Field()
    verslag_soort = scrapy.Field()
    verslag_status = scrapy.Field()
    source_resource_url = scrapy.Field()
    xml_content = scrapy.Field()
