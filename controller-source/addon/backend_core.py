"""Connected destinations for the portable BlackLanturn settings review."""
SETTINGS_GROUPS=[
 ('Skin & discovery','Choose the lists and sections that make up your home.',[
  ('rows','Home, movie and show rows','Choose add-on sources, labels and row order.'),
  ('genres','Genre pages','Configure ordered add-on rows within each genre.'),
  ('categories','Category pages','Configure ordered rows within themed collections.'),
  ('sidebar','Sidebar','Add pages, add-ons and Kodi sections; choose names, icons and order.')]),
 ('Previews','Set how previews behave while you browse.',[
  ('preview_mode','Movie & show automatic previews','Switch movie and show previews between automatic and manual.'),
  ('preview_delay','Preview delay','Wait before starting a preview on a selected title.'),
  ('preview_language','Preview language','Prefer English and dubbed previews; retain other-language fallbacks.'),
  ('youtube_previews','YouTube automatic previews','Preview the highlighted YouTube video without changing watch history.'),
  ('youtube_end_suggestions','YouTube next-video suggestions','Show related videos after playback ends; Back hides them, then exits.'),
  ('youtube_end_autoplay','YouTube next-video autoplay','Play the first suggestion after a cancellable 15-second countdown.')]),
 ('Ratings','Choose your scores and their order below the description.',[
  ('ratings','Rating sources','Show or hide critic and audience scores.'),
  ('rating_order','Rating order','Move enabled scores left or right.')]),
 ('Accounts & integrations','Open the settings supplied by each integration.',[
  ('integration_status','Integration status','Availability, versions and failed lists; account setup remains in each add-on.'),
  ('addon:plugin.video.themoviedb.helper','Discovery, Trakt & metadata','TMDbHelper account, list and metadata settings.'),
  ('addon:plugin.video.umbrella','Playback & provider accounts','Umbrella account, source and playback settings.'),
  ('addon:plugin.video.youtube','YouTube account & previews','Connect YouTube for its sidebar section, personal feeds and previews.')]),
 ('Kodi settings','All Kodi controls remain available.',[
  ('kodi:settings','All Kodi settings','Open the complete Kodi settings screen.'),
  ('kodi:PlayerSettings','Player','Video, audio, subtitles and playback preferences.'),
  ('kodi:MediaSettings','Media & library','Library, music, pictures and media preferences.'),
  ('kodi:PVRSettings','Live TV & PVR','TV guide, channels and recording settings.'),
  ('kodi:ServiceSettings','Services','Network, sharing and control services.'),
  ('kodi:GameSettings','Games','Kodi game preferences.'),
  ('kodi:InterfaceSettings','Interface','Language, region, display and skin selection.'),
  ('kodi:SkinSettings','Kodi skin controls','Options supplied by the installed Kodi skin.'),
  ('kodi:Profiles','Profiles','Manage Kodi profiles.'),
  ('kodi:SystemSettings','System','Display, audio, input and power settings.'),
  ('kodi:filemanager','File manager','Files and source locations.'),
  ('kodi:addonbrowser','Add-ons','Installed add-ons and repositories.'),
  ('kodi:systeminfo','System information','Kodi version, hardware and network information.'),
  ('kodi:eventlog','Event log','Kodi notices and errors.')]),
 ('Help','Guidance for using BlackLanturn.',[
  ('update_notes','What’s new & update notices','View installed changes and choose whether to show update notices.'),
  ('startup_preview','Preview loading screen','Review the BlackLanturn startup design.'),
  ('help','Using BlackLanturn','Browsing, search, accounts, previews and recovery.'),
  ('clear_search','Clear saved search','Remove the last search term saved on this device.'),
  ('recovery','Return to previous skin','Switch back to your previous skin; add-ons and accounts remain installed.')]),
 ('Appearance','Choose artwork and information shown while browsing.',[
  ('status_display','Time, date & weather','Independent visibility switches; weather uses your Kodi service.'),
  ('title_logos','Title logos','Use movie and show logos when available; otherwise show the full title.'),
('icon_pack','Sidebar icon style','Choose an installed icon pack. Sidebar choices and order stay saved.')])]

SETTINGS_GROUPS.append(('Recommendations','Exact-title choices on this device. Your genre preferences stay unchanged.',[
  ('hidden_titles','Hidden titles','Unhide a movie or show. Search, saved titles and watch progress remain available.'),
  ('reduced_titles','Reduced titles','Restore normal frequency for titles you chose to see less often.')]))

class CoreSettingsReturn:
 """Wait for actual core activation, then Home; avoid an early-return race."""
 def __init__(self,started):self.started=started;self.entered=False
 def tick(self,window,now):
  if window!=10000:self.entered=True;return 'wait'
  if self.entered:return 'return'
  return 'failed' if now-self.started>=5 else 'wait'
