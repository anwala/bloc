import logging
import numpy as np
import sys

from copy import deepcopy
from numpy import linalg as LA
from scipy.spatial import distance
from sklearn.metrics import confusion_matrix
from sklearn.metrics import accuracy_score, recall_score, f1_score
from sklearn.metrics import classification_report
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

from bloc.util import dumpJsonToFile
from bloc.util import genericErrorInfo
from bloc.util import get_bloc_variant_tf_matrix

from warnings import warn

logger = logging.getLogger('bloc.bloc')

def is_invalidate_matrix(matrix_key, tf_mat):
    if( matrix_key not in tf_mat or 'vocab' not in tf_mat ):
        logger.warning(f'\t{matrix_key} not in tf_mat, returning, see: ' + str(tf_mat.keys()) )
        return True

def get_bloc_tf_matrix(doc_lst, bloc_model):

    logger.info('\nget_bloc_tf_matrix()')
    logger.info('\tdoc_lst.len:', len(doc_lst))
    logger.info('\tngram:', bloc_model['ngram'])
    logger.info('\ttoken_pattern:', bloc_model['token_pattern'])
    logger.info('\tbloc_variant:', bloc_model['bloc_variant'])
    
    logger.info('\tget_bloc_variant_tf_matrix() - start')
    tf_mat = get_bloc_variant_tf_matrix(
        doc_lst,
        bloc_model['ngram'],
        token_pattern=bloc_model['token_pattern'],
        bloc_variant=bloc_model['bloc_variant'],
        add_all_docs=False
    )
    logger.info('\tget_bloc_variant_tf_matrix() - end')
    
    return tf_mat

def get_one_v_rest_centroid( dataset, vector_key, user ):

    count = 0
    centroid = []
    
    for u in dataset:
        
        if( user['user'] == u['user'] ):
            continue

        if( user['class'] != u['class'] ):
            continue

        if( len(centroid) == 0 ):
            centroid = np.zeros( len(u[vector_key]) )

        count += 1
        centroid += u[vector_key]

    if( count == 0 ):
        return {}

    return {
        'centroid': centroid/count,
        'count': count
    }

def predict_user_type_centroid_helper(user_vect, candidates, dist_metric='cosine'):

    min_dist = {'class': '', 'dist': sys.maxsize}
    for src, clss_dct in candidates.items():
        
        if( dist_metric == 'cosine' ):
            if( isinstance(user_vect, csr_matrix) ):
                user_vect = user_vect.toarray()[0]
            dist = distance.cosine(user_vect, clss_dct['centroid'])
        else:
            dist = LA.norm(user_vect - clss_dct['centroid'])
        

        if( dist < min_dist['dist'] ):
            min_dist['class'] = clss_dct['class']
            min_dist['dist'] = dist
            min_dist['src'] = src
    
    return min_dist['class']

def run_pca(matrix, features, n_components=10, z_score_normalize=True):

    n_features = len(features)
    if( n_features < 3 ):
        return {}
    
    if( n_components > n_features ):
        warn(f'run_pca(): setting n_components = 2 since n_components ({n_components}) > n_features ({n_features})')
        n_components = 2

    
    pca = PCA(n_components=n_components) # estimate only 2 PCs

    #X = np.array( [[-1, -1], [-2, -1], [-3, -2], [1, 1], [2, 1], [3, 2]] )
    X = [ v['tf_vector'] for v in matrix ]
    
    # Z-score the features
    #this might not be needed since tf-idf already performs some level of normalization
    if( z_score_normalize is True ):
        scaler = StandardScaler()
        scaler.fit(X)
        X = scaler.transform(X)
    

    # The PCA model
    #credit: https://medium.com/ai-in-plain-english/how-to-implement-pca-with-python-and-scikit-learn-22f3de4e5983
    #for model training/testing see: https://stackabuse.com/implementing-pca-in-python-with-scikit-learn/ and https://towardsdatascience.com/pca-using-python-scikit-learn-e653f8989e60
    #pca = PCA(n_components=n_components) # estimate only 2 PCs
    X_new = pca.fit_transform(X) # project the original data into the PCA space

    #The PCA class contains explained_variance_ratio_ which returns the variance caused by each of the principal components. 
    explained_variance = pca.explained_variance_ratio_
    explained_variance_sum = sum(explained_variance)
    abs_eigenvector = abs(pca.components_)

    if( n_components > len(explained_variance) ):
        n_components = len(explained_variance)
    
    feature_importance = []
    for i in range( len(features) ):

        score = 0
        for j in range(n_components):
            score += abs_eigenvector[:,i][j] * explained_variance[j]

        score = score/explained_variance_sum
        #score is weighted average of eigenvector components (where weights are explained variance ratio of PC)
        feature_importance.append({
            'feature': features[i],
            'score': score,
            'indx': i
        })

    feature_importance = sorted( feature_importance, key=lambda x: x['score'], reverse=True )

    return {
        'pca': pca,
        'pca_points': [ {'pca_vect': v} for v in X_new ],
        'feature_importance': feature_importance
    }

def get_bloc_pred_centroids( tf_mat, vocab, n_components=0, **kwargs ):

    if( len(tf_mat) == 0 or len(vocab) == 0 ):
        return {}
    
    pca_payload = {}
    centroids = {}
    
    kwargs.setdefault('pca_z_score_normalize', False)

    if( n_components > 0 ):
        
        try:
            pca_payload = run_pca( tf_mat, vocab, n_components=n_components, z_score_normalize=kwargs['pca_z_score_normalize'] )
        except:
            genericErrorInfo()

        if( len(pca_payload) == 0 ):
            return {}

        n_components = len(pca_payload['pca_points'][0]['pca_vect'])#it's possible for n_components to change after run_pca
        centroid_vect_dim = n_components
    else:
        centroid_vect_dim = len( tf_mat[0]['tf_vector'] )


    for i in range( len(tf_mat) ):
        
        user = tf_mat[i]
        classname = user['class']
        centroids.setdefault(classname, {'centroid': np.zeros(centroid_vect_dim), 'count': 0, 'class': classname})
        centroids[classname]['count'] += 1

        if( n_components > 0 and len(pca_payload) > 0 ):
            pca_payload['pca_points'][i]['user'] = user['user']
            pca_payload['pca_points'][i]['class'] = classname

            #centroid is calculated from PCA
            centroids[classname]['centroid'] += pca_payload['pca_points'][i]['pca_vect']
        else:
            #centroid is calculated from raw tf_vector
            centroids[classname]['centroid'] += tf_mat[i]['tf_vector']


    for classname in centroids:
        centroids[classname]['centroid'] = centroids[classname]['centroid']/centroids[classname]['count']

    return {
        'pca_payload': pca_payload,
        'centroids': centroids
    }

def predict_user_class_centroid(doc_lst, tf_mat, centroids, pca_payload, one_v_rest=True):

    if( len(doc_lst) == 0 or len(tf_mat) == 0 ):
        return {}

    all_classes = list(centroids.keys())
    all_classes.sort()

    y_true = []
    y_pred = []
    class_rep = {}
    conf_mat = np.zeros( (len(all_classes), len(all_classes)) )
    
    for i in range( len(doc_lst) ):

        user = doc_lst[i]
        classname = user['class']
        loc_centroid = centroids if one_v_rest is False else deepcopy(centroids)

        if( len(pca_payload) == 0 ):
            #train_split = -1: suggests doc_lst is a test set and tf_mat was generated with test set, but centroids was calculated with training set, so no need to replace centroid that includes user with get_one_v_rest_centroid()
            #empty pca_payload means centroids are calculated from raw TF matrices.
            #get_one_v_rest_centroid recalculates centroid, but ensures user is not part of te calculation
            
            loc_centroid[classname] = loc_centroid[classname] if one_v_rest is False else get_one_v_rest_centroid( tf_mat, 'tf_vector', user )
            pred = predict_user_type_centroid_helper( tf_mat[i]['tf_vector'], loc_centroid )
        else:
            
            loc_centroid[classname] = loc_centroid[classname] if one_v_rest is False else get_one_v_rest_centroid( pca_payload['pca_points'], 'pca_vect', user )
            pred = predict_user_type_centroid_helper( pca_payload['pca_points'][i]['pca_vect'], loc_centroid )
        
        
        pred_i = all_classes.index(pred)
        actu_i = all_classes.index(user['class'])
        conf_mat[pred_i, actu_i] += 1

        y_true.append(user['class'])
        y_pred.append(pred)
        
        '''
        print( i, 'user:', user['user'] )
        print( 'Pred/Actu:', pred, user['class'] )
        print(conf_mat)
        print()
        '''

    if( len(y_true) != 0 and len(y_pred) != 0 ):
        class_rep = classification_report(y_true, y_pred, output_dict=True, target_names=all_classes)
    
    return {
        'confusion_matrix': conf_mat,
        'all_classes': all_classes,
        'classification_report': class_rep
    }

def predict_user_class_tfidf(training_doc_lst, test_doc_lst, model, **kwargs):

    if( len(training_doc_lst) == 0 or len(test_doc_lst) == 0 ):
        logger.warning('len(training_doc_lst) == 0 or len(test_doc_lst) == 0, returning')
        return {}

    kwargs.setdefault('matrix_key', 'tf_idf_matrix')
    min_df = kwargs.get('min_df', 1)

    matrix_key = kwargs['matrix_key']

    train_per_src_doc = {}
    details = {}
    all_train_classes = set()
    all_test_classes = set([ d['class'] for d in test_doc_lst ])

    
    for i in range( len(training_doc_lst) ):
        src = training_doc_lst[i]['src']
        classs = training_doc_lst[i]['class']
        cent_src = f'{src}.{classs}'

        train_per_src_doc.setdefault( cent_src, {'user_indices': [], 'class': classs} )
        train_per_src_doc[cent_src]['user_indices'].append(i)
        all_train_classes.add( classs )


    if( len(all_train_classes - all_test_classes) > 0 ):
        #all_test_classes MUST be proper subset of all_train_classes
        logger.warning(' all_test_classes has class(es) absent from all_train_classes, returning')
        return {}

    
    train_test_tf_mat = get_bloc_variant_tf_matrix(
        training_doc_lst + test_doc_lst,
        model['ngram'],
        token_pattern=model['token_pattern'],
        bloc_variant=model['bloc_variant'],
        min_df=min_df,
        add_all_docs=False
    )
    
    if( is_invalidate_matrix( matrix_key, train_test_tf_mat ) ):
        logger.warning(' is_invalidate_matrix( matrix_key, train_test_tf_mat ), returning')
        return {}

    if( len(train_test_tf_mat[matrix_key]) == 0 ):
        logger.warning(' train_test_tf_mat is empty, returning')
        return {}

    details['vocab'] = train_test_tf_mat['vocab']
    #get centroids for training models - start
    for src in train_per_src_doc:
        cent = np.zeros( len(details['vocab']) )
        for indx in train_per_src_doc[src]['user_indices']:
            cent += train_test_tf_mat[matrix_key][indx]['tf_vector']
        
        cent = cent / len(train_per_src_doc[src]['user_indices'])
        train_per_src_doc[src]['centroid'] = cent
    #get centroids for training models - end

    all_train_classes = list(all_train_classes)
    all_train_classes.sort()

    y_true = []
    y_pred = []
    class_rep = {}
    conf_mat = np.zeros( (len(all_train_classes), len(all_train_classes)) )

    for i in range( len(test_doc_lst) ):

        u = test_doc_lst[i]
        classname = u['class']
        test_tf_mat_indx = len(training_doc_lst) + i#because training_doc_lst + test_doc_lst

        if( u['user_id'] != train_test_tf_mat[matrix_key][test_tf_mat_indx]['user_id'] ):
            logger.warning('\npredict_user_class_tfidf(): UNEXPECTED STATE, USER MISMATCH\n')
            continue

        pred = predict_user_type_centroid_helper( train_test_tf_mat[matrix_key][test_tf_mat_indx]['tf_vector'], train_per_src_doc, dist_metric=kwargs.get('dist_metric', 'cosine') )
        
        pred_i = all_train_classes.index(pred)
        actu_i = all_train_classes.index(u['class'])
        conf_mat[pred_i, actu_i] += 1

        y_true.append(u['class'])
        y_pred.append(pred)
        
        '''
        print( i, 'user:', u['user'] )
        print( 'Pred/Actu:', pred, u['class'] )
        print(conf_mat)
        print()
        '''

    if( len(y_true) != 0 and len(y_pred) != 0 ):
        class_rep = classification_report(y_true, y_pred, output_dict=True, target_names=all_train_classes)
    
    return {
        'confusion_matrix': conf_mat,
        'all_classes': all_train_classes,
        'details': details,
        'classification_report': class_rep
    }

def predict_user_class_bloc_centroid(bloc_model, n_components=0, training_doc_lst=[], test_doc_lst=[], **kwargs):

    '''
        n_components: if < 1 means no PCA vector should be used, else PCA would be used to calculate centroid
    
        if only training_doc_lst.len > 0, model is trained with entire training_doc_lst and evaluated with one v rest method
        if training_doc_lst.len > 0 and test_doc_lst.len > 0, model is trained with training_doc_lst and tested on test_doc_lst
    '''
    if( bloc_model not in ['bigram', 'word'] ):
        logger.warning(f'{bloc_model} not bigram or word, returning')
        return {}

    bloc_model_params = {
        'bigram': {
                'ngram': 2,
                'token_pattern': '[^ |()*]',
                'bloc_variant': None
            },
        'word': {
                'ngram': 1,
                'token_pattern': '[^□⚀⚁⚂⚃⚄⚅ |()*]+|[□⚀⚁⚂⚃⚄⚅]',
                'bloc_variant': {'type': 'folded_words', 'fold_start_count': 4, 'count_applies_to_all_char': False}
            }
        }

    kwargs.setdefault('matrix_key', 'tf_idf_matrix')
    matrix_key = kwargs['matrix_key']
    #train_split=-1

    if( len(training_doc_lst) > 0 and len(test_doc_lst) > 0 ):

        training_tf_mat = get_bloc_tf_matrix( training_doc_lst, bloc_model_params[bloc_model] )
        if( is_invalidate_matrix( matrix_key, training_tf_mat ) ):
            return {}

        test_tf_mat = get_bloc_tf_matrix( test_doc_lst, bloc_model_params[bloc_model] )
        if( is_invalidate_matrix( matrix_key, test_tf_mat ) ):
            return {}

        training_cent_pca = get_bloc_pred_centroids( training_tf_mat[matrix_key], training_tf_mat['vocab'], n_components=n_components, **kwargs )
        test_cent_pca = get_bloc_pred_centroids( test_tf_mat[matrix_key], test_tf_mat['vocab'], n_components=n_components, **kwargs )
        if( len(training_cent_pca) == 0 or len(test_cent_pca) == 0 ):
            return {}
        class_rep = predict_user_class_centroid( test_doc_lst, test_tf_mat[matrix_key], training_cent_pca['centroids'], test_cent_pca['pca_payload'], one_v_rest=False )

    else:

        tf_mat = get_bloc_tf_matrix( training_doc_lst, bloc_model_params[bloc_model] )
        if( is_invalidate_matrix( matrix_key, tf_mat ) ):
            return {}
        
        cent_pca = get_bloc_pred_centroids( tf_mat[matrix_key], tf_mat['vocab'], n_components=n_components, **kwargs )
        class_rep = predict_user_class_centroid( training_doc_lst, tf_mat[matrix_key], cent_pca['centroids'], cent_pca['pca_payload'], one_v_rest=True )

    return class_rep

def predict_user_class_bloc_tfidf(bloc_model, training_doc_lst=[], test_doc_lst=[], **kwargs):

    if( bloc_model not in ['bigram', 'word'] ):
        logger.warning(f'{bloc_model} not bigram or word, returning')
        return {}

    if( len(training_doc_lst) == 0 or len(test_doc_lst) == 0 ):
        return {}

    parenth_flag = '' if kwargs.get('omit_content_parentheses', False) is True else '()'
    pause_flag = '|[□⚀⚁⚂⚃⚄⚅]' if kwargs.get('add_pauses', True) is True else ''
    word_token_pattern = f'[^□⚀⚁⚂⚃⚄⚅ |*{parenth_flag}]+{pause_flag}'

    #print('\tword_token_pattern:', word_token_pattern)

    default_model_params = {
        'bigram': {
                'ngram': 2,
                'token_pattern': '[^ |()*]',
                'bloc_variant': None
            },
        'word': {
                'ngram': 1,
                'token_pattern': word_token_pattern,
                'bloc_variant': {'type': 'folded_words', 'fold_start_count': 4, 'count_applies_to_all_char': False}
        }
    }
    
    bloc_model_params = kwargs.get('bloc_model_params', default_model_params[bloc_model])

    if( len(bloc_model_params) == 0 ):
        print('len(bloc_model_params) == 0, returning')
        return {}

    class_rep = predict_user_class_tfidf( training_doc_lst, test_doc_lst, bloc_model_params, **kwargs )
        
    return class_rep