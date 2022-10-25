import json
import logging
import numpy as np
import warnings

from copy import deepcopy
from datetime import datetime
from sklearn.feature_extraction.text import CountVectorizer

from bloc.util import genericErrorInfo
from bloc.util import get_color_txt
from bloc.util import getDictFromJsonGZ
from bloc.util import gzipTextFile

logger = logging.getLogger('bloc.bloc')

class BLOCMarkovChain:
    
    '''
        Class for trianing a BLOC Markov Model. See use_cases() for usage examples
    '''
    def __init__(self, training_sequence_lst=None, model=None, model_output_filename=None, model_label='', states=None, init_prob_dist=None, transition_matrix=None, **kwargs):
            
        if( training_sequence_lst is not None ):
            #create model from training data
            training_model = BLOCMarkovChain.train_markov_model(training_sequence_lst, model_output_filename, model_label)

        elif( model is not None ):
            #instantiate markov chain from model
            training_model = model
        else:
            training_model = None

        
        self.states = states
        self.transition_matrix = transition_matrix
        self.init_prob_dist = init_prob_dist
        self.training_model = training_model
        self.model_label = model_label

        BLOCMarkovChain.validate_prob_params(self.states, self.transition_matrix, self.init_prob_dist)
    
    @staticmethod
    def validate_prob_params(states, transition_matrix, init_prob_dist):

        valid_flag = True


        if( states is None ):
            valid_flag = False
        elif( len(states) == 0 ):
            warnings.warn('States is empty.')
            valid_flag = False


        if( transition_matrix is None ):
            valid_flag = False
        else:
            transition_matrix = np.array(transition_matrix)
            if not np.all(transition_matrix >= 0):
                warnings.warn('Transition matrix contains negative value(s).')
                valid_flag = False
            
            for i in range( transition_matrix.shape[0] ):
                sm = np.sum( transition_matrix[i] )
                if not np.isclose( sm, 1. ):
                    warnings.warn( 'Transition probabilities don\'t sum to 1. Row {}, Sum = {}'.format(i, sm) )
                    valid_flag = False


        if( init_prob_dist is None ):
            valid_flag = False
        elif not np.isclose(np.sum(init_prob_dist), 1.):
            warnings.warn('Initial probabilities distribution don\'t sum to 1.')
            valid_flag = False

        return valid_flag

    @staticmethod
    def train_markov_model(sequence_lst, model_output_filename=None, model_label=''):
        
        ngram_freq = BLOCMarkovChain.get_ngram_freq(sequence_lst)
        mk_freq_mat = BLOCMarkovChain.get_markov_freq_matrix(ngram_freq)

        if( model_output_filename is not None ):
            if( 'markov_freq_matrix' in mk_freq_mat ):

                mk_freq_mat['markov_freq_matrix'] = list( mk_freq_mat['markov_freq_matrix'] )

                for i in range( len(mk_freq_mat['markov_freq_matrix']) ):
                    mk_freq_mat['markov_freq_matrix'][i] = [ float(a) for a in mk_freq_mat['markov_freq_matrix'][i] ]

                mk_freq_mat['model_label'] = model_label
                mk_freq_mat['model_created_at_utc'] = datetime.utcnow().isoformat().split('.')[0] + 'Z'
                gzipTextFile(model_output_filename, json.dumps(mk_freq_mat, ensure_ascii=False))

        return mk_freq_mat

    @staticmethod
    def mle_get_markov_params( markov_freq_mat, unknown_seq ):

        if( 'vocab' not in markov_freq_mat or 'markov_freq_matrix' not in markov_freq_mat or unknown_seq == '' ):
            logger.info("\tmle_get_markov_params(): 'vocab' not in markov_freq_mat or 'markov_freq_matrix' not in markov_freq_mat or unknown_seq == ''")
            return markov_freq_mat

        if( len(markov_freq_mat['vocab']) == 0 ):
            logger.info("\tmle_get_markov_params(): len(markov_freq_mat['vocab']) == 0")
            return markov_freq_mat


        if( isinstance(markov_freq_mat['markov_freq_matrix'], list) ):
            markov_freq_mat['markov_freq_matrix'] = np.array( markov_freq_mat['markov_freq_matrix'] )

        
        start_prob_dist = [ markov_freq_mat['start_dist'][s] for s in markov_freq_mat['vocab'] ]

        #find/add unseen states - start
        new_states = []
        for s in set(unknown_seq):
            if( s not in markov_freq_mat['vocab'] ):
                new_states.append(s)
                markov_freq_mat['start_dist'][s] = 0

        
        new_states_count = len(new_states)
        markov_freq_mat['vocab'] += new_states

        row, col = markov_freq_mat['markov_freq_matrix'].shape
        z = np.zeros(( row, new_states_count ))
        
        #add extra columns of zeros for new states
        markov_freq_mat['markov_freq_matrix'] = np.concatenate( (markov_freq_mat['markov_freq_matrix'], z), axis=1 )
        
        #add extra rows of zeros to new matrix
        z = np.zeros(( new_states_count, len(markov_freq_mat['vocab']) ))
        markov_freq_mat['markov_freq_matrix'] = np.concatenate( (markov_freq_mat['markov_freq_matrix'], z), axis=0 )
        #find/add unseen states - end


        #gen (smoothed) start_dist - start
        start_prob_dist += [0] * new_states_count
        if( 0 in start_prob_dist ):
            start_prob_dist = [ v+1 for v in start_prob_dist ]

        total_freq = sum(start_prob_dist)
        markov_freq_mat['start_prob_dist'] = [ v/total_freq for v in start_prob_dist ]
        #gen (smoothed) start_dist - end

        
        #calc transition probs, smooth if necessary 
        markov_freq_matrix_row_sums = [ sum(v) for v in markov_freq_mat['markov_freq_matrix'] ]
        #new_states        


        n = len(markov_freq_mat['vocab'])
        markov_freq_mat['markov_trans_prob_matrix'] = np.zeros( (n,n) )

        '''
            print('vocab/transition_matrix:')
            print(markov_freq_mat['vocab'])
            print(markov_freq_mat['markov_freq_matrix'])
            print('all transition prob')
        '''
        if( 'un_smoothed_markov_freq_matrix' not in markov_freq_mat ):
            markov_freq_mat['un_smoothed_markov_freq_matrix'] = deepcopy( markov_freq_mat['markov_freq_matrix'] )

        for i in range(n):

            s0 = markov_freq_mat['vocab'][i]

            if( 0 in markov_freq_mat['markov_freq_matrix'][i] ):
                markov_freq_mat['markov_freq_matrix'][i] = markov_freq_mat['markov_freq_matrix'][i] + 1
                markov_freq_matrix_row_sums[i] = sum( markov_freq_mat['markov_freq_matrix'][i] )

            sm = markov_freq_matrix_row_sums[i]

            for j in range(n):

                s1 = markov_freq_mat['vocab'][j]
                ky = s0 + ' ' + s1

                prob = markov_freq_mat['markov_freq_matrix'][i, j]/sm
                markov_freq_mat['markov_trans_prob_matrix'][i, j] = prob
                
                #print( '{}, {}, sq: {}, C({}|{}) = {}, C(*|{}) = {}'.format(i, j, ky, s1, s0, markov_freq_mat['markov_freq_matrix'][i, j], s0, sm), 'P({}|{}) = {:.2f}'.format(s1, s0, prob) )

        #print('markov_trans_prob_matrix')
        #print( markov_freq_mat['markov_trans_prob_matrix'] )
        return markov_freq_mat

    @staticmethod
    def get_markov_freq_matrix(ngram_freq):
        
        payload = {
            'vocab': [],
            'start_dist': ngram_freq.get('start_dist', {}),
            'un_smoothed_markov_freq_matrix': np.array([]),
            'markov_freq_matrix': np.array([])
        }

        if( 'vocab' not in ngram_freq or 'ngram_freq' not in ngram_freq ):
            return payload

        if( 'all_docs' not in ngram_freq['ngram_freq'] ):
            return payload


        #generate markov chain states
        markov_states = []
        dedup_set = set()
        for v in ngram_freq['vocab']:
            
            v_split = v.split(' ')

            if( len(v_split) != 1 or v in dedup_set ):
                continue

            dedup_set.add(v)
            markov_states.append(v)
        
        n = len(markov_states)
        markov_freq_matrix = np.zeros((n, n))


        #prerequisite for markov chain transition matrix: populate markov_freq_matrix (pre-cursor to markov_transition_matrix) with counts that would be used to calc P(x|y)
        for i in range(n):

            s0 = markov_states[i]
            for j in range(n):
                
                s1 = markov_states[j]
                ky = s0 + ' ' + s1

                if( ky not in ngram_freq['ngram_freq']['all_docs'] ):
                    continue

                markov_freq_matrix[i, j] = ngram_freq['ngram_freq']['all_docs'][ky]

            #set missing start_dist - start
            payload['start_dist'].setdefault(s0, 0)
            #set missing start_dist - end
    
        
        #for debug - start
        '''
        print('\nmarkov_states', markov_states)
        for i in range(n):

            s0 = markov_states[i]
            for j in range(n):

                s1 = markov_states[j]
                ky = s0 + ' ' + s1
                sm = sum(markov_freq_matrix[i])

                print( 'ky: {}, C({}|{}) = {}, C(*|{}) = {}'.format(ky, s1, s0, markov_freq_matrix[i, j], s0, sm) )

        print('\nmarkov_freq_matrix:')
        print(markov_freq_matrix)
        '''
        #for debug - end

        payload['vocab'] = markov_states
        payload['markov_freq_matrix'] = markov_freq_matrix
        payload['un_smoothed_markov_freq_matrix'] = deepcopy(markov_freq_matrix)
        return payload

    @staticmethod
    def get_ngram_freq(sequence_lst, ngram_range=(1, 2), token_pattern=r'[^ |()*]', **kwargs):
        
        kwargs.setdefault('lowercase', False)
        payload = {
            'vocab': [],
            'start_dist': {},
            'ngram_freq': {
                'all_docs': {},
                'all_docs_total_tf': {}
            }
        }


        for seq in sequence_lst:
            
            if( seq == '' ):
                continue

            payload['start_dist'].setdefault( seq[0], 0 )
            payload['start_dist'][ seq[0] ] += 1


        try:
            count_vectorizer = CountVectorizer(
                stop_words=None, 
                token_pattern=token_pattern, 
                ngram_range=ngram_range,
                lowercase=kwargs['lowercase']
            )

            payload['tf_matrix'] = count_vectorizer.fit_transform(sequence_lst).toarray()
            payload['vocab'] = count_vectorizer.get_feature_names()

            #convert types for JSON serialization - start
            for opt in ['tf_matrix']:

                if( opt not in payload ):
                    continue

                payload[opt] = list( payload[opt] )
                for i in range( len(payload[opt]) ):
                    payload[opt][i] = [ float(a) for a in payload[opt][i] ]
            #convert types for JSON serialization - end
        except:
            genericErrorInfo()
            return payload


        for i in range( len(payload['tf_matrix']) ):

            total_tf = sum(payload['tf_matrix'][i])
            if( total_tf == 0 ):
                total_tf = -1

            single_doc_tf = [ {'term': v, 'term_freq': int(payload['tf_matrix'][i][j]), 'term_rate': payload['tf_matrix'][i][j]/total_tf} for (j, v) in enumerate(payload['vocab']) if payload['tf_matrix'][i][j] != 0 ]
            
            for tf_dct in single_doc_tf:
                payload['ngram_freq']['all_docs'].setdefault( tf_dct['term'], 0 )
                payload['ngram_freq']['all_docs'][ tf_dct['term'] ] += int(tf_dct['term_freq'])

                term_ngram = '{}-gram'.format( len(tf_dct['term'].split(' ')) )
                
                payload['ngram_freq']['all_docs_total_tf'].setdefault( term_ngram, 0 )
                payload['ngram_freq']['all_docs_total_tf'][ term_ngram ] += int(tf_dct['term_freq'])    

        del payload['tf_matrix']
        return payload

    def frm_prob_of_seq_mle_get_markov_params(self, sequence):

        #here means object was created without instantiating states or init_prob_dist or transition_matrix
        if( self.training_model is None ):
            return None
        else:
            #Attempt to instantiate states or init_prob_dist or transition_matrix from training_model
            markov_params = BLOCMarkovChain.mle_get_markov_params(self.training_model, sequence)
            
            self.states = markov_params.get('vocab', None)
            self.init_prob_dist = markov_params.get('start_prob_dist', None)
            self.transition_matrix = markov_params.get('markov_trans_prob_matrix', None)

            if( BLOCMarkovChain.validate_prob_params(self.states, self.transition_matrix, self.init_prob_dist) is False ):
                return None

            return True

    def prob_of_sequence(self, sequence, log_prob=True):
        
        #print('prob_of_sequence({}):'.format(sequence))
        if( self.states is None or self.init_prob_dist is None or self.transition_matrix is None ):
            #print('\t0, None: vocab: {}, init_prob_dist: {}, transition_matrix: {}'.format(self.states is None, self.init_prob_dist is None, self.transition_matrix is None))            
            
            #here means object was created without instantiating states or init_prob_dist or transition_matrix
            if( self.frm_prob_of_seq_mle_get_markov_params(sequence) is None ):
                return None
        else:
            #print('\t1')
            seq_min_states = set(sequence) - set(self.states)
            #print('\tseq - states:', seq_min_states)
            if( len(seq_min_states) != 0 ):
                #here means that the sequence has an unseen state, so retrain model and smooth for unseen state
                if( self.frm_prob_of_seq_mle_get_markov_params(sequence) is None ):
                    return None

            


        if( isinstance(sequence, str) ):
            sequence = list(sequence)

        start = sequence[0]
        prob = self.states.index( start )
        prob = self.init_prob_dist[ prob ]

        if( log_prob is True ):
            prob = np.log(prob)
        
        #logger.info( '\nprob_of_sequence():' )
        #logger.info( '\tstates: {}'.format(self.states) )
        #logger.info( '\tP({}):'.format(sequence) )
        #logger.info( '\n\tP({}) = {:4f}'.format(start, prob) )
        for i in range( 1, len(sequence) ):
            
            cur_indx = self.states.index( sequence[i-1] )
            next_indx = self.states.index( sequence[i] )
            trans_prob = self.transition_matrix[cur_indx, next_indx]
            na = 1 if self.training_model['un_smoothed_markov_freq_matrix'][cur_indx, next_indx] == 0 else 0
            
            if( log_prob is True ):
                trans_prob = np.log( trans_prob )
                prob += trans_prob
            else:
                prob *= trans_prob
            
            #logger.info( '\tP({}|{}) = {:.4f} (NA: {})'.format(sequence[i], sequence[i-1], trans_prob, na) )

        return prob

    @staticmethod
    def s_prob_of_sequence(training_model, sequence, log_prob=True):
                
        #Attempt to instantiate states or init_prob_dist or transition_matrix from training_model
        markov_params = BLOCMarkovChain.mle_get_markov_params(deepcopy(training_model), sequence)
        
        states = markov_params.get('vocab', None)
        init_prob_dist = markov_params.get('start_prob_dist', None)
        transition_matrix = markov_params.get('markov_trans_prob_matrix', None)
        un_smoothed_markov_freq_matrix = markov_params.get('un_smoothed_markov_freq_matrix', None)

        #print('\t\tv:', states)
        #print('\t\ts:', markov_params.get('start_dist', None))
        #if( BLOCMarkovChain.validate_prob_params(states, transition_matrix, init_prob_dist) is False ):
        #    return None
        #print('vocab/states:', states)
        #print('markov_freq_matrix:\n', markov_params['markov_freq_matrix'])
        #print('transition_matrix:\n', transition_matrix)


        if( isinstance(sequence, str) ):
            sequence = list(sequence)

        start = sequence[0]
        prob = states.index( start )
        prob = init_prob_dist[ prob ]
        #prob = [1/len(states)]*len(states)

        if( log_prob is True ):
            prob = np.log(prob)
        
        
        #logger.info( '\nprob_of_sequence():' )
        #logger.info( '\tstates: {}'.format(states) )
        #logger.info( '\tP({}):'.format(sequence) )
        #logger.info( '\n\tP({}) = {:4f}'.format(start, prob) )
        
        #print( '\nprob_of_sequence():' )
        #print( '\tstates: {}'.format(states) )
        #print( '\tP({}):'.format(sequence) )
        #print( '\n\tP({}) = {:4f}'.format(start, prob) )
        #print('un_smoothed_markov_freq_matrix:\n', un_smoothed_markov_freq_matrix)
        #print('\ntransition_matrix:')
        #print(transition_matrix)

        for i in range( 1, len(sequence) ):
            
            cur_indx = states.index( sequence[i-1] )
            next_indx = states.index( sequence[i] )
            trans_prob = transition_matrix[cur_indx, next_indx]

            #print('\tcur_indx:', cur_indx)
            #print('\tnext_indx:', next_indx)
            #print()
            #na = 1 if un_smoothed_markov_freq_matrix[cur_indx, next_indx] == 0 else 0

            if( log_prob is True ):
                trans_prob = np.log( trans_prob )
                prob += trans_prob
            else:
                prob *= trans_prob
            
            #logger.info( '\tP({}|{}) = {:.4f} (NA: {})'.format(sequence[i], sequence[i-1], trans_prob, na) )

        return prob

    @staticmethod
    def matrix_to_str( matrix, col_mat, vocab, model_label, mat_name ):
        
        if( len(matrix) == 0 or len(vocab) == 0 or matrix.shape != col_mat.shape ):
            return ''

        N = len(matrix) 
        all_prnt = ''
        dec = 5#match with: val = '{:5}'.format(val)

        heading = (' '*dec).join(['{}'.format(v) for v in vocab])
        all_prnt += model_label + f'{mat_name}:\n' + ' '*(dec*2) + heading + '\n'
        
        for i in range(N):
            
            prnt = ''
            row = matrix[i]
            for j in range( len(row) ):
                val = row[j]
                val = '{:5}'.format(val)
                
                if( col_mat[i, j] == 0 ):
                    prnt += '{} '.format(val)
                else:
                    prnt += '{} '.format( getColorTxt(val) )

            all_prnt += ' '*dec + vocab[i] + ' ' + prnt
            
            if( i < N-1 ):
                all_prnt += '\n'

        return all_prnt

    def __str__(self):
        
        model_label = self.model_label + '\n' if self.model_label != '' else ''

        to_prnt_frq_mat = BLOCMarkovChain.matrix_to_str( 
            self.training_model['markov_freq_matrix'], 
            self.training_model['un_smoothed_markov_freq_matrix'],
            self.training_model['vocab'], 
            model_label, 
            'markov_freq_matrix'
        )

        return to_prnt_frq_mat

