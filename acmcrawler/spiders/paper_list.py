import scrapy


# class ACMSpider(scrapy.Spider):
#     name = 'list'
#     url = 'http://dl.acm.org/proceedings.cfm?CFID=900705154&CFTOKEN=97736866'

#     def parse(self, response):
#         page = response.url.split("/")[-2]
#         filename = 'quotes-%s.html' % page
#         with open(filename, 'wb') as f:
#             f.write(response.body)

import urllib2,cookielib

class ACMSpider(scrapy.Spider):
    name = 'list'
    site= "http://dl.acm.org/proceedings.cfm?CFID=900705154&CFTOKEN=97736866"
    hdr = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11',
           'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
           'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
           'Accept-Encoding': 'none',
           'Accept-Language': 'en-US,en;q=0.8',
           'Connection': 'keep-alive'}

    req = urllib2.Request(site, headers=hdr)

    try:
        page = urllib2.urlopen(req)
    except urllib2.HTTPError, e:
        print e.fp.read()

    content = page.read()

    # write acm homepage to a file named page.html
    with open('page.html', 'wb') as f:
        f.write(content)

