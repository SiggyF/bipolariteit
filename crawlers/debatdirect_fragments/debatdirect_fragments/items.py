import scrapy


class VideoFragmentItem(scrapy.Item):
    terms = scrapy.Field()
    debate_id = scrapy.Field()
    debate_title = scrapy.Field()
    debate_date = scrapy.Field()
    video_url = scrapy.Field()
    deep_link_url = scrapy.Field()
    event_type = scrapy.Field()
    event_start = scrapy.Field()
    object_id = scrapy.Field()
    speaker = scrapy.Field()
    party = scrapy.Field()
    highlight = scrapy.Field()
    manifest_url = scrapy.Field()
    clip_start_seconds = scrapy.Field()
    clip_duration_seconds = scrapy.Field()
