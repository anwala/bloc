import gzip

from bloc.generator import add_bloc_sequences
from bloc.util import genericErrorInfo
from bloc.util import getDictFromJson

def user_tweets_generator_0(filenames, pos_id_mapping, gen_bloc_params, **kwargs):
    
    '''
        Expects gzip compressed file.
        File format (user_id_k is optional):
        user_id_0\tJSON list of tweets
        user_id_1\tJSON list of tweets
        user_id_2\tJSON list of tweets

    '''

    index = -1
    rm_doc_text = kwargs.get('rm_doc_text', True)
    keep_bloc_details = kwargs.get('keep_bloc_details', ['created_at_utc', 'screen_name', 'user_id'])

    for f in filenames:
        with gzip.open(f, 'rb') as file:
            for row in file:
                
                doc = ''
                index += 1
                
                try:
                    row = row.decode().split('\t')
                    if( len(row) == 0 ):
                        continue
                    
                    tweets = row[-1]
                    tweets = getDictFromJson(tweets)
                    bloc_payload = add_bloc_sequences(tweets, **gen_bloc_params)

                    if( len(tweets) != 0 and 'bloc' in bloc_payload ):
                        doc = [ bloc_payload['bloc'][dim] for dim in bloc_payload['bloc'] ]
                        doc = ' '.join(doc).strip()
                except:
                    genericErrorInfo()

                if( isinstance(pos_id_mapping, dict) ):
                    
                    pos_id_mapping[index] = {'id': index}

                    for ky in keep_bloc_details:
                        if( ky in bloc_payload ):
                            pos_id_mapping[index][ky] = bloc_payload[ky]

                    if( rm_doc_text is False ):
                        pos_id_mapping[index]['text'] = doc

                yield doc