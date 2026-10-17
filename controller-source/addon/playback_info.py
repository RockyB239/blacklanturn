"""Title-safe playback metadata. Native fields remain usable without any lookup."""
def name(value):return str(value or '').strip().casefold()

def playback_identity(item):
    if item.get('type')=='episode' or isinstance(item.get('season'),int) and isinstance(item.get('episode'),int) and item['season']>=0 and item['episode']>=0:
        show=name(item.get('showtitle') or item.get('tvshowtitle'))
        return ('episode',show,item.get('season'),item.get('episode')) if show and isinstance(item.get('season'),int) and isinstance(item.get('episode'),int) and item['season']>=0 and item['episode']>=0 else None
    title=name(item.get('title'))
    return ('movie',title,item.get('year',0)) if title else None

def cast_text(people):
    result=[];seen=set()
    for person in people or []:
        if not isinstance(person,dict):continue
        who=str(person.get('name') or '').strip();role=str(person.get('role') or person.get('character') or '').strip()
        if not who or (name(who),name(role)) in seen:continue
        seen.add((name(who),name(role)));result.append(who+(' — '+role if role else ''))
    return '\n'.join(result)

def playback_info_fields(current,target=None,details=None):
    target=target or {};details=details or {};identity=playback_identity(current)
    matched=bool(identity and playback_identity(details)==identity)
    source=details if matched else {}
    plot=source.get('plot') or current.get('plot') or ''
    people=list(source.get('cast') or [])+list(source.get('guest_stars') or [])
    heading='Episode cast' if identity and identity[0]=='episode' else 'Cast'
    if not cast_text(people):
        people=current.get('cast') or [];heading='Cast'
    if not cast_text(people) and identity and playback_identity(target)==identity:
        people=target.get('cast') or [];heading='Cast'
        plot=plot or target.get('plot') or ''
    if not cast_text(people) and identity and identity[0]=='episode' and target.get('filetype')=='directory' and name(target.get('title'))==identity[1]:
        people=target.get('cast') or [];heading='Series cast'
    fields={'title':str(current.get('title') or ''),'showtitle':str(current.get('showtitle') or ''),'season':str(current.get('season',-1)),'episode':str(current.get('episode',-1)),'year':str(current.get('year',0)),'plot':str(plot),'cast':cast_text(people),'castLabel':heading if cast_text(people) else ''}

    seen=set();selected=[]
    for person in people:
        if not isinstance(person,dict) or not name(person.get('name')) or name(person['name']) in seen:continue
        seen.add(name(person['name']));selected.append(person)
        if len(selected)==6:break
    from live_core import person_identity
    identities={};person_details={}
    for candidate in source.get('people') or []:
        who=name(candidate.get('title') or candidate.get('label'))
        identity=person_identity(candidate.get('file',''))
        if who and identity:
            identities.setdefault(who,set()).add(identity);person_details[identity]=candidate
    for i in range(1,7):
        person=selected[i-1] if i<=len(selected) else {}
        thumb=str(person.get('thumbnail') or person.get('thumb') or person.get('profile_path') or '')
        if thumb.startswith('/') and not thumb.startswith('//'):thumb='https://image.tmdb.org/t/p/w185'+thumb
        matches=identities.get(name(person.get('name')),set())
        identity=next(iter(matches)) if len(matches)==1 else ''
        fields['cast'+str(i)+'.id']=identity
        fields['cast'+str(i)+'.bio']=str(person_details.get(identity,{}).get('plot') or '')
        fields.update({'cast'+str(i)+'.name':str(person.get('name') or ''),'cast'+str(i)+'.role':str(person.get('role') or person.get('character') or ''),'cast'+str(i)+'.thumb':thumb})
    return fields
