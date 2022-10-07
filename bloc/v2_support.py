from datetime import datetime
from copy import deepcopy
def get_v1_user_obj(v2_users):

    all_users = {}
    for u in v2_users:

        u['screen_name'] = u.pop('username', '')
        u['followers_count']  = u['public_metrics'].pop('followers_count', -1)
        u['friends_count']  = u['public_metrics'].pop('following_count', -1)
        u['statuses_count']  = u['public_metrics'].pop('tweet_count', -1)
        u['listed_count']  = u['public_metrics'].pop('listed_count', -1)
        u['favourites_count'] = -1
        u['created_at'] = datetime.strptime(u['created_at'], '%Y-%m-%dT%H:%M:%S.000Z').strftime('%a %b %d %H:%M:%S +0000 %Y')

        all_users[ u['id'] ] = u

    return all_users

def get_referenced_v2_tweets(v2_tweets):
    
    all_twts = {}
    for t in v2_tweets:
        all_twts[ t['id'] ] = t

    return all_twts

def get_v1_lite_twt(v2_tweet, all_v1_user_objs, all_referenced_v2_tweets):
    
    def get_in_reply_to_status_id(v2_tweet):

        for t in v2_tweet.get('referenced_tweets', []):
            if( t['type'] == 'replied_to' ):
                return t['id']

        return None

    def get_v1_entities(v2_entities):

        if( 'mentions' in v2_entities ):
            for i in range( len(v2_entities['mentions']) ):

                m = v2_entities['mentions'][i]
                m['screen_name'] = m.pop('username', '')
                m['indices'] = [ m.pop('start', -1), m.pop('end', -1) ]

            v2_entities['user_mentions'] = v2_entities.pop('mentions', [])

        if( 'hashtags' in v2_entities ):
            for i in range( len(v2_entities['hashtags']) ):
                h = v2_entities['hashtags'][i]
                h['text'] = h.pop('tag', '')
                h['indices'] = [ h.pop('start', -1), h.pop('end', -1) ]

        if( 'cashtags' in v2_entities ):
            for i in range( len(v2_entities['cashtags']) ):
                c = v2_entities['cashtags'][i]
                c['text'] = c.pop('tag', '')
                c['indices'] = [ c.pop('start', -1), c.pop('end', -1) ]
            v2_entities['symbols'] = v2_entities.pop('cashtags', [])

        if( 'urls' in v2_entities ):
            for i in range( len(v2_entities['urls']) ):
                u = v2_entities['urls'][i]
                u['indices'] = [ u.pop('start', -1), u.pop('end', -1) ]


        v2_entities.setdefault('user_mentions', [])
        v2_entities.setdefault('hashtags', [])
        v2_entities.setdefault('symbols', [])
        v2_entities.setdefault('urls', [])
        return v2_entities


    if( 'id' not in v2_tweet ):
        return {}

    if( v2_tweet['author_id'] not in all_v1_user_objs ):
        return {}


    in_reply_to_user_id = v2_tweet.get('in_reply_to_user_id', None)
    in_reply_to_screen_name = None if in_reply_to_user_id is None else all_v1_user_objs.get(in_reply_to_user_id, {}).get('screen_name', None)
    place = v2_tweet.get('geo', {}).get('place_id', None) #assumption is that geo, coordinates and places have collapsed into place
    payload = {
        'id': v2_tweet['id'],
        'full_text': v2_tweet.get('text', ''),
        'source': v2_tweet.get('source', ''),
        'lang': v2_tweet.get('lang', ''),
        'user': deepcopy(all_v1_user_objs[ v2_tweet['author_id'] ]),
        'geo': None,
        'coordinates': None,
        'place': place if place is None else {'id': place},
        'in_reply_to_status_id': get_in_reply_to_status_id(v2_tweet),
        'in_reply_to_screen_name': in_reply_to_screen_name,
        'in_reply_to_user_id': in_reply_to_user_id,
        'created_at': datetime.strptime(v2_tweet['created_at'], '%Y-%m-%dT%H:%M:%S.000Z').strftime('%a %b %d %H:%M:%S +0000 %Y'),
        'entities': get_v1_entities(deepcopy( v2_tweet.get('entities', {}) ))
    }

    if( 'context_annotations' in v2_tweet ):
        payload['context_annotations'] = v2_tweet['context_annotations']


    #add retweeted_status - start
    r_twts = v2_tweet.get('referenced_tweets', [])
    if( len(r_twts) == 1 ):

        twtype = r_twts[0]['type']; rtid = r_twts[0]['id']
        if( twtype == 'retweeted' and rtid in all_referenced_v2_tweets ):
            payload['retweeted_status'] = get_v1_lite_twt( all_referenced_v2_tweets[rtid], all_v1_user_objs, all_referenced_v2_tweets ) 
    #add retweeted_status - end


    #add extended_entities - start
    if( 'attachments' in v2_tweet and 'media_keys' in v2_tweet['attachments'] ):
        media = [ m.split('_')[-1] for m in v2_tweet['attachments']['media_keys'] ]
        media = [ {'id': m} for m in media ]
        payload['extended_entities'] = {'media': media}
    #add extended_entities - end
    
    return payload

def conv_v2_tweets_to_v1(v2_tweets):

    if( 'data' not in v2_tweets ):
        return []

    all_v1_user_objs = get_v1_user_obj( v2_tweets.get('includes', {}).get('users', []) )
    all_referenced_v2_tweets = get_referenced_v2_tweets( v2_tweets.get('includes', {}).get('tweets', []) )
    
    return [ get_v1_lite_twt(t, all_v1_user_objs, all_referenced_v2_tweets) for t in v2_tweets['data'] ]