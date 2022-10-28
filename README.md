## Behavioral Language for Online Classification (BLOC)
BLOC is a language that represents the behaviors of social media accounts irrespective of class (e.g., human or cyborg or bot) or intent (e.g., malicious or benign). BLOC represents behaviors as words consisting of letters drawn from multiple alphabets (e.g., `action` and `content_syntactic`). BLOC words map to features which aid in the study of behaviors, bot and coordination detection, etc.

Even though BLOC can be applied to other social media accounts, this Python tool supports Twitter exclusively. For a comprehensive description of BLOC, please see the BLOC paper, [A General Language for Modeling Social Media Account Behavior](#). To cite, kindly use:
```
@techreport{nwala_flammini_menczer,
  author={Nwala, Alexander C. and Flammini, Alessandro and Menczer, Filippo},
  institution = {arXiv},
  number = {XXXX.XXXXX},
  title={A General Language for Modeling Social Media Account Behavior},
  type = {Preprint},
  year = {2022}
}
```

## Installation
Option 1:

```bash
$ pip install twitterbloc
```

Option 2:

```bash
$ git clone https://github.com/anwala/bloc.git
$ cd bloc/; pip install .; cd ..; rm -rf bloc;
```

Option 3 (Install inside Docker container): 

```bash
$ docker run -it --rm --name BLOC -v "$PWD":/usr/src/myapp -w /usr/src/myapp python:3.7-stretch bash
$ git clone https://github.com/anwala/bloc.git
$ cd bloc/; pip install .; cd ..; rm -rf bloc;
```

## BLOC example

The image below outlines the BLOC strings for a sequence of three tweets (a reply, an original tweet, and a retweet) by the [`@NASA`](https://twitter.com/nasa) account. Using the `action` alphabet, the sequence can be represented by three single-letter words `p.T.r` separated by dots. Using the `content_syntactic` alphabet, it can be represented by these three words `(Emt)(mmt)(mmmmmUt)` enclosed in parentheses.

<img src="misc/nasa_bloc_timeline.png" alt="BLOC action and content strings for NASA" height="350">

## BLOC Alphabets (Code vs. Paper)

More alphabets are implemented here compared to the BLOC paper ([*A General Language for Modeling Social Media Account Behavior*](https://github.com/anwala/general-language-behavior)). Specifically, this BLOC tool implements these [alphabets](/blob/main/bloc/symbols.json):
* `action`
* `content_syntactic`
* `content_semantic_sentiment`
* `change`
* `time` aka `pause`

The paper introduced the Action (which was combined with Pause aka Time) and Content alphabets. Also note that the Pause symbols implemented here differ from those introduced in the paper:

Pause symbols implemented:
* blank symbol (very short time)
* □ - pause under minute_mark
* ⚀ - pause under hour
* ⚁ - pause under day
* ⚂ - pause under week
* ⚃ - pause under month
* ⚄ - pause under year
* ⚅ - pause over year

Pause symbols introduced in paper:

<img src="misc/f_1.png" alt="BLOC pause function, f_1(delta)" height="100"><br/>
<img src="misc/f_2.png" alt="BLOC pause function, f_2(delta)" height="200">

For both paper and code, the dot (`.`) symbol is used when time granularity is not needed (`--time-function=f1`). Also, one may change the alphabets by supplying a path (e.g., `--bloc-symbols-file=/path/to/my/custom/bloc_symbols.json`) to a JSON file formatted similarly as [alphabets](/blob/main/bloc/symbols.json). However, ensure that there are no duplicate or multi-letter symbols.

## Usage/Examples

### Basic command-line usage:
BLOC supports Twitter v1.1 and v2. For Twitter v1.1, the following command generates BLOC for [`OSoMe_IU`](https://twitter.com/OSoMe_IU/) tweets for a maximum of 4 pages (`-m 4`; 20 tweets per page), and saves the BLOC strings with tweets (`--keep-tweets`) in osome_bloc.json (`-o osome_bloc.json`):
```bash
  $ bloc -m 4 -o osome_bloc.json --keep-tweets --consumer-key="foo" --consumer-secret="foo" --access-token="bar" --access-token-secret="bar" OSoMe_IU
```
<details>
  <summary>Output:</summary>
  
  ```python
  @OSoMe_IU's BLOC for 12 week(s), (84 day(s), 7:14), 80 tweet(s) from 2022-08-03 01:10:44 to 2022-10-26 08:24:49
  action:
  T | ⚂r⚁r⚁r⚀r⚂T⚁r⚀r⚁T⚀T⚁T⚀π⚂r⚂r | ⚂r⚁r⚂T | ⚂r⚂r | ⚁T⚁rp⚂p⚂r⚂T | ⚁T⚂T⚂r | ⚂T⚂r⚀r⚂T | ⚂r⚂T⚁r⚀T⚁p⚁p⚁r⚁p⚁rr⚂T | ⚂T⚁T⚂T | ⚂pr⚁p⚂rrrrrrr⚁p | ⚂T⚁r⚁rrrrrr⚂rr⚁r⚁r⚁r⚁T | ⚂r□r□r□rr⚂T⚂r⚂T | ⚂p 

  change:
  (s)(s)(s)(s) | (s)(λ)(λ) | (s)(s) | (s)(s)(s) | (s)(s) | (s)(s)(s) | (λ)(λ)(s) | (s)(s) | (s) | (s) 

  content_syntactic:
  (Uqt) | (mmmUt)(HmmUt)(mmUφt)(Emmt)(Ut) | (mmmqt) | (EUt)(t)(Ut)(Ut) | (Et)(mUt) | (Ut)(mmqt) | (Ut)(Emt)(mmt)(mmt)(mt)(mUt) | (mmUt)(EUt)(Uqt) | (t)(t)(t) | (Ut)(mqt) | (mUt)(Ut) | (t) 

  content_semantic_entity:


  content_semantic_sentiment:
  ⋃ | ⚂⋃⚁⋃⚁⋃⚀-⚂-⚁⋂⚀⋃⚁⋃⚀⋃⚁⋂⚀⋂⚂⋂⚂⋃ | ⚂⋃⚁⋃⚂⋃ | ⚂-⚂⋃ | ⚁⋂⚁⋃⋂⚂⋃⚂⋃⚂⋃ | ⚁-⚂-⚂⋃ | ⚂-⚂⋃⚀⋃⚂⋃ | ⚂⋃⚂⋃⚁⋃⚀⋃⚁⋃⚁⋃⚁⋃⚁-⚁⋂⋃⚂- | ⚂-⚁⋃⚂⋃ | ⚂-⋃⚁⋂⚂⋂⋃⋃⋃⋃-⋃⚁⋂ | ⚂⋃⚁-⚁⋃⋃-⋃-⋃⚂⋂⋃⚁⋃⚁⋃⚁⋃⚁⋃ | ⚂⋃□-□⋃□-⋃⚂⋃⚂⋃⚂- | ⚂⋃ 

  action key:
  blank: <60 secs, □: <5 mins ⚀: <hour,  ⚁: <day,
  ⚂:    <week, ⚃: <month, ⚄: <year, ⚅: >year
  | separates week_number segments

  write_output(): wrote: osome_bloc.json
  ```
</details>

For Twitter v2 (each page returns a maximum of 100 tweets):
```bash
$ bloc -m 4 -o osome_bloc.json --keep-tweets --bearer-token="foo" OSoMe_IU
```
<details>
  <summary>Output:</summary>
  
  ```python
  @OSoMe_IU's BLOC for 2 week(s), (377 day(s), 21:59), 399 tweet(s) from 2021-10-13 10:25:36 to 2022-10-26 08:24:49
  action:
  T⚁r⚁p⚀p⚂r□p⚂T⚂r | ⚂r⚂T⚁p□r⚁T⚂T⚁r⚁T | ⚁p⚂r | ⚂T⚁r⚁T⚁T⚁T | ⚂T⚁T⚂T⚂T⚁r⚀T | ⚂T⚁T⚂r⚁T⚁p⚂T | ⚂r⚂r | ⚂T⚁p | ⚂T⚂r⚂T | ⚂r⚂rr⚀T⚂p | ⚂T⚁T⚂T⚁T | ⚂T⚁T | ⚃r□r⚂T | ⚂T⚂r | ⚂T⚁T⚁r⚂Tππ⚀π⚂T | ⚂r⚂T⚁r⚁T⚁r⚂T | ⚁T⚁r⚂T⚂πT⚀r⚁r□Tr | ⚂T⚁r⚂T⚁T⚁r⚀π⚁p□ρ | ⚂p⚂r⚂r⚀r□r⚁r | ⚂r⚁r⚁T⚂r⚁T | ⚂T⚂p⚀p⚀p⚂T | ⚂r⚁T⚂πTππππ | ⚂r⚂r | ⚂r⚁r⚁T⚀p⚀T⚂r⚁T | ⚂T⚁r⚁r⚁Tππππππ⚂r⚂T | ⚂r⚂p⚂p□r⚂r⚁Tπ | ⚂r⚁T⚁T⚁T⚁r⚁r⚁p⚁T⚂p | ⚂T⚂r⚁T⚂r⚁r | ⚂T⚁r⚁T⚁πTπππππππ⚁rrr⚁T⚁r⚁rrp⚁rr□r⚁r⚂rr | ⚁T⚁p⚂T□r⚁Tπππππ⚂T⚁T⚂T⚁T | ⚁T⚁r⚁r⚁T⚀T⚁T⚀rr□rr⚁Tπππππ⚁T⚁r⚁r⚁r⚁T⚁T⚁r⚁T⚀r | ⚁r⚀r□r⚁r⚁T⚁r⚁r⚁r⚂T⚀p⚂T⚂p⚂T | ⚁T⚁T⚀T⚂r⚁T⚁T⚁T⚁r⚁r⚁r | ⚂T⚀r⚁rr⚁T⚂T⚁T⚂T⚁r⚁r⚁rr□r | ⚁r⚁T⚁πTπππ⚂Trr⚁r⚁T⚁rrrrr | ⚂T⚁T⚀π⚁p⚁r⚂T⚀p⚀p⚁T | ⚂T⚁T⚁T⚂T⚁T | ⚂r⚂T⚁r⚁T⚁Tπ⚂r | ⚂T⚀p⚁T⚁T⚁p⚂p | ⚂T⚁r□r⚂r | ⚂T⚁T⚁r⚁T | ⚂T⚁T⚂r⚁r⚀r⚁T⚁T⚂T | ⚂r⚁p⚀T⚀T | ⚂r⚁r⚁r⚀r⚂T⚁r⚀r⚁T⚀T⚁T⚀π⚂r⚂r | ⚂r⚁r⚂T | ⚂r⚂r | ⚁T⚁rp⚂p⚂r⚂T | ⚁T⚂T⚂r | ⚂T⚂r⚀r⚂T | ⚂r⚂T⚁r⚀T⚁p⚁p⚁r⚁p⚁rr⚂T | ⚂T⚁T⚂T | ⚂pr⚁p⚂rrrrrrr⚁p | ⚂T⚁r⚁rrrrrr⚂rr⚁r⚁r⚁r⚁T | ⚂r□r□r□rr⚂T⚂r⚂T | ⚂p 

  change:
  (s)(s)(s) | (s)(s)(s) | (s) | (s)(s)(s) | (s)(s) | (s)(s) | (s) | (s)(s) | (s) | (s)(s)(s) | (s)(s)(s) | (s)(s) | (s)(s) | (λ)(λ)(s)(s) | (s)(s)(s)(s)(s)(s) | (s) | (s)(sλ)(λ) | (s)(s)(s)(s)(s) | (s)(s) | (s)(s) | (s) | (s)(s)(s)(s)(s) | (s)(s) | (s)(s)(s)(s)(sλ) | (sλ)(s)(s)(s) | (s)(sλ)(λ)(s)(s)(s)(s) | (s)(s)(s)(s)(s)(s)(s) | (s)(s)(s)(s)(s)(s)(s) | (s)(s)(s)(λ)(λ)(s)(s) | (s)(s)(s) | (s)(s)(s)(s)(s)(s) | (s)(s)(s)(s) | (s)(s)(s)(λ)(sλ)(s) | (λ)(λ)(s)(s) | (s)(s)(λ)(sλ) | (s)(s)(λ)(λ) | (s)(s) | (s)(s) | (s)(s)(s) | (s)(s)(s) | (s)(s)(s)(s) | (s)(λ)(λ) | (s)(s) | (s)(s)(s) | (s)(s) | (s)(s)(s) | (λ)(λ)(s) | (s)(s) | (s) | (s) 

  content_syntactic:
  (qt)(t)(t)(t)(HmmmmUUt) | (EHHHmt)(t)(qqt)(qt)(Uqt) | (t) | (Ut)(qt)(Ut)(qt) | (HUt)(t)(Ut)(Et)(Ut) | (Et)(qt)(EHHmUUt)(mmmt)(mUt) | (mmUt)(mmmmmmmmt) | (Ut)(Ut) | (Ut)(mt) | (mUt)(qt)(Et)(EmUUφt) | (Et)(mmUt) | (mUt) | (HHφt) | (mUt)(EUt)(mmUqt)(mmφUt)(mUt)(HUt)(qt) | (Ut)(mmUt)(mmmmmUt) | (Ut)(mmUt)(Ut)(Emt)(qt) | (UUt)(Emt)(qt)(mmmUt)(q) | (t) | (mUt)(EEEEHHt) | (EHHHmmmmmmmUt)(mmt)(mmt)(t)(mqt) | (HUqt)(Ut)(HUt)(Et)(EHt)(Et)(Et) | (HmUt)(mt)(Et)(EEEEmmmt) | (mmmmmUt)(EHmmmmUt)(EEt)(Et)(Et)(Et)(Et)(Et)(mUt) | (mmt)(t)(Emmmmmmmmmt)(mmmmUt) | (mUt)(mqt)(mmmUt)(t)(mmmmUqt)(t) | (EmmmmUt)(EmmmmUt) | (EmmmmUt)(Ut)(Et)(HmUt)(Et)(Ut)(mUt)(Et)(EmmmmUt)(t)(t)(mmmqt)(Ut) | (HmmmmUt)(mt)(HmUt)(HUt)(t)(Et)(Et)(t)(Et)(EEEEt)(Ut)(EEEEmt)(Ut) | (mUt)(HUt)(qt)(mUt)(qt)(t)(t)(t)(t)(t)(EmmmmUt)(mmUt)(mUt)(mmmUt) | (HHHHHHmUt)(EmmmmUt)(Em)(Ut)(mt)(Hmqt) | (EmmmmUt)(mUt)(mmUt)(Ut)(HUt)(mmUt) | (HmUt)(HmmUt)(HHHHHHUt)(HUt)(HmmUt) | (mmUt)(HmmqUt)(Hmmmmmt)(HUt)(HmmmφUt)(HUt)(qt)(HmUt) | (EmmmmmUt)(EHt)(t)(mmmmt)(mUt)(Emmmmmmmmmt)(mt)(mmUt) | (EmmmmmUt)(E)(Ut)(mUt)(Ut) | (mUt)(φt)(mmUt)(EEEEUt) | (EHHmmmmmUt)(mφt)(mmqt)(Ut)(mm)(mmt) | (EHmmmmmUt) | (EmmmmmUt)(EmmmmUt)(qt) | (Ut)(Hmmqt)(Emt)(HUUUqt)(mmUt) | (Ut)(mUt)(Uqt) | (mmmUt)(HmmUt)(mmUφt)(Emmt)(Ut) | (mmmqt) | (EUt)(t)(Ut)(Ut) | (Et)(mUt) | (Ut)(mmqt) | (Ut)(Emt)(mmt)(mmt)(mt)(mUt) | (mmUt)(EUt)(Uqt) | (t)(t)(t) | (Ut)(mqt) | (mUt)(Ut) | (t) 

  content_semantic_entity:
  (⋈⋈⊛⊛)(⊛⊛) | (⋈)(⊛)(⊛⊛) | (⊛⚇)(⊛⋈⊛)(⊛) | (⊛⊛)(⊛⊛)(⋈⊛)(⊛⊛⊛⊛) | (⊛⋈⊛)(⊛⊛⋈⚇⚇⚇⚇) | (⋈) | (⊛) | (⊛⊛)(⊛)(⊛) | (⚇) | (⊛) | (⊛⌖) | (⊛)(⊛⚇)(⊛)(⋈)(⊛) | (⊛⊛⊛) | (⚇⊛)(⊛)(⚇⚇) | (⊛)(⊛⊛⊛)(⊛⌖) | (⌖⌖⌖⚇) | (⊛⊛)(⊛⊛⊛⊛)(⊛⊛⊛⊛)(⚇)(⚇) | (⌖⊛)(⊛⊛⊛⌖)(⊛⌖)(⊛)(⌖⌖)(⌖⌖)(⌖) | (⊛)(⌖⌖)(⊛⊛) | (⊛)(⊛⊛⊛)(⊛)(⊛)(⊛) | (⊛)(⊛)(⚇) | (⊛⌖⌖)(⌖⊛)(⊛) | (⊛)(⊛) | (⊛⌖)(⌖⊛⊛)(⊛⊛)(⊛⊛)(⊛⊛)(⚇⌖⋈)(⊛) | (⊛)(⊛)(⊛⌖⌖)(⊛)(⊛)(⊛)(⌖⌖)(⊛⊛⊛⊛)(⊛⊛⊛)(⚇)(⊛⋈⊛) | (⊛⊛⚇⊛)(⚇⊛)(⚇⊛)(⚇)(⊛)(⊛)(⋈⊛)(⊛⚇)(⊛⊛)(⊛⚇)(⌖⊛⚇) | (⚇⚇)(⊛⚇)(⚇⊛) | (⊛)(⊛⊛)(⊛⊛) | (⚇⊛)(⋈)(⊛⊛)(⚇⊛)(⚇⊛) | (⚇)(⊛⊛⊛⊛)(⊛⊛⊛)(⊛⊛)(⊛⊛)(⊛⊛)(⚇⊛) | (⋈⋈⚇⚇)(⚇)(⊛⚇)(⊛)(⊛⊛) | (⊛) | (⋈)(⊛⊛) | (⊛)(⊛)(⌖) | (⊛⊛) | (⊛)(⊛) | (⚇⋈)(⊛⊛⊛)(⊛⋈) | (⊛)(⊛⊛)(⊛) | (⚇⊛)(⊛⚇⊛)(⊛)(⊛⊛⊛⊛⊛⊛⊛) | (⚇⊛) | (⊛)(⊛) | (⊛)(⊛⊛) | (⊛) | (⚇)(⊛)(⊛)(⊛) | (⚇⊛)(⊛)(⊛) | (⊛) | (⊛⌖) | (⌖)(⊛) 

  content_semantic_sentiment:
  ⋂⚁-⚁⋂⚀⋃⚂-□⋃⚂⋂⚂⋂ | ⚂-⚂-⚁-□-⚁⋃⚂⋃⚁⋃⚁- | ⚁⋃⚂⋃ | ⚂⋃⚁-⚁⋂⚁⋃⚁⋃ | ⚂-⚁-⚂⋃⚂⋃⚁-⚀⋃ | ⚂⋃⚁-⚂⋃⚁⋃⚁⋃⚂⋃ | ⚂⋂⚂⋂ | ⚂⋃⚁⋃ | ⚂-⚂⋃⚂- | ⚂⋃⚂⋃⋃⚀⋂⚂- | ⚂⋂⚁-⚂⋂⚁⋃ | ⚂⋃⚁⋃ | ⚃⋃□-⚂⋃ | ⚂⋃⚂⋃ | ⚂⋂⚁⋃⚁-⚂⋃⋃⋃⚀⋂⚂⋃ | ⚂⋂⚂⋃⚁-⚁⋃⚁-⚂- | ⚁⋃⚁⋂⚂⋃⚂⋃⋃⚀-⚁⋃□⋃- | ⚂⋃⚁⋃⚂⋂⚁-⚁⋃⚀⋃⚁-□⋂ | ⚂-⚂⋃⚂-⚀⋃□-⚁- | ⚂⋃⚁⋂⚁⋃⚂⋃⚁⋂ | ⚂⋃⚂⋃⚀⋃⚀⋃⚂⋂ | ⚂⋂⚁⋃⚂⋃-⋃⋃⋃⋂ | ⚂⋃⚂⋃ | ⚂-⚁⋃⚁⋃⚀⋃⚀⋂⚂⋂⚁⋃ | ⚂⋃⚁-⚁-⚁⋃⋂⋃⋃⋃--⚂⋃⚂- | ⚂⋃⚂⋃⚂-□⋃⚂⋃⚁⋃- | ⚂⋃⚁-⚁-⚁⋃⚁⋃⚁⋃⚁-⚁-⚂- | ⚂⋃⚂⋃⚁⋃⚂⋃⚁⋃ | ⚂⋃⚁⋃⚁⋂⚁⋃⋃⋃--⋃⋃⋂⋃⚁-⋃⋃⚁-⚁-⚁⋃-⋃⚁⋃-□⋃⚁⋃⚂⋃⋃ | ⚁⋃⚁-⚂⋃□-⚁⋃⋃⋂⋃⋃⋂⚂-⚁⋃⚂-⚁- | ⚁⋂⚁⋂⚁⋃⚁⋂⚀⋃⚁⋃⚀⋃⋃□⋃⋃⚁⋃⋂⋂⋃⋃-⚁⋃⚁⋃⚁⋃⚁-⚁⋃⚁⋃⚁⋂⚁⋃⚀⋃ | ⚁⋂⚀⋃□⋃⚁⋃⚁-⚁⋃⚁-⚁-⚂⋃⚀-⚂⋃⚂-⚂- | ⚁⋃⚁⋃⚀-⚂⋃⚁⋃⚁⋂⚁⋃⚁⋃⚁⋃⚁⋂ | ⚂⋃⚀⋃⚁--⚁-⚂⋃⚁⋃⚂⋃⚁-⚁⋂⚁--□- | ⚁⋃⚁⋂⚁⋃⋃--⋃⚂⋂-⋃⚁⋃⚁-⚁⋃⋂⋃⋃- | ⚂⋃⚁⋂⚀⋂⚁⋃⚁⋂⚂-⚀-⚀⋂⚁⋂ | ⚂⋃⚁-⚁-⚂-⚁- | ⚂⋂⚂⋃⚁-⚁-⚁⋃-⚂- | ⚂⋃⚀-⚁-⚁-⚁-⚂⋂ | ⚂⋃⚁⋃□⋃⚂- | ⚂⋃⚁⋃⚁⋃⚁⋃ | ⚂-⚁⋃⚂⋃⚁⋃⚀⋃⚁⋃⚁⋃⚂- | ⚂-⚁-⚀⋃⚀⋃ | ⚂⋃⚁⋃⚁⋃⚀-⚂-⚁⋂⚀⋃⚁⋃⚀⋃⚁⋂⚀⋂⚂⋂⚂⋃ | ⚂⋃⚁⋃⚂⋃ | ⚂-⚂⋃ | ⚁⋂⚁⋃⋂⚂⋃⚂⋃⚂⋃ | ⚁-⚂-⚂⋃ | ⚂-⚂⋃⚀⋃⚂⋃ | ⚂⋃⚂⋃⚁⋃⚀⋃⚁⋃⚁⋃⚁⋃⚁-⚁⋂⋃⚂- | ⚂-⚁⋃⚂⋃ | ⚂-⋃⚁⋂⚂⋂⋃⋃⋃⋃-⋃⚁⋂ | ⚂⋃⚁-⚁⋃⋃-⋃-⋃⚂⋂⋃⚁⋃⚁⋃⚁⋃⚁⋃ | ⚂⋃□-□⋃□-⋃⚂⋃⚂⋃⚂- | ⚂⋃ 

  action key:
  blank: <60 secs, □: <5 mins ⚀: <hour,  ⚁: <day,
  ⚂:    <week, ⚃: <month, ⚄: <year, ⚅: >year
  | separates week_number segments

  write_output(): wrote: osome_bloc.json
  ```
</details>

For a full list of all the command-line options BLOC offers, run `$ bloc --help`

### Python script usage:

Generate BLOC from list of `OSoMe_IU`'s tweet `dict` objects stored in a list `osome_iu_tweets_lst` with `add_bloc_sequences()`:
```python
from bloc.generator import add_bloc_sequences
from bloc.util import get_default_symbols

all_bloc_symbols = get_default_symbols()
osome_iu_bloc = add_bloc_sequences(osome_iu_tweets_lst, all_bloc_symbols=all_bloc_symbols, bloc_alphabets= ['action', 'content_syntactic'])
```

Sample content of `osome_iu_bloc`:
```json
{
    "bloc": {
        "action": "T | ⚂r⚁r⚁r⚀r⚂T⚁r⚀r⚁T⚀T⚁T⚀π⚂r⚂r | ⚂r⚁r⚂T | ⚂r⚂r | ⚁T⚁rp⚂p⚂r⚂T | ⚁T⚂T⚂r | ⚂T⚂r⚀r⚂T | ⚂r⚂T⚁r⚀T⚁p⚁p⚁r⚁p⚁rr⚂T | ⚂T⚁T⚂T | ⚂pr⚁p⚂rrrrrrr⚁p | ⚂T⚁r⚁rrrrrr⚂rr⚁r⚁r⚁r⚁T | ⚂r□r□r□rr⚂T⚂r⚂T | ⚂p ",
        "content_syntactic": "(Uqt) | (mmmUt)(HmmUt)(mmUφt)(Emmt)(Ut) | (mmmqt) | (EUt)(t)(Ut)(Ut) | (Et)(mUt) | (Ut)(mmqt) | (Ut)(Emt)(mmt)(mmt)(mt)(mUt) | (mmUt)(EUt)(Uqt) | (t)(t)(t) | (Ut)(mqt) | (mUt)(Ut) | (t) "
    },
    "tweets": [],
    "bloc_segments": {
        "segments": {},
        "last_segment": "2022.043",
        "segment_count": 13,
        "segmentation_type": "week_number"
    },
    "created_at_utc": "2022-10-27T23:09:36Z",
    "screen_name": "OSoMe_IU",
    "user_id": 187521608
}
```

<details>
  <summary>Generate BLOC TF-IDF matrix with `get_bloc_variant_tf_matrix()` using four different BLOC models defined in `bloc_settings`. The `bigram` and `word-basic` models were used in the BLOC paper. The rest are experimental: </summary>
  
  ```python
  from bloc.generator import add_bloc_sequences
  from bloc.util import get_default_symbols
  from bloc.util import conv_tf_matrix_to_json_compliant
  from bloc.util import get_bloc_doc_lst
  from bloc.util import get_bloc_variant_tf_matrix

  minimum_document_freq = 2
  bloc_settings = [
      {
          'name': 'm1: bigram',
          'ngram': 2,
          'token_pattern': '[^ |()*]',
          'tf_matrix_norm': 'l1',#set to '' if tf_matrices['tf_matrix_normalized'] not needed
          'keep_tf_matrix': True,
          'set_top_ngrams': True,#set to False if tf_matrices['top_ngrams']['per_doc'] not needed. If True, keep_tf_matrix must be True
          'top_ngrams_add_all_docs': True,#set to False if tf_matrices['top_ngrams']['all_docs'] not needed. If True, keep_tf_matrix must be True
          'bloc_variant': None,
          'bloc_alphabets': ['action', 'content_syntactic']
      },
      {
          'name': 'm2: word-basic',
          'ngram': 1,
          'token_pattern': '[^□⚀⚁⚂⚃⚄⚅. |()*]+|[□⚀⚁⚂⚃⚄⚅.]',
          'tf_matrix_norm': '',
          'keep_tf_matrix': False,
          'sort_action_words': True,
          'bloc_variant': {'type': 'folded_words', 'fold_start_count': 4, 'count_applies_to_all_char': False},
          'bloc_alphabets': ['action', 'content_syntactic']
      },
      {
          'name': 'm3: word-content-with-pauses',
          'ngram': 1,
          'token_pattern': '[^□⚀⚁⚂⚃⚄⚅. |*]+|[□⚀⚁⚂⚃⚄⚅.]',
          'tf_matrix_norm': '',
          'keep_tf_matrix': False,
          'sort_action_words': True,
          'bloc_variant': {'type': 'folded_words', 'fold_start_count': 4, 'count_applies_to_all_char': False},
          'bloc_alphabets': ['action', 'content_syntactic_with_pauses']
      },
      {
          'name': 'm4: word-action-content-session',
          'ngram': 1,
          'token_pattern': '[^□⚀⚁⚂⚃⚄⚅. |*]+|[□⚀⚁⚂⚃⚄⚅.]',
          'tf_matrix_norm': '',
          'keep_tf_matrix': False,
          'sort_action_words': True,
          'bloc_variant': {'type': 'folded_words', 'fold_start_count': 4, 'count_applies_to_all_char': False},
          'bloc_alphabets': ['action_content_syntactic']
      }
  ]
    
  all_bloc_symbols = get_default_symbols()
  for bloc_model in bloc_settings:
      #extract BLOC sequences from list containing tweet dictionaries
      osome_iu_bloc = add_bloc_sequences( osome_iu_tweets_lst, all_bloc_symbols=all_bloc_symbols, bloc_alphabets=bloc_model['bloc_alphabets'], sort_action_words=bloc_model.get('sort_action_words', False) )
      iu_bloom_bloc = add_bloc_sequences( iu_bloom_tweets_lst, all_bloc_symbols=all_bloc_symbols, bloc_alphabets=bloc_model['bloc_alphabets'], sort_action_words=bloc_model.get('sort_action_words', False) )
      bloc_collection = [osome_iu_bloc, iu_bloom_bloc]
      
      #generate collection of BLOC documents
      bloc_doc_lst = get_bloc_doc_lst(bloc_collection, bloc_model['bloc_alphabets'], src='IU', src_class='human')
      tf_matrices = get_bloc_variant_tf_matrix(bloc_doc_lst, tf_matrix_norm=bloc_model['tf_matrix_norm'], keep_tf_matrix=bloc_model['keep_tf_matrix'], min_df=minimum_document_freq, ngram=bloc_model['ngram'], token_pattern=bloc_model['token_pattern'], bloc_variant=bloc_model['bloc_variant'], set_top_ngrams=bloc_model.get('set_top_ngrams', False), top_ngrams_add_all_docs=bloc_model.get('top_ngrams_add_all_docs', False))
      
      #to get JSON serializatable version of tf_matrices: tf_matrices = conv_tf_matrix_to_json_compliant(tf_matrices)
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
      "tf_matrix_normalized": [<SAME STRUCTURE AS tf_matrix>],
      "tf_idf_matrix": [<SAME STRUCTURE AS tf_matrix>],
      "vocab": ["E U", "E m", "E t", "H m", "T ⚀",..., "⚁ r", "⚂ T", "⚂ p", "⚂ r"],
      "token_pattern": "[^ |()*]"
    }
  ```
</details>

<details>
  <summary>A more efficient way to generate BLOC TF-IDF matrix with `get_bloc_variant_tf_matrix()` is outlined below. The previous example requires all BLOC documents (`bloc_doc_lst`) to reside in memory. This could be problematic if we're processing a large collection. To remedy this, we could pass a generator to `get_bloc_variant_tf_matrix()` instead of a list of documents. For this example, we use a custom generator `user_tweets_generator_0()` which requires a gzip file containing tweets of a specific format (each line: `user_id \t [JSON list of tweets]`). You might need to write your own generator function that reads the tweets and generates BLOCs similar to `user_tweets_generator_0()`. However, the workflow is identical after reading tweets and generating BLOC strings: </summary>
  
  ```python
  from bloc.tweet_generators import user_tweets_generator_0
  from bloc.util import get_bloc_variant_tf_matrix

  minimum_document_freq = 2
  bloc_settings = [
    {
      'name': 'm1: bigram',
      'ngram': 2,
      'token_pattern': '[^ |()*]',
      'bloc_variant': None,
      'bloc_alphabets': ['action', 'content_syntactic']
    }
  ]

  for bloc_model in bloc_settings:

      pos_id_mapping = {}
      gen_bloc_params = {'bloc_alphabets': bloc_model['bloc_alphabets']}
      input_files = ['/tmp/ten_tweets.jsonl.gz']

      doc_lst = user_tweets_generator_0(input_files, pos_id_mapping, gen_bloc_params=gen_bloc_params)
      tf_matrices = get_bloc_variant_tf_matrix(doc_lst, min_df=minimum_document_freq, ngram=bloc_model['ngram'], token_pattern=bloc_model['token_pattern'], bloc_variant=bloc_model['bloc_variant'], pos_id_mapping=pos_id_mapping)
  ```
</details>
