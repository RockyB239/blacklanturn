"""Validate one portable ZIP destination namespace before reading/extracting data.

Kodi targets include case-insensitive, Unicode-normalizing Apple filesystems.
Validate implicit directories too: aliasing a managed directory can inject an
extra file without colliding with any existing full filename.
"""
import stat
import unicodedata

class PathError(ValueError):
    pass

def validate(archive):
    entries = set()
    destinations = {}
    for item in archive.infolist():
        raw = item.orig_filename
        directory = raw.endswith('/')
        name = raw[:-1] if directory else raw
        parts = name.split('/')
        if (not raw or raw != item.filename or '\x00' in raw or '\\' in raw
                or any(part in ('', '.', '..') for part in parts)
                or parts[0] not in ('addons', 'userdata')
                or stat.S_ISLNK(item.external_attr >> 16)):
            raise PathError('The download has an invalid or noncanonical path. Your current build has been kept.')
        if raw in entries:
            raise PathError('The download contains duplicate destinations. Your current build has been kept.')
        entries.add(raw)
        identity = []
        for index, part in enumerate(parts):
            # Canonical caseless matching: normalization before and after fold.
            folded = unicodedata.normalize('NFD', part)
            identity.append(unicodedata.normalize('NFD', folded.casefold()))
            key = tuple(identity)
            destination = (tuple(parts[:index + 1]), index < len(parts) - 1 or directory)
            previous = destinations.get(key)
            if previous is not None and previous != destination:
                raise PathError('The download contains conflicting destinations. Your current build has been kept.')
            destinations[key] = destination
