import logging
import numpy as np
import re

from copy import deepcopy
from random import randint

from bloc.util import dumpJsonToFile
from bloc.util import genericErrorInfo
from bloc.util import gen_bloc_variant_tf_mat
from bloc.util import get_tf_matrix
#from bloc.util import merge_bloc_matrices
from bloc.util import update_bloc_model

from bloc.MarkovChain import BLOCMarkovChain

from sklearn.metrics import pairwise_distances

logger = logging.getLogger('bloc.bloc')

def extract_bloc_from_segments(testing_segment, training_segments):

    experiment = []
    for segment in training_segments:
        experiment.append({'testing_seg': testing_segment, 'training_seg': segment})

    return experiment

def generate_bloc_expr_template(all_screenames_bloc):

    max_segment_number = -1
    min_segment_number = 1000000000
    
    #get max and min segment_number
    for user in all_screenames_bloc:

        segment_numbers = user['bloc_segments']['segments'].keys()
        loc_max = max( segment_numbers )
        loc_min = min( segment_numbers )

        if( loc_max > max_segment_number ):
            max_segment_number = loc_max

        if( loc_min < min_segment_number ):
            min_segment_number = loc_min
    

    experiment_buckets = {}
    src_target_experiment_buckets = []
    for src_segment_number in range(max_segment_number, min_segment_number, -1):
    
        experiment_buckets[src_segment_number] = []
        for tgt_segment_number in range(src_segment_number-1, min_segment_number-1, -1):
            experiment_buckets[src_segment_number].append( list(range(src_segment_number-1, tgt_segment_number-1, -1)) )
        
        src_target_experiment_buckets.append(
            {'testing_segment': src_segment_number, 
            'training_segments': experiment_buckets[src_segment_number]
        })


    #extract bloc from src_segment and combined(single_target) for all users
    all_experiments = []
    for expr_run in src_target_experiment_buckets:
        all_experiments += extract_bloc_from_segments( expr_run['testing_segment'], expr_run['training_segments'] )


    flat_experiment = {}
    for expr_run in all_experiments:
        
        s_seg = expr_run['testing_seg']
        flat_experiment.setdefault(s_seg, [])
        flat_experiment[s_seg].append( expr_run['training_seg'] )


    semantic_exper = []
    for test_seg, train_seg in flat_experiment.items():
        semantic_exper.append({'testing_segment': test_seg, 'training_segments': train_seg})
    
    return semantic_exper

def obsolete_get_user_bloc_for_dim(bloc_segments, segment_numbers, seg_dimensions ):

    doc_lst = []
    for seg_num in segment_numbers:

        if( seg_num not in bloc_segments ):
            continue

        seg_dimensions_docs = ''
        for seg_dim in seg_dimensions.split(', '):
        
            seg_dim = seg_dim.strip()
            if( seg_dim not in bloc_segments[seg_num] ):
                continue

            seg_dimensions_docs = seg_dimensions_docs + ' * ' + bloc_segments[seg_num][seg_dim]

        if( seg_dimensions_docs.startswith(' * ') ):
            seg_dimensions_docs = seg_dimensions_docs[3:]

        if( seg_dimensions_docs.endswith(' * ') ):
            seg_dimensions_docs = seg_dimensions_docs[:-3]

        doc_lst.append( seg_dimensions_docs )

    return doc_lst

def get_user_bloc_for_dim(bloc_segments, segment_numbers, seg_dimensions ):

    doc_lst = []
    for seg_num in segment_numbers:

        if( seg_num not in bloc_segments ):
            continue

        seg_dimensions_docs = {}
        for seg_dim in seg_dimensions.split(', '):
        
            seg_dim = seg_dim.strip()
            if( seg_dim not in bloc_segments[seg_num] ):
                continue

            seg_dimensions_docs[seg_dim] = bloc_segments[seg_num][seg_dim]

        doc_lst.append( seg_dimensions_docs )

    return doc_lst

def combine_text_across_segs_bloc_dims(seg_dim_text):

    doc_lst = []

    for segment in seg_dim_text:

        seg_dimensions_docs = ''
        for dim, bloc_seq in segment.items():
            seg_dimensions_docs = seg_dimensions_docs + ' * ' + bloc_seq

        if( seg_dimensions_docs.startswith(' * ') ):
            seg_dimensions_docs = seg_dimensions_docs[3:]

        if( seg_dimensions_docs.endswith(' * ') ):
            seg_dimensions_docs = seg_dimensions_docs[:-3]

        doc_lst.append( seg_dimensions_docs )

    doc_lst = ' ** '.join(doc_lst)
    return doc_lst

def rm_absent_segment(cur_segments, user_segments):

    dedup_set = set()
    final_segments = []
    
    for segment in cur_segments:
        
        new_segment = []
        for seg in segment:
            if( seg in user_segments ):
                new_segment.append( seg )

        ky = str(new_segment)
        if( ky in dedup_set ):
            continue

        dedup_set.add(ky)
        
        if( len(new_segment) != 0 ):
            final_segments.append( new_segment )

    return final_segments

def gen_expr_doc_lst_for_single_user(user, all_experiments, expr_bloc_dims):

    logger.debug('\ngen_expr_doc_lst_for_single_user(), user: ' + user['screen_name'])

    for expr_run in all_experiments:

        if( 'testing_segment' not in expr_run or 'training_segments' not in expr_run ):
            continue
        
        test_seg = expr_run['testing_segment']
        test_doc_lst = get_user_bloc_for_dim( user['bloc_segments']['segments'], [test_seg], expr_bloc_dims )

        if( len(test_doc_lst) == 0 ):
            #no test docs so no need for training docs
            continue
        
        logger.debug( 'experiment: ' + str(expr_run['testing_segment']) + ' vs ' + str(expr_run['training_segments']) )
        expr_run['training_segments'] = rm_absent_segment( expr_run['training_segments'], user['bloc_segments']['segments'] )
        logger.debug( 'experiment: ' + str(expr_run['testing_segment']) + ' vs ' + str(expr_run['training_segments']) + ' (actually)')
        
        if( len(expr_run['training_segments']) != 0 ):
            
            expr_run['training_doc_lst'] = []
            #don't add test if training is absent
            #expr_run['testing_doc_lst'] = { 'text': ' ** '.join(test_doc_lst), 'segments': [test_seg]}
            expr_run['testing_doc_lst'] = { 'text': test_doc_lst, 'segments': [test_seg]}
            
        for train in expr_run['training_segments']:
            
            train_doc_lst = get_user_bloc_for_dim( user['bloc_segments']['segments'], train, expr_bloc_dims )
            expr_run['training_doc_lst'].append({
                #'text': ' ** '.join(train_doc_lst),
                'text': train_doc_lst,
                'segments': train
            })
            
            
            logger.debug('\t' + str(test_seg) + ' vs ' + str(train))
            logger.debug('\t\ttest_doc_lst: ' + str(test_doc_lst))
            logger.debug('\t\ttrain_doc_lst: ' + str(train_doc_lst))
    
    logger.debug('')
    for expr_run in all_experiments:
        
        #remove testing_segment and training_segments
        if( 'testing_segment' in expr_run ):
            del expr_run['testing_segment']

        if(  'training_segments' in expr_run ):
            del expr_run['training_segments']

def gen_expr_doc_lst_for_users( all_screenames_bloc, all_experiments, expr_bloc_dims ):

    for i in range( len(all_screenames_bloc) ):

        user = all_screenames_bloc[i]
        user['bloc_experiment_docs'] = deepcopy(all_experiments)
        user['bloc_experiment_docs_dim'] = expr_bloc_dims

        gen_expr_doc_lst_for_single_user( user, user['bloc_experiment_docs'], expr_bloc_dims )

        #rm empty experiment docs
        user['bloc_experiment_docs'] = [ doc for doc in user['bloc_experiment_docs'] if len(doc) != 0 ]

def gen_ngram_tf_matrix(all_screenames_bloc, ngram, token_pattern, matrix_key='tf_matrix_normalized', tf_matrix_norm='l1', tf_idf_norm='l2' ):

    logger.debug('\ngen_ngram_tf_matrix()')
    tf_matrix = []

    for i in range( len(all_screenames_bloc) ):
        user = all_screenames_bloc[i]

        if( 'bloc_experiment_docs' not in user ):
            continue

        logger.debug('user: ' + user['screen_name'])

        for j in range( len(user['bloc_experiment_docs']) ):
            
            expr_doc = user['bloc_experiment_docs'][j]
            if( 'testing_doc_lst' not in expr_doc and 'training_doc_lst' not in expr_doc ):
                continue

            logger.debug('\ttesting doc: ' + str(expr_doc['testing_doc_lst']))

            tf_matrix.append({
                'screen_name': user['screen_name'],
                'segments': expr_doc['testing_doc_lst']['segments'],
                'text': combine_text_across_segs_bloc_dims( expr_doc['testing_doc_lst']['text'] ),
                'text_structured': expr_doc['testing_doc_lst']['text'],
                'id': str(i) + ', ' + str(j),
                'user_indx': i,
                'experiment_indx': j
            })

            for k in range( len(expr_doc['training_doc_lst']) ):

                tf_matrix.append({
                    'screen_name': user['screen_name'],
                    'segments': expr_doc['training_doc_lst'][k]['segments'],
                    'text': combine_text_across_segs_bloc_dims( expr_doc['training_doc_lst'][k]['text'] ),
                    'text_structured': expr_doc['training_doc_lst'][k]['text'],
                    'id': str(i) + ', ' + str(j) + ', ' + str(k),
                    'user_indx': i,
                    'experiment_indx': j,
                    'training_doc_indx': k
                })

                
                logger.debug( '\t\ttraining doc: ' + str(expr_doc['training_doc_lst'][k]) )
                logger.debug( '\t\t user_indx: ' + str(i) )
                logger.debug( '\t\t expr_indx: ' + str(j) )
                logger.debug( '\t\t training_doc_indx: ' + str(k) )
                logger.debug('')
        
        logger.debug('')
        logger.debug('')


    #generate matrix
    if( len(tf_matrix) != 0 ):
        tf_matrix = get_tf_matrix( 
            tf_matrix, 
            n=ngram, 
            token_pattern=token_pattern,
            lowercase=False, 
            add_normalized_tf_matrix=tf_matrix_norm,
            add_tf_idf_matrix=tf_idf_norm,
            rm_doc_text=False,
        )
    
    
    if( matrix_key in tf_matrix ):
        update_user_test_train_tf_vects( tf_matrix[matrix_key], all_screenames_bloc )

    return tf_matrix



def query_user_experiment_sample(user, experiment_type):

    if( 'bloc_experiment_docs' not in user ):
        return []

    experiment_runs = []
    for expr_run in user['bloc_experiment_docs']:

        if( experiment_type == 'testing_doc_lst' ):
            experiment_runs.append( expr_run['testing_doc_lst'] )

    return experiment_runs

def rm_dup_train_screen_name(training_samples):
    
    '''
        Precondition: training segments are already sorted in descending order (see: generate_bloc_expr_template() )

        Remove duplicate training samples, leave just one; the one closest to the test segment
        E.g.,
        Input: (anwala has multiple segment samples, so leave just one, the one closest to the test segment)
        i: 0 shawnmjones, [44] test
            0.35 phonedude_mln train-seg-2 [43, 42] (r ⚁, 0.18)
            0.45 acnwala train-seg-2 [40, 39] (⚁ r, 0.33)
            0.47 acnwala train-seg-2 [41, 40] (⚁ r, 0.32)
            0.48 acnwala train-seg-2 [43, 42] (r ⚁, 0.23)
            0.57 acnwala train-seg-2 [42, 41] (⚂ r, 0.36)

        Output:
        i: 0 shawnmjones, [44] test
            0.35 phonedude_mln train-seg-2 [43, 42] (r ⚁, 0.18)
            0.48 acnwala train-seg-2 [43, 42] (r ⚁, 0.23)
    '''

    new_training_samples = {}
    for sampl in training_samples:
        
        screen_name = sampl['screen_name']
        if( screen_name in new_training_samples ):
            
            #e.g., [43, 42] > [42, 41]
            if( sampl['segments'][0] > new_training_samples[screen_name]['segments'][0] ):
                new_training_samples[screen_name] = sampl
        else:
            new_training_samples[screen_name] = sampl


    dedup_training_samples = []
    for user, train_sampl in new_training_samples.items():
        dedup_training_samples.append( train_sampl )

    return dedup_training_samples

def get_sample_top_ngram(top_per_doc_ngram):
    
    if( len(top_per_doc_ngram) == 0 ):
        top_ngrams = 'NA'
    else:
        top_ngrams = '(' + top_per_doc_ngram[0]['term'] + ', ' + "{0:0.2f}".format(top_per_doc_ngram[0]['term_rate']) + ')'

    return top_ngrams

def get_markov_chains_for_bloc_dims(segment_seqs):

    mkv_inputs = {}
    for segment in segment_seqs:
        for dim, bloc_seq in segment.items():
            if( bloc_seq != '' ):

                bloc_seq = re.sub(r'[ |()*]', '', bloc_seq)
                mkv_inputs.setdefault(dim, [])
                mkv_inputs[dim].append(bloc_seq)


    mkv_chains = {}
    for dim, bloc_seq in mkv_inputs.items():
        mkv_chains[dim] = { 'model': BLOCMarkovChain(training_sequence_lst=bloc_seq), 'training_seq': ''.join(bloc_seq) }

    return mkv_chains

def get_src_tgt_mkv_dist(mc_src, mc_tgt):

    total_src_tgt_prob_all_models = 0
    good_prob_flag = False
    #dist in function name because: smaller log prob is better, if ordinary prob is used (log_prob = False), then this function performs sim est. since larger values are better

    for dim in mc_src:
        if( dim in mc_tgt ):

            good_prob_flag = True
            prob_src_tgt = BLOCMarkovChain.prob_of_sequence( mc_src[dim]['model'].training_model, mc_tgt[dim]['training_seq'], log_prob=True )
            prob_src_tgt = prob_src_tgt/len(mc_tgt[dim]['training_seq'])

            prob_tgt_src = BLOCMarkovChain.prob_of_sequence(mc_tgt[dim]['model'].training_model, mc_src[dim]['training_seq'], log_prob=True)
            prob_tgt_src = prob_tgt_src/len(mc_src[dim]['training_seq'])

            total_src_tgt_prob_all_models += (prob_src_tgt+prob_tgt_src)/2
            
    return total_src_tgt_prob_all_models, good_prob_flag

def pairwise_pred_prob_multi_markvov( tf_matrix ):
    
    X = len(tf_matrix)
    pred_prob_matrix = []

    '''
        ' * ':  separates bloc dimenensions
        ' ** ': separates combined segments
        ' | ':  time segmenter

        For example:
            ⚂T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T * ttttt(Ht)tttttttttttttt ** T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T * tt(Ht)tttt(Ht)t(Ht)(Ht)ttttttttt
            segment 1: ⚂T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T * ttttt(Ht)tttttttttttttt
            segment 2: T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T * tt(Ht)tttt(Ht)t(Ht)(Ht)ttttttttt
    '''
    
    for i in range(X):

        print( '\tpairwise_pred_prob(), user: {} of {}'.format(i, X) )
        
        pred_prob_matrix.append([])
        mc_src = get_markov_chains_for_bloc_dims( tf_matrix[i]['text_structured'] )

        for j in range(X):

            mc_tgt = get_markov_chains_for_bloc_dims( tf_matrix[j]['text_structured'] )
            total_src_tgt_prob_all_models, good_prob_flag = get_src_tgt_mkv_dist( mc_src, mc_tgt )

            if( good_prob_flag ):
                pred_prob_matrix[-1].append( total_src_tgt_prob_all_models )
            else:
                pred_prob_matrix[-1].append( -1000 )

    return pred_prob_matrix

def pairwise_pred_prob( tf_matrix ):
    

    X = len(tf_matrix)
    pred_prob_matrix = []


    print( '\tpairwise_pred_prob(): revise function since BLOCMarkovChain has changed, returning' )
    for i in range(X):
        pred_prob_matrix.append([])
        for j in range(X):
            pred_prob_matrix[-1].append(0.5)
    return pred_prob_matrix

    


    print( '\tpairwise_pred_prob():' )
    '''
        tf_matrix[j]['text']'s structure
        ' * ':  separates bloc dimenensions
        ' ** ': separates combined segments
        ' | ':  time segmenter

        For example:
            ⚂T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T * ttttt(Ht)tttttttttttttt ** T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T * tt(Ht)tttt(Ht)t(Ht)(Ht)ttttttttt
            segment 1: ⚂T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T * ttttt(Ht)tttttttttttttt
            segment 2: T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T⚁T * tt(Ht)tttt(Ht)t(Ht)(Ht)ttttttttt
    '''
    
    for i in range(X):

        print( '\tpairwise_pred_prob(), user: {} of {}'.format(i, X) )
        pred_prob_matrix.append([])
        
        src_seq = re.sub(r'[ |()*]', '', tf_matrix[i]['text'])
        mc_src = BLOCMarkovChain( training_sequence_lst=[src_seq] )

        for j in range(X):

            tgt_seq = re.sub(r'[ |()*]', '', tf_matrix[j]['text'])
            mc_tgt = BLOCMarkovChain( training_sequence_lst=[ tgt_seq ] )
            #prob = mc.prob_of_sequence( tgt_seq, log_prob=True )
            
            prob_src_tgt = BLOCMarkovChain.s_prob_of_sequence(mc_src.training_model, tgt_seq, log_prob=True)
            prob_src_tgt = prob_src_tgt/len(tgt_seq)

            prob_tgt_src = BLOCMarkovChain.s_prob_of_sequence(mc_tgt.training_model, src_seq, log_prob=True)
            prob_tgt_src = prob_tgt_src/len(src_seq)
            
            pred_prob_matrix[-1].append( (prob_src_tgt+prob_tgt_src)/2 )
            #pred_prob_matrix[-1].append( 0 )

    return pred_prob_matrix

def analyze_ngram_vectors( tf_matrix, matrix_key='tf_matrix_normalized', analyze_training_segment_length=1 ):

    if( matrix_key not in tf_matrix ):
        return {
            'experiment_parameters': {
                'matrix_key': matrix_key
            },
            'prediction_results': []
        }

    if( len(tf_matrix[matrix_key]) == 0 ):
        return {
            'experiment_parameters': {
                'matrix_key': matrix_key
            },
            'prediction_results': []
        }
    
    bloc_prediction_results = []
    markov_prediction_results = []

    X = np.array([ user['tf_vector'] for user in tf_matrix[matrix_key] ])

    distance_matrix = pairwise_distances( X, metric='euclidean' )#site 1
    prob_seq_matrix = pairwise_pred_prob( tf_matrix[matrix_key] )

    logger.debug( '\nanalyze_ngram_vectors() for matrix_key:' + matrix_key )
    logger.debug( 'matrix.len: ' + str(len(tf_matrix[matrix_key])) )
    logger.debug( 'dist mat:' + str(distance_matrix.shape) + '\n' )

    for i in range( distance_matrix.shape[0] ):
        
        a = tf_matrix[matrix_key][i]['screen_name'] + ', ' + str(tf_matrix[matrix_key][i]['segments'])
        if( 'training_doc_indx' in tf_matrix[matrix_key][i] ):
            continue

        logger.debug('i: ' + str(i) + ' ' + a + ' test ' + get_sample_top_ngram( tf_matrix['top_ngrams']['per_doc'][i]['ngrams'] ) )

        training_samples = []
        train_dedup_set = set()
        pred_payload = {
            'test': {
                'screen_name': tf_matrix[matrix_key][i]['screen_name'],
                'segments': tf_matrix[matrix_key][i]['segments'],
                'train_non_test_screen_name_count': set()
            }
        }
        
        for j in range( distance_matrix.shape[1] ):

            if( i == j ):
                continue

            train_tf_mat = tf_matrix[matrix_key][j]
            training_ky = train_tf_mat['screen_name'] + ', ' + str(train_tf_mat['segments'])


            if( len(train_tf_mat['segments']) != analyze_training_segment_length ):
                #mismatch of count
                continue

            if( training_ky in train_dedup_set ):
                #this is a duplicate training sample
                continue
            train_dedup_set.add(training_ky)


            if( tf_matrix[matrix_key][i]['screen_name'] == train_tf_mat['screen_name'] ):

                test_set = set(tf_matrix[matrix_key][i]['segments'])
                train_set = set(train_tf_mat['segments'])  
                
                if( len(test_set & train_set) != 0 ):
                    #skip because train and test have segment in common
                    continue

            if( train_tf_mat['segments'][0] >= tf_matrix[matrix_key][i]['segments'][0] ):
                #skip future (e.g, 44) trained to predict current 43
                continue


            top_per_doc_ngram = 'NA'
            if( train_tf_mat['id'] == tf_matrix['top_ngrams']['per_doc'][j]['id'] ):
                top_per_doc_ngram = get_sample_top_ngram( tf_matrix['top_ngrams']['per_doc'][j]['ngrams'] )


            if( tf_matrix[matrix_key][i]['screen_name'] != train_tf_mat['screen_name'] ):
                pred_payload['test']['train_non_test_screen_name_count'].add( train_tf_mat['screen_name'] )

            training_samples.append({
                'screen_name': train_tf_mat['screen_name'],
                'segments': train_tf_mat['segments'],
                'distance': distance_matrix[i][j], #site 2
                'pred_prob': prob_seq_matrix[i][j],
                'label': 'train-seg-' + str( len(train_tf_mat['segments']) ),
                'top_per_doc_ngram': top_per_doc_ngram,
                'text': train_tf_mat['text']
            })

        training_samples = rm_dup_train_screen_name( training_samples )
        bloc_training_samples = sorted( training_samples, key=lambda i: i['distance'] )
        markov_training_samples = sorted( training_samples, key=lambda i: i['pred_prob'], reverse=True )
        
        pred_payload['test']['train_non_test_screen_name_count'] = list(pred_payload['test']['train_non_test_screen_name_count'])
        bloc_prediction_results.append({
            'test': pred_payload['test'],
            'train': bloc_training_samples
        })

        markov_prediction_results.append({
            'test': pred_payload['test'],
            'train': markov_training_samples
        })

        for j in range( len(bloc_training_samples) ):
            train = bloc_training_samples[j]
            logger.debug( '\tbloc ' + "{0:0.2f}".format(train['distance']) + ' ' + train['screen_name'] + ' ' + train['label'] + ' ' + str(train['segments']) + ' ' + train['top_per_doc_ngram'] )
        
        logger.debug('')
        logger.debug('i: ' + str(i) + ' ' + a + ' test ' + tf_matrix[matrix_key][i]['text'] )
        
        for j in range( len(markov_training_samples) ):
            train = markov_training_samples[j]
            logger.debug( '\tmkv ' + "{0:0.2f}".format(train['pred_prob']) + ' ' + train['screen_name'] + ' ' + train['label'] + ' ' + str(train['segments']) + ' ' + train['text'] )
        
        logger.debug('')

    return {
        'experiment_parameters': {
            'matrix_key': matrix_key
        },
        'prediction_results': {
            'bloc': bloc_prediction_results,
            'markov': markov_prediction_results#site 3
        }
    }

def report_prediction_results( pred_results, parameters ):

    retrieved_docs = 0
    relevant_docs = 0
    random_relevant_docs = 0

    for test_train in pred_results:

        if( 'test' not in test_train  or 'train' not in test_train ):
            continue

        if( len(test_train['test']['train_non_test_screen_name_count']) == 0 or len(test_train['train']) == 0 ):
            continue

        retrieved_docs += 1
        
        if( test_train['test']['screen_name'] == test_train['train'][0]['screen_name'] ):
            relevant_docs += 1

        guess = randint( 0, len(test_train['train'])-1 )
        if( test_train['test']['screen_name'] == test_train['train'][guess]['screen_name'] ):
            random_relevant_docs += 1
    
    if( retrieved_docs == 0 ):
        precision = -1
        random_precision = -1
    else:
        precision = relevant_docs/retrieved_docs
        random_precision = random_relevant_docs/retrieved_docs

    return {
        'precision': precision,
        'random_precision': random_precision
    }

def update_user_test_train_tf_vects(tf_matrix, all_screenames_bloc):
    
    if( len(all_screenames_bloc) == 0 ):
        return

    for mat in tf_matrix:

        i = mat['user_indx']
        j = mat['experiment_indx']
        user = all_screenames_bloc[i]

        if( 'training_doc_indx' in mat ):            
            k = mat['training_doc_indx']
            user['bloc_experiment_docs'][j]['training_doc_lst'][k]['tf_vector'] = mat['tf_vector']

        else:
            user['bloc_experiment_docs'][j]['testing_doc_lst']['tf_vector'] = mat['tf_vector']

def analyze_bloc_for_users(all_screenames_bloc, ngram=1, analyze_bloc_dimensions='action', analyze_matrix_key='tf_matrix_normalized', analyze_training_segment_length=1, max_pages=-1, timeline_startdate='', timeline_scroll_by_hours=None, **kwargs):

    kwargs.setdefault('analyze_tf_matrix_norm', 'l1')
    kwargs.setdefault('analyze_tf_idf_matrix_norm', 'l2')
    kwargs.setdefault('token_pattern', r'[^ |()*]')
    kwargs.setdefault('bloc_variant', None)

    new_tf_matrix = {}
    all_experiments = generate_bloc_expr_template( all_screenames_bloc )
    

    gen_expr_doc_lst_for_users( all_screenames_bloc, deepcopy(all_experiments), analyze_bloc_dimensions )
    tf_matrix = gen_ngram_tf_matrix( all_screenames_bloc, ngram, token_pattern=kwargs['token_pattern'], matrix_key=analyze_matrix_key, tf_matrix_norm=kwargs['analyze_tf_matrix_norm'], tf_idf_norm=kwargs['analyze_tf_idf_matrix_norm'] )

    if( kwargs['bloc_variant'] is not None ):

        bloc_variant_tf_matrix = gen_bloc_variant_tf_mat( tf_matrix, kwargs['bloc_variant'] )
        new_tf_matrix = merge_bloc_matrices( tf_matrix, bloc_variant_tf_matrix, kwargs['bloc_variant'] )

        #dumpJsonToFile('tf_matrix.json', tf_matrix)

        tf_matrix = update_bloc_model(tf_matrix, new_tf_matrix, tf_matrix_norm=kwargs['analyze_tf_matrix_norm'], tf_idf_norm=kwargs['analyze_tf_idf_matrix_norm'] )
        if( analyze_matrix_key in tf_matrix ):
            update_user_test_train_tf_vects(tf_matrix[analyze_matrix_key], all_screenames_bloc)

        #dumpJsonToFile('new_tf_matrix.json', tf_matrix)

    pred_res = analyze_ngram_vectors( tf_matrix, matrix_key=analyze_matrix_key, analyze_training_segment_length=analyze_training_segment_length )
    
    pred_res['experiment_parameters']['ngram'] = ngram
    pred_res['experiment_parameters']['analyze_training_segment_length'] = analyze_training_segment_length
    pred_res['experiment_parameters']['bloc_experiment_dimensions'] = analyze_bloc_dimensions

    pred_res['experiment_parameters']['max_pages'] = max_pages
    pred_res['experiment_parameters']['timeline_startdate'] = timeline_startdate
    pred_res['experiment_parameters']['timeline_scroll_by_hours'] = timeline_scroll_by_hours

    pred_report_bloc = { 'precision': -1, 'random_precision': -1 }
    pred_report_markov = { 'precision': -1, 'random_precision': -1 }

    if( len(pred_res['prediction_results']) != 0 ):
        pred_report_bloc = report_prediction_results( pred_res['prediction_results']['bloc'], pred_res['experiment_parameters'] )
        pred_report_markov = report_prediction_results( pred_res['prediction_results']['markov'], pred_res['experiment_parameters'] )

    return {
        'all_screenames_bloc': all_screenames_bloc, #conforming to how bloc.proc_req() returns 
        'prediction_report': {'bloc': pred_report_bloc, 'markov': pred_report_markov},
        'experiment_parameters': pred_res['experiment_parameters']
    }