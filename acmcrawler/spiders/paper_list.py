import scrapy
from scrapy.selector import Selector

class ACMSpider(scrapy.Spider):
    name = 'list'
    
    def start_requests(self):
        print "jj1"
        site= "http://dl.acm.org/proceedings.cfm?CFID=900705154&CFTOKEN=97736866"
        hdr = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/37.0.2062.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
            'Accept-Encoding': 'none',
            'Accept-Language': 'en-US,en;q=0.8',
            'Connection': 'keep-alive'}

        yield scrapy.Request(url=site, headers=hdr, callback=self.parse)

    def parse(self, response):
        print response.css('title::text').extract_first()
        
        for meeting in response.css('strong'):
            confname = meeting.css('a::text').extract_first()
            confurl = meeting.css('a::attr(href)').extract_first()
            result = {
                'confname': confname,
                'confurl': confurl,
                'conflist': []
            }
            meetingList = meeting.xpath('./following-sibling::ul[1]').css('li')
            for meetingItem in meetingList:
                result['conflist'].append({
                    'title': meetingItem.css('a::attr(title)').extract_first(),
                    'name': meetingItem.css('a::text').extract_first(),
                    'href': meetingItem.css('a::attr(href)').extract_first()
                })
            yield result