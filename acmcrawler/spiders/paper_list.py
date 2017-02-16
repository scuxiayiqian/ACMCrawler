import scrapy

class ACMSpider(scrapy.Spider):
    name = 'list'

    def start_requests(self):
        site= "http://dl.acm.org/proceedings.cfm?CFID=900705154&CFTOKEN=97736866"
        hdr = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11',
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

            yield {
                'confname': confname,
                'confurl': confurl,
            }

        for meetinglist in response.css('div.text12 ul'):
            for meetingitem in meetinglist.css('li'):
                itemtitle = meetingitem.css('a::attr(title)').extract_first()
                itemhref = meetingitem.css('a::attr(href)').extract_first()
                itemname = meetingitem.css('a::text').extract_first()

                yield {
                    'itemtitle': itemtitle,
                    'itemname': itemname,
                    'itemhref': itemhref,
                }










