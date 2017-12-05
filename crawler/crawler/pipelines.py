# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html

from datetime import datetime
from scrapy import signals
from scrapy.exporters import JsonLinesItemExporter

class CrawlerPipeline(object):
    def process_item(self, item, spider):
        return item

class KSUPipeline(object):
    """
        Custom pipeline to write the WebPage item data 
        in a JSON line format in a JSON file.
    """

    def __init__(self):
        self.files = {}

    @classmethod
    def from_crawler(cls, crawler):
        pipeline = cls()
        crawler.signals.connect(pipeline.spider_opened, signals.spider_opened)
        crawler.signals.connect(pipeline.spider_closed, signals.spider_closed)
        return pipeline

    # Open the file when Spider starts
    def spider_opened(self, spider):
        date_hour = datetime.strftime(datetime.now(), "%Y-%m-%d_%H")
        file_name = ('%s_%s.json' % (spider.name, date_hour))
        file = open(file_name, 'w+b')
        self.files[spider] = file
        self.exporter = JsonLinesItemExporter(file)
        self.exporter.start_exporting()

    # Close the file when Spider is closed
    def spider_closed(self, spider):
        self.exporter.finish_exporting()
        file = self.files.pop(spider)
        file.close()

    def process_item(self, item, spider):
        self.exporter.export_item(item)
        return item
