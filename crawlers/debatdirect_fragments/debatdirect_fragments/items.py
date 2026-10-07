import scrapy


class VideoFragmentItem(scrapy.Item):
    """Dynamisch item (zie Scrapy-docs "Supporting a dynamic item type"):
    nieuwe velden hoeven niet vooraf als Field() gedeclareerd te worden,
    spiders/fragments.py kan gewoon een nieuwe key toekennen. Scheelt dit
    bestand hoeven aan te passen bij elk veld dat de spider later toevoegt."""

    def __setitem__(self, key, value):
        if key not in self.fields:
            self.fields[key] = scrapy.Field()
        super().__setitem__(key, value)
