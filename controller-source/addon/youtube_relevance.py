"""Positive YouTube video taxonomy for explicitly named interest shelves."""
import re
from urllib.parse import urlsplit,unquote

_LABELS={
 'music':r'music|guitar|piano|violin|drums|jazz|hip hop|rhythm and blues',
 'gaming':r'gaming|video games?|(?:action|adventure|strategy|racing|simulation|puzzle|role playing) games?|moba|mmo|clash of clans',
 'sports':r'sports?|football|soccer|basketball|baseball|hockey|tennis|golf|cricket|rugby|boxing|motorsport|volleyball|mixed martial arts|formula 1',
}
_CATEGORIES={'music':'10','gaming':'20','sports':'17'}
_TOPICS={
 'music':{'Music','Christian_music','Classical_music','Country_music','Electronic_music','Hip_hop_music','Independent_music','Jazz','Music_of_Asia','Music_of_Latin_America','Pop_music','Reggae','Rhythm_and_blues','Rock_music','Soul_music'},
 'gaming':{'Video_game_culture','Action_game','Action-adventure_game','Casual_game','Music_video_game','Puzzle_video_game','Racing_video_game','Role-playing_video_game','Simulation_video_game','Sports_game','Strategy_video_game'},
 'sports':{'Sport','American_football','Baseball','Basketball','Boxing','Cricket','Football','Golf','Ice_hockey','Mixed_martial_arts','Motorsport','Tennis','Volleyball','Professional_wrestling'},
}

def family(label):
    text=re.sub(r'[^a-z0-9]+',' ',str(label).casefold()).strip()
    if re.search(r'\b(?:board games?|game shows?)\b',text):return None
    found=[key for key,terms in _LABELS.items() if re.search(r'\b(?:'+terms+r')\b',text)]
    return found[0] if len(found)==1 else None

def taxonomy(raw):
    """Retain only public classification fields, never titles or account data."""
    if not isinstance(raw,dict):return None
    snippet=raw.get('snippet',{});details=raw.get('topicDetails',{})
    category=snippet.get('categoryId') if isinstance(snippet,dict) else None
    topics=details.get('topicCategories',[]) if isinstance(details,dict) else []
    topics=[x for x in topics if isinstance(x,str)] if isinstance(topics,list) else []
    if not isinstance(category,str):category=''
    if not category and not topics:return None
    return {'snippet':{'categoryId':category},'topicDetails':{'topicCategories':topics}}

def matches(raw,wanted):
    data=taxonomy(raw)
    if wanted not in _CATEGORIES or not data:return False
    if data['snippet']['categoryId']==_CATEGORIES[wanted]:return True
    for link in data['topicDetails']['topicCategories']:
        try:parsed=urlsplit(link)
        except ValueError:continue
        if parsed.scheme!='https' or parsed.hostname!='en.wikipedia.org' or not parsed.path.startswith('/wiki/'):continue
        if unquote(parsed.path[6:]) in _TOPICS[wanted]:return True
    return False
