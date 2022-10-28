import gzip
import json
import logging
import os
import osometweet
import re
import sys
import time
import numpy as np
import scipy.sparse as sp

from datetime import datetime

from sklearn.feature_extraction.text import CountVectorizer
from sklearn.feature_extraction.text import TfidfTransformer
from sklearn.preprocessing import normalize

logger = logging.getLogger('bloc.bloc')

def procLogHandler(handler, loggerDets):
    
    if( handler is None ):
        return
        
    if( 'level' in loggerDets ):
        handler.setLevel( loggerDets['level'] )    
        
        if( loggerDets['level'] == logging.ERROR ):
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s :\n%(message)s')
            handler.setFormatter(formatter)

    if( 'format' in loggerDets ):
        
        loggerDets['format'] = loggerDets['format'].strip()
        if( loggerDets['format'] != '' ):
            formatter = logging.Formatter( loggerDets['format'] )
            handler.setFormatter(formatter)

    logger.addHandler(handler)

def setLoggerDets(logger, loggerDets):

    if( len(loggerDets) == 0 ):
        return

    consoleHandler = logging.StreamHandler()

    if( 'level' in loggerDets ):
        logger.setLevel( loggerDets['level'] )
    else:
        logger.setLevel( logging.INFO )

    if( 'file' in loggerDets ):
        loggerDets['file'] = loggerDets['file'].strip()
        
        if( loggerDets['file'] != '' ):
            fileHandler = logging.FileHandler( loggerDets['file'] )
            procLogHandler(fileHandler, loggerDets)

    procLogHandler(consoleHandler, loggerDets)

def setLogDefaults(params):
    
    params['log_dets'] = {}

    if( params['log_level'] == '' ):
        params['log_dets']['level'] = logging.INFO
    else:
        
        logLevels = {
            'CRITICAL': 50,
            'ERROR': 40,
            'WARNING': 30,
            'INFO': 20,
            'DEBUG': 10,
            'NOTSET': 0
        }

        params['log_level'] = params['log_level'].strip().upper()

        if( params['log_level'] in logLevels ):
            params['log_dets']['level'] = logLevels[ params['log_level'] ]
        else:
            params['log_dets']['level'] = logging.INFO
    
    params['log_format'] = params['log_format'].strip()
    params['log_file'] = params['log_file'].strip()

    if( params['log_format'] != '' ):
        params['log_dets']['format'] = params['log_format']

    if( params['log_file'] != '' ):
        params['log_dets']['file'] = params['log_file']

def genericErrorInfo(slug=''):
    exc_type, exc_obj, exc_tb = sys.exc_info()
    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
    
    errMsg = fname + ', ' + str(exc_tb.tb_lineno)  + ', ' + str(sys.exc_info())
    logger.error(errMsg + slug)

    return errMsg

#http://stackoverflow.com/questions/4770297/python-convert-utc-datetime-string-to-local-datetime
def datetimeFromUtcToLocal(utc_datetime):
    now_timestamp = time.time()
    offset = datetime.fromtimestamp(now_timestamp) - datetime.utcfromtimestamp(now_timestamp)
    return utc_datetime + offset

#tweet_datetime: 2020-08-10T23:59:59
def gen_post_snowflake_twitter_id(tweet_datetime):
    
    pre_snowflake_last_tweet_id = 29700859247 #(2010-11-04T21:02:48.000Z)

    offset = 1288834974657
    
    if( isinstance(tweet_datetime, str) ):
        tweet_datetime = datetime.strptime(tweet_datetime, '%Y-%m-%d %H:%M:%S')
    
    tweet_datetime = (tweet_datetime.timestamp() * 1000) - offset#convert seconds to nanoseconds by * 1000
    tweet_datetime = int(tweet_datetime)

    tweet_id = "{0:b}".format(tweet_datetime) + '1'*22
    tweet_id = int(tweet_id, 2)

    return tweet_id

def find_tweet_timestamp_post_snowflake(tid):
    #credit: https://github.com/oduwsdl/tweetedat/blob/master/script/TimestampEstimator.py#L175 and https://ws-dl.blogspot.com/2019/08/2019-08-03-tweetedat-finding-tweet.html
    offset = 1288834974657
    tstamp = (tid >> 22) + offset
    utcdttime = datetime.utcfromtimestamp(tstamp/1000)
    return utcdttime

#extract realDonaldTrump from 'https://twitter.com/realDonaldTrump/status/863007411132649473'
def get_screen_name_frm_status_uri(tweet_uri):

    tweet_uri = tweet_uri.strip()
    tweet_uri = tweet_uri.replace('http://twitter.com/', 'https://twitter.com/')

    if( tweet_uri.startswith('https://twitter.com/') is False or tweet_uri.find('/status/') == -1 ):
        return ''

    return tweet_uri.replace('https://twitter.com/', '').split('/')[0]
#file - start

def readTextFromFile(infilename):

    text = ''

    try:
        with open(infilename, 'r') as infile:
            text = infile.read()
    except:
        print('\treadTextFromFile()error filename:', infilename)
        genericErrorInfo()
    

    return text

def dumpJsonToFile(outfilename, dictToWrite, indentFlag=True, extraParams=None):

    if( extraParams is None ):
        extraParams = {}

    extraParams.setdefault('verbose', True)

    try:
        outfile = open(outfilename, 'w')
        
        if( indentFlag ):
            json.dump(dictToWrite, outfile, ensure_ascii=False, indent=4)#by default, ensure_ascii=True, and this will cause  all non-ASCII characters in the output are escaped with \uXXXX sequences, and the result is a str instance consisting of ASCII characters only. Since in python 3 all strings are unicode by default, forcing ascii is unecessary
        else:
            json.dump(dictToWrite, outfile, ensure_ascii=False)

        outfile.close()

        if( extraParams['verbose'] ):
            logger.info('\tdumpJsonToFile(), wrote: ' + outfilename)
    except:
        genericErrorInfo('\n\terror: outfilename: ' + outfilename)
        return False

    return True

def getDictFromJsonGZ(path):

    json = getTextFromGZ(path)
    if( len(json) == 0 ):
        return {}
    return getDictFromJson(json)

def getTextFromGZ(path):
    
    try:
        with gzip.open(path, 'rb') as f:
            return f.read().decode('utf-8')
    except:
        genericErrorInfo()

    return ''

def getDictFromJson(jsonStr):

    try:
        return json.loads(jsonStr)
    except:
        genericErrorInfo('\tjsonStr prefix: ' + jsonStr[:100])

    return {}

def getDictFromFile(filename):

    try:

        if( os.path.exists(filename) == False ):
            return {}

        return getDictFromJson( readTextFromFile(filename) )
    except:
        print('\tgetDictFromFile(): error filename', filename)
        genericErrorInfo()

    return {}

def gzipTextFile(path, txt):
    
    try:
        with gzip.open(path, 'wb') as f:
            f.write(txt.encode())
    except:
        genericErrorInfo()

#file - end

#/stringmatrix/vector manipulation - start

def get_color_txt(txt, ansi_code='91m'):
    return txt if txt.strip() == '' else '\033[' + ansi_code + '{}\033[00m'.format(txt)

def color_bloc_action_str(bloc_action_str, split_pattern='([^□⚀⚁⚂⚃⚄⚅.|()*]+)', ansi_code='91m'):

    if( ansi_code.strip() == '' ):
        return bloc_action_str

    colored_bloc_action_str = ''
    bloc_action_tokens = re.split(split_pattern, bloc_action_str)
    
    for tok in bloc_action_tokens:

        if( tok.strip() not in split_pattern ):
            tok = get_color_txt(tok, ansi_code=ansi_code)
        
        colored_bloc_action_str += tok

    return colored_bloc_action_str

def get_char_ngram(string, n):

    if( n < 1 or n > len(string) ):
        return []

    return [ string[i:i+n] for i in range(len(string)-n+1) ]

def get_char_ngram_vocab(string, n):
    
    ngrams = get_char_ngram(string, n)
    vocab = {}
    
    for gram in ngrams:

        vocab.setdefault(gram, 0)
        vocab[gram] += 1

    vocab = sorted(vocab.items(), key=lambda x: x[1], reverse=True)
    return vocab

def get_doc_lst_pos_maps(doc_lst, rm_text=True):

    new_doc_list = []
    pos_id_mapping = {}

    try:

        for i in range( len(doc_lst) ):

            d = doc_lst[i]
            d.setdefault('id', i)
            pos_id_mapping[i] = {'id': d['id']}

            #transfer other properties - start
            for ky, val in d.items():

                if( rm_text is True ):
                    if( ky == 'text' ):
                        continue

                pos_id_mapping[i][ky] = val
            #transfer other properties - end

            new_doc_list.append( d['text'] )
    
    except:
        genericErrorInfo()
        return [], {}

    return new_doc_list, pos_id_mapping

def map_tf_mat_to_doc_ids(payload, pos_id_mapping):

    #see get_tf_matrix().payload for payload's structure
    if( 'tf_matrix' not in payload and 'top_ngrams' not in payload ):
        return {}

    if( 'per_doc' not in payload['top_ngrams'] ):
        return {}

    tf_matrix = []
    top_ngrams_per_doc = []
    for pos, doc_dct in pos_id_mapping.items():
        if( pos < len(payload['tf_matrix']) ):

            tf_matrix.append({
                'id': doc_dct['id'], 
                'tf_vector': payload['tf_matrix'][pos]
            })

            if( len(payload['top_ngrams']['per_doc']) != 0 ):
                top_ngrams_per_doc.append({
                    'id': doc_dct['id'],
                    'ngrams': payload['top_ngrams']['per_doc'][pos]
                })

            #transfer other properties - start
            for ky, val in doc_dct.items():
                tf_matrix[-1][ky] = val

                if( len(top_ngrams_per_doc) != 0 ):
                    top_ngrams_per_doc[-1][ky] = val
            #transfer other properties - end


    #special case for (optional, see: get_tf_matrix().tf_matrix_norm) tf_matrix_normalized - start
    for opt in ['tf_matrix_normalized', 'tf_idf_matrix']:
        if( opt in payload ):
            
            opt_vect = []
            for pos, doc_dct in pos_id_mapping.items():
                if( pos < len(payload[opt]) ):

                    opt_vect.append({
                        'id': doc_dct['id'], 
                        'tf_vector': payload[opt][pos]
                    })

                    #transfer other properties - start
                    for ky, val in doc_dct.items():
                        opt_vect[-1][ky] = val
                    #transfer other properties - end

            payload[opt] = opt_vect
    #special case for (optional, see: get_tf_matrix().tf_matrix_norm) tf_matrix_normalized - end

    payload['tf_matrix'] = tf_matrix
    payload['top_ngrams']['per_doc'] = top_ngrams_per_doc

    return payload

def gen_folded_vocab( tf_matrix, bloc_variant ):

    if( 'vocab' not in tf_matrix or 'type' not in bloc_variant ):
        return {}

    expected_types = ['folded_words']
    if( bloc_variant['type'] not in expected_types ):
        return {}
    
    new_vocab = {}
    logger.debug('\ngen_folded_vocab():')
    logger.debug('\tfold_start_count:', bloc_variant['fold_start_count'])

    for i in range( len(tf_matrix['vocab']) ):
        
        v = tf_matrix['vocab'][i]
        new_v = fold_word(v, bloc_variant['fold_start_count'], count_applies_to_all_char=bloc_variant['count_applies_to_all_char'], fold_exclude_chars=bloc_variant.get('fold_exclude_chars', '') )

        new_vocab.setdefault(new_v, [])
        new_vocab[new_v].append(i)

    return new_vocab

def get_default_symbols():
    bloc_symbols_file = '{}/symbols.json'.format(os.path.dirname(os.path.abspath(__file__)))
    return getDictFromFile(bloc_symbols_file)

def gen_bloc_variant_tf_mat( tf_matrix, bloc_variant ):

    if( 'tf_matrix' not in tf_matrix or 'vocab' not in tf_matrix or 'type' not in bloc_variant ):
        return {}

    if( len(tf_matrix['tf_matrix']) == 0 ):
        return {}

    expected_types = ['folded_words']
    if( bloc_variant['type'] not in expected_types ):
        return {}
    
    new_vocab = {}
    bloc_variant.setdefault('fold_start_count', 4)
    bloc_variant.setdefault('count_applies_to_all_char', False)
    bloc_variant.setdefault('fold_exclude_chars', '')

    logger.debug( '\ngen_bloc_variant_tf_mat():' )
    logger.debug( '\ttype: {}'.format(bloc_variant['type']) )
    logger.debug( '\tfold_start_count: {}'.format(bloc_variant['fold_start_count']) )
    logger.debug( '\tcount_applies_to_all_char: {}'.format(bloc_variant['count_applies_to_all_char']) )
    logger.debug( '\told vocab: {} entries'.format(len(tf_matrix['vocab'])) )

    tf_mat = tf_matrix['tf_matrix'][0]['tf_vector']
    for i in range( 1, len(tf_matrix['tf_matrix']) ):
        tf_mat = sp.vstack( (tf_mat, tf_matrix['tf_matrix'][i]['tf_vector']), format='csr' )

    new_vocab = gen_folded_vocab( tf_matrix, bloc_variant )

    logger.debug('')
    logger.debug( f'new_vocab: {len(new_vocab)} entries' )
    
    feature_indx = 0
    new_tf_mat = None
    new_vocab_lst = []
    #this function merges columns of features across all users
    for v, col_indices in new_vocab.items():
        
        logger.debug( '\tfeature_indx: {} {} col_indices: {}'.format(feature_indx, v, col_indices) )
        feature_indx += 1
        new_vocab_lst.append(v)
        
        if( len(col_indices) == 1 ):
            
            indx = col_indices[0]
            if( new_tf_mat is None ):
                new_tf_mat = tf_mat[:,indx]
            else:
                new_tf_mat = sp.hstack( (new_tf_mat, tf_mat[:,indx]), format='csr' )
        else:
            
            #sum all columns (from col_indices) in tf_mat to merge features
            indx = col_indices[0]
            col_sum = tf_mat[:,indx]
            col_indices.pop(0)

            for indx in col_indices:
                col_sum = np.sum( [col_sum, tf_mat[:,indx]], axis=0 )

            if( new_tf_mat is None ):
                new_tf_mat = col_sum
            else:
                new_tf_mat = sp.hstack( (new_tf_mat, col_sum), format='csr' )

    logger.debug('')
    logger.debug( '\tnew_tf_mat shape: {}'.format(new_tf_mat.shape) )
    logger.debug( '\tnew_vocab: {}'.format(new_vocab_lst) )
    logger.debug('')

    return {
        'tf_matrix': new_tf_mat,
        'vocab': new_vocab_lst
    }

def update_bloc_model( old_bloc_model, new_tf_mat, tf_matrix_norm, tf_idf_norm, **kwargs ):
    
    if( len(new_tf_mat) == 0 ):
        return old_bloc_model
    
    #mimic signature of function call in gen_ngram_tf_matrix() and process payload similar to gen_ngram_tf_matrix()
    pos_id_mapping = kwargs.pop('pos_id_mapping', None)
    new_tf_mat = get_tf_matrix( 
        doc_lst=['dummy'], 
        n=0, 
        tf_mat=new_tf_mat['tf_matrix'],
        vocab=new_tf_mat['vocab'],
        tf_matrix_norm=tf_matrix_norm,
        tf_idf_norm=tf_idf_norm,
        pos_id_mapping=None,
        **kwargs
    )

    if( pos_id_mapping is not None ):
        kwargs['pos_id_mapping'] = pos_id_mapping

    if( 'token_pattern' in old_bloc_model ):
        new_tf_mat['token_pattern'] = old_bloc_model['token_pattern']


    for m in ['tf_matrix', 'tf_matrix_normalized', 'tf_idf_matrix']:
        
        if( m not in new_tf_mat ):
            continue

        for i in range( len(new_tf_mat[m]) ):
            
            old_bloc_model[m][i]['tf_vector'] = new_tf_mat[m][i]
            new_tf_mat[m][i] = old_bloc_model[m][i]


    for m in ['per_doc', 'all_docs']:

        if( 'top_ngrams' not in new_tf_mat or 'top_ngrams' not in old_bloc_model ):
            continue

        if( m not in new_tf_mat['top_ngrams'] or m not in old_bloc_model['top_ngrams'] ):
            continue

        if( len(new_tf_mat['top_ngrams'][m]) != len(old_bloc_model['top_ngrams'][m]) ):
            continue

        for i in range( len(new_tf_mat['top_ngrams'][m]) ):
            
            old_bloc_model['top_ngrams'][m][i]['ngrams'] = new_tf_mat['top_ngrams'][m][i]
            new_tf_mat['top_ngrams'][m][i] = old_bloc_model['top_ngrams'][m][i]

    return new_tf_mat

def get_bloc_lite_twt_frm_full_twt(tweet):
    
    def tranfer_dets_for_stream_statuses(twt):
        
        #transfer details for tweets gotten from streams
        #See: http://web.archive.org/web/20210812135100/https://docs.tweepy.org/en/stable/extended_tweets.html
        if( 'extended_tweet' not in twt ):
            return twt

        for ky in ['full_text', 'display_text_range', 'entities', 'extended_entities']:
            if( ky in twt['extended_tweet'] ):
                twt[ky] = twt['extended_tweet'][ky]

        return twt

    if( 'id' not in tweet ):
        return {}

    tweet = tranfer_dets_for_stream_statuses(tweet)
    payload = {
        'id': tweet['id'],
        'source': tweet['source'],
        'created_at': tweet['created_at'],
        'user': tweet['user']
    }
    
    for itm in ['full_text', 'text']:
        if( itm in tweet ):
            payload['full_text'] = tweet[itm]
            break
    

    if( tweet['in_reply_to_status_id'] is None ):
        payload['in_reply_to_status_id'] = None
        payload['in_reply_to_user_id'] = None
    else:
        payload['in_reply_to_status_id'] = tweet['in_reply_to_status_id']
        payload['in_reply_to_user_id'] = tweet['in_reply_to_user_id']

    
    payload['in_reply_to_screen_name'] = tweet['in_reply_to_screen_name']
    for itm in ['display_text_range', 'entities', 'extended_entities']:
        if( itm in tweet ):
            payload[itm] = tweet[itm]


    if( 'retweeted_status' in tweet ):
        payload['retweeted_status'] = {
            'user': {'screen_name': tweet['retweeted_status']['user']['screen_name'], 'id': tweet['retweeted_status']['user']['id']},
            'created_at': tweet['retweeted_status']['created_at'],
            'id': tweet['retweeted_status']['id']
        }
    
    return payload

def get_bloc_doc_lst(twts_bloc, dimensions, src='', src_class=''):

    doc_lst = []

    for d in twts_bloc:

        if( 'bloc' not in d ):
            continue
        
        doc = [ d['bloc'][dim] for dim in dimensions if dim in d['bloc'] ]
        if( len(doc) == 0 ):
            continue

        doc = ''.join(doc)
        doc = doc.strip()
    
        if( doc == '' ):
            continue

        doc_lst.append({
            'text': doc,
            'user_id': d['user_id'],
            'screen_name': d['screen_name'],
            'src': src,
            'class': src_class
        })

    return doc_lst

def get_bloc_variant_tf_matrix(doc_lst, ngram, tf_mat=None, vocab=None, token_pattern='[^□⚀⚁⚂⚃⚄⚅. |()*]+|[□⚀⚁⚂⚃⚄⚅.]', **kwargs):

    #bigram: r'[^ |()*]', word: '[^□⚀⚁⚂⚃⚄⚅. |()*]+|[□⚀⚁⚂⚃⚄⚅.]'
    #reconcile implementation with bloc_analyzer.py::analyze_bloc_for_users()
    bloc_variant = kwargs.get('bloc_variant', None)

    if( bloc_variant is None ):

        tf_matrix = get_tf_matrix( 
            doc_lst, 
            ngram,
            tf_mat=tf_mat,
            vocab=vocab,
            token_pattern=token_pattern,
            lowercase=False, 
            **kwargs
        )

    else:
        tf_matrix = get_tf_matrix( 
            doc_lst, 
            ngram,
            tf_mat=tf_mat,
            vocab=vocab,
            token_pattern=token_pattern,
            lowercase=False,
            keep_tf_matrix=True,
            tf_matrix_norm='',
            tf_idf_norm='',
            pos_id_mapping=kwargs.get('pos_id_mapping', None)
        )

        bloc_variant_tf_matrix = gen_bloc_variant_tf_mat( tf_matrix, bloc_variant )
        
        #since tf_matrix only has tf_matrix, transfer properties for each document to tf_matrix so they'd eventually be transfered to bloc_variant_tf_matrix - start
        for m in ['tf_matrix_normalized', 'tf_idf_matrix']:
            for i in range( len(tf_matrix['tf_matrix']) ):
                doc_dct = [ (v[0], v[1]) for v in tf_matrix['tf_matrix'][i].items() if v[0] != 'tf_vector' ]
                tf_matrix[m].append( dict(doc_dct) )

        tf_matrix = update_bloc_model(tf_matrix, bloc_variant_tf_matrix, tf_matrix_norm=kwargs.pop('tf_matrix_norm', ''), tf_idf_norm=kwargs.pop('tf_idf_norm', 'l2'), **kwargs )
        if( kwargs.get('keep_tf_matrix', False) is False ):
            tf_matrix['tf_matrix'] = []
        
    return tf_matrix

def conv_tf_matrix_to_json_compliant(tf_mat):
    
    if( 'vocab' in tf_mat ):
        tf_mat['vocab'] = list(tf_mat['vocab'])

    for opt in ['tf_matrix', 'tf_matrix_normalized', 'tf_idf_matrix']:
        if( opt not in tf_mat ):
            continue
        
        for i in range( len(tf_mat[opt]) ):
            tf_mat[opt][i]['tf_vector'] = [ float(a) for a in tf_mat[opt][i]['tf_vector'].toarray()[0] ]

    return tf_mat

def get_tf_matrix(doc_lst, n, tf_mat=None, vocab=None, token_pattern=r'(?u)\b[a-zA-Z\'\’-]+[a-zA-Z]+\b|\d+[.,]?\d*', **kwargs):

    kwargs.setdefault('rm_doc_text', True)
    pos_id_mapping = kwargs.get('pos_id_mapping', None)

    if( isinstance(doc_lst, list) ):
        if( len(doc_lst) == 0 ):
            return {}

        if( isinstance(doc_lst[0], dict) ):
            doc_lst, pos_id_mapping = get_doc_lst_pos_maps( doc_lst, rm_text=kwargs['rm_doc_text'] )
            if( len(doc_lst) == 0 ):
                return {}
    
    
    kwargs.setdefault('top_ngrams_add_all_docs', False)
    kwargs.setdefault('keep_tf_matrix', True)
    kwargs.setdefault('lowercase', True)
    kwargs.setdefault('min_df', 1)
    kwargs.setdefault('set_top_ngrams', False)
    kwargs.setdefault('tf_matrix_norm', '')#can use l1
    kwargs.setdefault('tf_idf_norm', 'l2')
    kwargs.setdefault('count_vectorizer_kwargs', {})

    
    #if payload changes, update map_tf_mat_to_doc_ids()
    #also update conv_tf_matrix_to_json_compliant()
    payload = {
        'tf_matrix': [],
        'tf_matrix_normalized': [],
        'tf_idf_matrix': [],
        'vocab': [],
        'top_ngrams': {
            'per_doc': [],
            'all_docs': []
        },
        'token_pattern': token_pattern
    }
    
    try:
        count_vectorizer = CountVectorizer(
            stop_words=kwargs.get('stop_words', None), 
            tokenizer=kwargs.get('tokenizer', None),
            token_pattern=token_pattern,
            ngram_range=(n, n),
            lowercase=kwargs['lowercase'],
            min_df=kwargs['min_df'],
            **kwargs['count_vectorizer_kwargs']
        )

        if( tf_mat is not None and vocab is not None ):
            payload['tf_matrix'] = tf_mat
            payload['vocab'] = vocab
        else:
            payload['tf_matrix'] = count_vectorizer.fit_transform(doc_lst)
            payload['vocab'] = count_vectorizer.get_feature_names_out()

        if( kwargs['tf_matrix_norm'] != '' ):
            payload['tf_matrix_normalized'] = normalize(payload['tf_matrix'], norm=kwargs['tf_matrix_norm'], axis=1)

        if( kwargs['tf_idf_norm'] != '' ):
            tfidf = TfidfTransformer( norm=kwargs['tf_idf_norm'] )
            tfidf.fit(payload['tf_matrix'])
            payload['tf_idf_matrix'] = tfidf.transform(payload['tf_matrix'])

        if( kwargs['keep_tf_matrix'] is False ):
            payload['tf_matrix'] = []

        
        for opt in ['tf_matrix', 'tf_matrix_normalized', 'tf_idf_matrix']:
            if( opt not in payload ):
                continue
            payload[opt] = list( payload[opt] )
    except:
        genericErrorInfo()
        return {}
    
    if( kwargs['set_top_ngrams'] is True ):
        calc_top_ngrams( payload, top_ngrams_add_all_docs=kwargs['top_ngrams_add_all_docs'] )

    if( pos_id_mapping is not None ):
        payload = map_tf_mat_to_doc_ids(payload, pos_id_mapping)

    return payload

def calc_top_ngrams(payload, top_ngrams_add_all_docs=False):

    all_docs_tf = {}
    all_docs_total_tf = 0
    corpus_size = len(payload['tf_matrix'])
    for i in range( corpus_size ):
        
        row = payload['tf_matrix'][i].toarray()[0]
        total_tf = sum(row)
        if( total_tf == 0 ):
            total_tf = -1

        single_doc_tf = [ {'term': v, 'term_freq': int(row[j]), 'term_rate': row[j]/total_tf} for (j, v) in enumerate(payload['vocab']) if row[j] != 0 ]
        single_doc_tf = sorted( single_doc_tf, key=lambda i: i['term_freq'], reverse=True )
        
        payload['top_ngrams']['per_doc'].append( single_doc_tf )


        if( top_ngrams_add_all_docs is True ):
            for tf_dct in single_doc_tf:
                all_docs_tf.setdefault( tf_dct['term'], {'tf': 0, 'df': 0} )
                all_docs_tf[ tf_dct['term'] ]['tf'] += int(tf_dct['term_freq'])
                all_docs_tf[ tf_dct['term'] ]['df'] += 1
                all_docs_total_tf += int(tf_dct['term_freq'])

    
    if( top_ngrams_add_all_docs is True ):

        if( all_docs_total_tf == 0 ):
            all_docs_total_tf = -1

        payload['top_ngrams']['all_docs'] = sorted( all_docs_tf.items(), key=lambda x: x[1]['df'], reverse=True )
        payload['top_ngrams']['all_docs'] = [ {'term': t[0], 'term_freq': t[1]['tf'], 'term_rate': t[1]['tf']/all_docs_total_tf, 'doc_freq': t[1]['df'], 'doc_rate': t[1]['df']/corpus_size} for t in payload['top_ngrams']['all_docs'] ]

def segment_paren_word(word, sort_paren=True):
    word = word.strip()
    if( word == '' ):
        return []

    paren_words = ['']
    for w in word:

        if( w == '(' ):
            paren_words.append('')
            continue
        elif( w == ')' ):
            paren_words[-1] = '(' + ''.join( sorted(paren_words[-1]) ) + ')' if sort_paren is True else '(' + paren_words[-1] + ')'
            paren_words.append('')
            continue

        paren_words[-1] += w

    paren_words = [w for w in paren_words if w != '']
    return paren_words

def gen_bloc_folded_letters(word, fold_start_count=100, sort_paren=True):

    if( word == '' ):
        return []
    
    '''
        gen_bloc_folded_letters() examples

        E:   E-1         [(E, 1)]
        EE:  E-2         [(E, 2)]
        EEAE:E-2,A-1,E-1 [(E, 2), (A, 1), (E, 1)]
        AB:  A-1,B-1     [(A, 1), (B, 1)]
    '''
    if( word.find('(') == -1 ):
        #e.g., word: AAAAABBBBBBABABABAB
        word = [ w for w in word ]
    else:
        '''
        e.g., word: (AAAAABBBBBB)(AB)(AB)(AB)(AB) -> (AAA+BBB+)(AB)(AB)(AB)+, fold_start_count = 4
        without recursive call to fold_word(), word: (AAAAABBBBBB)(AB)(AB)(AB)(AB) -> word: (AAAAABBBBBB)(AB)(AB)(AB)+
        '''
        word = segment_paren_word(word, sort_paren)

        new_word = []
        for w in word:
            if( w.startswith('(') and w.endswith(')') ):
                new_word.append( '(' + fold_word(w[1:-1], fold_start_count) + ')' )
            else:
                new_word.append( fold_word(w, fold_start_count) )
        word = new_word
        
    c_count = {}
    prev_c = word[0]
    word = word + ['*']
    folded_word = []
    
    for i in range( len(word) ):
        
        c = word[i]

        if( prev_c != c ):
            freq = c_count[prev_c]['freq']
            folded_word.append( (prev_c, freq) )
            c_count = {}

        c_count.setdefault(c, {'freq': 0, 'pos': i})
        c_count[c]['freq'] += 1
        prev_c = c

    return folded_word

def fold_word(word, fold_start_count, sort_paren=True, count_applies_to_all_char=False, fold_exclude_chars=''):

    if( fold_start_count < 1 ):
        return word

    if( isinstance(word, str) ):
        word = gen_bloc_folded_letters(word, fold_start_count=fold_start_count, sort_paren=sort_paren)

    new_word = ''
    exceed_cf_count = 0
    create_vocab_new_entry = True

    if( count_applies_to_all_char is True ):

        for c, cf in word:
            if( cf >= fold_start_count and c not in fold_exclude_chars ):
                
                plus_count = fold_start_count - 1 if fold_start_count > 1 else 1
                
                new_word += f'{c*plus_count}+'
                exceed_cf_count += 1
            else:
                new_word += f'{c*cf}'

        if( exceed_cf_count == len(word) ):
            create_vocab_new_entry = False
        else:
            new_word  = ''.join([ c[0] for c in word ])
    else:

        for c, cf in word:
            if( cf >= fold_start_count and c not in fold_exclude_chars ):
                
                create_vocab_new_entry = False
                plus_count = fold_start_count - 1 if fold_start_count > 1 else 1
                
                new_word += f'{c*plus_count}+'
            else:
                new_word += f'{c*cf}'

    return new_word


def bloc_sf_content_map(bloc_str, typ):

    sf = ''
    bloc_str = bloc_str.strip()
    if( bloc_str == '' ):
        return ''
    
    if( typ == 'b3_content' ):
        if( bloc_str == 't' ):
            sf = 'N' #N: tweet contains no entities (plaintext)
        elif( len(set(bloc_str)) == 1 ):
            sf = 'E' #E: tweet contains entities of one type
        else:
            sf = 'X' #X: tweet contains entities of mixed types

        return sf
    

    bloc_sf_b6_content_map = {
        't': 'N', #N: tweet contains no entities (plaintext)
        'U': 'U', #U: tweet contains 1+ URLs
        'H': 'H', #H: tweet contains 1+ Hashtags
        'm': 'M', #M: tweet contains 1+ Mentions
        'M': 'M', #M: tweet contains 1+ Mentions
        'E': 'D'  #D: tweet contains 1+ Media
    }
    
    ori = bloc_str
    bloc_str = ''.join( set(bloc_str) )
    if( len(bloc_str) > 1 ):
        sf = 'X'
    else:
        sf = bloc_sf_b6_content_map.get(bloc_str, '')
    
    return sf

def get_social_fingerprint_frm_bloc( bloc_str, dimension='action' ):
    #social fingerprint based on: https://ieeexplore.ieee.org/abstract/document/7876716    
    

    if( dimension == 'action' ):
        sf = re.sub(r'[^Tpr]', '', bloc_str)
        sf = re.sub(r'[T]', 'A', sf) #tweet 
        sf = re.sub(r'[p]', 'C', sf) #reply
        sf = re.sub(r'[r]', 'T', sf) #retweet
        return [{ 'text': sf, 'type': 'b3_type' }]

    elif( dimension == 'content_syntactic' ):
        sf = re.sub(r'[ (|*]', '', bloc_str)
        sf = sf.split(')')
        sf = [ s for s in sf if s != '' ]
        
        b3_c = [ bloc_sf_content_map(s, 'b3_content') for s in sf ]
        b6_c = [ bloc_sf_content_map(s, 'b6_content') for s in sf ]
        
        return [
            {'text': ''.join(b3_c), 'type': 'b3_content'},
            {'text': ''.join(b6_c), 'type': 'b6_content'}
        ]
    
    return []

#/stringmatrix/vector manipulation - end

#twitter v2 - start
def twitter_v2_user_lookup_ids(osome_twt_obj, screen_names):

    logger.info( '\ntwitter_v2_user_lookup_ids():' )

    max_users_for_req = len(screen_names)
    all_users = []
    
    for i in range(0, max_users_for_req, 100):
        
        logger.info(f'\tscreen_name lookup {i+1} of {max_users_for_req//100}, total users: {max_users_for_req}')
        
        if( max_users_for_req > 100 ):
            logger.info('\t\tsleeping for 3 seconds, check if 1 seconds would do')
            time.sleep(3)
 
        try:
            response = osome_twt_obj.user_lookup_usernames( screen_names[i:i+100], fields=osometweet.UserFields(everything=True) )
        except:
            genericErrorInfo()
            continue
        
        all_users += response.get('data', [])

    return all_users

#twitter v2 - end
