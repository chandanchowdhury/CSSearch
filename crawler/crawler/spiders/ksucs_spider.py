import re
from urlparse import urlparse
import scrapy

class WebPage(scrapy.Item):
    page_url = scrapy.Field()
    page_title = scrapy.Field()
    page_content = scrapy.Field()
    page_links = scrapy.Field()

class KsuCSSpider(scrapy.Spider):
    name = "ksucs"

    allowed_domains = [
        "ksu.edu",
        "k-state.edu"
    ]

    def start_requests(self):
        urls = [
            "http://www.cs.ksu.edu", "http://cs.k-state.edu"
            ,"https://www.cs.ksu.edu", "https://cs.k-state.edu"
        ]

        for url in urls:
            yield scrapy.Request(url=url, callback=self.parse)

    def parse(self, response):

        # process only HTML content
        if not re.match('text/html', response.headers.get('Content-Type').decode('utf-8')):
            return

        page = WebPage()

        # Page URL
        #print("Parsing: "+response.url)
        page['page_url'] = response.url

        # Page title 
        page['page_title'] = response.selector.xpath('//title/text()').extract()

        # Page content
        # Save the page content "as it is", will process the content offline
        page['page_content'] = response.body

        #page['page_content'] = response.selector.xpath('//text()').extract()
        #soup = BeautifulSoup(response.body, 'html.parser')
        #page['page_content'] = soup.get_text()

        #print(response.css("a::attr(href)").extract_first())        
        
        ## Process all URLs in the page
        page['page_links'] = []
        for href in response.css("a::attr(href)"):
            #print(href)
            
            ## Convert relative URLs into full URLs
            url = href.extract().split("/")

            url_cleaned = ""
            # if starts with HTTP
            if url[0][:4] == "http":
                url_cleaned = href.extract()
            else:
                # else join with parent URL we are visiting
                url_cleaned = response.urljoin(href.extract())

            # Add the URL to the list of links contained in the page for link analysis
            page['page_links'].append(url_cleaned)
            #print("Cleaned URL: "+url_cleaned)

            # add the URL for crawling, the allowed_domain setting will ignore non K-state domains
            yield scrapy.Request(url=url_cleaned, callback=self.parse)
            
            #domain = urlparse(url_cleaned).netloc
            #print("Domain: "+ domain)
            #if domain[7:] == 'ksu.edu':
            #    print("Adding to crawling list: "+url_cleaned)
                #yield scrapy.Request(url=url_cleaned, callback=self.parse)
            
 
        # return the populated WebPage
        yield page
