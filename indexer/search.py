try:
    import cPickle as pickle
except:
    import pickle

import collections
import operator
import string
from sets import Set

from stemming.porter import stem

ROUND_DIGITS = 6
EPSILON = 0.8

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
        #print("\n\nQuery Term: %s" % term)
        #print(links)

        # special case for first iteration, because: empty & anything = empty
        if final_links == None:
            final_links = links

        # take intersection of links set
        final_links = final_links & links

        #print(final_links)

    # convert the Set to List and return
    return list(final_links)

def rank_links(tf_idf_table, query_terms, links):
    """
        Rank the list of given links in terms of relevance.

        :param TF-IDF table
        :param query_terms as list of strings
        :param links List of URLs

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


        #print("Term: %s \t\t Query TF-IDF: %d" % (t, q_tf_idf.get(t)))

        idf_row = tf_idf_table.get(t)
        # if the query term is in our corpus
        if idf_row != None:
            #print(idf_row)

            # get the document frequency
            df = float(len(idf_row))
            #print("DF: %d" % (df))

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

                # skip any link that are not relevant
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

    sorted_by_score = sorted(doc_score.items(), key=operator.itemgetter(1), reverse=True)
    #print(sorted_by_score)

    sorted_score = collections.OrderedDict()
    for url, score in sorted_by_score:
        sorted_score[url] = score

    #print(sorted_score)
    return sorted_score
    

def print_scores(ranked_list, links, topN=10):
    """
        Takes an OrderdDict and print topN entries which are also in links
    """
    n = topN
    for url, score in ranked_list.items():
        try:
            _  = links.index(url)
            print("Score: %f \t URL: %s" %(score, url))

            n -= 1

            if n <= 0:
                break
        except:
            pass

        

def normalize_scores(scores):
    """
        Normalize the scores so that their sum is equal to 1.
    """
    #print(scores)
    keys = scores.keys()

    sum = 0.0
    for k in keys:
        #print("%06f\t" % scores.get(k)),
        sum += scores.get(k)

    if sum == 1.0:
        return scores

    new_scores = {}
    for k in keys:
        new_scores[k] = scores.get(k)/float(sum)

    return new_scores

def calculate_pagerank_with_teleport(Graph, epsilon, iterations=50):
    prev_score = None
    score = None
    iteration = 1

    #print("No. of Nodes: %d" % len(Graph))

    # Loop 
    while True:
        #print("\nIteration: "+str(iteration))
        iteration += 1

        # first iteration
        if score is None:
            score = {}
            no_of_nodes = len(Graph.keys())
            for node in Graph:
                score[node] = 1/float(no_of_nodes)
        else:
            # normal iterations
            score = {}
            for A in Graph:
                #print("-"*10)
                #print("Node: "+A)

                # Reinitialize the score
                score[A] = epsilon/float(no_of_nodes)

                for B in Graph:    
                    #print("Link from: "+B)
                    #print(Graph.get(B))
                    #print(Graph.get(B).index(A))
                    try:
                        _ = Graph.get(B).index(A)                    
                        #print(B+" points to "+A)
                        degree_B = len(Graph.get(B))   
                        #print("Score: "+str(prev_score[B]))
                        #print("Degree: "+str(degree_B))
                        #print("Adding "+str(prev_score[B]/float(degree_B))+ " to "+str(score[A]))
                        score[A] += (1-epsilon) * prev_score[B]/float(degree_B)
                        #print("New score:"+str(score[A]))
                        
                        
                    except ValueError:
                        #print(A +" not in "+B)
                        pass
                score[A] = round(score[A], ROUND_DIGITS)

        #print("Before Normalization")
        #print_scores(score)
        #normalize the scores
        #print("After Normalization")
        score = normalize_scores(score)
        #print_scores(score)

        # check for convergence
        if score == prev_score:
            break
        
        prev_score = score

        if iteration > iterations:
            break

    # sort by score
    sorted_by_score = sorted(score.items(), key=operator.itemgetter(1), reverse=True)

    #print(sorted_by_score)

    sorted_score = collections.OrderedDict()
    for url, score in sorted_by_score:
        sorted_score[url] = score

    #print(sorted_score)


    return sorted_score

def build_graph(link_data, links):
    """
        Use the link_data to build a graph of the links.

        :param link_data as dictionary of source link with destination links
        :param links the links as list for which the graph need to be created

        :return graph as dictionary
    """
    graph = {}

    # add all data for links
    for l in links:
        #print("Adding "+l)
        #print(link_data.get(l))
        graph[l] = list(link_data.get(l))

    # add all links that point to links
    for slink in link_data:
        for l in links:
            # the links is already in graph, skip
            if graph.has_key(slink):
                continue

            try:
                dest_links = list(link_data.get(slink))
                # if slink points to l
                _ = dest_links.index(l)
                # add the slink to graph
                graph[slink] = dest_links
                #print("Adding "+slink)
            except Exception as e:
                pass

    #print(len(graph))
    #print(graph)

    return graph


def search(index_data, link_data, stop_word_list, search_string):
    """
        1. Clean and Stem the query terms
        2. Get all the links which contain the query terms
        3. Rank the links
    """

    topN = 5

    query_terms = sanitize(search_strings, stop_word_list)
    print(query_terms)

    # get all links which contain all the query terms
    links = get_links(query_terms)
    print("\nURLs containing all of the query terms (%d):" % len(links))
    for l in links:
        print(l)

    # rank the links using Vector model
    vector_ranked = rank_links(index_data, query_terms, links)
    #print(ranked_list)
    
    # build a graph of the links
    graph = build_graph(link_data, links)

    # rank the links using Vector model
    page_ranked = calculate_pagerank_with_teleport(graph, EPSILON, 10)        
    
    # return the data
    return links, vector_ranked, page_ranked


if __name__ == "__main__":

    # get stop-words
    stop_word_list = getStopWordList("stopwords.txt")

    index_data, link_data = loadData()
    #print(link_data)
    
    search_strings = [
        #"computer science"
        #"caragea"
        #"cornelia caragea"
        #"computer science information retrieval"        
        #"computer science caragea"
        #"computer science facebook"
        #"beocat"
        #"beocat help"
        #"beocat administration team"
        #"chandan"
        #"chandan chowdhury"
        #"krutarth"
        #"ranojoy chatterjee"
        #"joydeep mitra"
        "George Amariucai" # zero results?
    ]
    for s in search_strings:
        print("\n\nQuery: %s" % s)
        links, vector_ranked, page_ranked = search(index_data, link_data, stop_word_list, s)
        print("\n\nVector model result:")
        print_scores(vector_ranked, links)

        print("\n\nPageRank with teleport(e=%f) result:" % EPSILON)
        print_scores(page_ranked, links)
        

        

