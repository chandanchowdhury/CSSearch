try:
    import cPickle as pickle
except:
    import pickle

import operator
import string
from sets import Set

from stemming.porter import stem

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

def loadData():
    """
        Load the pickle data.

    """
    project_dir = "/home/c/chandanchowdhury/Documents/CIS-833/CSSearch/indexer/"

    index_file = "index_file.pkl"
    link_file = "link_file.pkl"

    index_data = loadPickle(project_dir+index_file)
    link_data = loadPickle(project_dir+link_file)

    return index_data, link_data

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

def stemm_word(word):
    """
        Use Porter stemmer to stem words.

    :param word: String

    :return: Stemmed word
    """
    return stem(word)

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

def get_links(query_terms):
    """
        Get all the links which contains the terms in the query string.

        :param query_terms as list of strings

        :return 
    """

    # the set of links all of which contains all the terms in the query string
    final_links = None
    for term in query_terms:
        # get all links containing the term and put in a set
        links = Set(index_data.get(term))
        print("\n\nQuery Term: %s" % term)
        #print(links)

        # special case for first iteration, because: empty & anything = empty
        if final_links == None:
            final_links = links

        # take intersection of links set
        final_links = final_links & links

        print(final_links)

    # convert the Set to List and return
    return list(final_links)

def rank_links(tf_idf_table, query_terms, links, topN=5):
    """
        Rank the list of given links in terms of relevance.

        :param links List of URLs
        :param query_terms as list of strings

        :return List of URLs ranked
    """
    
    tf = {}
    for w in query_terms:
        f = query_terms.count(w)
        tf[w] = f

    q_tf_idf = {}
    for term in tf:
        # if the query term is found in files
        if tf_idf_table.has_key(term):
            q_tf_idf[term] = tf.get(term) # * log(N/1)
        else:
            # if the query term is NOT found in files, set IDF to 0
            q_tf_idf[term] = 0

    # score of all docs for this query    
    doc_vals = {}

    # Wiq denominator in CosSim
    DWiq = 0
    for t in tf_idf_table:       

        DWiq = q_tf_idf.get(t)
        # if the term is not in query, ignore
        if DWiq == None:
            continue


        print("Term: %s \t\t Query TF-IDF: %d" % (t, q_tf_idf.get(t)))

        idf_row = tf_idf_table.get(t)
        # if the query term is in our corpus
        if idf_row != None:
            #print(idf_row)

            # get the document frequency
            df = float(len(idf_row)) - 1 
            print("DF: %d" % (df))

            # Wij denominator in CosSim
            DWij = 0

            # Numerator in CosSim
            Njq = 0

            # calculate values of each document specific

            for doc in idf_row:
                #print(doc)

                # The "df" should not be processed
                if doc == "df":
                    continue

                try:
                    _ = links.index(doc)
                except:
                    continue

                #print("Doc ID: %s \tTF: %d" % (doc, idf_row.get(doc)))

                DWij = idf_row.get(doc)

                #Njq =  q_tf_idf.get(t) * idf_row.get(doc)

                if doc_vals.has_key(doc):
                    vals = doc_vals.get(doc)
                    vals["DWiq"] += pow(DWiq, 2)
                    vals["DWij"] += pow(DWij, 2)
                    vals["NWjq"] += DWij * DWiq

                    doc_vals[doc]  = vals
                else:
                    vals = {}
                    vals["DWiq"] = pow(DWiq, 2)
                    vals["DWij"] = pow(DWij, 2)
                    vals["NWjq"] = DWij * DWiq

                    doc_vals[doc]  = vals

        #print(doc_vals)

    # Calculate the CosSim value
    doc_score = {}
    for doc in doc_vals:
        #print(doc)
        vals = doc_vals.get(doc)
        #print(vals)
        #n = vals.get("NWjq")
        #d = float(pow(vals.get("DWij") * vals.get("DWiq"),0.5))
        #print(n)
        #print(d)            
        #print(float(n/float(d)))
        doc_score[doc] = float(vals.get("NWjq"))/float(pow(vals.get("DWij") * vals.get("DWiq"),0.5))
        #print(doc_score[doc])


    #print(doc_score)

    doc_score = sorted(doc_score.items(), key=operator.itemgetter(1), reverse=True)
    

    return doc_score


def search(index_data, link_data, stop_word_list, search_string):
    """
        1. Clean and Stem the query terms
        2. Get all the links which contain the query terms
        3. Rank the links
    """

    query_terms = sanitize(search_strings, stop_word_list)

    # get related links
    links = get_links(query_terms)

    # rank the links
    ranked_list = rank_links(index_data, query_terms, links)

    return ranked_list


if __name__ == "__main__":

    # get stop-words
    stop_word_list = getStopWordList("stopwords.txt")

    index_data, link_data = loadData()
    
    search_strings = [
        #"computer science"
        #"computer science information retrieval"
        #"computer science caragea"
        #"beocat"
        #"beocat help"
        "beocat administration team"
    ]
    for s in search_strings:
        print("\n\nQuery: %s" % s)
        links = search(index_data, link_data, stop_word_list, s)
        print("\n\nResult:")
        for l in links:
            print(l)

