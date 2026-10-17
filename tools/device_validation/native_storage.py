"""Read-only native settings diagnostics, safe for Kodi tvOS virtual XML.

A directory URL without its trailing slash can omit native XML and poison
Kodi's directory cache. Prime the correct listing before reading. Never recover
an unreadable settings file by creating defaults or writing a replacement.
"""
import xml.etree.ElementTree as ET


def require(condition, message):
    """Checks must execute even when Kodi runs optimized Python."""
    if not condition:
        raise RuntimeError(message)


def listdir(vfs, directory):
    path = str(directory).rstrip('/\\')
    if not path or '\x00' in path:
        raise ValueError('Invalid diagnostic directory')
    return vfs.listdir(path + '/')


def read_xml(vfs, path, max_bytes=4 * 1024 * 1024):
    """Return validated XML bytes without modifying the file or its settings."""
    path = str(path)
    if '/' not in path or not path.lower().endswith('.xml'):
        raise ValueError('Expected a local Kodi XML path')
    listdir(vfs, path.rsplit('/', 1)[0])
    stream = vfs.File(path)
    try:
        if stream.size() > max_bytes:
            raise ValueError('Diagnostic XML exceeds limit')
        raw = bytes(stream.readBytes())
    finally:
        stream.close()
    if not raw or len(raw) > max_bytes:
        raise ValueError('Diagnostic XML is unreadable or exceeds limit')
    try:
        ET.fromstring(raw)
    except ET.ParseError as exc:
        raise ValueError('Diagnostic XML is invalid; original kept') from exc
    return raw
