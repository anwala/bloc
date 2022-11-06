import logging
from itertools import combinations
from sklearn.metrics.pairwise import cosine_similarity

from bloc.generator import add_bloc_sequences
from bloc.generator import get_word_type

from bloc.util import conv_tf_matrix_to_json_compliant
from bloc.util import dumpJsonToFile
from bloc.util import five_number_summary
from bloc.util import get_bloc_doc_lst
from bloc.util import get_bloc_variant_tf_matrix
from bloc.util import get_default_symbols

logger = logging.getLogger('bloc.bloc')

def run_subcommands(args, subcommand, bloc_collection):

    if( bloc_collection is None ):
        return {}

    report = []
    bloc_variant = None if args.ngram > 1 else {'type': 'folded_words', 'fold_start_count': args.fold_start_count, 'count_applies_to_all_char': False}
    if( args.token_pattern == 'bigram' ):
        token_pattern = '([^ |()*])'
    elif( args.token_pattern == 'word' ):
        token_pattern = '[^□⚀⚁⚂⚃⚄⚅. |()*]+|[□⚀⚁⚂⚃⚄⚅.]'
    else:
        token_pattern = args.token_pattern

    if( subcommand == 'top_ngrams' ):
        args.keep_tf_matrix = True
        args.set_top_ngrams = True
        args.top_ngrams_add_all_docs = True
        logger.info('\nSetting --keep-tf-matrix, --set-top-ngrams, and --top-ngrams-add-all-docs to True.');


    bloc_model = {
        'ngram': args.ngram,
        'bloc_variant': bloc_variant,
        'bloc_alphabets': args.bloc_alphabets,
        'token_pattern': token_pattern,
        'tf_matrix_norm': args.tf_matrix_norm,                  #set to '' if tf_matrices['tf_matrix_normalized'] not needed
        'keep_tf_matrix': args.keep_tf_matrix,
        'set_top_ngrams': args.set_top_ngrams,                  #set to False if tf_matrices['top_ngrams']['per_doc'] not needed. If True, keep_tf_matrix must be True
        'top_ngrams_add_all_docs': args.top_ngrams_add_all_docs #set to False if tf_matrices['top_ngrams']['all_docs'] not needed. If True, keep_tf_matrix must be True
    }

    all_bloc_symbols = get_default_symbols()
    #generate collection of BLOC documents
    bloc_doc_lst = get_bloc_doc_lst(bloc_collection, bloc_model['bloc_alphabets'], src=args.account_src, src_class=args.account_class)

    if( subcommand == 'change' ):
        return all_usr_self_cmp(bloc_collection, bloc_model, args.bloc_alphabets, args.change_mean, args.change_stddev)

    
    tf_matrices = get_bloc_variant_tf_matrix(
        bloc_doc_lst, 
        min_df=2, 
        ngram=bloc_model['ngram'], 
        tf_matrix_norm=bloc_model['tf_matrix_norm'], 
        keep_tf_matrix=bloc_model['keep_tf_matrix'], 
        token_pattern=bloc_model['token_pattern'], 
        bloc_variant=bloc_model['bloc_variant'], 
        set_top_ngrams=bloc_model['set_top_ngrams'], 
        top_ngrams_add_all_docs=bloc_model['top_ngrams_add_all_docs']
    )

    if( subcommand == 'top_ngrams' ):
        report = print_top_ngrams(tf_matrices)
        report['users'] = [ u['screen_name'] for u in bloc_doc_lst ]
    elif( subcommand == 'sim' ):
        report = pairwise_usr_cmp(tf_matrices)
    
    return report

def feature_importance(vocab, fst_vect, sec_vect, k=10):

    feat_importance = []
    for i in range( len(vocab) ):
        feat = vocab[i]
        feat_importance.append({ 'feat': feat, 'score': fst_vect[i] * sec_vect[i] })
    feat_importance = sorted( feat_importance, key=lambda x: x['score'], reverse=True )[:k]
    
    counter = 1
    for f in feat_importance:

        logger.info( '\t{:>4} {:.4f} {}'.format(f'{counter}.', f['score'], f['feat']) )
        counter += 1

    return feat_importance

def pairwise_usr_cmp(tf_mat):

    logger.info('\npairwise_usr_cmp():')    

    if( 'tf_idf_matrix' not in tf_mat ):
        logger.info('tf_idf_matrix not in tf_mat, returning')
        return []
    
    report = []
    avg_sim = []
    tf_mat = conv_tf_matrix_to_json_compliant(tf_mat)
    indices = list(range(len(tf_mat['tf_idf_matrix'])))     
    pairs = combinations(indices, 2)

    for fst_u_indx, sec_u_indx in pairs:
        fst_u = tf_mat['tf_idf_matrix'][fst_u_indx]
        sec_u = tf_mat['tf_idf_matrix'][sec_u_indx]

        sim = cosine_similarity( [fst_u['tf_vector']], [sec_u['tf_vector']] )[0][0]
        avg_sim.append(sim)
        report.append({
            'sim': sim,
            'user_pair_indx': (fst_u_indx, sec_u_indx),
            'user_pair': (fst_u['screen_name'], sec_u['screen_name'])
        })

    report = sorted( report, key=lambda x: x['sim'], reverse=True )
    avg_sim = 0 if avg_sim == [] else sum(avg_sim)/len(avg_sim)

    logger.info('\nFeatures importance,')
    for i in range( len(report) ):
        
        r = report[i]
        logger.info( '\t{} vs. {}, (score, feature):'.format(r['user_pair'][0], r['user_pair'][1]) )
        
        fst_u_indx, sec_u_indx = r['user_pair_indx']
        r['feature_importance'] = feature_importance(tf_mat['vocab'], tf_mat['tf_idf_matrix'][fst_u_indx]['tf_vector'], tf_mat['tf_idf_matrix'][sec_u_indx]['tf_vector'])
        
        logger.info('')

    logger.info('Cosine sim,')
    for r in report:
        logger.info('\t{:.4f}: {} vs. {}'.format(r['sim'], r['user_pair'][0], r['user_pair'][1]))
        fst_u_indx, sec_u_indx = r['user_pair_indx']
    logger.info('\t------')
    logger.info('\t{:.4f}: Average cosine sim'.format(avg_sim))

    return report

def all_usr_self_cmp(bloc_collection, bloc_model, bloc_alphabets, change_mean=None, change_stddev=None):
    
    logger.info('\nall_usr_self_cmp():')

    all_self_sim_reports = []
    for u_bloc in bloc_collection:   

        u_bloc['change_report'] = usr_self_cmp(u_bloc, bloc_model, bloc_alphabets, mean_sim=change_mean, stddev_sim=change_stddev)
        all_self_sim_reports.append(u_bloc)

    return all_self_sim_reports


def usr_self_cmp(usr_bloc, bloc_model, bloc_alphabets, mean_sim, stddev_sim):

    def self_doc_lst(bloc_segments, alphabet):
        
        if( 'segments' not in bloc_segments ):
            return []

        doc_lst = []
        for seg_id, seg_dets in bloc_segments['segments'].items():
            
            if( alphabet not in seg_dets ):
                continue

            if( seg_dets[alphabet].strip() == '' ):
                continue
            
            doc_lst.append({ 'text': seg_dets[alphabet], 'seg_id': seg_id })

        return doc_lst
    
    def calc_self_sim(self_bloc_doc_lst, bloc_model):

        if( len(self_bloc_doc_lst) == 0 ):
            return []

        all_self_sim = []
        for i in range( 1, len(self_bloc_doc_lst) ):
            
            fst_doc = self_bloc_doc_lst[i-1]
            sec_doc = self_bloc_doc_lst[i]

            self_mat = get_bloc_variant_tf_matrix(
                [fst_doc, sec_doc], 
                min_df=2, 
                ngram=bloc_model['ngram'], 
                tf_matrix_norm=bloc_model['tf_matrix_norm'], 
                keep_tf_matrix=bloc_model['keep_tf_matrix'], 
                token_pattern=bloc_model['token_pattern'], 
                bloc_variant=bloc_model['bloc_variant'], 
                set_top_ngrams=bloc_model['set_top_ngrams'], 
                top_ngrams_add_all_docs=bloc_model['top_ngrams_add_all_docs']
            )

            if( 'tf_idf_matrix' not in self_mat ):
                continue
            
            #print('vocab:', self_mat['vocab'])
            pre_vect = self_mat['tf_idf_matrix'][0]['tf_vector']
            cur_vect = self_mat['tf_idf_matrix'][1]['tf_vector']
            sim = cosine_similarity( pre_vect, cur_vect )[0][0]

            all_self_sim.append({'fst_doc_indx': i-1, 'sec_doc_indx': i, 'sim': sim})

            '''
            print('d1:', fst_doc)
            print('d2:', sec_doc)
            print('v1:', pre_vect.toarray()[0])
            print('v2:', cur_vect.toarray()[0])
            print('sim:', sim)
            print('all_self_sim')
            print(all_self_sim)
            print()
            '''

        return all_self_sim
    
    def get_segment_dates(seg_id, segments_details):

        if( seg_id not in segments_details ):
            return []

        local_dates = list(segments_details[seg_id]['local_dates'].keys())
        local_dates.sort()
        return local_dates

    print(usr_bloc['screen_name'])

    self_sim_report = {'self_sim': {}}
    for alph in bloc_alphabets:
        
        self_bloc_doc_lst = self_doc_lst(usr_bloc.get('bloc_segments', {}), alph)
        self_sim_report['self_sim'][alph] = calc_self_sim(self_bloc_doc_lst, bloc_model)
        
        summary_stats = {}
        if( mean_sim is None or stddev_sim is None ):
            summary_stats = five_number_summary([ v['sim'] for v in self_sim_report['self_sim'][alph] ])
        else:
            summary_stats['mean'] = mean_sim  
            summary_stats['median'] = mean_sim
            summary_stats['pstdev'] = stddev_sim

        if( len(summary_stats) == 0 ):
            continue

        print('\t({:.4f}, {:.4f}, {:.4f}) {}'.format(summary_stats['mean'], summary_stats['median'], summary_stats['pstdev'], alph) )
        drastic_change_count = 0
        for sm in self_sim_report['self_sim'][alph]:
            
            if( summary_stats['pstdev'] == 0 ):
                continue

            zscore_sim = (abs(sm['sim'] - summary_stats['mean']))/summary_stats['pstdev']
            if( zscore_sim <= 1.5 ):
                continue

            fst_indx = sm['fst_doc_indx']
            sec_indx = sm['sec_doc_indx']

            st_segment_date = get_segment_dates(seg_id=self_bloc_doc_lst[fst_indx]['seg_id'], segments_details=usr_bloc['bloc_segments']['segments_details'])
            en_segment_date = get_segment_dates(seg_id=self_bloc_doc_lst[sec_indx]['seg_id'], segments_details=usr_bloc['bloc_segments']['segments_details'])

            #here means sim change is more than 1 - std. dev from mean, so it could indicate drastic change
            print( '\tdrastic change sim/z-score: {:.2f} {:.2f}'.format(sm['sim'], zscore_sim) )
            print( '\t', self_bloc_doc_lst[fst_indx]['text'], 'vs', self_bloc_doc_lst[sec_indx]['text'] )
            print( '\t', st_segment_date[0], 'vs', en_segment_date[-1], '\n' )
            drastic_change_count += 1

        print( '\tdrastic_change_count: {} (of {} = {:.2f})'.format(drastic_change_count, len(self_sim_report['self_sim'][alph]), drastic_change_count/len(self_sim_report['self_sim'][alph])) )
        print()
        print()
        

    return self_sim_report

def print_top_ngrams(tf_mat, k=10):

    def print_top_k_ngrams( top_ngrams, rate_key, skip_pause_glyph=True ):

        counter = 1
        for i in range( len(top_ngrams) ):

            n = top_ngrams[i]
            if( skip_pause_glyph is True and '□⚀⚁⚂⚃⚄⚅.'.find(n['term']) > -1 ):
                continue
            
            line = '\t{:<4} {:.4f} {} ({})'.format(f'{counter}.', n[rate_key], n['term'], get_word_type(n['term']) )
            counter += 1
            logger.info( line )

    logger.info('\nprint_top_ngrams():')

    if( 'top_ngrams' not in tf_mat ):
        logger.info('top_ngrams not in tf_mat, returning')
        return {}

    for i in range( len(tf_mat['top_ngrams']['per_doc']) ):
        
        topngrams = tf_mat['top_ngrams']['per_doc'][i]
        user = tf_mat['tf_idf_matrix'][i]['screen_name']        
        logger.info(f'\nTop {k} ngrams for user {user}, (term freq. TF, word):')
        print_top_k_ngrams( topngrams[:k], 'term_rate' )

    logger.info(f'\nTop {k} ngrams across all users, (document freq. DF, word):')
    print_top_k_ngrams( tf_mat['top_ngrams']['all_docs'][:k], 'doc_rate' )

    return tf_mat['top_ngrams']

    
