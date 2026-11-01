"""Explicit, targeted metadata refresh without clearing custom artwork or watch data."""
def refresh_title(params,factory=None):
 if params.get('tmdb_type') not in ('movie','tv') or not str(params.get('tmdb_id','')).isdigit():raise ValueError('A title identity is required')
 if factory is None:
  import sys,xbmcaddon
  from pathlib import Path
  root=str(Path(xbmcaddon.Addon('plugin.video.themoviedb.helper').getAddonInfo('path'))/'resources')
  if root not in sys.path:sys.path.insert(0,root)
  from tmdbhelper.lib.items.database.baseitem_factories.factory import BaseItemFactory
  factory=BaseItemFactory
 targets=[('movie' if params['tmdb_type']=='movie' else 'tvshow',None,None)]
 if params['tmdb_type']=='tv' and params.get('season') is not None:
  targets.append(('season',params['season'],None))
  if params.get('episode') is not None:targets.append(('episode',params['season'],params['episode']))
 for mediatype,season,episode in targets:
  request=factory(mediatype);request.tmdb_id=params['tmdb_id'];request.season=season;request.episode=episode
  request.cache_refresh='force';request.cache_translations=True;request.clear_user_art=False
  if not request.data:raise RuntimeError("Title information is unavailable")
