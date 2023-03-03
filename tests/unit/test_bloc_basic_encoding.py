import unittest

from bloc.generator import add_bloc_sequences
from bloc.util import get_default_symbols
from bloc.util import getDictFromJsonGZ

class TestBLOC(unittest.TestCase):
    
    fst_tweets = getDictFromJsonGZ('./sample-tweets/tweets_0.json.gz')
    sec_tweets = getDictFromJsonGZ('./sample-tweets/tweets_1.json.gz')

    @staticmethod
    def remove_bloc_frm_tweets(tweets):
        [t.pop('bloc') for t in tweets]

    def test_basic_use(self):
        
        all_bloc_symbols = get_default_symbols()
        tweet_order = 'NoOp'#Tweets already in reverse order, so no need to reverse them again
        bloc_alphabets = ['action', 'content_syntactic', 'change', 'content_syntactic', 'content_semantic_entity', 'content_semantic_sentiment']

        for u in [TestBLOC.fst_tweets, TestBLOC.sec_tweets]:
            
            TestBLOC.remove_bloc_frm_tweets(u['tweets'])
            current_bloc = add_bloc_sequences(u['tweets'], all_bloc_symbols=all_bloc_symbols, bloc_alphabets=bloc_alphabets, tweet_order=tweet_order)
            
            for alph in bloc_alphabets:
                cur_bloc = current_bloc['bloc'][alph]
                ref_bloc = u['bloc'][alph]
                print(ref_bloc)
                self.assertEqual( cur_bloc, ref_bloc, f'cur_bloc ≠ ref_bloc' )
            

if __name__ == '__main__':
    unittest.main()