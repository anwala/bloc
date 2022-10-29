from bloc.generator import add_bloc_sequences
from bloc.util import get_bloc_doc_lst
from bloc.util import get_bloc_variant_tf_matrix
from bloc.util import get_default_symbols

#from bloc.util import conv_tf_matrix_to_json_compliant
#from bloc.util import dumpJsonToFile

def run_subcommands(args, subcommand, payload):
    
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
        print_top_ngrams(tf_matrices)

def print_top_ngrams(tf_mat, k=10):

    def get_word_type(word):
    
        bloc_types = {
            'action': set('DfLlPpπRrρT'),
            'content_syntactic': set('EHMmqφtU'),
            'time': set('□⚀⚁⚂⚃⚄⚅'),
            'change': set('aDdFfgGλLlnNsuWw'),
            'content_semantic_entities': set('⚇⌖⋈x⊛'),
            'content_semantic_sentiment': set('⋃-⋂')
        }
        
        word = set(word)
        for typ, tokens in bloc_types.items():
            if( len(word & tokens) > 0 ):
                return typ

        return ''

    def print_top_k_ngrams( top_ngrams, rate_key, skip_pause_glyph=True ):

        counter = 1
        for i in range( len(top_ngrams) ):

            n = top_ngrams[i]
            if( skip_pause_glyph is True and '□⚀⚁⚂⚃⚄⚅.'.find(n['term']) > -1 ):
                continue
            
            line = '\t{:<4} {:.4f} {} ({})'.format(f'{counter}.', n[rate_key], n['term'], get_word_type(n['term']) )
            counter += 1
            print( line )

    if( 'top_ngrams' not in tf_mat ):
        print('top_ngrams not in tf_mat, returning')
        return


    for i in range( len(tf_mat['top_ngrams']['per_doc']) ):
        
        topngrams = tf_mat['top_ngrams']['per_doc'][i]
        user = tf_mat['tf_idf_matrix'][i]['screen_name']        
        print(f'\nTop {k} ngrams for user: {user}')
        print_top_k_ngrams( topngrams[:k], 'term_rate' )

    print(f'\nTop {k} ngrams across all users')
    print_top_k_ngrams( tf_mat['top_ngrams']['all_docs'][:k], 'doc_rate' )

    







