## Behavioral Language for Online Classification (BLOC)
The aggregate behavior of an arbitrary social media user is not random.The Behavioral Language for Online Classification (BLOC) provides an alphabet system for characterizing the acts of social media users across multiple dimensions such as action, content, target, etc. Through such characterization behavioral patterns (aka features) emerge which aid in the study of the dynamics of behavior of social media users, coordination detection, bot identification etc.

[More on BLOC](https://github.iu.edu/anwala/bloc/wiki)
## Installation
Option 1:
```
$ git clone https://github.iu.edu/anwala/bloc.git
$ cd bloc/; pip install .; cd ..; rm -rf bloc;
```
Option 2 (Install inside Docker container): 

```
$ docker run -it --rm --name BLOC -v "$PWD":/usr/src/myapp -w /usr/src/myapp python:3.7-stretch bash
$ git clone https://github.iu.edu/anwala/bloc.git
$ cd bloc/; pip install .; cd ..; rm -rf bloc;
```

## BLOC Alphabets (Code vs. Paper)

More alphabets are implemented here compared to the BLOC intro paper ([*A General Language for Modeling Social Media Account Behavior*](https://github.com/anwala/general-language-behavior)). Specifically, this BLOC tool implements these alphabets:
* Action
* Content-Syntactic
* Content-Semantic-Sentiment
* Change
* Time

The paper introduced the Action (which was combined with Time) and Content alphabets. Also note that the Time symbols implemented here differ from those introduced in the paper:

Time symbols implemented:
* blank symbol (very short time)
* □ - Time (under minute_mark)
* ⚀ - Time (under hour)
* ⚁ - Time (under day)
* ⚂ - Time (under week)
* ⚃ - Time (under month)
* ⚄ - Time (under year)
* ⚅ - Time (over year)

Time symbols introduced in paper:

<img src="misc/f_1.png" alt="BLOC time function, f_1(delta)" height="100"><br/>
<img src="misc/f_2.png" alt="BLOC time function, f_2(delta)" height="200">

## Usage/Examples
### (Selected) Command line parameters
```
bloc [options] --access-token "foo" --access-token-secret "foo" --consumer-key "bar" --consumer-secret "bar" screen_names_or_ids

positional arguments:
  screen_names_or_ids                               Twitter screen_name(s) or user_id(s) to generate BLOC. If user_ids set --no-screen-name.

optional arguments:
  --access-token                                    Twitter API access-token
  --access-token-secret                             Twitter API access-token-secret
  --consumer-key                                    Twitter API consumer-key
  --consumer-secret                                 Twitter API consumer-secret
  -h, --help                                        Show this help message and exit

  --cache-path=''                                   Path to save timeline tweets.
  --cache-read=False                                Attempt to read timeline tweets from cache-path. Default is False
  --cache-write=False                               Write timeline tweets to cache-path. Default is False
  --following-lookup=False                          Check following (distinguish between friend/non-friend).
  --label-rt=False                                  For Content BLOC, assign BLOC sequence to retweets. Default is OFF.
  --log-file=''                                     Log output filename
  --log-format=''                                   Log print format, see: https://docs.python.org/3/howto/logging-cookbook.html
  --log-level=info                                  Log level. Options: {critical,error,warning,info,debug,notset}
  -m, --max-pages=1                                 The maximum number of user Timeline pages (20 tweets/page) to extract tweets.
  --short-pause=False                               Use dots to mark minute pauses when --seconds-mark >= 60
  --minute-mark=5                                   Actions done under --minute-mark are assigned the □ prefix
  --no-screen-name=False                            "screen_names_or_ids" contains user_ids and not screen_names
  -o, --output                                      Output file
  --seconds-mark=60                                 Actions done under --seconds-mark are assigned blank prefix
  --timeline-startdate=today(YYYY-MM-DD HH:MM:SS)   Extract tweets published from --timeline-startdate (YYYY-MM-DD HH:MM:SS).
  --timeline-scroll-by-hours                        Starting at --timeline-startdate, scroll up (positive hours) or down (negative hours) timeline by this value to retrieve timeline tweets.
```
### Basic command-line usage:
Generate BLOC for [`OSoMe_IU`](https://twitter.com/OSoMe_IU/) tweets from a maximum of 4 pages (`-m 4`; 20 tweets per page), save BLOC strings with tweets (`--keep-tweets`) in osome_bloc.json (`-o osome_bloc.json`):
  ```
  bloc -m 4 -o osome_bloc.json --consumer-key="foo" --consumer-secret="foo" --access-token="bar" --access-token-secret="bar" OSoMe_IU
  ```
### Python script usage:
* Generate BLOC from list of `OSoMe_IU`'s tweets (`osome_iu_tweets_lst`) with [`add_bloc_sequences()`](https://github.iu.edu/anwala/bloc/blob/cb610921aa4a65c342baf0c089a07b6fadf7c286/bloc/generator.py#L543):
  ```
  from bloc.generator import add_bloc_sequences
  osome_iu_bloc = add_bloc_sequences(osome_iu_tweets_lst)
  ```
  Sample content of `osome_iu_bloc`:
  ```
  {
    "bloc": {
        "content_syntactic": "(Et)(Ut)(mUt) | (mUt)(Ut) | (HmUφqt)(mmqt) | (mUt)(t)(Ut) | (Ut)(mqt)(Ut)(t) | (Ut)(Ut) | (HHmmqt)(EEHmUt)(HHUUt)(HmmmmmmUt)(t)(Ut)(Ut)(HUt)(EHmmmmmUt)(EHt)(EHt)(EHt)(EHt)(EHt)(EHt)(Hmmmqt) | (HUt)(Ut) | (Ut)(t) | (t)(mUqt)(EHmmUt) | (Hmqt)(qt)(Et)(t)(t) | (t)(UUt)(t) | (UUt)(t)(mUt) ",
        "action": "T⚁p⚂T | ⚁T□r⚂T | ⚂r⚁r⚁T⚂r⚁T⚀r | ⚂r⚁T⚂r⚂p⚁T | ⚂r⚀T⚁T⚁T⚁r⚁r⚂p | ⚂r⚂r⚁r⚁r⚂T□T | ⚂r⚁T⚁Tρρ⚁T⚀T⚁p□r⚀ρTρρρρρρ⚁r⚂r□r⚁T⚁r | ⚂T⚂T | ⚂T⚂T | ⚃r⚁r | ⚂r⚂r⚁p⚁T⚀T | ⚂T⚁r⚁T⚁T⚁r⚂r⚁ρ□p | ⚂r⚁r⚂p⚂T⚁p | ⚂T⚂r⚂p⚁T ",
        "action_post_ref_time": "T⚁p⚂T | ⚁T⚁r⚂T | ⚀r⚁r⚁T⚁r⚁T⚁r | ⚁r⚁T⚁r⚁p⚁T | □r⚀T⚁T⚁T⚁r⚁r⚀p | ⚁r⚁r⚂r⚀r⚂T□T | ⚁r⚁T⚁Tρρ⚁T⚀T⚁p⚁rρTρρρρρρ⚁r⚁r⚁r⚁T⚁r | ⚂T⚂T | ⚂T⚂T | ⚁r⚁r | ⚁r⚀r⚀p⚁T⚀T | ⚂T⚁r⚁T⚁T⚁r⚁r⚂ρ⚁p | ⚁r⚀r⚁p⚂T⚁p | ⚂T⚁r⚁p⚁T "
    },
    "tweets": [],
    "bloc_segments": {
        "segments": {},
        "last_segment": 30,
        "segment_count": 14,
        "segmentation_type": "week_number"
    },
    "created_at_utc": "2021-08-02T17:44:45Z",
    "screen_name": "OSoMe_IU",
    "user_id": "187521608"
  }
  ```
* Generate BLOC TF-IDF matrix with [`get_bloc_variant_tf_matrix()`](https://github.iu.edu/anwala/bloc/blob/cb610921aa4a65c342baf0c089a07b6fadf7c286/bloc/util.py#L544) using four different BLOC models defined in `bloc_settings`, 
  ```
  from bloc.generator import add_bloc_sequences
  from bloc.util import get_bloc_doc_lst
  from bloc.util import get_bloc_variant_tf_matrix

  minimum_document_freq = 2
  bloc_settings = [
    {
      'name': 'm1: bigram',
      'ngram': 2,
      'token_pattern': '[^ |()*]',
      'bloc_variant': None,
      'dimensions': ['action', 'content_syntactic']
    },
    {
      'name': 'm2: word-basic',
      'ngram': 1,
      'token_pattern': '[^□⚀⚁⚂⚃⚄⚅ |()*]+|[□⚀⚁⚂⚃⚄⚅]',
      'bloc_variant': {'type': 'folded_words', 'fold_start_count': 4, 'count_applies_to_all_char': False},
      'dimensions': ['action', 'content_syntactic']
    },
    {
      'name': 'm3: word-content-with-pauses',
      'ngram': 1,
      'token_pattern': '[^□⚀⚁⚂⚃⚄⚅ |*]+|[□⚀⚁⚂⚃⚄⚅]',
      'bloc_variant': {'type': 'folded_words', 'fold_start_count': 4, 'count_applies_to_all_char': False},
      'dimensions': ['action', 'content_syntactic_with_pauses']
    },
    {
      'name': 'm4: word-action-content-session',
      'ngram': 1,
      'token_pattern': '[^□⚀⚁⚂⚃⚄⚅ |*]+|[□⚀⚁⚂⚃⚄⚅]',
      'bloc_variant': {'type': 'folded_words', 'fold_start_count': 4, 'count_applies_to_all_char': False},
      'dimensions': ['action_content_syntactic']
    }
  ]

  for bloc_model in bloc_settings:

    #extract BLOC sequences from list containing tweet dictionaries
    osome_iu_bloc = add_bloc_sequences( osome_iu_tweets_lst, bloc_alphabets=bloc_model['dimensions'] )
    iu_bloom_bloc = add_bloc_sequences( iu_bloom_tweets_lst, bloc_alphabets=bloc_model['dimensions'] )
    bloc_collection = [osome_iu_bloc, iu_bloom_bloc]

    #generate collection of BLOC documents
    bloc_doc_lst = get_bloc_doc_lst(bloc_collection, bloc_model['dimensions'], src='IU', src_class='human')
    tf_matrices = get_bloc_variant_tf_matrix(bloc_doc_lst, min_df=minimum_document_freq, ngram=bloc_model['ngram'], token_pattern=bloc_model['token_pattern'], bloc_variant=bloc_model['bloc_variant'])
  ```
  Sample annotated & abbreviated content of `tf_matrices`:
  ```
  {
    "tf_matrix": [
        {
            "id": 0,
            "tf_vector": [0.0, 1.0, 1.0,...,31.0, 28.0,1.0]
        },
        {
            "id": 1,
            "tf_vector": [1.0, 0.0,..., 55.0, 0.0, 3.0]
        }
    ],
    "tf_matrix_normalized": "<SAME STRUCTURE AS tf_matrix>",
    "tf_idf_matrix": "<SAME STRUCTURE AS tf_matrix>",
    "vocab": ["EEE+Ut", "EEHmUt", "EHmmUt",..., "⚁", "⚂", "⚃"],
    "token_pattern": "[^□⚀⚁⚂⚃⚄⚅ |()*]+|[□⚀⚁⚂⚃⚄⚅]"
  }
  ```
* A more efficient way to generate BLOC TF-IDF matrix with [`get_bloc_variant_tf_matrix()`](https://github.iu.edu/anwala/bloc/blob/cb610921aa4a65c342baf0c089a07b6fadf7c286/bloc/util.py#L544): The previous example requires all BLOC documents (`bloc_doc_lst`) to reside in memory. This could be problematic if we're processing a large collection. To remedy this, we could pass a generator to `get_bloc_variant_tf_matrix()` instead of a list of documents. For this example, we use a custom generator ([`user_tweets_generator_0()`](https://github.iu.edu/anwala/bloc/blob/fa013033069c7116f7ed2a97e9fb19cf9fe95cea/bloc/tweet_generators.py#L7)) which requires a gzip file containing tweets of a specific format (each line: `user_id \t [JSON list of tweets]`). You might need to write your own generator function that reads the tweets and generates BLOCs similar to [`user_tweets_generator_0()`](https://github.iu.edu/anwala/bloc/blob/fa013033069c7116f7ed2a97e9fb19cf9fe95cea/bloc/tweet_generators.py#L7). However, the workflow is identical after reading tweets and generating BLOC strings:
  ```
    from bloc.tweet_generators import user_tweets_generator_0
    from bloc.util import get_bloc_variant_tf_matrix

    minimum_document_freq = 2
    bloc_settings = [
      {
        'name': 'm1: bigram',
        'ngram': 2,
        'token_pattern': '[^ |()*]',
        'bloc_variant': None,
        'dimensions': ['action', 'content_syntactic']
      }
    ]

    for bloc_model in bloc_settings:

        pos_id_mapping = {}
        gen_bloc_params = {'bloc_alphabets': bloc_model['dimensions']}
        input_files = ['/tmp/ten_tweets.jsonl.gz']

        doc_lst = user_tweets_generator_0(input_files, pos_id_mapping, gen_bloc_params=gen_bloc_params)
        tf_matrices = get_bloc_variant_tf_matrix(doc_lst, min_df=minimum_document_freq, ngram=bloc_model['ngram'], token_pattern=bloc_model['token_pattern'], bloc_variant=bloc_model['bloc_variant'], pos_id_mapping=pos_id_mapping)
  ```
