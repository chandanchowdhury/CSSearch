import scrapy

class KsuCSSpider(scrapy.Spider):
    name = "ksucs"

    allowed_domains = [
        "ksu.edu",
        "k-state.edu"
    ]

    def start_requests(self):
        urls = [
            "http://cs.ksu.edu", "http://cs.k-state.edu"
            #,"https://cs.ksu.edu", "https://cs.k-state.edu"]
        ]

        for url in urls:
            yield scrapy.Request(url=url, callback=self.parse)

    def parse(self, response):
        print("Parsing: "+response.url)
        #print(response.css("a::attr(href)").extract_first())
        
        ## Get all the URLs in the page
        for href in response.css("a::attr(href)"):
            
            ## Convert relative URLs into full URLs
            url = href.extract().split("/")
            # if starts with HTTP
            if url[0][:4] == "http":
                print(href.extract())
            else:
                # else join with parent URL we are visiting
                print(response.urljoin(href.extract()))
