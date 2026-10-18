"""Positive YouTube video taxonomy for explicitly named interest shelves."""
import re
from urllib.parse import urlsplit,unquote

_LABELS={
 'music':r'music|guitar|piano|violin|drums|jazz|hip hop|rhythm and blues',
 'gaming':r'gaming|video games?|(?:action|adventure|strategy|racing|simulation|puzzle|role playing|mobile) games?|rpgs?|moba|mmo|clash of clans',
 'sports':r'sports?|football|soccer|basketball|baseball|hockey|tennis|golf|cricket|rugby|boxing|motorsport|volleyball|mixed martial arts|formula 1',
 'science':r'science|physics|astronomy|astrophysics|biology|chemistry|geology|space exploration',
 'history':r'history|historical|archaeology',
 'ancient_history':r'ancient history|ancient civilizations?|archaeology',
 'electronics':r'consumer electronics|electronics|smartphones?|computer hardware',
 'technology':r'technology|computing|programming|software|artificial intelligence',
 'philosophy':r'philosophy|philosophical|stoicism',
 'psychology':r'psychology|psychological|neuroscience',
 'food':r'food|cooking|recipes?|baking',
 'travel':r'travel|tourism|destinations?',
 'animals':r'pets?|animals?|wildlife',
 'nature':r'nature|natural world',
 'mysteries':r'mysteries|unsolved|true crime',
 'vehicles':r'vehicles?|cars?|automotive|motorcycles?',
 'fitness':r'fitness|workouts?|exercise',
 'beauty':r'beauty|makeup|fashion|skincare',
 'business':r'business|finance|financial|investing|economics',
 'news':r'news|politics|political',
 'comedy':r'comedy|humou?r|stand up',
 'screen':r'movies?|films?|television|tv',
}
_CATEGORIES={'music':'10','gaming':'20','sports':'17','animals':'15','travel':'19','vehicles':'2','news':'25','comedy':'23'}
_TOPICS={
 'music':{'Music','Christian_music','Classical_music','Country_music','Electronic_music','Hip_hop_music','Independent_music','Jazz','Music_of_Asia','Music_of_Latin_America','Pop_music','Reggae','Rhythm_and_blues','Rock_music','Soul_music'},
 'gaming':{'Video_game_culture','Action_game','Action-adventure_game','Casual_game','Music_video_game','Puzzle_video_game','Racing_video_game','Role-playing_video_game','Simulation_video_game','Sports_game','Strategy_video_game'},
 'sports':{'Sport','American_football','Baseball','Basketball','Boxing','Cricket','Football','Golf','Ice_hockey','Mixed_martial_arts','Motorsport','Tennis','Volleyball','Professional_wrestling'},
 'science':{'Science','Physics','Chemistry','Biology','Astronomy','Geology'},
 'history':{'History','Ancient_history','Archaeology'},'ancient_history':{'Ancient_history','Archaeology'},
 'technology':{'Technology'},'food':{'Food','Cooking'},'travel':{'Tourism','Travel'},
 'animals':{'Pet','Pets','Animal','Wildlife'},'nature':{'Nature','Natural_environment','Wildlife'},
 'philosophy':{'Philosophy'},'psychology':{'Psychology','Neuroscience'},
 'vehicles':{'Vehicle','Vehicles'},'fitness':{'Physical_fitness'},'beauty':{'Fashion','Physical_attractiveness'},
 'business':{'Business','Finance','Economics'},'news':{'Politics'},'comedy':{'Humour','Humor','Comedy'},
 'screen':{'Film','Television_program','Television','Movies'},
}
# The API's Knowledge/Education/Science-and-Technology buckets are too broad
# for these subjects. Require positive evidence in the video's own public title;
# channel names and description boilerplate cannot establish subject affinity.
_WORDS={
 'science':r'science|scientific|physics|quantum|black holes?|dark matter|astronom\w*|astrophysic\w*|cosmolog\w*|universe|galax\w*|planet\w*|solar system|space exploration|nasa|chemistry|chemical|atoms?|molecules?|biology|biological|living cells?|dna|genetic\w*|evolution|geolog\w*|volcano\w*|paleontolog\w*|dinosaurs?',
 'history':r'history|historical|ancient (?:history|people|civilizations?|rome|egypt|babylon)|archaeolog\w*|roman (?:empire|aqueducts?|concrete|legions?)|egyptian (?:pyramids?|tombs?|pharaohs?)|pyramid\w*|mesopotamia\w*|sumer\w*|medieval|viking\w*|byzantin\w*|ottoman\w*|renaissance|world war|cold war|civil war|napoleon|bronze age|stone age|last ice age|empire\w*|civilizations?|stonehenge|gobekli tepe',
 'ancient_history':r'ancient (?:history|people|civilizations?|rome|egypt|babylon)|archaeolog\w*|roman (?:empire|aqueducts?|concrete|legions?)|egyptian (?:pyramids?|tombs?|pharaohs?)|pyramid\w*|mesopotamia\w*|sumer\w*|bronze age|stone age|last ice age|mayan|ancient maya|maya (?:civilization|ruins|temples|culture)|aztec\w*|inca\w*|neanderthal\w*|prehistor\w*|stonehenge|gobekli tepe',
 'electronics':r'electronics?|smartphones?|phones?|iphone\w*|ipad\w*|macbook\w*|laptops?|tablets?|gpus?|cpus?|processors?|ryzen|nvidia|headphones?|earbuds?|cameras?|televisions?|computer hardware|graphics cards?|ios|ipados|macos|carplay',
 'technology':r'technolog\w*|software|programming|coding|computers?|artificial intelligence|machine learning|linux|cybersecurity|robot\w*',
 'philosophy':r'philosoph\w*|stoic\w*|socrates|plato|aristotle|nietzsche|existential\w*|epistemolog\w*|metaphysic\w*|kant|schopenhauer|ethics',
 'psychology':r'psycholog\w*|cognitive|neuroscience|brain|behavio\w*|mental health|anxiety|depression|trauma|personality|narciss\w*',
 'food':r'food|cook\w*|recipes?|baking|bake|chef|cuisine|pasta|bread|barbecue',
 'travel':r'travel\w*|touris\w*|visiting|destinations?|vacation|sightseeing',
 'animals':r'animals?|wildlife|pets?|dogs?|cats?|birds?|rescue dog|veterinar\w*',
 'nature':r'nature|wildlife|animals?|forest\w*|ocean\w*|rainforest\w*|ecosystem\w*|coral|volcano\w*|glacier\w*',
 'mysteries':r'myster\w*|unsolved|unexplained|disappearance\w*|true crime|detective|cold case',
 'vehicles':r'cars?|vehicles?|automotive|motorcycles?|engines?|automobiles?|driving|electric vehicles?',
 'fitness':r'fitness|workout\w*|exercise\w*|strength training|weightlifting|yoga|pilates',
 'beauty':r'beauty|makeup|fashion|skincare|cosmetics?|hairstyles?',
 'business':r'business|financ\w*|investing|investment\w*|investor\w*|econom\w*|inflation|stocks|stock market|entrepreneur\w*|accounting',
 'news':r'politic\w*|election\w*|news|parliament|congress',
 'comedy':r'comedy|comedian\w*|stand up|humou?r|sketch comedy',
 'screen':r'movies?|films?|cinema|television|film trailer|tv series',
}

def _has(text,terms):return bool(re.search(r'\b(?:'+terms+r')\b',text))

def _text(value):
    import unicodedata
    value=unicodedata.normalize('NFKD',str(value)).encode('ascii','ignore').decode().casefold()
    return re.sub(r'[^a-z0-9]+',' ',value).strip()

def matches_title(title,wanted):
    """A playlist lacks video taxonomy; admit only its own subject evidence."""
    if wanted not in _LABELS or not isinstance(title,str):return False
    title=_text(title[:512])
    if wanted=='science' and _has(title,r'science fiction|sci fi|samsung|galaxy (?:s[0-9]+|z|tab|watch|buds)'):return False
    return _has(title,_WORDS.get(wanted,_LABELS[wanted]))

def family(label):
    text=_text(label)
    if re.search(r'\b(?:board games?|game shows?)\b',text):return None
    found=[key for key,terms in _LABELS.items() if _has(text,terms)]
    if 'ancient_history' in found and 'history' in found:found.remove('history')
    return found[0] if len(found)==1 else None

def taxonomy(raw):
    """Retain bounded public classification/title evidence, never account data."""
    if not isinstance(raw,dict):return None
    snippet=raw.get('snippet',{});details=raw.get('topicDetails',{})
    category=snippet.get('categoryId') if isinstance(snippet,dict) else None
    topics=details.get('topicCategories',[]) if isinstance(details,dict) else []
    topics=[x for x in topics if isinstance(x,str)] if isinstance(topics,list) else []
    if not isinstance(category,str):category=''
    if not category and not topics:return None
    title=snippet.get('title','') if isinstance(snippet,dict) else ''
    return {'snippet':{'categoryId':category,'title':title[:512] if isinstance(title,str) else ''},'topicDetails':{'topicCategories':topics[:32]}}

def matches(raw,wanted):
    data=taxonomy(raw)
    if wanted not in _LABELS or not data:return False
    if wanted in _CATEGORIES and data['snippet']['categoryId']==_CATEGORIES[wanted]:return True
    topics=set()
    for link in data['topicDetails']['topicCategories']:
        try:parsed=urlsplit(link)
        except ValueError:continue
        if parsed.scheme!='https' or parsed.hostname!='en.wikipedia.org' or not parsed.path.startswith('/wiki/'):continue
        topics.add(unquote(parsed.path[6:]))
    title=_text(data['snippet']['title'])
    if wanted=='science' and _has(title,r'science fiction|sci fi|samsung|galaxy (?:s[0-9]+|z|tab|watch|buds)'):return False
    if wanted in _WORDS and (data['snippet']['categoryId'] in ('10','20') or topics&_TOPICS['gaming']):return False
    return bool(topics&_TOPICS.get(wanted,set())) or (wanted in _WORDS and matches_title(title,wanted))
