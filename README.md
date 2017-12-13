# CSSearch

A simple crawler and search written python for Information Retrieval & Machine Learning (CIS-833) class project. The crawler only crawls domains under ksu.edu or k-state.edu.

## Install
* Clone the repo

* Setup virtualenv

   ```virtualenv CSSearch```

* Install the required packages

   ```pip install -r requirements.txt```

* Download NLTK data

    ```python -m nltk.downloader all```
    
## Run
* Run the crawler

   ```scrapy crawl ksucs```

* Run the indexer

* Perform search

## Required Packages
* Scrapy - for crawling
* Beautifulsoap - for HTML parsing
* NLTK 
