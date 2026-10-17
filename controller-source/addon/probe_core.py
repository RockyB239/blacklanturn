"""Throwaway probe safety checks and two-clip transition state."""
from pathlib import Path

def isolated_paths(expected, profile, temp):
    root=Path(expected).resolve()
    return Path(profile).resolve()==root/'userdata' and Path(temp).resolve()==root/'temp'

class EpisodeTransition:
    def __init__(self):
        self.episode=1
        self.cancelled=False
    def tick(self,remaining,episode):
        if self.cancelled or self.episode!=1 or episode!=1:
            return 'continue'
        if remaining<=0:
            self.episode=2
            return 'next'
        return 'show' if remaining<=10 else 'continue'
    def cancel(self):
        self.cancelled=True

def catalogue_indices(items,section,genre='All',saved=()):
    kind={'Movies':'Movie','Shows':'TV'}.get(section)
    return [i for i,item in enumerate(items)
            if (kind is None or item['type']==kind)
            and (genre=='All' or item['genre']==genre)
            and (section!='My Stuff' or item['id'] in saved)]

def wheel_route(focus,direction,rows):
    if 10<=focus<=15:
        return 'focus',max(10,min(15,focus+direction))
    for row in rows:
        if focus in row:
            pos=max(0,min(len(row)-1,row.index(focus)+direction))
            return 'focus',row[pos]
    return 'vertical','down' if direction>0 else 'top'

class HoverScroll:
    def __init__(self):
        self.control=None
        self.due=0
    def tick(self,now,control,mouse):
        if not mouse or control not in (700,701,710,711,712,713,720,721):
            self.control=None
            return None
        if control!=self.control:
            self.control=control
            self.due=now+.35
            return None
        if now>=self.due:
            self.due=now+.3
            return control
        return None
