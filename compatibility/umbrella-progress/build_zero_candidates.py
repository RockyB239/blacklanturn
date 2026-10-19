"""Reproduce the reviewed event sampler plus explicit-zero resume clearing.

Outputs stay separate from the frozen event-progress-1 candidates until review.
"""
import ast
import hashlib
import json
from pathlib import Path
import build_candidates as base

HERE=Path(__file__).resolve().parent

def patch(raw):
 s=base.patch(raw).decode().replace('\r\n','\n')
 s=base.replace_once(s,'\t\tself._progress_seek_received = True\n','\t\tself._progress_seek_received = True\n\t\tself._progress_seek_target = position\n')
 s=base.replace_once(s,'''\tdef _sendFinishedItemState(self):
\t\tself._sample_progress()
\t\tBookmarks().reset(self.current_time, self.media_length, self.name, self.year)''','''\tdef _sendFinishedItemState(self):
\t\tself._sample_progress()
\t\t# Only an accepted exact-zero seek can clear this item's old resume.
\t\t# Failed starts and unknown-duration streams keep their existing behavior.
\t\tclear_zero = (getattr(self, '_progress_seek_target', None) == 0
\t\t\t\tand self.current_time == 0 and self.media_length > 0)
\t\tBookmarks().reset(self.current_time, self.media_length, self.name, self.year, clear_zero=clear_zero)''')
 # Limit the new remote operation to the existing configured Trakt gate in the
 # terminal writer. Other providers and normal nonzero requests stay unchanged.
 tree=ast.parse(s);player=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Player')
 terminal=next(n for n in player.body if isinstance(n,ast.FunctionDef) and n.name=='_sendFinishedItemState')
 lines=s.splitlines(True);method=''.join(lines[terminal.lineno-1:terminal.end_lineno])
 old='''\t\tif self.traktCredentials and _remote_playback_enabled(_scrobble_source, '1', 'trakt.markwatched'):
\t\t\tBookmarks().set_scrobble(self.current_time, self.media_length, self.media_type, self.imdb, self.tmdb, self.tvdb, self.season, self.episode, already_watched=self.watched_during_playback)'''
 new='''\t\tif self.traktCredentials and _remote_playback_enabled(_scrobble_source, '1', 'trakt.markwatched'):
\t\t\tif clear_zero:
\t\t\t\t# Trakt rejects pause progress below 1%. Reuse its existing resume-only
\t\t\t\t# reset after refreshing the playback ID; watched history is untouched.
\t\t\t\ttrakt.sync_playbackProgress(forced=True)
\t\t\t\ttrakt.scrobbleReset(imdb=self.imdb, tmdb=self.tmdb, tvdb=self.tvdb, season=self.season, episode=self.episode, refresh=False, clear_local=True)
\t\t\telse:
\t\t\t\tBookmarks().set_scrobble(self.current_time, self.media_length, self.media_type, self.imdb, self.tmdb, self.tvdb, self.season, self.episode, already_watched=self.watched_during_playback)'''
 method=base.replace_once(method,old,new)
 s=''.join(lines[:terminal.lineno-1])+method+''.join(lines[terminal.end_lineno:])
 s=base.replace_once(s,"\tdef reset(self, current_time, media_length, name, year='0'):","\tdef reset(self, current_time, media_length, name, year='0', clear_zero=False):")
 s=base.replace_once(s,"if getSetting('bookmarks') != 'true' or media_length == 0 or current_time == 0: return", "if getSetting('bookmarks') != 'true' or media_length == 0: return\n\t\t\tif current_time == 0 and not (clear_zero and (_progress_number(media_length) or 0) > 0): return")
 ast.parse(s)
 return s.replace('\n','\r\n').encode()

if __name__=='__main__':
 manifest={'patch':'event-progress-2','path':'resources/lib/modules/player.py','variants':{}}
 for version,(path,member,expected) in base.SOURCES.items():
  raw=path.read_bytes();assert base.sha(raw)==expected
  frozen=base.patch(raw);result=patch(raw)
  target=HERE/'zero-candidate'/version/'player.py';target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(result)
  manifest['variants'][version]={'before_sha256':base.sha(raw),'previous_sha256':base.sha(frozen),'after_sha256':base.sha(result),'file':str(target.relative_to(HERE))}
 (HERE/'manifest-zero.json').write_text(json.dumps(manifest,indent=2)+'\n')
 print(json.dumps(manifest,indent=2))
