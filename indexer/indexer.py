try:
    import cPickle as pickle
except:
    import pickle

import json
import string
import hashlib

from sets import Set

from bs4 import BeautifulSoup

from stemming.porter import stem
from nltk.corpus import stopwords

def getHash(url):
    """
        return the SAH256 hash of the URL

        :param url as string
        :return sha256 has as string
    """
    #return hashlib.sha256(url).hexdigest()

    # NOTE: debugging
    return url


def savePickle(pickle_file, data):
    """
        Save data in Pickle format.
    """
    print("Saving pickle data to file: "+pickle_file)

    try:
        with open(pickle_file, "wb") as fd:
            pickle.dump(data, fd)            
    except pickle.PicklingError as pe:
        print("Failed: Saving pickle data")
        return 1


def loadPickle(pickle_file):
    """
        Load the Pickle data from file.
    """
    print("Loading pickle data from file: "+pickle_file)

    data = None
    try:
        with open(pickle_file, "rb") as fd:
            data = pickle.load(fd)
    except EOFError:
        pass
    except pickle.UnpicklingError as upe:
        print("Failed: Loading Pickle Data")
    except IOError:
        data = {}

    return data

def stemm_word(word):
    """
        Use Porter stemmer to stem words.

    :param word: String

    :return: Stemmed word
    """
    return stem(word)

def getStopWordList(stop_word_list_file_path=None):
    
    stop_word_list = None

    if stop_word_list_file_path == None:
        stop_word_list = set(stopwords.words('english'))
    else:
        fd = open(stop_word_list_file_path, "r")
        txt = fd.readlines()
        fd.close()

        stop_word_list = []
        for l in txt:
            stop_word_list.append(l.lstrip().rstrip())

    return stop_word_list

def parseSGML(data):
    """
        Reads a SGML data and return the TITLE and TEXT

    :param data: SGML data

    :return:
        title as string
        contents as string
    """
    
    soup = BeautifulSoup(data, 'html.parser')

    # remove Scripts and CSS
    # Ref: https://stackoverflow.com/a/35565549
    tags_to_remove = ['script', 'style']
    for tag in soup.find_all(tags_to_remove):
        tag.decompose()

    try:
        title = soup.title.get_text()
    except AttributeError:
        title = ""

    # Get the text between all tags joined by a space character
    contents = soup.get_text(' ')

    #print("Title:", title)
    #print("Text:", contents)

    return title, contents

def sanitize(text, stop_word_list):
    """
        Reads a text, remove stop words, stem the words.

    :param text: String

    :return: List of words
    """

    # convert the text into Unicode
    text = unicode(text)

    #print(type(text))

    # replace dot with space
    text = text.translate({ord("."): ord(" ")})
    # replace dash with space
    text = text.translate({ord("-"): ord(" ")})

    # split the text on white-space
    words = text.split()
    sanitized_words = []
    for w in words:

        # ignore numbers
        if w.isnumeric():
            continue

        # print("Word (Before Punctuation): " + w)

        # remove punctuation
        # Ref: https://stackoverflow.com/questions/265960/best-way-to-strip-punctuation-from-a-string-in-python
        # w = w.translate(None, string.punctuation)

        # The above method does not work for Unicode strings
        # Ref: https://stackoverflow.com/questions/23175809/typeerror-translate-takes-one-argument-2-given-python#23306505
        # print(type(w))

        # replace punctuations with None
        w = w.translate({ord(c): None for c in string.punctuation})
        w = w.lower()
        # print("Word (After Punctuation): "+w)

        # Note: Remove stop-words before Stemming, or else the stop-word
        # matching will not work.
        # If the word is in Stop Word List
        try:
            i = stop_word_list.index(w.lower())
            # skip further processing of word loop
            # print("Stop Word Removed: "+w)
            continue
        except ValueError:
            pass

        w = stemm_word(w)

        # hack, hack, hack
        if w == '':
            continue

        # add the sanitized word into return list
        sanitized_words.append(w)

    return sanitized_words

def includeInVocabulary(vocabulary, doc_id, words):
    """
        Add the terms of "text" from "doc_id" in our vocabulary.
    
    :param vocabulary A dictionary of words and docs which contain the word 
    :param doc_id: Document ID
    :param words: List of words to be added to the Index

    :return: Updated document index
    """

    # store the words in vocabulary table
    for w in words:
        # if the term is in the table
        if vocabulary.has_key(w):
            doc_entry = vocabulary.get(w)
            #doc_entry["df"] += 1

            # if the doc_id is already in the table
            if doc_entry.has_key(doc_id):
                doc_entry[doc_id] += 1
                
            else:
                doc_entry[doc_id] = 1
                

            vocabulary[w] = doc_entry

        else:
            # a dict of {doc_id, tf}
            doc_entry = {}
            doc_entry[doc_id] = 1
            #doc_entry["df"] = 1

            vocabulary[w] = doc_entry

    return vocabulary

def updateLinksData(src_url, outgoing_links, link_data):
    """
        Keep a data structure of source links to destinations links.

        :param source page URL
        :param outgoing_links as link of URLs
        :param link_data as dictionary of links with their own link of outgoing links

        {src_link: 
            Set(dest_link)
        }
    """

    #print(outgoing_links)

    new_link_set = Set()
    # for each new link in the list
    for l in outgoing_links:
        # URL must start with HTTP
        if l[:4] == "http":
            # add the link to the set of links
            new_link_set.add(l)
            print("Adding to link_data: "+l)

    if link_data.has_key(src_url):
        # get the link entry
        link_set = link_data.get(src_url)  
        # take the union of the link sets and save it back    
        new_link_set = link_set | new_link_set
        
    
    # the source URL does not exists, create a new entry
    link_data[src_url] = list(new_link_set)

    return link_data

def process(scrapped_data_file):
    """
        Read all files in a path and generates a TF-IDF table.

    :param path: String

    :return:
        index_data: The TF-IDF data
        link_data: All links and their child links
    """
    index_file = "index_file.pkl"
    link_file = "link_file.pkl"

    index_data = {}
    link_data = {}

    # load the previous index
    index_data = loadPickle(index_file)
    if index_data == None:
        print("Cannot load index file")
        exit(1)

    # load the previous index
    link_data = loadPickle(link_file)
    if link_data == None:
        print("Cannot load index file")
        exit(1)

    # load scrapped data
    try:
        scrapped_data = open(scrapped_data_file, "r").readlines()
    except IOError:
        print("Cannot find scrapped_data_file")
        exit(2)

    # get stop-words
    stop_word_list = getStopWordList("stopwords.txt")

    # update the index
    for data in scrapped_data:
        webpage_data = json.loads(data)

        title = webpage_data["page_title"]
        url = webpage_data["page_url"]
        title, content = parseSGML(webpage_data["page_content"])
        
        doc_id = getHash(url)
        #doc_id_title[doc_id] = title

        print("Processing: "+url)
        #print(content)
        #print(title)

        # sanitize the text to get only useful words
        words = sanitize(title + "\n" + content, stop_word_list)

        index_data = includeInVocabulary(index_data, doc_id, words)

        link_data = updateLinksData(url, webpage_data['page_links'], link_data)

        #break

    # Once the index has been created, save it for later reuse
    if savePickle(index_file, index_data) > 0:
        print("Cannot save index file")
        exit(3)

    if savePickle(link_file, link_data) > 0:
        print("Cannot save link file")
        exit(3)

    return index_data, link_data


if __name__ == "__main__":
    project_dir = "/home/c/chandanchowdhury/Documents/CIS-833/CSSearch/"

    
    scrapped_data_file = "crawler/crawler/spiders/ksucs_2017-12-09_16.json"
    #scrapped_data_file = "crawler/crawler/spiders/sample.json"

    index_data, link_data = process(project_dir+scrapped_data_file)
    #print("N =%d" % N)
    #print("Index")
    #print(index_data)
    #print("link data")
    #for l in link_data:
    #    print("SRC: %s" % l)
    #    for lc in link_data.get(l):
    #        print("-> %s" % lc)


