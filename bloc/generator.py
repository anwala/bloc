import json
import logging
import os, sys
import osometweet
import re
import time

from copy import deepcopy
from datetime import datetime, timedelta
from requests_oauthlib import OAuth1Session
from textblob import TextBlob

from bloc.util import color_bloc_action_str
from bloc.util import datetimeFromUtcToLocal
#from bloc.util import dumpJsonToFile
from bloc.util import find_tweet_timestamp_post_snowflake
from bloc.util import genericErrorInfo
from bloc.util import getDictFromFile
from bloc.util import getDictFromJsonGZ
from bloc.util import get_screen_name_frm_status_uri
from bloc.util import gen_post_snowflake_twitter_id
from bloc.util import gzipTextFile
from bloc.util import twitter_v2_user_lookup_ids
from bloc.v2_support import conv_v2_tweets_to_v1

logger = logging.getLogger('bloc.bloc')
'''
    Alphabets
    Action
    Content-Syntactic
    Content-Semantic-Sentiment
    Change
    Time

    BLOC Master Alphabets list
    - - Content-Semantic-Sentiment    (- - Neutral)
    a - Change                        (Profile appearance change)
    D - Change                        (Delete tweet)
    d - Change                        (Description change)
    E - Content-Syntactic             (E - Media)
    F - Change                        (Follow someone)
    f - Change                        (Unfollow someone)
    g - Change                        (Profile location change)
    G - Change                        (geographical location change (see coordinates and place))
    H - Content-Syntactic             (H - Hashtag)
    L - Change                        (Liked tweet)
    l - Change                        (Unliked tweet)
    M - Content-Syntactic             (M - Mention of friend (can't be checked until friendship relationship assigned))
    m - Content-Syntactic             (m - Mention of non-friend)
    n - Change                        (Name change)
    N - Change                        (Handle change)
    P - Action                        (Reply a friend (can't be checked until friendship relationship assigned))
    p - Action                        (Reply a non-friend)
    q - Content-Syntactic             (q - Quote URL)
    R - Action                        (Retweet a friend (can't be checked until friendship relationship assigned))
    r - Action                        (Retweet a non-friend)
    s - Change                        (source change)
    T - Action                        (Tweet)
    t - Content-Syntactic             (t - Text)
    u - Change                        (URL change)
    U - Content-Syntactic             (U - URL)
    W - Change                        (Gained followers)
    w - Change                        (Lossed followers)
    x - Content-Semantic-Entities     (Product (e.g., Mountain Dew, Mozilla Firefox))
    ¤ - Content-Syntactic             (¤ - Cashtag)
    λ - Change                        (Language change)
    π - Action                        (Reply self)
    ρ - Action                        (Retweet self)
    φ - Content-Syntactic             (φ - Quote self)
    ⊛ - Content-Semantic-Entities     (Other (e.g., Diabetes, Super Bowl 50))
    ⋂ - Content-Semantic-Sentiment    (⋂ - Negative)
    ⋃ - Content-Semantic-Sentiment    (⋃ - Positive)
    ⋈ - Content-Semantic-Entities     (Organization (e.g., Chicago White Sox, IBM))
    ⌖ - Content-Semantic-Entities     (Place (e.g., Detroit, Cali, or "San Francisco, California"))
    □ - Time                          (under minute_mark)
    ⚀ - Time                          (under hour)
    ⚁ - Time                          (under day)
    ⚂ - Time                          (under week)
    ⚃ - Time                          (under month)
    ⚄ - Time                          (under year)
    ⚅ - Time                          (over year)
    ⚇ - Content-Semantic-Entities     (Person (e.g., Barack Obama, Daniel, or George W. Bush))
'''

def friendship_lookup(oauth, source_screen_name, target_screen_name, msg=''):

    #1 request per 5 seconds: https://developer.twitter.com/en/docs/twitter-api/v1/accounts-and-users/follow-search-get-users/api-reference/get-friendships-show
    logger.info('friendship_lookup(): sleeping for 5 seconds' + msg)
    time.sleep(5)

    params = {
        'source_screen_name': source_screen_name,
        'target_screen_name': target_screen_name
    }
    try:
        response = oauth.get('https://api.twitter.com/1.1/friendships/show.json', params=params)
        friendship = json.loads(response.text)['relationship']

        return friendship
    except:
        genericErrorInfo()

    return {}

def fmt_twt_time_to_loc(created_at):
    created_at = datetime.strptime(created_at, '%a %b %d %H:%M:%S %z %Y')

    local_time = datetimeFromUtcToLocal( created_at )
    local_time = datetime.strftime( local_time, '%Y-%m-%d %H:%M:%S' )   

    return local_time

def get_tweet_type(twt):

    if( 'in_reply_to_status_id' not in twt ):
        return ''

    if( twt['in_reply_to_status_id'] is not None ):
        return 'reply'
    elif( 'retweeted_status' in twt ):
        return 'retweet'
    else:
        return 'tweet'

def get_timeline_tweets(oauth, screen_name, user_id='', max_pages=1, following_lookup=True, timeline_startdate='', timeline_scroll_by_hours=None):

    if( max_pages < 0 ):
        return []


    params = {'tweet_mode': 'extended', 'count': 20}
    screen_name = screen_name.strip()
    user_id = user_id.strip()
    
    if( screen_name == '' and user_id == '' ):
        return []

    if( screen_name != '' ):
        params['screen_name'] = screen_name
    elif( user_id != '' ):
        params['user_id'] = user_id


    tweets = []
    dedup_set = set()
    timeline_startdate = '' if timeline_startdate == '' else datetime.strptime( timeline_startdate, '%Y-%m-%d %H:%M:%S' )

    if( isinstance(timeline_scroll_by_hours, int) is False ):
        timeline_startdate = ''


    logger.info('\nget_timeline_tweets():')
    for i in range(max_pages):

        user_id_det = '' if user_id == '' else f' (id: {user_id})'
        logger.info('\tpage: ' + str(i+1) + ' of ' + str(max_pages) + ', for: @' + screen_name + f'{user_id_det}')

        #guess max_id, since_id - start
        if( timeline_startdate != '' ):
            try:
                timeline_next_date = timeline_startdate + timedelta(hours=timeline_scroll_by_hours)
                next_twt_id = gen_post_snowflake_twitter_id(timeline_startdate)

                params.pop('max_id', None)
                params.pop('since_id', None)

                if( timeline_scroll_by_hours > 0 ):
                    params['since_id'] = next_twt_id
                else:
                    params['max_id'] = next_twt_id

                logger.info('\ttimeline_startdate: ' + str(timeline_startdate) + ' (' + str(timeline_scroll_by_hours) + ') -> ' + str(next_twt_id) )

            except:
                genericErrorInfo()
        #guess max_id, since_id - end


        try:
            response = oauth.get("https://api.twitter.com/1.1/statuses/user_timeline.json", params=params)
            timeline = json.loads(response.text)
        except:
            genericErrorInfo()
            

        if( 'errors' in timeline ):
            logger.error( '\terror: ' + str(timeline['errors']) )
            #to conform with 1 request per second rate limit for user auth: https://developer.twitter.com/en/docs/twitter-api/v1/tweets/timelines/api-reference/get-statuses-user_timeline
            time.sleep(1)
            continue

        if( isinstance(timeline, dict) or len(timeline) == 0 ):
            #to conform with 1 request per second rate limit for user auth: https://developer.twitter.com/en/docs/twitter-api/v1/tweets/timelines/api-reference/get-statuses-user_timeline
            time.sleep(1)
            continue
        
        
        #dedup tweets - start
        for twt in timeline:
            
            if( 'id' not in twt ):
                continue

            if( twt['id'] in dedup_set ):
                continue

            dedup_set.add( twt['id'] )
            tweets.append(twt)
        #dedup tweets - end
        logger.info( f'\t{len(tweets)} tweets' )


        if( timeline_startdate == '' ):
            #use default timeline pagination since user is not paginating by time
            params['max_id'] = timeline[-1]['id'] - 1
        else:
            timeline_startdate = timeline_next_date
            logger.info('\tpaginating with datetime: ' + str(timeline_startdate) + '\n' )


        #add bloc key to tweets
        for j in range( len(timeline) ):
            timeline[j].setdefault('bloc', {
                'src_follows_tgt': None,
                'tgt_follows_src': None
            })

        sleep_flag = True
        if( following_lookup is True ):
            #no need to sleep for 1 second since friendship look up sleeps for 5 seconds.
            
            timeline_len = len(timeline)
            for j in range( timeline_len ):
                
                twt = timeline[j]
                if( 'in_reply_to_status_id' not in twt ):
                    continue

                tweet_type = get_tweet_type(twt)
                if( tweet_type not in ['reply', 'retweet'] ):
                    continue

                if( tweet_type == 'reply' ):
                    tgt = twt['in_reply_to_screen_name']
                elif( tweet_type == 'retweet' ):
                    tgt = twt['retweeted_status']['user']['screen_name']
                else:
                    continue

                #skip self
                if( screen_name == tgt ):
                    continue
                
                msg = ', for ' + tweet_type + ', ' + str(j+1) + ' of ' + str(timeline_len)
                relationship = friendship_lookup(oauth, screen_name, tgt, msg=msg)
                sleep_flag = False

                if( len(relationship) != 0 ):
                    twt['bloc']['src_follows_tgt'] = relationship['source']['following']
                    twt['bloc']['tgt_follows_src'] = relationship['source']['followed_by']
                    
        if( sleep_flag ):
            #to conform with 1 request per second rate limit for user auth: https://developer.twitter.com/en/docs/twitter-api/v1/tweets/timelines/api-reference/get-statuses-user_timeline
            time.sleep(1)

    return tweets

def v2_get_timeline_tweets(ostwt, user_id, max_pages=1, max_results=100, timeline_startdate='', timeline_scroll_by_hours=None):

    if( max_pages < 0 ):
        return []

    user_id = user_id.strip()
    if( user_id == '' ):
        return []


    tweets = []
    dedup_set = set()
    user_screen_name = ''
    next_token = None
    timeline_scroll_by_hours = 0 if timeline_scroll_by_hours is None else timeline_scroll_by_hours    
    timeline_startdate = '' if timeline_startdate == '' else datetime.strptime( timeline_startdate, '%Y-%m-%d %H:%M:%S' )

    logger.info('\nv2_get_timeline_tweets():')
    for i in range(max_pages):

        logger.info( f'\tpage: {i+1} of {max_pages} for id: {user_id}{user_screen_name}' )
        if( timeline_startdate != '' ):
            logger.info( f'\tfrom: {timeline_startdate} (timeline_scroll_by_hours: {timeline_scroll_by_hours})' )

        try:
            end_time = None if timeline_startdate == '' else timeline_startdate.strftime('%Y-%m-%dT%H:%M:%S') + 'Z' 
            response = ostwt.get_tweet_timeline(user_id, max_results=max_results, everything=True, pagination_token=next_token, end_time=end_time)
        except:
            genericErrorInfo()

        if( max_pages > 1 ):
            logger.info('\tsleeping for 3 seconds')
            time.sleep(3)

        if( 'meta' not in response or 'data' not in response ):
            logger.info('\tno meta and data keys, breaking')
            break        
        
        v1_tweets = conv_v2_tweets_to_v1(response)
        #dedup tweets - start
        for twt in v1_tweets:
            
            if( 'id' not in twt ):
                continue

            if( twt['id'] in dedup_set ):
                continue

            dedup_set.add( twt['id'] )
            user_screen_name = ' (@' + twt['user']['screen_name'] + ')'
            twt.setdefault('bloc', {'src_follows_tgt': None, 'tgt_follows_src': None})
            tweets.append(twt)
        #dedup tweets - end
        logger.info( '\t{} tweets, {} errors'.format(len(tweets), len(response.get('errors', []))) )


        next_token = response['meta'].get('next_token', None)
        #paginate - start
        if( timeline_startdate != '' and timeline_scroll_by_hours != 0 ):
            timeline_startdate = datetime.strptime( response['data'][-1]['created_at'], '%Y-%m-%dT%H:%M:%S.000Z' )
            timeline_startdate = timeline_startdate + timedelta(hours=timeline_scroll_by_hours)
            next_token = None
            logger.info('\ttime pagination, setting next_token to None')#time pagination and next_token are mutually exclusive

        elif( next_token is None ):
            logger.info('\tno next_token, breaking')
            break
        #paginate - end

        logger.info('')

    return tweets

def get_twt_text_exclusively(txt, entities):

    for ky, val in entities.items():
        for ent in val:
            
            if( 'indices' not in ent ):
                continue

            st, en = ent['indices']
            txt = txt[:st] + ' '*(en - st) + txt[en:]

    return txt

def get_action_glyphs():
    return ['P', 'p', 'π', 'R', 'r', 'ρ', 'T']

def get_delta_glyph(symbols, delta_seconds, blank_mark=60, minute_mark=5):
    
    '''
        Default time symbols
        □ under minute_mark
        ⚀ under hour
        ⚁ under day
        ⚂ under week
        ⚃ under month
        ⚄ under year
        ⚅ over year
    '''

    if( delta_seconds < blank_mark ):
        glyph = symbols['blank_mark']['symbol']
    #elif( delta_seconds < short_pause_mark ):
    #    glyph = '.' * ( (delta_seconds//60) )
    elif( delta_seconds < minute_mark*60 ):
        glyph = symbols['under_minute_mark']['symbol']
    elif( delta_seconds < 3600 ):
        glyph = symbols['under_hour_mark']['symbol']
    elif( delta_seconds < 86400 ):
        glyph = symbols['under_day_mark']['symbol']
    elif( delta_seconds < 604800 ):
        glyph = symbols['under_week_mark']['symbol']
    elif( delta_seconds < 2628000 ):
        glyph = symbols['under_month_mark']['symbol']
    elif( delta_seconds < 31540000 ):
        glyph = symbols['under_year_mark']['symbol']
    else:
        glyph = symbols['over_year_mark']['symbol']

    return glyph

def get_duration_prefix(symbols, cur_time, prev_time, blank_mark, minute_mark):

    seq_diff_time = datetime.strptime( cur_time, '%Y-%m-%d %H:%M:%S' ) - datetime.strptime( prev_time, '%Y-%m-%d %H:%M:%S' )
    #delta_seconds = (seq_diff_time.days*86400) + seq_diff_time.seconds
    delta_seconds = int( seq_diff_time.total_seconds() )

    dur_glyph = get_delta_glyph( symbols, delta_seconds, blank_mark=blank_mark, minute_mark=minute_mark )
    
    return delta_seconds, dur_glyph

def get_pause(symbols, twt, prev_twt, blank_mark, minute_mark, use_src_ref_time=False):

    if( 'in_reply_to_status_id' not in twt ):
        return -1, ''

    source_ref_time = ''
    delta_seconds = -1
    dur_glyph = ''

    if( use_src_ref_time is True ):
        if( twt['in_reply_to_status_id'] is not None ):#reply
            source_ref_time = find_tweet_timestamp_post_snowflake( twt['in_reply_to_status_id'] )
            source_ref_time = datetimeFromUtcToLocal( source_ref_time )
            source_ref_time = datetime.strftime( source_ref_time, '%Y-%m-%d %H:%M:%S' )
            
        elif( 'retweeted_status' in twt ):#retweet
            source_ref_time = twt['retweeted_status']['created_at']
            source_ref_time = datetime.strptime(source_ref_time, '%a %b %d %H:%M:%S %z %Y')
            source_ref_time = datetimeFromUtcToLocal( source_ref_time )
            source_ref_time = datetime.strftime( source_ref_time, '%Y-%m-%d %H:%M:%S' )
        
        elif( prev_twt != '' ):#tweet
            source_ref_time = prev_twt['bloc']['local_time']


    if( use_src_ref_time is True and source_ref_time != '' ):
        #dur_glyph encodes delta between twt (current) and the tweet that was replied to or retweeted
        delta_seconds, dur_glyph = get_duration_prefix( symbols=symbols, cur_time=twt['bloc']['local_time'], prev_time=source_ref_time, blank_mark=blank_mark, minute_mark=minute_mark )
    elif( prev_twt != '' ):
        #dur_glyph encodes delta between twt (current) and prev_twt
        delta_seconds, dur_glyph = get_duration_prefix( symbols=symbols, cur_time=twt['bloc']['local_time'], prev_time=prev_twt['bloc']['local_time'], blank_mark=blank_mark, minute_mark=minute_mark )
         
    return delta_seconds, dur_glyph

def get_bloc_action_seq(symbols, twt, delta_seconds, dur_glyph, content_syntactic_seq=''):

    '''
        UPDATE get_action_glyphs() IF CHANGES
        The ACTION alphabets are
            D - Delete a tweet (moved to Change alphabet)
            f - Follow someone (moved to Change alphabet)
            L - Like a friend's tweet (moved to Change alphabet)
            l - Like a non-friend's tweet (moved to Change alphabet)
            
            P - Reply a friend (can't be checked until friendship relationship assigned)
            p - Reply a non-friend
            π - Reply self
            R - Retweet a friend (can't be checked until friendship relationship assigned)
            r - Retweet a non-friend
            ρ - Retweet self
            T - Tweet
    '''
    if( twt.get('in_reply_to_status_id', None) is not None ):

        #this is a reply
        label = symbols['non_friend_reply']['symbol']
        note = symbols['non_friend_reply']['description']
        
        if( twt.get('in_reply_to_user_id', None) == twt['user']['id'] ):
            label = symbols['self_reply']['symbol']
            note = symbols['self_reply']['description']
            
        elif( twt['bloc']['src_follows_tgt'] is True ):
            label = label = symbols['friend_reply']['symbol']
            note = note = symbols['friend_reply']['description']
            
        action_seq = {
            'seq': label, 
            'note': note, 
            'seq_dets': { 'in_reply_to_screen_name': twt.get('in_reply_to_screen_name', '') }
        }

    elif( 'retweeted_status' in twt ):

        #this is a retweet

        label = symbols['non_friend_rt']['symbol']
        note = symbols['non_friend_rt']['description']
        
        if( twt['retweeted_status']['user']['id'] == twt['user']['id'] ):
            label = symbols['self_rt']['symbol']
            note = symbols['self_rt']['description']

        elif( twt['bloc']['src_follows_tgt'] is True ):
            label = symbols['friend_rt']['symbol']
            note = symbols['friend_rt']['description']

        action_seq = {
            'seq': label, 
            'note': note, 
            'seq_dets': { 'retweet_screen_name': twt['user']['screen_name'] }
        }

    else:

        #this is a tweet 

        label = symbols['tweet']['symbol']
        note = symbols['tweet']['description']

        action_seq = {
            'seq': symbols['tweet']['symbol'], 
            'note': symbols['tweet']['description'], 
            'seq_dets': { 'user_screen_name': twt['user']['screen_name'] }
        }

    action_seq['delta_seconds'] = delta_seconds
    action_seq['seq'] = dur_glyph + action_seq['seq'] + content_syntactic_seq
    return action_seq

def get_bloc_content_sem_sent_seq(symbols, twt, txt_key, delta_seconds, dur_glyph, content_syntactic_seq=''):
    
    '''
        The SENTIMENT alphabets are
            ⋃ - Positive
            - - Neutral
            ⋂ - Negative
    '''


    exclusive_text = ''
    sent_seq = {
        'delta_seconds': -1,
        'seq': '',
        'note': '',
        'seq_dets': {}
    }

    if( txt_key in twt ):
        exclusive_text = get_twt_text_exclusively( twt[txt_key], twt['entities'] )
    
    if( exclusive_text == '' ):
        return sent_seq
    

    try:
        sent = TextBlob(exclusive_text).sentiment.polarity
    except:
        genericErrorInfo()
        return sent_seq
    
    '''
        if( sent >= 0.3333 ):    #[ 0.3333,  1.0000)
            seq = '⋃'
        elif( sent >= -0.3333 ): #[-0.3333,  0.3333)
            seq = '-'
        else:                    #[-1.0000, -0.3333)
            seq = '⋂'
    '''

    if( sent > 0 ):    
        seq = symbols['positive']['symbol']
        sent_seq['note'] = symbols['positive']['description']
    elif( sent == 0 ): 
        seq = symbols['neutral']['symbol']
        sent_seq['note'] = symbols['neutral']['description']
    else:              
        seq = symbols['negative']['symbol']
        sent_seq['note'] = symbols['negative']['description']

    
    #dur_glyph = ''
    sent_seq['delta_seconds'] = delta_seconds
    sent_seq['seq'] = dur_glyph + seq + content_syntactic_seq
    sent_seq['seq_dets'] = { 'sent': sent }
    return sent_seq

def get_bloc_change_seq(symbols, twt, prev_twt, delta_seconds, dur_glyph, fold_start_count=0, include_time=False):

    def add_delete_tweet_change(symbol, symbol_note, prev_u, cur_u, fold_start_count):

        if( 'statuses_count' not in prev_u or 'statuses_count' not in cur_u ):
            return []

        deletion_count = cur_u['statuses_count'] - prev_u['statuses_count']
        if( deletion_count > -1 ):
            return []

        deletion_count = -1 * deletion_count
        label = symbol * deletion_count
    
        return [{
            'label': label[:fold_start_count] if fold_start_count > 0 else label, 
            'note': symbol_note, 
            'details': { 'current_statuses_count': cur_u['statuses_count'], 'previous_statuses_count': prev_u['statuses_count'] }
        }]

    def add_gen_tweet_count_change(key, pos_glyph, neg_glyph, pos_label, neg_label, prev_u, cur_u, fold_start_count):

        if( key not in prev_u or key not in cur_u ):
            return []

        diff = cur_u[key] - prev_u[key]

        if( diff == 0 ):
            return []
        elif( diff > 0 ):
            label = pos_glyph * diff
            note = pos_label
        else:
            diff = (-1) * diff
            label = neg_glyph * diff
            note = neg_label

        return [{
            'label': label[:fold_start_count] if fold_start_count > 0 else label, 
            'note': note, 
            'details': { 'current_' + key: cur_u[key], 'previous_' + key: prev_u[key] }
        }]

    def add_profile_appearance_change(symbol, symbol_note, prev_u, cur_u):

        for key, val in prev_u.items():

            if( key.startswith('profile_') is False ):
                continue

            if( key not in cur_u ):
                continue

            if( prev_u[key] != cur_u[key] ):
                return [{
                    'label': symbol, 
                    'note': symbol_note, 
                    'details': { 'current_' + key: cur_u[key], 'previous_' + key: prev_u[key] }
                }]

        return []

    def add_something_change_v1(key, glyph, prev_u, cur_u):

        if( key not in prev_u or key not in cur_u ):
            return []
        
        if( prev_u[key] != cur_u[key] ):
            return [{
                'label': glyph, 
                'note': key.capitalize() + ' change', 
                'details': { 'current_' + key: cur_u[key], 'previous_' + key: prev_u[key] }
            }]

        return []

    def add_something_change_v2(key, glyph, prev_val, cur_val):
        
        if( prev_val != cur_val ):
            return [{
                'label': glyph, 
                'note': key.capitalize() + ' change', 
                'details': { 'current_' + key: cur_val, 'previous_' + key: prev_val }
            }]

        return []

    def add_geo_change(glyph, prev_u, cur_u):
        
        response = []

        #attempt to check geo-change with place
        if( 'place' in prev_u and 'place' in cur_u ):

            places = [ prev_u['place'], cur_u['place'] ]
            if( places.count(None) == 2 ):
                #both locations are None
                response = []
            
            elif( places.count(None) == 1 ):
                #at least one location is None
                response = [{
                    'label': glyph, 
                    'note': 'Place change',
                    'previous_place': None if places[0] is None else places[0],
                    'current_place': None if places[1] is None else places[1]
                }]
                
            else:
                #both locations are defined
                if( places[0]['id'] == places[1]['id'] ):
                    response = []
                else:
                    response = [{
                        'label': glyph, 
                        'note': 'Place change',
                        'previous_place': places[0],
                        'current_place': places[1]
                    }]

        if( len(response) != 0 ):
            return response
        

        #attempt to check geo-change with coordinate
        if( 'coordinate' in prev_u and 'coordinate' in cur_u ):
            
            coordinates = [ prev_u['coordinate'], cur_u['coordinate'] ]
            if( coordinates.count(None) == 2 ):
                #both locations are None
                response = []
            
            elif( coordinates.count(None) == 1 ):
                #at least one geo is None
                response = [{
                    'label': glyph, 
                    'note': 'Coordinates change',
                    'previous_coordinates': None if coordinates[0] is None else coordinates[0],
                    'current_coordinates': None if coordinates[1] is None else coordinates[1]
                }]

            else:
                #both locations are defined
                if( coordinates[0]['coordinates']['type'] == 'Point' and coordinates[1]['coordinates']['type'] == 'Point' ):                    
                    if( coordinates[0]['coordinates']['coordinates'][0] == coordinates[1]['coordinates']['coordinates'][0] and coordinates[0]['coordinates']['coordinates'][1] == coordinates[1]['coordinates']['coordinates'][1] ):
                        response = []
                    else:                        
                        response = [{
                            'label': glyph, 
                            'note': 'Coordinates change',
                            'previous_coordinates': coordinates[0],
                            'current_coordinates': coordinates[1]
                        }]
                else:
                    response = []

        return response
        
    
    '''
        The default CHANGE alphabets are
            a - Profile appearance change
            D - Delete tweet
            d - Description change
            F - Follow someone
            f - Unfollow someone
            g - Profile location change
            G - geographical location change (see coordinates and place)
            λ - Language change
            L - Liked tweet
            l - Unliked tweet
            n - Name change
            N - Handle change
            s - source change
            u - URL change
            W - Gained followers
            w - Lost followers

        fold_start_count:
            Some alphabets (e.g., D - Deletion) could lead to large labels (e.g., 1000 Ds)
            fold_start_count truncates labels to fold_start_count (this value is the same passed to bloc.util.get_bloc_variant_tf_matrix().block_variant)
        
        To do:
            test add_geo_change()
    '''
    result = {
        'delta_seconds': -1,
        'seq': '',
        'seq_dets': []
    }
    if( 'in_reply_to_status_id' not in twt or prev_twt == '' ):
        return result

    if( 'user' not in twt or 'user' not in prev_twt ):
        return result

    seq = []

    seq += add_something_change_v1( key='screen_name', glyph=symbols['handle_change']['symbol'], prev_u=prev_twt['user'], cur_u=twt['user'] )
    seq += add_something_change_v1( key='name', glyph=symbols['name_change']['symbol'], prev_u=prev_twt['user'], cur_u=twt['user'] )
    seq += add_something_change_v1( key='location', glyph=symbols['profile_location_change']['symbol'], prev_u=prev_twt['user'], cur_u=twt['user'] )
    seq += add_geo_change( glyph=symbols['geo_location_change']['symbol'], prev_u=prev_twt, cur_u=twt )
    seq += add_profile_appearance_change( symbols['profile_appearance_change']['symbol'], symbols['profile_appearance_change']['description'], prev_twt['user'], twt['user'] )
    seq += add_something_change_v1( key='url', glyph=symbols['profile_url_change']['symbol'], prev_u=prev_twt['user'], cur_u=twt['user'] )    
    seq += add_something_change_v1( key='description', glyph=symbols['description_change']['symbol'], prev_u=prev_twt['user'], cur_u=twt['user'] )
    seq += add_something_change_v2( key='source', glyph=symbols['source_change']['symbol'], prev_val=prev_twt.get('source', None), cur_val=twt.get('source', None) )
    seq += add_something_change_v2( key='lang', glyph=symbols['language_change']['symbol'], prev_val=prev_twt.get('lang', None), cur_val=twt.get('lang', None) )

    seq += add_delete_tweet_change( symbols['delete_tweet']['symbol'], symbols['delete_tweet']['description'], prev_twt['user'], twt['user'], fold_start_count )
    seq += add_gen_tweet_count_change( key='friends_count', pos_glyph=symbols['follow_someone']['symbol'], neg_glyph=symbols['unfollow_someone']['symbol'], pos_label=symbols['follow_someone']['description'], neg_label=symbols['unfollow_someone']['description'], prev_u=prev_twt['user'], cur_u=twt['user'], fold_start_count=fold_start_count )    
    seq += add_gen_tweet_count_change( key='favourites_count', pos_glyph=symbols['like_tweet']['symbol'], neg_glyph=symbols['unlike_tweet']['symbol'], pos_label=symbols['like_tweet']['description'], neg_label=symbols['unlike_tweet']['description'], prev_u=prev_twt['user'], cur_u=twt['user'], fold_start_count=fold_start_count )
    seq += add_gen_tweet_count_change( key='followers_count', pos_glyph=symbols['follower_gain']['symbol'], neg_glyph=symbols['follower_loss']['symbol'], pos_label=symbols['follower_gain']['description'], neg_label=symbols['follower_loss']['description'], prev_u=prev_twt['user'], cur_u=twt['user'], fold_start_count=fold_start_count )

    if( len(seq) == 0 ):
        return result
   
    result = {
        'delta_seconds': delta_seconds,
        'seq': ''.join([ l['label'] for l in seq ]),
        'seq_dets': seq
    }
    result['seq'] = '(' + result['seq'] + ')'
    result['seq'] = dur_glyph + result['seq'] if include_time is True else result['seq']

    return result

def get_bloc_content_syn_seq(symbols, tweet, content_syntactic_add_pause=False, txt_key='full_text', gen_rt_content=True, add_txt_glyph=True, delta_seconds=-1, dur_glyph=''):
    
    '''
        The default CONTENT-SYNTACTIC alphabets are:
            E - Media 
            H - Hashtag
            ¤ - Cashtag
            M - Mention of friend (can't be checked until friendship relationship assigned)
            m - Mention of non-friend
            q - Quote URL
            φ - Quote self
            t - Text
            U - URL
    '''

    if( gen_rt_content is False and 'retweeted_status' in tweet ):
        return {
            'seq': '',
            'seq_dets': []
        }

    if( 'retweeted_status' in tweet ):
        twt = tweet['retweeted_status']
    else:
        twt = tweet


    seq = []
    exclusive_text = ''

    if( 'extended_entities' in twt ):
        #see: http://web.archive.org/web/20210812135035/https://developer.twitter.com/en/docs/twitter-api/v1/data-dictionary/object-model/extended-entities
        if( 'media' in twt['extended_entities'] ):
            
            media = [{
                'label': symbols['media']['symbol'], 
                'note': symbols['media']['description'], 
                'details': None
            }]

            seq += media * len( twt['extended_entities']['media'] )

    if( 'entities' in twt ):
        
        for h in twt['entities'].get('hashtags', []):
            seq.append({
                'label': symbols['hashtag']['symbol'], 
                'note': symbols['hashtag']['description'], 
                'details': {'hashtag': h['text']}
            })

        for c in twt['entities'].get('symbols', []):
            seq.append({
                'label': symbols['cashtag']['symbol'], 
                'note': symbols['cashtag']['description'], 
                'details': {'cashtag': c['text']}
            })


        #assume mention is from non-friend
        if( 'user_mentions' in twt['entities'] ):

            mention_cursor = 0
            label = ''
            note = symbols['non_friend_mention']['description']

            if( twt['in_reply_to_status_id'] is None and len(twt['entities']['user_mentions']) != 0 ):
                #this is NOT a reply
                label = symbols['non_friend_mention']['symbol']

            elif( len(twt['entities']['user_mentions']) > 1 ):
                #this is a reply with a mention
                label = symbols['non_friend_mention']['symbol']
                mention_cursor = 1#skip first reply 
                

            '''
                if there are multiple mentions, recall that friendship lookup is done just once for reply or retweet
                by default retweets are (gen_rt_content=True) assigned BLOC labels
                so an checking M here will only apply to replies, and this is already done by action check, so skip M check if( twt['bloc']['src_follows_tgt'] is True ): for now
            '''

            if( label != '' ):

                for i in range(mention_cursor, len(twt['entities']['user_mentions'])):
                    
                    m = twt['entities']['user_mentions'][i]

                    #check if mention is in display text range - start
                    '''
                    #UNSURE if distinction should be made between mentions explicitly added by user vs those added by Twitter for reply chains.
                    #Twitter V1 made a distinction with display_text_range unlike V2
                    if( 'display_text_range' in twt ):
                        st, en = twt['display_text_range']
                        if( twt[txt_key][st:en].lower().find( m['screen_name'].lower() ) == -1 ):
                            #this mention is not visible in text, so skip
                            continue
                    '''
                    #check if mention is in display text range - end


                    seq.append({
                        'label': label,
                        'note': note,
                        'details': {'mention_screen_name': m['screen_name']}
                    })


        
        for u in twt['entities'].get('urls', []):

            #check for self quote - start
            u_screen_name = get_screen_name_frm_status_uri( u['expanded_url'] )

            if( u_screen_name != '' and u['expanded_url'].find('/photo/') != -1 ):
                #this is a link of an image (V2 Twitter API)
                continue
        
            if( u_screen_name == '' ):
                link_label = symbols['url']['symbol']
                link_label_note = symbols['url']['description']
            elif( u_screen_name == twt['user']['screen_name'] ):
                link_label = symbols['self_quote']['symbol']
                link_label_note = symbols['self_quote']['description']
            else:
                link_label = symbols['quote_url']['symbol']
                link_label_note = symbols['quote_url']['description']
            #check for self quote - end

            seq.append({
                'label': link_label, 
                'note': link_label_note, 
                'details': {'url': u['expanded_url']}
            })
    

        if( txt_key in twt ):
            exclusive_text = get_twt_text_exclusively( twt[txt_key], twt['entities'] )
            
            if( 'extended_entities' in twt ):
                exclusive_text = get_twt_text_exclusively( exclusive_text, twt['extended_entities'] )
            

    exclusive_text = exclusive_text.strip()
    if( exclusive_text != '' and add_txt_glyph is True ):
        seq.append({
            'label': symbols['text']['symbol'], 
            'note': symbols['text']['description'], 
            'details': {'exclusive_text': exclusive_text}
        })
    


    result = {
        'seq': ''.join([ l['label'] for l in seq ]),
        'seq_dets': seq
    }

    result['delta_seconds'] = delta_seconds
    
    if( result['seq'] != '' ):
        result['seq'] = dur_glyph + '(' + result['seq'] + ')' if content_syntactic_add_pause is True else '(' + result['seq'] + ')'

    return result

def get_bloc_content_sem_ent_seq(symbols, tweet, content_semantic_add_pause=False, gen_rt_content=True, delta_seconds=-1, dur_glyph=''):
    
    '''
        The CONTENT-SEMENTIC alphabets are:

            ENTITIES
            
            ⚇ - Person (e.g., Barack Obama, Daniel, or George W. Bush)
            ⌖ - Place (e.g., Detroit, Cali, or "San Francisco, California")
            ⋈ - Organization (e.g., Chicago White Sox, IBM)
            x - Product (e.g., Mountain Dew, Mozilla Firefox)
            ⊛ - Other (e.g., Diabetes, Super Bowl 50)
    '''

    entity_type_maps = {
        'Person': symbols['person']['symbol'],
        'Place': symbols['place']['symbol'],
        'Organization': symbols['organization']['symbol'],
        'Product': symbols['product']['symbol'],
        'Other': symbols['other']['symbol']
    }

    #by default content-se is NOT assigned to retweets
    if( gen_rt_content is False and 'retweeted_status' in tweet ):
        return {
            'seq': '',
            'seq_dets': []
        }

    if( 'retweeted_status' in tweet ):
        twt = tweet['retweeted_status']
    else:
        twt = tweet


    seq = []
    if( 'entities' in twt ):
        
        for e in twt['entities'].get('annotations', []):
            if( e['type'] in entity_type_maps ):

                seq.append({
                    'label': entity_type_maps[e['type']], 
                    'note': e['type'], 
                    'details': {'text': e['normalized_text']}
                })

 

    result = {
        'seq': ''.join([ l['label'] for l in seq ]),
        'seq_dets': seq
    }

    result['delta_seconds'] = delta_seconds
    
    if( result['seq'] != '' ):
        result['seq'] = dur_glyph + '(' + result['seq'] + ')' if content_semantic_add_pause is True else '(' + result['seq'] + ')'

    return result

def bloc_segmenter(bloc_info, created_at, local_time, segmentation_type='week_number', days_segment_count=-1):

    bloc_info['local_time'] = datetime.strftime(local_time, '%Y-%m-%d %H:%M:%S')
    bloc_info['week_number'] = format(local_time.year, '04d') + '.' + format(local_time.isocalendar()[1], '03d')


    if( segmentation_type == 'yyyy-mm-dd' ):
        bloc_info['yyyy-mm-dd'] = datetime.strftime(created_at, '%Y-%m-%d')
    
    if( days_segment_count > 0 ):
        
        bloc_info['day_of_year']     = local_time.timetuple().tm_yday
        bloc_info['day_of_year_bin'] = (bloc_info['day_of_year']-1)//days_segment_count

        bloc_info['day_of_year']     = format(local_time.year, '04d') + '.' + format(bloc_info['day_of_year'], '03d')
        bloc_info['day_of_year_bin'] = format(local_time.year, '04d') + '.' + format(bloc_info['day_of_year_bin'], '03d')
        
    bloc_info['segmentation_type'] = segmentation_type

def add_bloc_sequences(tweets, blank_mark=60, minute_mark=5, gen_rt_content=True, add_txt_glyph=True, segmentation_type='week_number', **kwargs):

    def tranfer_dets_for_stream_statuses(twt):
        
        #transfer details for tweets gotten from streams
        #See: http://web.archive.org/web/20210812135100/https://docs.tweepy.org/en/stable/extended_tweets.html
        if( 'extended_tweet' not in twt ):
            return twt

        for ky in ['full_text', 'display_text_range', 'entities', 'extended_entities']:
            if( ky in twt['extended_tweet'] ):
                twt[ky] = twt['extended_tweet'][ky]

        return twt

    def add_bloc_segments(twt, segment_id, bloc_segments):

        twt['bloc']['bloc_sequences_short'] = {}
        for dim, dim_dct in twt['bloc']['bloc_sequences'].items():
            twt['bloc']['bloc_sequences_short'][dim] = dim_dct['seq']

            #segment_id bloc segmenter - start
            bloc_segments['segments'].setdefault( segment_id, {} )

            if( segment_id > bloc_segments['last_segment'] ):
                bloc_segments['last_segment'] = segment_id

            if( dim in bloc_segments['segments'][segment_id] ):
                bloc_segments['segments'][segment_id][dim] += twt['bloc']['bloc_sequences'][dim]['seq']
            else:
                bloc_segments['segments'][segment_id][dim] = twt['bloc']['bloc_sequences'][dim]['seq']         
            #segment_id bloc segmenter - end
    
    def fmt_action_content_syntactic_bloc(symbols, bloc_segments, alph_key):

        #mv all content to behind action, e.g., go from T(qt)T(qt) to TT(qt)(qt)

        time_glyphs = [symb[1]['symbol'] for symb in symbols.items() if symb[0] != 'blank_mark']
        blank_and_time_glyphs = [symbols['blank_mark']['symbol']] + time_glyphs
        time_glyphs = ''.join(time_glyphs)

        for seg_num, segs in bloc_segments.items():
            
            if( alph_key not in segs ):
                return

            new_segs = re.split( f'([{time_glyphs}])', segs[alph_key] )
            final_segs = ''
            
            for c in new_segs:
                
                if( c in blank_and_time_glyphs ):
                    final_segs += c
                    continue

                act_glyphs = ''.join(get_action_glyphs())
                only_act = re.sub(r'\(([^\)]+)\)', '', c)
                only_cnt = re.sub(r'[()' + act_glyphs + ']', '', c)
                only_cnt = only_cnt if only_cnt == '' else f'({only_cnt})'
                final_segs += only_act + only_cnt
            
            segs[alph_key] = final_segs

    def sort_action_words(symbols, bloc_segments, alph_key):

        time_glyphs = [symb[1]['symbol'] for symb in symbols.items() if symb[0] != 'blank_mark']
        time_glyphs = ''.join(time_glyphs)
        act_glyphs = get_action_glyphs()

        for seg_num, segs in bloc_segments.items():
            if( alph_key not in segs ):
                continue
            
            new_act = ''
            prev_act = segs[alph_key]
            prev_act = re.split( f'([(){time_glyphs}])', prev_act )
            
            for w in prev_act:
                
                if( w == '' ):
                    continue

                if( w[0] in act_glyphs ):
                    new_act += ''.join( sorted(w) )
                else:
                    new_act += w
    
            segs[alph_key] = new_act

    kwargs.setdefault('keep_tweets', False)
    kwargs.setdefault('keep_bloc_segments', False)
    kwargs.setdefault('fold_start_count', 5)
    kwargs.setdefault('change_add_pause', False)
    kwargs.setdefault('time_reference', 'previous_tweet')#previous_tweet or reference_tweet
    kwargs.setdefault('sort_action_words', False)
    
    all_bloc_symbols = kwargs.get('all_bloc_symbols', {})

    if( is_symbols_good(all_bloc_symbols) is False ):
        logger.error(f'\nadd_bloc_sequences(): all_bloc_symbols is corrupt, so returning')
        return {}

    days_segment_count = kwargs.get('days_segment_count', -1)
    bloc_alphabets = kwargs.get('bloc_alphabets', ['action', 'content_syntactic', 'content_semantic_entity'])#additional valid bloc_alphabets: change, content_syntactic_with_pauses, action_content_syntactic

    segmentation_type = segmentation_type if segmentation_type in ['week_number', 'day_of_year_bin', 'yyyy-mm-dd'] else 'week_number'
    bloc_segments = {'segments': {}, 'last_segment': '', 'segment_count': 0, 'segmentation_type': segmentation_type}
    use_src_ref_time = True if kwargs['time_reference'] == 'reference_tweet' else False

    if( days_segment_count > 0 ):
        segmentation_type = 'day_of_year_bin'
        bloc_segments['segmentation_type'] = 'day_of_year_bin'
        bloc_segments['days_segment_count'] = days_segment_count

    twt_len = len(tweets)
    for i in range( twt_len ):    
        twt = tweets[i]
        twt = tranfer_dets_for_stream_statuses(twt)
        twt.setdefault('bloc', {'src_follows_tgt': None, 'tgt_follows_src': None})

        #Wed Oct 10 20:19:24 +0000 2018
        created_at = datetime.strptime(twt['created_at'], '%a %b %d %H:%M:%S %z %Y')
        bloc_segmenter( twt['bloc'], created_at, datetimeFromUtcToLocal(created_at), segmentation_type=segmentation_type, days_segment_count=days_segment_count )

    prev_twt = ''
    user_id = ''
    screen_name = ''
    tweets = sorted( tweets, key=lambda x: x['bloc']['local_time'] )
    for i in range( twt_len ):
        
        twt = tweets[i]
        segment_id = twt['bloc'][segmentation_type]
        twt_text_ky = 'full_text' if 'full_text' in twt else 'text'
        user_id = twt['user']['id']
        screen_name = twt['user']['screen_name']

        ex_txt = get_twt_text_exclusively( twt[twt_text_ky], twt['entities'] )
        
        delta_seconds, dur_glyph = get_pause(symbols=all_bloc_symbols['bloc_alphabets']['time'], twt=twt, prev_twt=prev_twt, blank_mark=blank_mark, minute_mark=minute_mark, use_src_ref_time=use_src_ref_time)
        twt['bloc']['bloc_sequences'] = {}

        if( 'action' in bloc_alphabets ):
            twt['bloc']['bloc_sequences']['action'] = get_bloc_action_seq( all_bloc_symbols['bloc_alphabets']['action'], twt, delta_seconds, dur_glyph )

        if( 'content_syntactic' in bloc_alphabets ):
            twt['bloc']['bloc_sequences']['content_syntactic'] = get_bloc_content_syn_seq(all_bloc_symbols['bloc_alphabets']['content_syntactic'], twt, content_syntactic_add_pause=False, txt_key=twt_text_ky, gen_rt_content=gen_rt_content, add_txt_glyph=add_txt_glyph, delta_seconds=delta_seconds, dur_glyph=dur_glyph)

        if( 'content_syntactic_with_pauses' in bloc_alphabets ):
            twt['bloc']['bloc_sequences']['content_syntactic_with_pauses'] = get_bloc_content_syn_seq(all_bloc_symbols['bloc_alphabets']['content_syntactic'], twt, content_syntactic_add_pause=True, txt_key=twt_text_ky, gen_rt_content=gen_rt_content, add_txt_glyph=add_txt_glyph, delta_seconds=delta_seconds, dur_glyph=dur_glyph)

        if( 'content_semantic_entity' in bloc_alphabets ):
            twt['bloc']['bloc_sequences']['content_semantic_entity'] = get_bloc_content_sem_ent_seq( all_bloc_symbols['bloc_alphabets']['content_semantic_entities'], twt, content_semantic_add_pause=False, gen_rt_content=gen_rt_content, delta_seconds=delta_seconds, dur_glyph=dur_glyph)
        
        if( 'content_semantic_sentiment' in bloc_alphabets ):
            twt['bloc']['bloc_sequences']['content_semantic_sentiment'] = get_bloc_content_sem_sent_seq( all_bloc_symbols['bloc_alphabets']['content_semantic_sentiment'], twt, txt_key=twt_text_ky, delta_seconds=delta_seconds, dur_glyph=dur_glyph, content_syntactic_seq='')

        if( 'change' in bloc_alphabets ):
            twt['bloc']['bloc_sequences']['change'] = get_bloc_change_seq( all_bloc_symbols['bloc_alphabets']['change'], twt, prev_twt, delta_seconds=delta_seconds, dur_glyph=dur_glyph, fold_start_count=kwargs['fold_start_count'], include_time=kwargs['change_add_pause'])

        if( 'action_content_syntactic' in bloc_alphabets ):
            tmp_cnt = get_bloc_content_syn_seq(all_bloc_symbols['bloc_alphabets']['content_syntactic'], twt, content_syntactic_add_pause=False, txt_key=twt_text_ky, gen_rt_content=gen_rt_content, add_txt_glyph=add_txt_glyph, delta_seconds=delta_seconds, dur_glyph=dur_glyph)
            twt['bloc']['bloc_sequences']['action_content_syntactic'] = get_bloc_action_seq( all_bloc_symbols['bloc_alphabets']['action'], twt, delta_seconds, dur_glyph, content_syntactic_seq=tmp_cnt['seq'] )

        add_bloc_segments(twt, segment_id, bloc_segments)
        prev_twt = twt
    
    if( 'action_content_syntactic' in bloc_alphabets ):
        fmt_action_content_syntactic_bloc(all_bloc_symbols['bloc_alphabets']['time'], bloc_segments['segments'], 'action_content_syntactic')
    if( 'content_syntactic_with_pauses' in bloc_alphabets ):
        fmt_action_content_syntactic_bloc(all_bloc_symbols['bloc_alphabets']['time'], bloc_segments['segments'], 'content_syntactic_with_pauses')
    
    if( kwargs['sort_action_words'] is True ):
        #must be after fmt_action_content_syntactic_bloc() is called
        sort_action_words( all_bloc_symbols['bloc_alphabets']['time'], bloc_segments['segments'], 'action' )
        sort_action_words( all_bloc_symbols['bloc_alphabets']['time'], bloc_segments['segments'], 'action_content_syntactic' )

    #measure to enable empty tweets have empty bloc - start
    #caution keys tight coupling with twt['bloc']['bloc_sequences']
    aggregate_bloc = {}
    for dim in bloc_alphabets:
        aggregate_bloc[dim] = ''
    #measure to enable empty tweets have empty bloc - start
    

    #combine bloc across multiple segments into single bloc sequence delimited by | 
    bloc_segments['segment_count'] = len(bloc_segments['segments'])
    all_segment_ids = list(bloc_segments['segments'].keys())
    all_segment_ids.sort()

    for segment_id in all_segment_ids:
        
        dimensions = bloc_segments['segments'][segment_id]
        for dim in dimensions:

            aggregate_bloc.setdefault(dim, '')
            if( dimensions[dim] == '' ):
                continue
            aggregate_bloc[dim] += dimensions[dim] + ' | '


    #remove last | which does not have bloc sequences following it
    for dim, bloc_seq in aggregate_bloc.items():
    
        aggregate_bloc[dim] = bloc_seq.strip()
        if( aggregate_bloc[dim].endswith('|') ):
            aggregate_bloc[dim] = bloc_seq.strip()[:-1]

    if( kwargs['keep_bloc_segments'] is False ):
        bloc_segments['segments'] = {}

    result = {
        'bloc': aggregate_bloc,
        'tweets': tweets if kwargs['keep_tweets'] is True else [],
        'bloc_segments': bloc_segments,
        'created_at_utc': datetime.utcnow().isoformat().split('.')[0] + 'Z',
        'screen_name': screen_name,
        'user_id': user_id
    }
    
    return result

def post_proc_bloc_sequences(report, seconds_mark, minute_mark, ansi_code, segmentation_type):

    if( 'tweets' not in report or 'bloc' not in report ):
        return

    tweets = report['tweets']
    aggregate_bloc = report['bloc']

    logger.info( get_timeline_request_dets(report) )
    for dim, bloc_seq in aggregate_bloc.items():

        logger.info(dim + ':')
        
        if( dim == 'action' or dim == 'content_semantic_sentiment' ):
            logger.info( color_bloc_action_str(bloc_seq, ansi_code=ansi_code) )
        else:
            logger.info(bloc_seq)
        
        logger.info('')

    logger.info( get_timeline_key_dets(seconds_mark, minute_mark, segmentation_type) )

def get_timeline_request_dets(report):

    if( 'tweets' not in report or 'bloc' not in report ):
        return ''

    if( len(report['tweets']) == 0 ):
        return ''

    tweets = report['tweets']
    details = ''
    try:
        screen_name = report['screen_name'] if report['screen_name'] != '' else tweets[0]['user']['screen_name']
        st_time = datetime.strptime(tweets[0]['bloc']['local_time'], '%Y-%m-%d %H:%M:%S')
        en_time = datetime.strptime(tweets[-1]['bloc']['local_time'], '%Y-%m-%d %H:%M:%S')
        week_diff = en_time.isocalendar()[1] - st_time.isocalendar()[1]

        delta = en_time - st_time
        delta = '(' + str(delta.days) + ' day(s), ' + str(delta.seconds//3600) + ':' + str( ((delta.seconds//60)%60) ) + '), '
        
        details = '\n@' + screen_name + '\'s BLOC for ' + str(week_diff) + ' week(s), ' + delta + str(len(tweets)) + ' tweet(s) from ' + str(st_time) + ' to ' + str(en_time)
    except:
        genericErrorInfo()
    
    return details

def get_timeline_key_dets(seconds_mark, minute_mark, segmentation_type):
    
    ky_dets = 'action key:\n'
    ky_dets += f'blank: <{seconds_mark} secs, □: <{minute_mark} mins ⚀: <hour,  ⚁: <day,\n⚂:    <week, ⚃: <month, ⚄: <year, ⚅: >year\n| separates {segmentation_type} segments'

    return ky_dets

def get_timeline_tweets_cache_filename(cache_path, screen_name, max_pages, following_lookup, timeline_startdate, timeline_scroll_by_hours):

    cache_path = cache_path.strip()
    if( cache_path.endswith('/') is False ):
        cache_path = cache_path + '/'

    filename = ''
    try:
    
        os.makedirs( cache_path, exist_ok=True )
        
        following_lookup = '1' if following_lookup is True else '0'
        timeline_startdate = timeline_startdate.replace(' ', '_').replace(':', '-')
        timeline_scroll_by_hours = str(timeline_scroll_by_hours)

        filename = cache_path + screen_name + '_' + str(max_pages) + '_' + following_lookup + '_' + timeline_startdate + '_' + timeline_scroll_by_hours + '.json.gz'
    
    except:
        genericErrorInfo()

    return filename

def get_user_bloc(oauth_or_ostwt, screen_name, user_id='', max_pages=1, following_lookup=False, timeline_startdate='', timeline_scroll_by_hours=None, **kwargs):

    kwargs.setdefault('gen_rt_content', True)
    
    kwargs.setdefault('cache_path', '')
    kwargs.setdefault('cache_read', False)
    kwargs.setdefault('cache_write', False)

    kwargs.setdefault('blank_mark', 60)
    kwargs.setdefault('minute_mark', 5)

    kwargs.setdefault('ansi_code', '91m')
    
    tweets = []
    write_cache = True
    prev_now = datetime.now()

    if( screen_name == '' ):
        cache_filename = get_timeline_tweets_cache_filename(kwargs['cache_path'], user_id, max_pages=max_pages, following_lookup=following_lookup, timeline_startdate=timeline_startdate, timeline_scroll_by_hours=timeline_scroll_by_hours)
    else:
        cache_filename = get_timeline_tweets_cache_filename(kwargs['cache_path'], screen_name, max_pages=max_pages, following_lookup=following_lookup, timeline_startdate=timeline_startdate, timeline_scroll_by_hours=timeline_scroll_by_hours)
    

    if( kwargs['cache_path'] != '' and kwargs['cache_read'] is True ):
        
        logger.info('\nget_user_bloc() attempting to read timeline tweets from: ' + cache_filename)
        tweets = getDictFromJsonGZ( cache_filename )
        
        if( len(tweets) == 0 ):
            write_cache = True
            logger.info('\tcache MISS')
        else:
            write_cache = False
            logger.info('\tcache HIT')

    if( len(tweets) == 0 ):

        if( isinstance(oauth_or_ostwt, osometweet.OsomeTweet) ):
            tweets = v2_get_timeline_tweets(oauth_or_ostwt, user_id=user_id, max_pages=max_pages, max_results=kwargs.get('max_results', 100), timeline_startdate=timeline_startdate, timeline_scroll_by_hours=timeline_scroll_by_hours)
        else:
            tweets = get_timeline_tweets(oauth_or_ostwt, screen_name, user_id=user_id, max_pages=max_pages, following_lookup=following_lookup, timeline_startdate=timeline_startdate, timeline_scroll_by_hours=timeline_scroll_by_hours)

    if( cache_filename != '' and kwargs['cache_write'] is True and write_cache ):
        gzipTextFile(cache_filename, json.dumps(tweets, ensure_ascii=False))

    
    delta = datetime.now() - prev_now
    payload = add_bloc_sequences(tweets, **kwargs)
    
    payload['elapsed_time'] = str(delta)
    post_proc_bloc_sequences(payload, kwargs['blank_mark'], kwargs['minute_mark'], kwargs['ansi_code'], kwargs.get('segmentation_type', None))

    return payload

def is_symbols_good(all_bloc_symbols):

    if( len(all_bloc_symbols) == 0 or isinstance(all_bloc_symbols, dict) is False ):
        logger.error('\nis_symbols_good(): len(all_bloc_symbols) == 0 or isinstance(all_bloc_symbols, dict) is False, returning')
        return False

    if( 'bloc_alphabets' in all_bloc_symbols ):
        for alph in ['action', 'time', 'content_syntactic', 'change', 'content_semantic_entities', 'content_semantic_sentiment']:
            
            if( alph not in all_bloc_symbols['bloc_alphabets'] ):
                logger.error( '\nis_symbols_good(): {} alphabet not in {}, returning'.format(alph, all_bloc_symbols['bloc_alphabets'].keys()) )
                return False

            if( len(all_bloc_symbols['bloc_alphabets'][alph]) == 0 ):
                logger.error( "\nis_symbols_good(): len(all_bloc_symbols['bloc_alphabets']['{}']) == 0, returning".format(alph) )
                return False

    return True

def f1_time_function(symbols):
    
    for symb_key, symb_val in symbols.items():
        if( symb_key == 'blank_mark' ):
            continue

        symbols[symb_key]['symbol'] = '.'

def gen_bloc_for_users(screen_names_or_ids, bearer_token, consumer_key, consumer_secret, access_token, access_token_secret, max_pages=1, following_lookup=False, timeline_startdate=datetime.now().strftime('%Y-%m-%d %H:%M:%S'), timeline_scroll_by_hours=None, ngram=1, **kwargs):
    
    kwargs.setdefault('no_screen_name', False)
    bloc_symbols_file = kwargs.get('bloc_symbols_file', None)
    
    bloc_symbols_file = '{}/symbols.json'.format(os.path.dirname(os.path.abspath(__file__))) if bloc_symbols_file is None else bloc_symbols_file
    all_bloc_symbols = getDictFromFile(bloc_symbols_file)
    
    if( is_symbols_good(all_bloc_symbols) is False ):
        logger.warning(f'\ngen_bloc_for_users(): all_bloc_symbols is corrupt (bloc_symbols_file: {bloc_symbols_file}), so returning')
        return []

    if( kwargs.get('time_function', 'f1') == 'f1' ):
        f1_time_function(all_bloc_symbols['bloc_alphabets']['time'])

    kwargs['all_bloc_symbols'] = all_bloc_symbols
    if( bearer_token == '' ):
        oauth_or_ostwt = OAuth1Session(consumer_key, client_secret=consumer_secret, resource_owner_key=access_token, resource_owner_secret=access_token_secret)
    else:
        
        oauth_or_ostwt = osometweet.OsomeTweet( osometweet.OAuth2(bearer_token=bearer_token, manage_rate_limits=False) )
        if( kwargs['no_screen_name'] == False ):
            #screen_names_or_ids consists of screen_names so convert to user_ids and set kwargs['no_screen_name'] = True before calling get_user_bloc
            
            screen_names_or_ids = twitter_v2_user_lookup_ids(oauth_or_ostwt, screen_names_or_ids)
            screen_names_or_ids = [ u['id'] for u in screen_names_or_ids ]
            kwargs['no_screen_name'] = True

    i = 1
    all_users_bloc = []
    src_len = len(screen_names_or_ids)

    for scn_name_or_id in screen_names_or_ids:
        
        #logger.info(str(i) + ' of ' + str(src_len))

        user_id = ''; scn_name = ''
        if( kwargs['no_screen_name'] is True ):
            user_id = scn_name_or_id
        else:
            scn_name = scn_name_or_id

        user_bloc = get_user_bloc(
            oauth_or_ostwt=oauth_or_ostwt,
            screen_name=scn_name,
            user_id=user_id,
            max_pages=max_pages,
            following_lookup=following_lookup,
            timeline_startdate=timeline_startdate,
            timeline_scroll_by_hours=timeline_scroll_by_hours,
            **kwargs
        )
        all_users_bloc.append( user_bloc )

        i += 1

    return all_users_bloc
