"""Reproduce duration-gap repair separately from frozen event-progress-1/2."""
import ast
import json
from pathlib import Path
import build_candidates as base
import build_zero_candidates as zero

HERE=Path(__file__).resolve().parent
METHODS='''\tdef _seed_progress_length(self, meta):
\t\t# This item's Kodi metadata duration is already seconds. It is only a
\t\t# fallback for callbacks queued until after Stop discards native timing.
\t\tif self.scrobble_sent or self.onPlayBackStopped_ran or not self._progress_owns_playback(): return
\t\tif getattr(self, '_progress_length_contradicted', False): return
\t\tif (_progress_number(self.media_length) or 0) > 0 or not isinstance(meta, dict): return
\t\tvalue = meta.get('duration')
\t\tif isinstance(value, bool): return
\t\tlength = _progress_number(value)
\t\tif length is not None and length > 0:
\t\t\tself.media_length = length
\t\t\tself._progress_length_fallback = True

\tdef _accept_progress_length(self, value):
\t\tif isinstance(value, bool): return
\t\tlength = _progress_number(value)
\t\tif length is None or length <= 0: return
\t\t# The first native value supersedes approximate metadata in either
\t\t# direction; later native reads keep the established maximum policy.
\t\tif getattr(self, '_progress_length_fallback', False):
\t\t\tself.media_length = length
\t\t\tcurrent = _progress_number(self.current_time)
\t\t\tpending = getattr(self, '_progress_pending_seek', None)
\t\t\tif ((current is not None and current > length)
\t\t\t\t\tor (pending is not None and pending[0] > length)):
\t\t\t\tself._progress_length_contradicted = True
\t\telse:
\t\t\tself.media_length = max(_progress_number(self.media_length) or 0, length)
\t\tself._progress_length_fallback = False
\t\t# A contradicted snapshot stays blocked until position is accepted too.

'''

def patch(raw):
 s=zero.patch(raw).decode().replace('\r\n','\n')
 s=base.replace_once(s,'\tdef _sample_progress(self):',METHODS+'\tdef _sample_progress(self):')
 s=base.replace_once(s,'\t\t\tposter, thumb, season_poster, fanart, banner, clearart, clearlogo, discart, meta = self.getMeta(meta)\n','\t\t\tposter, thumb, season_poster, fanart, banner, clearart, clearlogo, discart, meta = self.getMeta(meta)\n\t\t\tself._seed_progress_length(meta)\n')
 s=base.replace_once(s,'\t\t\tlength = _progress_number(self.getTotalTime())\n\t\t\tif length is not None and length > 0: self.media_length = max(self.media_length, length)','\t\t\tself._accept_progress_length(self.getTotalTime())')
 s=base.replace_once(s,'\t\t\tlength = _progress_number(self.getTotalTime())\n\t\t\tif length is not None and length > 0: self.media_length = max(_progress_number(self.media_length) or 0, length)','\t\t\tself._accept_progress_length(self.getTotalTime())')
 # A callback can disprove a rounded metadata denominator without supplying
 # the true duration. Keep the absolute intent but withhold progress writes.
 s=base.replace_once(s,'\t\tif length and position > length: return',"""\t\tif length and position > length:
\t\t\tif not getattr(self, '_progress_length_fallback', False): return
\t\t\tself.media_length = 0
\t\t\tself._progress_length_contradicted = True""")
 s=base.replace_once(s,'\tdef _sendFinishedItemState(self):\n\t\tself._sample_progress()',"""\tdef _sendFinishedItemState(self):
\t\tself._sample_progress()
\t\tif getattr(self, '_progress_length_contradicted', False):
\t\t\t# Unknown only because this item's accepted seek disproved metadata.
\t\t\t# Preserve the old resume/history until a native denominator is known.
\t\t\tself.scrobble_sent = True
\t\t\treturn False, getSetting('scrobble.source')""")
 s=base.replace_once(s,'\t\tif not self.av_started_ran:\n',"\t\tif not self.av_started_ran and not getattr(self, '_progress_length_contradicted', False):\n")
 # Preserve the existing heartbeat cadence; only withhold invalid payloads.
 start=s.index('\tdef keepAlive(self):');end=s.index('\tdef _start_skip_intro_lookup',start)
 region=s[start:end]
 for credential in ('scrob','punchplay'):
  region=base.replace_once(region,'if self.'+credential+'Credentials and ',"if not getattr(self, '_progress_length_contradicted', False) and self."+credential+'Credentials and ')
 s=s[:start]+region+s[end:]
 # A native denominator shorter than the accepted target invalidates that
 # pending acknowledgment window. Only a validated native position resolves it.
 s=base.replace_once(s,'\t\tif self.media_length > 0 and position > self.media_length: return\n',"""\t\tif self.media_length > 0 and position > self.media_length: return
\t\tif (getattr(self, '_progress_length_contradicted', False)
\t\t\t\tand not getattr(self, '_progress_length_fallback', False) and self.media_length > 0):
\t\t\tpending = getattr(self, '_progress_pending_seek', None)
\t\t\tif pending is not None and pending[0] > self.media_length:
\t\t\t\tself._progress_pending_seek = None
""")
 start=s.index('\tdef _sample_progress(self):');end=s.index('\tdef getWatchedPercent(self):',start)
 region=s[start:end]
 region=base.replace_once(region,'\t\tself.current_time = position\n',"""\t\tself.current_time = position
\t\tif self.media_length > 0 and not getattr(self, '_progress_length_fallback', False):
\t\t\tself._progress_length_contradicted = False
""")
 s=s[:start]+region+s[end:]
 s=base.replace_once(s,'\t\tself._progress_seek_received = True\n',"""\t\tif self.media_length > 0 and not getattr(self, '_progress_length_fallback', False):
\t\t\tself._progress_length_contradicted = False
\t\tself._progress_seek_received = True
""")
 for name in ('getWatchedPercent','onPlayBackPaused','onPlayBackResumed'):
  start=s.index('\tdef '+name+'(');end=s.find('\tdef ',start+1)
  if end < 0:end=len(s)
  region=s[start:end]
  indent='\t\t\t'
  region=base.replace_once(region,indent+'self._sample_progress()\n',indent+"self._sample_progress()\n"+indent+"if getattr(self, '_progress_length_contradicted', False): return"+(' 0' if name=='getWatchedPercent' else '')+'\n')
  s=s[:start]+region+s[end:]
 # End must still clear the playlist/window and run its established refresh.
 start=s.index('\tdef onPlayBackEnded(self):');end=s.index('\tdef onPlayBackError(self):',start)
 region=s[start:end];write_start=region.index('\t\t\tBookmarks().reset(');write_end=region.index('\t\t\ttry:\n\t\t\t\tplayingfile',write_start)
 writes=region[write_start:write_end]
 region=region[:write_start]+"\t\t\tif getattr(self, '_progress_length_contradicted', False):\n\t\t\t\tself.scrobble_sent = True\n\t\t\telse:\n"+''.join('\t'+line if line.strip() else line for line in writes.splitlines(keepends=True))+region[write_end:]
 s=s[:start]+region+s[end:]
 start=s.index('\tdef onPlayBackError(self):');end=s.index('\tdef onPlayBackPaused(self):',start)
 region=s[start:end]
 region=base.replace_once(region,'\t\tBookmarks().reset(self.current_time, self.media_length, self.name, self.year)',"\t\tif not getattr(self, '_progress_length_contradicted', False):\n\t\t\tBookmarks().reset(self.current_time, self.media_length, self.name, self.year)")
 s=s[:start]+region+s[end:]
 ast.parse(s)
 return s.replace('\n','\r\n').encode()

if __name__=='__main__':
 manifest={'patch':'event-progress-3','path':'resources/lib/modules/player.py','duration_fallback':'current-item metadata.duration seconds; first valid native value supersedes it','contradicted_fallback':'contradicted metadata retains absolute intent and withholds duration-dependent writes until a consistent native duration/position snapshot','variants':{}}
 for version,(path,member,expected) in base.SOURCES.items():
  raw=path.read_bytes();assert base.sha(raw)==expected
  previous=zero.patch(raw);result=patch(raw)
  target=HERE/'duration-candidate'/version/'player.py';target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(result)
  manifest['variants'][version]={'before_sha256':base.sha(raw),'previous_sha256':base.sha(previous),'after_sha256':base.sha(result),'file':str(target.relative_to(HERE))}
 (HERE/'manifest-duration.json').write_text(json.dumps(manifest,indent=2)+'\n')
 print(json.dumps(manifest,indent=2))
