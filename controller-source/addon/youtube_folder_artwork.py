"""Resolve YouTube category art for display without changing provider records."""
import re
from copy import deepcopy
from pathlib import Path
from urllib.parse import urlsplit, parse_qs
from icon_packs import icon_path, selected_pack

ROOT = Path(__file__).resolve().parent


def provider_items(items):
    """Undo only our display artwork before caching/restoring category records."""
    result=[]
    for item in items:
        original=item.get('_youtube_folder_source_art')
        if isinstance(original,dict) and item.get('_youtube_folder_icon'):
            item=dict(item)
            for key in ('art','thumbnail','_youtube_folder_icon','_youtube_folder_source_art'):
                item.pop(key,None)
            item.update(deepcopy(original))
        result.append(item)
    return result


def category_icon(item):
    """Recognize native category routes, independent of localized labels/art URIs."""
    if item.get('filetype') != 'directory' or item.get('_page_control'):
        return None
    route = urlsplit(item.get('file', ''))
    if route.scheme != 'plugin' or route.netloc != 'plugin.video.youtube':
        return None
    path = route.path.rstrip('/')
    if path in ('/special/my_subscriptions', '/special/my_subscriptions_filtered'):
        return 'subscriptions'
    category = re.fullmatch(r'/(?:special/my_subscriptions(?:_filtered)?|channel/[^/]+)/(shorts|live)', path)
    if category:
        return 'youtube' if category[1] == 'shorts' else 'live-tv'
    playlist = re.fullmatch(r'/(?:channel/[^/]+/)?playlist/(UUSH|UULV)[A-Za-z0-9_-]+', path)
    if playlist:
        return 'youtube' if playlist[1] == 'UUSH' else 'live-tv'
    if path in ('/special/live', '/special/upcoming_live', '/special/completed_live'):
        return 'live-tv'
    if path.startswith('/kodion/search/') and parse_qs(route.query).get('event_type') in (['live'], ['upcoming'], ['completed']):
        return 'live-tv'
    return None


def display_items(items, config):
    """Keep one selected-pack identity on category cards and their header artwork.

    This is deliberately after cache/page preparation: raw provider/saved records
    stay portable and selecting another icon pack takes effect on the next bind.
    Real video, channel and ordinary playlist artwork is never rewritten.
    """
    pack = selected_pack(config)
    result = []
    for item in provider_items(items):
        slug = category_icon(item)
        if slug:
            image = icon_path(ROOT, slug, pack)
            original=deepcopy({key:item[key] for key in ('art','thumbnail') if key in item})
            item = dict(item, art=dict(item.get('art') or {}, thumb=image,
                                      icon=image, fanart=image, landscape=image),
                        thumbnail=image, _youtube_folder_icon=image,
                        _youtube_folder_source_art=original)
        result.append(item)
    return result
