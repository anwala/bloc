import logging
from itertools import combinations
from sklearn.metrics.pairwise import cosine_similarity

from bloc.generator import get_timeline_request_dets
from bloc.generator import get_word_type

from bloc.util import color_bloc_action_str
from bloc.util import conv_tf_matrix_to_json_compliant
from bloc.util import dumpJsonToFile
from bloc.util import five_number_summary
from bloc.util import get_bloc_doc_lst
from bloc.util import get_bloc_variant_tf_matrix
from bloc.util import get_color_txt

logger = logging.getLogger('bloc.bloc')

def print_change_report(change_report, args):

    def single_user_change_rep(chng, alph, args):

        logger.info( f'{alph}: (change highlighted in red)' )

        bloc_segments = list( chng.get('bloc_segments', {}).get('segments', {}).keys() )
        bloc_segments.sort()
        if( len(bloc_segments) == 0 ):
            return

        sm = {}
        bloc_alph_str = ''
        segment_member = {}

        for sm in chng['change_report']['self_sim'].get(alph, []):
            
            changed_flag = sm.get('changed', False)

            fst_key = bloc_segments[ sm['fst_doc_indx'] ]
            sec_key = bloc_segments[ sm['sec_doc_indx'] ]

            fst_doc = chng['bloc_segments']['segments'][fst_key][alph]
            sec_doc = chng['bloc_segments']['segments'][sec_key][alph]

            if( changed_flag is True ):
                segment_member[ sm['sec_doc_indx'] ] = True
                fst_doc = color_bloc_action_str(fst_doc)
            elif( sm['fst_doc_indx'] in segment_member ):
                fst_doc = color_bloc_action_str(fst_doc)

            bloc_alph_str += fst_doc + ' | '
        
        if( sm.get('sec_doc_indx', None) in segment_member ):
            sec_doc = color_bloc_action_str(sec_doc)
        
        bloc_alph_str += sec_doc

        logger.info( f'{bloc_alph_str}\n' )

    for chng in change_report:
        
        logger.info( get_timeline_request_dets(chng) )
        for alph in args.bloc_alphabets:
            single_user_change_rep(chng, alph, args)
    

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
        print_change_report(change_report, args)
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
        sim = 1 if sim > 1 else sim
        sim = -1 if sim < -1 else sim
        
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

def all_bloc_change_usr_self_cmp(bloc_collection, bloc_model, bloc_alphabets, change_mean=None, change_stddev=None, change_zscore_threshold=1.5):
    
    logger.info('\nall_bloc_change_usr_self_cmp():')
    logger.info( '\tzscore_sim: Would {}compute change_mean since {} was supplied'.format('' if change_mean is None else 'NOT ', change_mean) )
    logger.info( '\tzscore_sim: Would {}compute change_stddev since {} was supplied'.format('' if change_stddev is None else 'NOT ', change_stddev) )
    logger.info( f'\tzscore_sim: change_zscore_threshold: {change_zscore_threshold}\n' )

    all_self_sim_reports = []
    for u_bloc in bloc_collection:   

        u_bloc['change_report'] = bloc_change_usr_self_cmp(u_bloc, bloc_model, bloc_alphabets, change_mean=change_mean, change_stddev=change_stddev, change_zscore_threshold=change_zscore_threshold)
        all_self_sim_reports.append(u_bloc)

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
            sim = 1 if sim > 1 else sim
            sim = -1 if sim < -1 else sim

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

    logger.info('change report for {}'.format(usr_bloc['screen_name']))
    self_sim_report = {'self_sim': {}, 'change_rates': {}}
    for alph in bloc_alphabets:
        
        self_bloc_doc_lst = self_doc_lst(usr_bloc.get('bloc_segments', {}), alph)
        self_sim_report['self_sim'][alph] = calc_self_sim(self_bloc_doc_lst, bloc_model)
        summary_stats = five_number_summary([ v['sim'] for v in self_sim_report['self_sim'][alph] ])
        if( len(summary_stats) == 0 ):
            continue

        logger.info('\t{} cosine sim summary stats, mean: {:.4f}, median: {:.4f}, stddev: {:.4f}'.format(alph, summary_stats['mean'], summary_stats['median'], summary_stats['pstdev']) )
        zscore_mean = summary_stats['mean'] if change_mean is None else change_mean
        zscore_stddev = summary_stats['pstdev'] if change_stddev is None else change_stddev

        
        change_rate = 0
        for sm in self_sim_report['self_sim'][alph]:
            
            if( zscore_stddev == 0 ):
                continue

            zscore_sim = (sm['sim'] - zscore_mean)/zscore_stddev
            if( abs(zscore_sim) <= change_zscore_threshold ):
                continue

            fst_indx = sm['fst_doc_indx']
            sec_indx = sm['sec_doc_indx']

            st_segment_date = get_segment_dates(seg_id=self_bloc_doc_lst[fst_indx]['seg_id'], segments_details=usr_bloc['bloc_segments']['segments_details'])
            en_segment_date = get_segment_dates(seg_id=self_bloc_doc_lst[sec_indx]['seg_id'], segments_details=usr_bloc['bloc_segments']['segments_details'])

            #here means sim change is more than 1 - std. dev from mean, so it could indicate change
            logger.info( '\t{}. change sim: {:.2f}, z-score: {:.2f}'.format(change_rate+1, sm['sim'], zscore_sim) )
            logger.info( '\t{} vs. {}'.format(self_bloc_doc_lst[fst_indx]['text'], self_bloc_doc_lst[sec_indx]['text']) )
            logger.info( '\t{} -- {}\n'.format(st_segment_date[0], en_segment_date[-1]) )

            sm['changed'] = True
            change_rate += 1

        self_sim_report['change_rates'][alph] = change_rate/len(self_sim_report['self_sim'][alph])
        logger.info( '\tchange_rate: {:.2f} ({}/{})'.format(self_sim_report['change_rates'][alph], change_rate, len(self_sim_report['self_sim'][alph])) )
        logger.info('')
        

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

    
