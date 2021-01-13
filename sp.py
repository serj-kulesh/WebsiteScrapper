from sys import platform as sys_platform, argv as sys_argv
import os
import re
import time
import tarfile
import sqlite3
import scrapy
from scrapy.crawler import CrawlerProcess
from lxml import etree

conn = sqlite3.connect('app.db')

dir_name = "files"

dir_sep = '/'
if sys_platform.startswith('win'):
    dir_sep = '\\'

full_path = os.path.dirname(os.path.realpath(__file__)) + dir_sep + dir_name
if not os.path.isdir(full_path):
    os.mkdir(full_path, mode = 0o777)

class WebsiteSpyder(scrapy.Spider):
    """ Spider based on scrapy.Spider
        
        params:
        url_list = list of start urls to crawl
    """
    name = 'WebsiteSpyder'


    custom_settings = {
        'DEPTH_LIMIT': 3,
    }

    def __init__(self, *args, **kwargs):
        self.start_urls = kwargs.pop('url_list', [])
        self.allowed_domains = [re.findall('\w+\:\/\/([^\/]+)', 
                                self.start_urls[0])[0]]
        url_dir = re.findall('\w+\:\/\/([^\/]+)', self.start_urls[0])[0]
        self.dir_name = url_dir + str(time.time())
        full_url_dir = full_path + dir_sep + self.dir_name
        os.mkdir(full_url_dir, mode = 0o777)
        self.full_url_dir = full_url_dir
        self.html_dir = full_url_dir + dir_sep + 'html'
        os.mkdir(self.html_dir, mode = 0o777)
        self.css_dir = full_url_dir + dir_sep + 'css'
        os.mkdir(self.css_dir, mode = 0o777)
        self.js_dir = full_url_dir + dir_sep + 'js'
        os.mkdir(self.js_dir, mode = 0o777)
        self.media_dir = full_url_dir + dir_sep + 'media'
        os.mkdir(self.media_dir, mode = 0o777)
        
        
        super(WebsiteSpyder, self).__init__(*args, **kwargs)

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super(WebsiteSpyder, cls).from_crawler(crawler, 
                                                        *args, **kwargs)
        crawler.signals.connect(spider.stop_event,
                                signal=scrapy.signals.spider_closed)
        return spider
	
    def save_f(self, dir = None, response = None):
        type = 'wb'
        filename = re.findall("[^\/]+\.[a-zA-Z0-9]+$", response.url)
        file_body = response.body
        
        if dir == self.html_dir:
            type = 'w'
            filename = [re.sub('[\/\:\?\&\@\[\]\=]', '_', 
                        response.url) + '.html']
            file_body = response.text
            
        if dir == self.css_dir or dir == self.js_dir:
            type = 'w'
            filename = re.findall("[^\/]+$", response.url)
            file_body = response.text

        if filename:    
            with open(dir + dir_sep + filename[0], type) as file:
                file.write(file_body)
                file.close()
    
    def parse_image(self, response):
        self.save_f(self.media_dir, response)
    
    def parse_js(self, response):
        self.save_f(self.js_dir, response)
    
    def parse_css(self,response):
        self.save_f(self.css_dir, response)
        
        img_urls = re.findall("url\s*\((.*(\.jpg|\.jpeg|\.png|\.gif))\)", 
                                response.text, flags=re.I)
        if img_urls:
            for img in img_urls:
                yield scrapy.Request(response.urljoin(img[0]), 
                                        self.parse_image)

    def parse(self, response):
        self.save_f(self.html_dir, response)
        
        for img_path in response.xpath('//img/@src').getall():
            yield scrapy.Request(response.urljoin(img_path), self.parse_image)

        for style_block in response.xpath('//style').getall():
            imported = re.findall("\@import\s(.*)", style_block)
            if imported:
                for i_line in imported:
                    i_str = re.findall('\("(.*)"\)', i_line)
                    if i_str:
                        yield scrapy.Request(response.urljoin(i_str[0]), 
                                                self.parse_css)
						
            img_urls = re.findall("""url\s*\('(.*(\.jpg|
                                    \.jpeg|\.png|\.gif))'\)""",
                                     response.text, flags=re.I | re.VERBOSE)
            if img_urls:
                for img in img_urls:
                    yield scrapy.Request(response.urljoin(img[0]), 
                                            self.parse_image)
			
		
		
        for css_link in response.xpath('//link').getall():
            tree=etree.HTML(css_link)
            if tree.xpath('//link/@rel')[0] is not None:
                if tree.xpath('//link/@rel')[0] == 'stylesheet':
                    yield scrapy.Request(
                        response.urljoin(
                            tree.xpath('//link/@href')[0]
                        ), self.parse_css)
            else:
                css_link_re = re.findall('[^\/]+\.css[^\/]*')
                if css_link_re:
                    yield scrapy.Request(
                        response.urljoin(
                            tree.xpath('//link/@href')[0]
                        ), self.parse_css)
        
        for js_link in response.xpath('//script/@src').getall():
            yield scrapy.Request(response.urljoin(js_link), self.parse_js)


        for href in response.xpath('//a/@href').getall():
            yield scrapy.Request(response.urljoin(href), self.parse)


    def stop_event(self):
        tar = tarfile.open(self.full_url_dir + '.tar.gz', "w:gz")
        tar.add(self.full_url_dir, arcname = self.dir_name)
        tar.close()
        
        cur = conn.cursor()
        cur.execute("""UPDATE tasks 
                        SET status = 1, filename = '{0}' 
                        WHERE id = {1}"""
                         . format(self.full_url_dir + '.tar.gz', task_id))
        conn.commit()

        
if len(sys_argv) > 2:
    url = sys_argv[1]
    task_id = sys_argv[2]
    process = CrawlerProcess()
    process.crawl(WebsiteSpyder,  url_list=[url])
    process.start()
