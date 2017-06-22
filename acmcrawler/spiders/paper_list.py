import scrapy
import pymongo
from scrapy.selector import Selector
from scrapy.conf import settings
import re
from twisted.internet import reactor, defer
from scrapy.crawler import CrawlerRunner
from scrapy.utils.log import configure_logging

class ACMSpider(scrapy.Spider):
	name = 'list'
	
	base_url = 'http://dl.acm.org/'
	
	hdr = {
		'User-Agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/37.0.2062.124 Safari/537.36',
		'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
		'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
		'Accept-Encoding': 'none',
		'Accept-Language': 'en-US,en;q=0.8',
		'Connection': 'keep-alive'}
	
	def __init__(self):
		connection = pymongo.MongoClient(
			settings['MONGODB_SERVER'],
			settings['MONGODB_PORT']
		)
		db = connection[settings['MONGODB_DB']]
		self.collection = db[settings['MONGODB_COLLECTION']]
	
	def start_requests(self):
		site= "http://dl.acm.org/proceedings.cfm?CFID=900705154&CFTOKEN=97736866"
		yield scrapy.Request(url=site, headers=self.hdr, callback=self.parse)
		
	def parse(self, response):
		# print response.css('title::text').extract_first()
		for meeting in response.css('strong'):
			array = []
			# all conference name
			pattern = r'id=([a-zA-Z0-9]+)'
			confname = meeting.css('a::text').extract_first()
			confurl = self.base_url + meeting.css('a::attr(href)').extract_first()
			result = {
				'confname': confname,
				'confurl': confurl,
				'conflist': []
			}
			
			# crawl all years of each conference
			meetingList = meeting.xpath('./following-sibling::ul[1]').css('li')
			for meetingItem in meetingList:
				result['conflist'].append({
					'id': re.findall(pattern, meetingItem.css('a::attr(href)').extract_first())[0],
					'title': meetingItem.css('a::attr(title)').extract_first(),
					'name': meetingItem.css('a::text').extract_first(),
					'href': self.base_url + meetingItem.css('a::attr(href)').extract_first(),
					'paperlist':[]
				})
				site = self.base_url + meetingItem.css('a::attr(href)').extract_first()
				array.append(site)
			self.collection.insert(result)


class ACMSpiderPaperList(scrapy.Spider):
	name = 'paperList'
	
	base_url = 'http://dl.acm.org/'
	
	# download_delay = settings['DOWNLOAD_DELAY']
	
	hdr = {
		'User-Agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/37.0.2062.124 Safari/537.36',
		'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
		'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
		'Accept-Encoding': 'none',
		'Accept-Language': 'en-US,en;q=0.8',
		'Connection': 'keep-alive'}
	
	def __init__(self):
		connection = pymongo.MongoClient(
			settings['MONGODB_SERVER'],
			settings['MONGODB_PORT']
		)
		db = connection[settings['MONGODB_DB']]
		self.collection = db[settings['MONGODB_COLLECTION']]
		self.index = 0
	
	def start_requests(self):
		print "paperList spider"
		events = self.collection.find({}, no_cursor_timeout=True)
		for event in events:
			for conf in event['conflist']:
				yield scrapy.Request(url=conf['href'], headers=self.hdr, callback=self.parse_paper_list)
	
	def parse_paper_list(self, response):
		pattern = r'(tab_about\.cfm\?.+&cftoken=[a-zA-Z0-9]+)'
		scripts = response.xpath('//script[@type="text/javascript"]').extract()
		
		str_scripts = str(scripts)
		paper_list_url = re.findall(pattern, str_scripts)[0]
		site = self.base_url + paper_list_url
		
		yield scrapy.Request(url=site, headers=self.hdr, callback=self.parse_paper)
	
	def parse_paper(self, response):
		self.index += 1
		session = ""
		print "<==============================>"
		print self.index
		pattern = r'\?id=([0-9a-zA-Z]+)'
		temp = {
			"name": "",
			'pdfUrl': "",
			"url": "",
			"session": "",
			"authors": [],
			"abstract": "",
			"references": [],
			"citations": []
		}
		trs = response.css('tr')
		for tr in trs:
			if len(tr.css('strong')) > 0:
				session = tr.css('strong::text').extract_first()
			temp['session'] = session
			links = tr.css('a')
			if len(links) == 1:
				if 'citation.cfm' in links.css('::attr(href)').extract_first():
					temp['name'] = links.css('::text').extract_first()
					temp['url'] = self.base_url + links.css('::attr(href)').extract_first()
				elif 'author_page.cfm' in links.css('::attr(href)').extract_first():
					if temp['url'] == "":
						continue
					temp['authors'].append({
						'name': links.css('::text').extract_first(),
						'url': self.base_url + links.css('::attr(href)').extract_first()
					})
				elif 'ft_gateway.cfm' in links.css('::attr(href)').extract_first():
					# ignore the session cover pdf
					if temp['url'] == "":
						continue
					temp['pdfUrl'] = self.base_url + links.css('::attr(href)').extract_first()
					record = self.collection.find_one(
						{'conflist': {'$elemMatch': {'id': re.findall(pattern, response.url)[0]}}})
					for item in record['conflist']:
						if item['id'] == re.findall(pattern, response.url)[0]:
							item['paperlist'].append(temp)
							self.collection.save(record)
							print "save into mongo" + re.findall(pattern, response.url)[0]
							break
					temp = {
						"name": "",
						'pdfUrl': "",
						"url": "",
						"session": "",
						"authors": [],
						"abstract": "",
						"references": [],
						"citations": []
					}
			elif len(links) > 1:
				for item in links:
					temp['authors'].append({
						"name": item.css('::text').extract_first(),
						"url": self.base_url + item.css('::attr(href)').extract_first()
					})


class ACMSpiderPaperDetail(scrapy.Spider):
	name = 'paperDetail'
	
	base_url = 'http://dl.acm.org/'
	
	# download_delay = settings['DOWNLOAD_DELAY']
	
	hdr = {
		'User-Agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/37.0.2062.124 Safari/537.36',
		'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
		'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
		'Accept-Encoding': 'none',
		'Accept-Language': 'en-US,en;q=0.8',
		'Connection': 'keep-alive'}
	
	def __init__(self):
		connection = pymongo.MongoClient(
			settings['MONGODB_SERVER'],
			settings['MONGODB_PORT']
		)
		db = connection[settings['MONGODB_DB']]
		self.collection = db[settings['MONGODB_COLLECTION']]
		self.index = 0
		self.user_agents_num = 0
		self.user_agents = []
		fileobj = open('acmcrawler/user_agent_list.txt', 'r')
		for line in fileobj:
			self.user_agents_num += 1
			self.user_agents.append(line)
		
	def start_requests(self):
		confs = self.collection.find({}, no_cursor_timeout=True)
		pattern = r'(\?id=[0-9a-zA-Z]+)'
		count = 0
		for conf in confs:
			for paper in conf['paperlist']:
				if self.index < 197000:
					self.index += 1
					continue
				part_url = re.findall(pattern, paper['url'])[0]
				site = self.base_url + 'citation.cfm' + part_url + '&preflayout=flat'
				self.hdr['User-Agent'] = self.user_agents[count % self.user_agents_num]
				count += 1
				yield scrapy.Request(url=site, headers=self.hdr, callback=self.parse)
					
	def parse(self, response):
		self.index += 1
		print '****************************'
		print self.index
		print response.url
		abstract = response.xpath('//a[@name="abstract"]/../following-sibling::div[@class="flatbody"][1]/div').xpath('string(.)').extract()[0]
		print abstract
		reference_table = response.xpath('//a[@name="references"]/../following-sibling::div[@class="flatbody"][1]/table/tr')
		references = []
		for tr in reference_table:
			href = tr.xpath('./td[3]/div/a[1]')
			if len(href) == 0:
				references.append({
					'name': unicode(tr.xpath('./td[3]/div/text()').extract_first()).replace('\r\n', '').replace('\t', ''),
					'url': 'null'
				})
			else:
				references.append({
					'name': unicode(href.xpath('./text()').extract_first()).replace('\r\n', '').replace('\t', ''),
					'url': self.base_url + href.xpath('./@href').extract_first()
				})
		citation_table = response.xpath('//a[@name="citedby"]/../following-sibling::div[@class="flatbody"][1]/table/tr')
		citations = []
		for tr in citation_table:
			href = tr.xpath('./td[2]/div/a[1]')
			if len(href) == 0:
				citations.append({
					'name': unicode(tr.xpath('./td[2]/div/text()').extract_first()).replace('\r\n', '').replace('\t', ''),
					'url': 'null'
				})
			else:
				citations.append({
					'name': unicode(href.xpath('./text()').extract_first()).replace('\r\n', '').replace('\t', ''),
					'url': self.base_url + href.xpath('./@href').extract_first()
				})
		pattern = r'\?id=([0-9a-zA-Z]+).*'
		paper_id = re.findall(pattern, response.url)[0]
		conf = self.collection.find_one({'paperlist':{'$elemMatch':{'url':{'$regex':'.*' + paper_id + '.*'}}}})
		for paper in conf['paperlist']:
			if '?id=' + paper_id in paper['url']:
				paper['abstract'] = abstract
				paper['references'] = references
				paper['citations'] = citations
				self.collection.save(conf)
				break
					

configure_logging()
runner = CrawlerRunner(settings)

@defer.inlineCallbacks
def crawl():
	# yield runner.crawl(ACMSpider)
	# yield runner.crawl(ACMSpiderPaperList)
	yield runner.crawl(ACMSpiderPaperDetail)
	reactor.stop()

crawl()
reactor.run()
