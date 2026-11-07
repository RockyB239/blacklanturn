"""Network-free title action layout; backend action IDs stay authoritative."""
from urllib.parse import urlsplit,parse_qs
GROUPS=(('save','Save & organize','collections'),('trakt','Trakt & watch status','history'),('discover','Discover','search'),('recommend','Recommendations','popular'),('refresh','Refresh','updates'))
GROUP_FOR={'category':'discover','search':'discover','home':'discover','mark_watched':'trakt','refresh_watch':'refresh','local':'save','library_add':'save','collections':'save','saved_searches':'save','save_search':'save','trakt':'trakt','movie_series':'discover','discover':'discover','youtube_refresh':'refresh','refresh':'refresh','reload_list':'refresh','refresh_metadata':'refresh','retry':'refresh','previous':'refresh','settings':'refresh','default_player':'refresh','normal_autoplay':'refresh'}
DESCRIPTIONS={'local':'Your My Stuff is saved on this device.','library_add':'Choose one of your personal collections.','collections':'View and manage your personal collections.','saved_searches':'Run a search you saved earlier.','save_search':'Keep this search for another time.','trakt':'Manage watched progress, watchlist and lists on Trakt.','movie_series':'Watch the movies in their release order.','discover':'Explore collections and work by the cast and creators.','title_hide':'Hide only this title from discovery rows.','title_less':'Reduce this title without changing your genres.','title_restore':'Restore this title’s normal visibility.','refresh':'Get the latest watched progress from Trakt.','reload_list':'Get fresh titles for the list you’re browsing.','refresh_metadata':'Update this title’s information and artwork.','youtube_refresh':'Refresh your YouTube recommendations.','retry':'Retry lists that could not load.','previous':'Return to the preceding page in this row.','default_player':'Choose the player used for future playback.','normal_autoplay':'Stop following the source chosen for this viewing session.'}
GROUP_FOR.update({
 'watch_tonight_toggle':'save',
 'watch_tonight':'save',
 'watch_tonight_next':'save',
 'coming_up':'discover',
 'shelf_tools':'discover',
 'streaming_services':'discover',
 'where_to_watch':'discover',
})
DESCRIPTIONS.update({
 'watch_tonight_toggle':'Change whether this title is in your queue on this device.',
 'watch_tonight':'Open, reorder, or remove queued movies and episodes.',
 'watch_tonight_next':'Open details for the first title in your queue.',
 'coming_up':'See upcoming TV air dates from your Trakt calendar.',
 'shelf_tools':'Filter or choose from the titles already shown in this shelf.',
 'streaming_services':'Browse regional availability from TMDb and JustWatch.',
 'jump_streaming_shelf':'Go directly to a row for this service.',
 'where_to_watch':'See indexed streaming providers for this title by country.',
 'title_more':'Prefer similar titles in recommendations on this device.',
})

def build_panel(options,episode=False):
 actions=[{'id':key,'label':label,'description':DESCRIPTIONS.get(key,'')} for key,label in options if not(episode and key=='genre')]
 quick=[a for key in ('play','browse_episodes','open_discovery','player','details','genre','jump_streaming_shelf') for a in actions if a['id']==key]
 ids={a['id'] for a in quick};playback=[a for a in actions if a['id'] in ('default_player','normal_autoplay')];ids.update(a['id'] for a in playback);grouped={key:[] for key,_,_ in GROUPS}
 for action in actions:
  if action['id'] in ids:continue
  key='recommend' if action['id'].startswith('title_') else GROUP_FOR.get(action['id'],'refresh')
  grouped[key].append(action)
 priority={'reload_list':0,'refresh_metadata':1,'refresh':2,'youtube_refresh':3,'retry':4}
 grouped['refresh'].sort(key=lambda a:priority.get(a['id'],10))
 for action in actions:
  if action['id']=='refresh_metadata' and action['label']=='Check for new episodes':action['description']='Check this show for new seasons and episodes.'
  if action['id']=='refresh_metadata' and action['label']=='Refresh episode information':action['description']='Update this episode’s information and artwork.'
 return {'quick':quick,'playback':playback,'groups':[{'id':key,'label':label,'icon':icon,'actions':grouped[key]} for key,label,icon in GROUPS if grouped[key]]}

def panel_header(item,section=''):
 item=item or {};art=item.get('art') or {};kind=item.get('type','')
 query=parse_qs(urlsplit(item.get('file','')).query)
 season=query.get('season',[item.get('season')])[0];number=query.get('episode',[item.get('episode')])[0]
 episode=kind=='episode' or ('episode' in query and str(season).isdigit() and str(number).isdigit()) or (kind not in ('movie','tvshow','season') and item.get('filetype')!='directory' and str(season).isdigit() and str(number).isdigit())
 title=item.get('title') or item.get('label') or section or 'Browse'
 if episode:
  meta='S%02d · E%02d'%(int(season),int(number)) if str(season).isdigit() and str(number).isdigit() else 'Episode'
  if item.get('showtitle'):meta=item['showtitle']+' · '+meta
 else:meta=('Show' if kind=='tvshow' or query.get('tmdb_type')==['tv'] or item.get('filetype')=='directory' else 'Movie' if kind=='movie' or query.get('tmdb_type')==['movie'] else section)
 if item.get('year'):meta+=' · '+str(item['year'])
 return {'title':title,'meta':meta,'art':art.get('landscape') or art.get('fanart') or art.get('thumb') or item.get('thumbnail','')}
