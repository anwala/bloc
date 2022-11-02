import logging
from itertools import combinations
from sklearn.metrics.pairwise import cosine_similarity

from bloc.generator import add_bloc_sequences
from bloc.generator import get_word_type

from bloc.util import conv_tf_matrix_to_json_compliant
#from bloc.util import dumpJsonToFile
from bloc.util import get_bloc_doc_lst
from bloc.util import get_bloc_variant_tf_matrix
from bloc.util import get_default_symbols

logger = logging.getLogger('bloc.bloc')

def run_subcommands(args, subcommand, payload):
    
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
    bloc_collection = [ubloc for ubloc in payload]

    #generate collection of BLOC documents
    bloc_doc_lst = get_bloc_doc_lst(bloc_collection, bloc_model['bloc_alphabets'], src=args.account_src, src_class=args.account_class)

    if( subcommand == 'cluster' ):
        return all_usr_self_cmp(bloc_collection, bloc_model, args.bloc_alphabets)

    
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

def all_usr_self_cmp(bloc_collection, bloc_model, bloc_alphabets):

    logger.info('\nall_usr_self_cmp():')
    for u_bloc in bloc_collection:
        
        self_sim_report = usr_self_cmp(u_bloc, bloc_model, bloc_alphabets)
        
        print(u_bloc['screen_name'])
        for alph, sim_vals in self_sim_report.items():
            avg_sim = -1 if sim_vals == [] else sum(sim_vals)/len(sim_vals)
            print('\t{:.4f}, {}'.format(avg_sim, alph) )
        
        print()

def usr_self_cmp(usr_bloc, bloc_model, bloc_alphabets):

    def self_doc_lst(bloc_segments, alphabet):
        
        if( 'segments' not in bloc_segments ):
            return []

        doc_lst = []
        for seg_id, seg_dets in bloc_segments['segments'].items():
            
            if( alphabet not in seg_dets ):
                continue

            if( seg_dets[alphabet].strip() == '' ):
                continue
            
            doc_lst.append({'text': seg_dets[alphabet]})

        return doc_lst
    
    def calc_self_sim(self_bloc_doc_lst, bloc_model):

        if( len(self_bloc_doc_lst) == 0 ):
            return []

        self_matrices = get_bloc_variant_tf_matrix(
            self_bloc_doc_lst, 
            min_df=2, 
            ngram=bloc_model['ngram'], 
            tf_matrix_norm=bloc_model['tf_matrix_norm'], 
            keep_tf_matrix=bloc_model['keep_tf_matrix'], 
            token_pattern=bloc_model['token_pattern'], 
            bloc_variant=bloc_model['bloc_variant'], 
            set_top_ngrams=bloc_model['set_top_ngrams'], 
            top_ngrams_add_all_docs=bloc_model['top_ngrams_add_all_docs']
        )

        if( 'tf_idf_matrix' not in self_matrices ):
            return []

        all_self_sim = []
        for i in range( 1, len(self_matrices['tf_idf_matrix']) ):
            pre_vect = self_matrices['tf_idf_matrix'][i-1]['tf_vector']
            cur_vect = self_matrices['tf_idf_matrix'][i]['tf_vector']
            sim = cosine_similarity( pre_vect, cur_vect )[0][0]
            all_self_sim.append(sim)

        return all_self_sim
    
    self_sim_report = {}
    for alph in bloc_alphabets:
        
        self_bloc_doc_lst = self_doc_lst(usr_bloc.get('bloc_segments', {}), alph)
        self_sim_report[alph] = calc_self_sim(self_bloc_doc_lst, bloc_model)

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

    
