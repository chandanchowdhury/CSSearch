try:
    import cPickle as pickle
except:
    import pickle

import json
import string
import hashlib

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


def saveIndex(index_file, index_data):
    """
        Save indexed data in ZPickle (Compressed Pickle) format.
    """
    print("Saving Index data to file: "+index_file)

    try:
        with open(index_file, "wb") as fd:
            pickle.dump(index_data, fd)
    except pickle.PicklingError as pe:
        print("Failed: Saving pickle data")
        return 1


def loadIndex(index_file):
    """
        Load the index file.
    """
    print("Loading previous Index data from file: "+index_file)

    index_data = {}
    try:
        with open(index_file, "rb") as fd:
            index_data = pickle.load(fd)
    except EOFError:
        pass
    except pickle.UnpicklingError as upe:
        print("Failed: Loading Pickle Data")
        index_data = None
    except IOError:
        index_data = {}

    return index_data

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

    title = soup.title
    # Get the text between all tags joined by a space character
    contents = soup.get_text(' ')
    # print("Title:", title)
    # print("Text:", contents)

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
    :param word: List of words to be added to the Index

    :return: Updated document index
    """

    # store the words in vocabulary table
    for w in words:
        # if the term is in the table
        if vocabulary.has_key(w):
            doc_entry = vocabulary.get(w)

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

            vocabulary[w] = doc_entry

    return vocabulary



def process(scrapped_data_file):
    """
        Read all files in a path and generates a TF-IDF table.

    :param path: String

    :return:
        N: Number of files read.
        tf_idf_table: The TF-IDF data
    """
    index_file = "index_file.pkl"
    index_data = None
    doc_id_title = {}

    # load the previous index
    index_data = loadIndex(index_file)
    if index_data == None:
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

        title = webpage_data["page_title"][0]
        _, content = parseSGML(webpage_data["page_content"])
        url = webpage_data["page_url"]
        doc_id = getHash(url)

        doc_id_title[doc_id] = title

        print("Processing: "+url)
        print(content)

        # sanitize the text to get only useful words
        words = sanitize(title + "\n" +content, stop_word_list)

        index_data = includeInVocabulary(index_data, doc_id, words)

        break

    # Once the index has been created, save it for later reuse
    #if saveIndex(index_file, index_data) > 0:
    #    print("Cannot save index file")
    #    exit(3)


    # now calculate and store TF-IDF for each term
    tf_idf_table = {}

    N = len(doc_id_title)
    #print("N: %d" % (N))

    for term in index_data:
        #print("-"*20)

        #print("Term: %s" % (term))
        doc_entries = index_data.get(term)
        df = len(doc_entries)
        #print("DF: %d" % (df))

        idf = {}
        # storing as part of IDF data
        idf["df"] = 0
        for doc_id in doc_entries:
            idf["df"] += 1
            #print("Doc ID: %s" % (doc_id))
            tf = doc_entries.get(doc_id) #1 + log(float(doc_entries.get(doc_id)))

            #print("TF: %f" % (tf))

            #print(float(log(N/df)))
            tf_idf = tf #/float(df) #* log(N/float(df))
            #print("TF-IDF %f" % (tf_idf))
            idf[doc_id] = tf_idf

        tf_idf_table[term] = idf

    return N, tf_idf_table, index_data


if __name__ == "__main__":
    project_dir = "/home/c/chandanchowdhury/Documents/CIS-833/CSSearch/"

    scrapped_data_file = "crawler/ksucs_2017-12-04_23.json"
    scrapped_data_file = "crawler/ksucs_2017-12-04_22.json"

    N, tf_idf_table, vocabulary = process(project_dir+scrapped_data_file)
    print("N =%d" % N)
    #print("vocabulary")
    #print(vocabulary)
    print("tf_idf_table")
    print(tf_idf_table)


