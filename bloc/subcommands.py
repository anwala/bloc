import sys
import logging
from itertools import combinations

from bloc.generator import get_timeline_request_dets
from bloc.generator import get_word_type

from bloc.util import color_bloc_action_str
from bloc.util import conv_tf_matrix_to_json_compliant
from bloc.util import cosine_sim
from bloc.util import dumpJsonToFile
from bloc.util import five_number_summary
from bloc.util import get_bloc_doc_lst
from bloc.util import get_bloc_variant_tf_matrix
from bloc.util import get_color_txt

from copy import deepcopy

logger = logging.getLogger('bloc.bloc')

def print_change_report(change_report, bloc_alphabets):

    def single_user_change_prof(chng, alph):

        change_profiles = {}
        for sm in chng['change_report']['self_sim'].get(alph, []):
            
            if( sm.get('changed', False) is False ):
                continue

            for change_type, change_score in sm['change_profile'].items():
                change_profiles.setdefault(change_type, [])
                change_profiles[change_type].append(change_score)

        if( len(change_profiles) != 0 ):
            logger.info('summary of kinds of changes (change profile)')
        
        change_profiles = sorted( change_profiles.items(), key=lambda x: x[1], reverse=True )
        for change_type, change_scores in change_profiles:
            avg = 0 if len(change_scores) == 0 else sum(change_scores)/len(change_scores)
            if( avg > -1 ):
                logger.info('\t{:.4f}: {}'.format(avg, change_type))
            else:
                logger.info('\tNA    : {}'.format(change_type))


    def single_user_change_rep(chng, alph):

        logger.info( f'{alph}: (change highlighted in red)' )

        if( len(chng.get('bloc_segments', {}).get('segments', {})) == 0 ):
            return

        sm = {}
        sec_doc = ''
        bloc_alph_str = ''
        segment_member = {}

        for sm in chng['change_report']['self_sim'].get(alph, []):
            
            changed_flag = sm.get('changed', False)

            fst_key = sm['fst_doc_seg_id']
            sec_key = sm['sec_doc_seg_id']

            fst_doc = chng['bloc_segments']['segments'][fst_key][alph]
            sec_doc = chng['bloc_segments']['segments'][sec_key][alph]

            if( changed_flag is True ):
                segment_member[ sm['sec_doc_seg_id'] ] = True
                fst_doc = color_bloc_action_str(fst_doc)
            elif( sm['fst_doc_seg_id'] in segment_member ):
                fst_doc = color_bloc_action_str(fst_doc)

            bloc_alph_str += fst_doc + ' | '
        
        if( sm.get('sec_doc_seg_id', None) in segment_member ):
            sec_doc = color_bloc_action_str(sec_doc)
        
        bloc_alph_str += sec_doc

        logger.info( f'{bloc_alph_str}\n' )


    for chng in change_report:
        
        logger.info( get_timeline_request_dets(chng) )
        for alph in bloc_alphabets:
            single_user_change_rep(chng, alph)
            single_user_change_prof(chng, alph)
    

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

    #generate collection of BLOC documents
    bloc_doc_lst = get_bloc_doc_lst(bloc_collection, bloc_model['bloc_alphabets'], src=args.account_src, src_class=args.account_class)

    if( subcommand == 'change' ):
        change_report = all_bloc_change_usr_self_cmp(bloc_collection, bloc_model, args.bloc_alphabets, args.change_mean, args.change_stddev, args.change_zscore_threshold)
        print_change_report(change_report, args.bloc_alphabets)
        return change_report
    
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
        report = pairwise_usr_cmp(tf_matrices, print_summary=not args.sim_no_summary)
    
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

def pairwise_usr_cmp(tf_mat, print_summary=True):

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
        
        if( len(fst_u['tf_vector']) == 0 or len(sec_u['tf_vector']) == 0 ):
            continue
        sim = cosine_sim( [fst_u['tf_vector']], [sec_u['tf_vector']] )
        
        avg_sim.append(sim)
        report.append({
            'sim': sim,
            'user_pair_indx': (fst_u_indx, sec_u_indx),
            'user_pair': (fst_u['screen_name'], sec_u['screen_name'])
        })

    if( print_summary is False ):
        return report

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

def all_bloc_change_usr_self_cmp(bloc_collection, bloc_model, bloc_alphabets, change_mean=None, change_stddev=None, change_zscore_threshold=-1.5):
    
    logger.info('\nall_bloc_change_usr_self_cmp():')
    logger.info( '\tzscore_sim: Would {}compute change_mean since {} was supplied'.format('' if change_mean is None else 'NOT ', change_mean) )
    logger.info( '\tzscore_sim: Would {}compute change_stddev since {} was supplied'.format('' if change_stddev is None else 'NOT ', change_stddev) )
    logger.info( f'\tzscore_sim: change_zscore_threshold: {change_zscore_threshold}\n' )

    all_self_sim_reports = []
    
    for u_bloc in bloc_collection:   

        u_bloc['change_report'] = bloc_change_usr_self_cmp(u_bloc, bloc_model, bloc_alphabets, change_mean=change_mean, change_stddev=change_stddev, change_zscore_threshold=change_zscore_threshold)
        #deepcopy used because on the event that change is run again on the same input, ensure to detach memory link with previous result
        all_self_sim_reports.append( deepcopy(u_bloc) )

    return all_self_sim_reports


def bloc_change_usr_self_cmp(usr_bloc, bloc_model, bloc_alphabets, change_mean, change_stddev, change_zscore_threshold):

    def self_doc_lst(bloc_segments, alphabet):
        
        if( 'segments' not in bloc_segments ):
            return []

        doc_lst = []
        seg_keys = list(bloc_segments['segments'].keys())
        seg_keys.sort()
        for seg_id in seg_keys:
            
            seg_dets = bloc_segments['segments'][seg_id]

            if( alphabet not in seg_dets ):
                continue

            if( seg_dets[alphabet].strip() == '' ):
                continue
                        
            doc_lst.append({ 'text': seg_dets[alphabet], 'seg_id': seg_id })

        return doc_lst
    
    def calc_self_sim(self_bloc_doc_lst, bloc_model):

        if( len(self_bloc_doc_lst) == 0 ):
            return {}

        total_pairs = 0
        all_self_sim = []
        sum_change_profile_no_filter = {}
        
        for i in range( 1, len(self_bloc_doc_lst) ):
            
            fst_doc = self_bloc_doc_lst[i-1]
            sec_doc = self_bloc_doc_lst[i]

            self_mat = get_bloc_variant_tf_matrix(
                [fst_doc, sec_doc], 
                ngram=bloc_model['ngram'], 
                tf_matrix_norm=bloc_model['tf_matrix_norm'], 
                keep_tf_matrix=True,
                token_pattern=bloc_model['token_pattern'], 
                bloc_variant=bloc_model['bloc_variant'], 
                set_top_ngrams=bloc_model['set_top_ngrams'], 
                top_ngrams_add_all_docs=bloc_model['top_ngrams_add_all_docs']
            )

            #'''
            if( 'tf_idf_matrix' not in self_mat ):
                continue
            pre_vect = self_mat['tf_idf_matrix'][0]['tf_vector']
            cur_vect = self_mat['tf_idf_matrix'][1]['tf_vector']
            #'''

            '''
            if( 'tf_matrix' not in self_mat ):
                continue
            pre_vect = self_mat['tf_matrix'][0]['tf_vector']
            cur_vect = self_mat['tf_matrix'][1]['tf_vector']
            '''
            
            '''
            if( pre_vect.nnz == 0 or cur_vect.nnz == 0 ):
                continue
            '''

            total_pairs += 1
            sim = cosine_sim( pre_vect, cur_vect )
            change_profile = get_change_profile(self_mat)
            all_self_sim.append({'fst_doc_seg_id': self_bloc_doc_lst[i-1]['seg_id'], 'sec_doc_seg_id': self_bloc_doc_lst[i]['seg_id'], 'sim': sim, 'change_profile': change_profile})

            for chng_dim, chng_val in change_profile.items():
                sum_change_profile_no_filter.setdefault(chng_dim, 0)
                sum_change_profile_no_filter[chng_dim] += chng_val
            '''
            print('\tvocab:', self_mat['vocab'])
            print('\td1:', fst_doc['text'])
            print('\td2:', sec_doc['text'])
            #print('v1:', pre_vect.toarray()[0])
            #print('v2:', cur_vect.toarray()[0])
            print('\tsim:', sim)
            #print('all_self_sim')
            #print(all_self_sim)
            print()
            '''

        for chng_dim in sum_change_profile_no_filter:
            sum_change_profile_no_filter[chng_dim] = sum_change_profile_no_filter[chng_dim]/total_pairs


        return {
            'self_sim': all_self_sim,
            'avg_change_profile_no_filter': sum_change_profile_no_filter
        }
    
    def get_change_profile(change_mat):
    
        vocab = change_mat['vocab']
        fst_doc_vect = change_mat['tf_idf_matrix'][0]['tf_vector'].toarray()
        sec_doc_vect = change_mat['tf_idf_matrix'][1]['tf_vector'].toarray()

        #word change
        #pause change
        #activity (session) change
        all_pauses = '□⚀⚁⚂⚃⚄⚅'
        pause_indices = []
        words_indices = []
        for i in range(len(vocab)):
            
            if( vocab[i] in all_pauses ):
                #pause
                pause_indices.append(i)
            else:
                #word
                words_indices.append(i)

        fst_doc_pause_vect = fst_doc_vect.take(pause_indices)
        sec_doc_pause_vect = sec_doc_vect.take(pause_indices)
        
        fst_doc_words_vect = fst_doc_vect.take(words_indices)
        sec_doc_words_vect = sec_doc_vect.take(words_indices)

        fst_doc_len = change_mat['tf_matrix'][0]['tf_vector'].toarray().take(words_indices)
        sec_doc_len = change_mat['tf_matrix'][1]['tf_vector'].toarray().take(words_indices)


        fst_doc_len = sum(fst_doc_len)
        sec_doc_len = sum(sec_doc_len)
        max_doc_len = max(fst_doc_len, sec_doc_len)

        pause_change = -1 if fst_doc_pause_vect.shape[0] == 0 or sec_doc_pause_vect.shape[0] == 0 else 1 - cosine_sim([fst_doc_pause_vect], [sec_doc_pause_vect])
        word_change = -1 if fst_doc_words_vect.shape[0] == 0 or sec_doc_words_vect.shape[0] == 0 else 1 - cosine_sim([fst_doc_words_vect], [sec_doc_words_vect])
        activity_change = -1 if max_doc_len == 0 else 1 - (min(fst_doc_len, sec_doc_len)/max_doc_len)

        return {
            'pause': pause_change,
            'word': word_change,
            'activity': activity_change
        }

    def get_segment_dates(seg_id, segments_details):

        if( seg_id not in segments_details ):
            return []

        local_dates = list(segments_details[seg_id]['local_dates'].keys())
        local_dates.sort()
        return local_dates

    change_report_header = 'change report for {}:'.format(usr_bloc['screen_name']) if 'screen_name' in usr_bloc else 'change report:'
    logger.info(change_report_header)

    not_enough_data_flag = '\tNot enough data to compute change'
    self_sim_report = {'self_sim': {}, 'change_rates': {}, 'avg_change_profile': {}, 'avg_change_profile_no_filter': {}}
    for alph in bloc_alphabets:
        
        self_bloc_doc_lst = self_doc_lst(usr_bloc.get('bloc_segments', {}), alph)

        self_sim_res = calc_self_sim(self_bloc_doc_lst, bloc_model)
        self_sim_report['self_sim'][alph] = self_sim_res.get('self_sim', [])
        self_sim_report['avg_change_profile_no_filter'][alph] = self_sim_res.get('avg_change_profile_no_filter', {})

        segments_len = len(usr_bloc['bloc_segments']['segments'])
       
        '''
        print('alph:', alph)
        print( 'segments_len/doc_len:', segments_len, len(self_bloc_doc_lst) )
        print('doc:', self_bloc_doc_lst)
        print('self_sim:', self_sim_report['self_sim'][alph])
        print(usr_bloc['bloc_segments']['segments'])
        print()
        '''
       

        summary_stats = five_number_summary([ v['sim'] for v in self_sim_report['self_sim'][alph] ])
        if( len(summary_stats) == 0 ):
            continue

        logger.info('\t{} cosine sim summary stats, mean: {:.4f}, median: {:.4f}, stddev: {:.4f}'.format(alph, summary_stats['mean'], summary_stats['median'], summary_stats['pstdev']) )
        zscore_mean = summary_stats['mean'] if change_mean is None else change_mean
        zscore_stddev = summary_stats['pstdev'] if change_stddev is None else change_stddev

        
        change_rate = 0
        sum_change_profile = {}
        for sm in self_sim_report['self_sim'][alph]:
            
            if( zscore_stddev == 0 ):
                continue

            zscore_sim = (sm['sim'] - zscore_mean)/zscore_stddev
            '''
            params, μ = 0.61 (zscore_mean), σ = 0.3 (zscore_stddev), change_zscore_threshold = -1.5
            zscore -1.5 --------- 0 --------- 1.5
            
            cosine sim of 0.16 (z-score = -1.5) and lower cosine values (e.g., 0.15) are considered significant change since they reach the change_zscore_threshold.
            Larger values (e.g., 0.17 with z-score -1.46) are not considered significant change since they are still close to the mean.
            '''
            if( zscore_sim > change_zscore_threshold ):
                not_enough_data_flag = ''
                continue

            fst_doc = usr_bloc['bloc_segments']['segments'][ sm['fst_doc_seg_id'] ][alph]
            sec_doc = usr_bloc['bloc_segments']['segments'][ sm['sec_doc_seg_id'] ][alph]

            st_segment_date = get_segment_dates(seg_id=sm['fst_doc_seg_id'], segments_details=usr_bloc['bloc_segments']['segments_details'])
            en_segment_date = get_segment_dates(seg_id=sm['sec_doc_seg_id'], segments_details=usr_bloc['bloc_segments']['segments_details'])

            #here means sim change is more than 1 - std. dev from mean, so it could indicate change
            logger.info( '\t{}. change sim: {:.2f}, z-score: {:.2f}'.format(change_rate+1, sm['sim'], zscore_sim) )
            #logger.info( '\t{} vs. {}'.format(self_bloc_doc_lst[fst_indx]['text'], self_bloc_doc_lst[sec_indx]['text']) )
            logger.info( '\t{} vs. {}'.format(fst_doc, sec_doc) )
            logger.info( '\t{} -- {}\n'.format(st_segment_date[0], en_segment_date[-1]) )

            not_enough_data_flag = ''
            sm['changed'] = True
            change_rate += 1

            for chng_dim, chng_val in sm['change_profile'].items():
                sum_change_profile.setdefault(chng_dim, 0)
                sum_change_profile[chng_dim] += chng_val


        self_sim_report['change_rates'][alph] = change_rate/len(self_sim_report['self_sim'][alph])
        if( change_rate != 0 ):
            for chng_dim in sum_change_profile:
                sum_change_profile[chng_dim] = sum_change_profile[chng_dim]/change_rate

            self_sim_report['avg_change_profile'][alph] = sum_change_profile

        logger.info( '\tchange_rate: {:.2f} ({}/{})\n'.format(self_sim_report['change_rates'][alph], change_rate, len(self_sim_report['self_sim'][alph])) )
    
    logger.info(not_enough_data_flag)

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

    
