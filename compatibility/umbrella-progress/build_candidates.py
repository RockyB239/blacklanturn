"""Build reviewed per-version player overlays from retained private evidence.

This utility reads source only, never a live profile. Outputs stay in candidate/.
"""
import ast
import hashlib
import json
from pathlib import Path
import zipfile

HERE = Path(__file__).resolve().parent
SOURCES = {
 '6.7.90': (HERE / 'upstream/6.7.90/player.py', None, '7fb46ee4747234fa5253f92bf43436dd2ea92475ed735db338dd5696e2c9cdd8'),
 '6.7.92': (HERE / 'upstream/6.7.92/player.py', None, '2e3397e4ea496690edb1b2db023d47c5c3f040cc21e7f86ec5a5800e1f9f6889')}

def sha(raw): return hashlib.sha256(raw).hexdigest()

def replace_once(source, old, new):
 assert source.count(old) == 1, (source.count(old), old[:100])
 return source.replace(old, new)

NUMBER = '''def _progress_now():
	return time.monotonic()


def _progress_number(value):
	"""Kodi timing must be finite and nonnegative; zero is a valid seek."""
	try:
		value = float(value)
		if value >= 0 and value < float('inf'): return value
	except (TypeError, ValueError, OverflowError): pass
	return None


'''

METHODS = '''	def _progress_owns_playback(self):
		# _playback_path is Kodi's resolved getPlayingFile(), never plugin metadata.
		if self.media_type is None: return False
		try:
			path = self.getPlayingFile()
			return not self._playback_path or not path or path == self._playback_path
		except RuntimeError:
			# Stop can discard the native file and clock; retain this item's cache.
			return True

	def _sample_progress(self):
		# Only called from existing playback/callback sampling sites. No poller.
		current = _progress_number(self.current_time)
		length = _progress_number(self.media_length)
		self.current_time = current if current is not None else 0
		self.media_length = length if length is not None else 0
		if self.scrobble_sent or not self._progress_owns_playback(): return
		try:
			length = _progress_number(self.getTotalTime())
			if length is not None and length > 0: self.media_length = max(self.media_length, length)
		except RuntimeError: pass
		try:
			position = _progress_number(self.getTime())
		except RuntimeError: return
		if position is None: return
		if self.media_length > 0 and position > self.media_length: return
		pending = getattr(self, '_progress_pending_seek', None)
		if pending is not None:
			target, started = pending
			# A callback can precede Kodi's updated getTime. Accept the destination
			# or real elapsed playback near it, including a paused exact target.
			elapsed = max(0, _progress_now() - started)
			if not target - 1 <= position <= target + elapsed + 1: return
			self._progress_pending_seek = None
		self.current_time = position

'''

SEEK = '''	def onPlayBackSeek(self, time, seekOffset):
		if self.scrobble_sent or self.onPlayBackStopped_ran or not self._progress_owns_playback(): return
		position = _progress_number(time)
		if position is None: return
		position /= 1000.0
		try:
			length = _progress_number(self.getTotalTime())
			if length is not None and length > 0: self.media_length = max(_progress_number(self.media_length) or 0, length)
		except RuntimeError: pass
		length = _progress_number(self.media_length)
		if length and position > length: return
		# Kodi supplies an absolute destination in milliseconds. The relative
		# seekOffset cannot reconstruct position reliably, especially backward.
		self.current_time = position
		self._progress_seek_received = True
		self._progress_pending_seek = (position, _progress_now())
'''


def patch(raw):
 s = raw.decode().replace('\r\n','\n')
 s = replace_once(s, 'def _remote_playback_enabled(', NUMBER + 'def _remote_playback_enabled(')
 s = replace_once(s, '\tdef getWatchedPercent(self):', METHODS + '\tdef getWatchedPercent(self):')
 s = replace_once(s, '''\t\t\tif self.isPlayback():
\t\t\t\ttry:
\t\t\t\t\tposition = self.getTime()
\t\t\t\t\tif position != 0: self.current_time = position
\t\t\t\t\ttotal_length = self.getTotalTime()
\t\t\t\t\tif total_length > 0: self.media_length = max(self.media_length, total_length)
\t\t\t\texcept: pass''', '\t\t\tself._sample_progress()')
 s = replace_once(s, '''\t\t\t\ttry:
\t\t\t\t\tself.current_time = self.getTime()
\t\t\t\t\t_total = self.getTotalTime()
\t\t\t\t\tif _total > 0: self.media_length = max(self.media_length, _total)
\t\t\t\texcept: pass''', '\t\t\t\tself._sample_progress()')
 s = replace_once(s, 'if self.av_started_ran or self.media_type is None: return', 'if self.av_started_ran or self.media_type is None or self.onPlayBackStopped_ran or self.scrobble_sent: return')
 s = replace_once(s, "if self.offset != '0' and self.playback_resumed is False:", "if self.offset != '0' and self.playback_resumed is False and not getattr(self, '_progress_seek_received', False):")
 s = replace_once(s, "\t\t\ttry:\n\t\t\t\tself.seekTime(self.offset)\n\t\t\texcept:\n\t\t\t\tlog_utils.log('Exception trying to seekTime() offset: %s'% self.offset, level=log_utils.LOGDEBUG)\n\t\t\tself.playback_resumed = True", "\t\t\t# The user may seek or Stop during the resume lookup/delay.\n\t\t\tif not getattr(self, '_progress_seek_received', False) and not self.onPlayBackStopped_ran and not self.scrobble_sent:\n\t\t\t\ttry:\n\t\t\t\t\tself.seekTime(self.offset)\n\t\t\t\texcept:\n\t\t\t\t\tlog_utils.log('Exception trying to seekTime() offset: %s'% self.offset, level=log_utils.LOGDEBUG)\n\t\t\t\tself.playback_resumed = True")
 s = replace_once(s, '\t\t\t\t\tself.seekTime(self.offset)\n', "\t\t\t\t\tself.seekTime(self.offset)\n\t\t\t\t\t# Native seek acknowledgement can arrive after this callback.\n\t\t\t\t\tif not getattr(self, '_progress_seek_received', False):\n\t\t\t\t\t\tposition = _progress_number(self.offset)\n\t\t\t\t\t\tif position is not None:\n\t\t\t\t\t\t\tself.current_time = position\n\t\t\t\t\t\t\tself._progress_pending_seek = (position, _progress_now())\n")
 s = replace_once(s, '''\t\ttry:
\t\t\tself.current_time = self.getTime()
\t\t\tself.media_length = self.getTotalTime()
\t\texcept: pass''', '\t\tself._sample_progress()')
 s = replace_once(s, 'try: _start_percent = round((float(self.offset) / self.getTotalTime()) * 100, 2) if self.playback_resumed and self.getTotalTime() > 0 else 0', 'try: _start_percent = round((self.current_time / self.media_length) * 100, 2) if self.media_length > 0 else 0')
 assert s.count('current_time=(self.offset if self.playback_resumed else 0), total_time=self.getTotalTime()') == 3
 s = s.replace('current_time=(self.offset if self.playback_resumed else 0), total_time=self.getTotalTime()', 'current_time=self.current_time, total_time=self.media_length')
 s = replace_once(s, '\tdef onPlayBackSeek(self, time, seekOffset):\n\t\tseekOffset /= 1000\n', SEEK)
 s = replace_once(s, '\tdef _sendFinishedItemState(self):\n', '\tdef _sendFinishedItemState(self):\n\t\tself._sample_progress()\n')
 # Stop already owns its duplicate-close gate. Pause/resume must not reopen a
 # closed Player or write the next file's native time to this item's IDs.
 for name in ('Paused', 'Resumed'):
  marker = "\t\tlog_utils.log('onPlayBack%s callback', level=log_utils.LOGDEBUG)\n" % name
  s = replace_once(s, marker, marker + '\t\tif self.scrobble_sent or self.onPlayBackStopped_ran or not self._progress_owns_playback(): return\n')
 s = replace_once(s, '''\t\t\ttotal_time = self.getTotalTime()
\t\t\tif total_time <= 0: return
\t\t\tpause_percent = round((self.getTime() / total_time) * 100, 2)''', '''\t\t\tself._sample_progress()
\t\t\ttotal_time = self.media_length
\t\t\tif total_time <= 0: return
\t\t\tpause_percent = round((self.current_time / total_time) * 100, 2)''')
 s = replace_once(s, '''\t\t\ttotal_time = self.getTotalTime()
\t\t\tif total_time <= 0: return
\t\t\tresume_position = self.getTime() or self.current_time''', '''\t\t\tself._sample_progress()
\t\t\ttotal_time = self.media_length
\t\t\tif total_time <= 0: return
\t\t\tresume_position = self.current_time''')
 # The pause snapshot is shared by every enabled provider, as it already is
 # for percent. Do not read a possibly discarded native clock per provider.
 s = s.replace('current_time=self.getTime(), total_time=total_time)', 'current_time=self.current_time, total_time=total_time)')
 ast.parse(s)
 return s.replace('\n','\r\n').encode()

if __name__ == '__main__':
 manifest = {'patch': 'event-progress-1', 'path': 'resources/lib/modules/player.py', 'variants': {}}
 for version, (path, member, expected) in SOURCES.items():
  if member:
   with zipfile.ZipFile(path) as archive: raw = archive.read(member)
  else: raw = path.read_bytes()
  assert sha(raw) == expected, 'Unreviewed Umbrella source: ' + version
  result = patch(raw)
  target = HERE / 'candidate' / version / 'player.py'
  target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(result)
  manifest['variants'][version] = {'before_sha256': sha(raw), 'after_sha256': sha(result), 'file': str(target.relative_to(HERE))}
 (HERE / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
 print(json.dumps(manifest, indent=2))
