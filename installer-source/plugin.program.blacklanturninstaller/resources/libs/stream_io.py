"""Bounded file transfer and SHA256 verification for runtime updates."""
import hashlib
from pathlib import Path

BUFFER_SIZE = 128 * 1024

def transfer(source, target=None):
    digest = hashlib.sha256()
    while True:
        chunk = source.read(BUFFER_SIZE)
        if not chunk: return digest.hexdigest()
        digest.update(chunk)
        if target is not None: target.write(chunk)

def file_hash(path):
    with Path(path).open('rb') as source: return transfer(source)
