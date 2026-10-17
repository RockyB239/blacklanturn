"""Original BlackLanturn vector family, transparent native exports and review sheets."""
from pathlib import Path
import json,shutil,subprocess
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parent
PROBE=ROOT.parents[1]
SAMPLES=ROOT.parent/'icon-samples'
APPROVED={'home':('Home','home-refined'),'movies':('Movies','movies'),'tv':('Shows','shows'),'live-tv':('Live TV','live-tv'),'youtube':('YouTube','youtube'),'settings':('Settings','settings'),'action':('Action','action-alternate'),'science-fiction':('Science fiction','scifi-alternate')}
SHAPES={
 'search':('Search','<circle cx="27" cy="27" r="17"/><path class="accent" d="m40 40 14 14"/>'),
 'bookmark':('My Stuff','<path d="M19 9h26a3 3 0 0 1 3 3v43L32 44 16 55V12a3 3 0 0 1 3-3Z"/><path class="accent" d="M25 25h14m-7-7v14"/>'),
 'music':('Music','<path d="M26 44V15l26-6v29M26 24l26-6"/><ellipse class="accent" cx="18" cy="47" rx="8" ry="6"/><ellipse class="accent" cx="44" cy="41" rx="8" ry="6"/>'),
 'sports':('Sports','<path d="M20 10h24v14c0 12-5 18-12 18s-12-6-12-18ZM20 16H10v7c0 8 4 12 13 12M44 16h10v7c0 8-4 12-13 12M32 42v10M23 56h18"/><path class="accent" d="m32 17 2 5 5 1-4 4 1 5-4-2-4 2 1-5-4-4 5-1Z"/>'),
 'guide':('TV guide','<rect x="9" y="12" width="46" height="42" rx="5"/><path d="M9 25h46M23 25v29M36 25v29"/><path class="accent" d="M29 33h20M14 42h14M42 44h6"/>'),
 'recordings':('Recordings','<rect x="9" y="14" width="46" height="37" rx="5"/><circle class="accent" cx="32" cy="32" r="10"/><path d="M24 57h16"/>'),
 'radio':('Radio','<rect x="9" y="24" width="46" height="30" rx="5"/><path d="m15 24 34-14M16 31h32"/><circle class="accent" cx="23" cy="42" r="7"/><path d="M38 39h9m-9 7h9"/>'),
 'pictures':('Pictures','<rect x="9" y="11" width="46" height="43" rx="5"/><circle class="accent" cx="42" cy="23" r="5"/><path d="m10 46 15-17 12 13 7-7 10 12"/>'),
 'games':('Games','<path d="M21 19h22c8 0 13 23 11 28-2 6-8 4-15-5H25c-7 9-13 11-15 5-2-5 3-28 11-28Z"/><path class="accent" d="M18 30h12m-6-6v12"/><circle cx="42" cy="28" r="2"/><circle cx="47" cy="34" r="2"/>'),
 'weather':('Weather','<circle class="accent" cx="23" cy="22" r="9"/><path class="accent" d="M23 6v4M7 22h4m1-11 3 3m20-3-3 3M39 22h-4"/><path d="M17 50h30a9 9 0 0 0 0-18 14 14 0 0 0-25-4 11 11 0 1 0-5 22Z"/>'),
 'files':('Files','<path d="M9 21v-7a3 3 0 0 1 3-3h16l6 8h18a3 3 0 0 1 3 3v29H9Z"/><path class="accent" d="M9 27h46"/>'),
 'addons':('Add-ons','<rect x="9" y="10" width="18" height="18" rx="4"/><rect class="accent" x="37" y="10" width="18" height="18" rx="4"/><rect x="9" y="38" width="18" height="18" rx="4"/><rect x="37" y="38" width="18" height="18" rx="4"/>'),
 'video-addons':('Video add-ons','<rect x="9" y="13" width="46" height="38" rx="6"/><path class="accent" d="m21 23 16 9-16 9Z"/><path d="M46 27v10m-5-5h10"/>'),
 'music-addons':('Music add-ons','<circle cx="32" cy="32" r="23"/><path class="accent" d="M29 40V20l16-4v20"/><ellipse cx="23" cy="42" rx="6" ry="4"/><ellipse cx="39" cy="38" rx="6" ry="4"/>'),
 'picture-addons':('Picture add-ons','<rect x="8" y="15" width="37" height="36" rx="4"/><path d="m9 43 12-14 10 10 6-6 7 9M19 9h33a4 4 0 0 1 4 4v31"/><circle class="accent" cx="34" cy="25" r="4"/>'),
 'program-addons':('Program add-ons','<rect x="8" y="10" width="48" height="44" rx="5"/><path d="M8 21h48"/><path class="accent" d="m22 30-7 7 7 7m20-14 7 7-7 7m-7-16-6 18"/>'),
 'services':('Services','<path d="M12 15h40v13H12ZM12 37h40v13H12ZM32 28v9"/><path class="accent" d="M18 21h3m5 0h3M18 43h3m5 0h3"/>'),
 'tools':('Tools','<path d="M51 10a15 15 0 0 0-20 18L11 48a5 5 0 0 0 7 7l20-20a15 15 0 0 0 18-20l-10 9-8-8Z"/><path class="accent" d="m17 49 14-14"/>'),
 'collections':('Collections','<rect x="18" y="18" width="36" height="37" rx="4"/><path d="M11 47V13a4 4 0 0 1 4-4h30"/><path class="accent" d="M26 30h20m-20 9h20m-20 9h12"/>'),
 'favourites':('Favourites','<path d="m32 8 7 16 18 3-13 13 3 18-15-8-15 8 3-18L7 27l18-3Z"/><path class="accent" d="m32 8 7 16 18 3"/>'),
 'continue-watching':('Continue watching','<path d="M12 23a23 23 0 1 1-1 19M10 10v15h15"/><path class="accent" d="m28 22 16 10-16 10Z"/>'),
 'trending':('Trending','<path d="M10 50h44M12 40l13-13 10 9 18-23M39 13h14v14"/><path class="accent" d="m35 36 18-23"/>'),
 'popular':('Popular','<path d="M32 7c4 14 17 17 17 31a17 17 0 0 1-34 0c0-8 4-16 10-20 0 7 2 10 5 12 6-8 5-15 2-23Z"/><path class="accent" d="M32 35c-6 5-8 9-8 13a8 8 0 0 0 16 0c0-5-3-9-8-13Z"/>'),
 'new-releases':('New releases','<rect x="10" y="14" width="44" height="41" rx="5"/><path d="M10 25h44M21 8v12M43 8v12"/><path class="accent" d="M32 33v14m-7-7h14"/>'),
 'kids':('Kids','<circle cx="32" cy="34" r="20"/><circle cx="15" cy="16" r="8"/><circle cx="49" cy="16" r="8"/><path class="accent" d="M24 29v2m16-2v2m-16 9c4 5 12 5 16 0"/>'),
 'family':('Family','<circle cx="19" cy="19" r="7"/><circle cx="45" cy="19" r="7"/><path d="M7 48v-9a12 12 0 0 1 20-9m30 18v-9a12 12 0 0 0-20-9"/><circle class="accent" cx="32" cy="35" r="6"/><path class="accent" d="M22 56v-4a10 10 0 0 1 20 0v4"/>'),
 'adventure':('Adventure','<circle cx="32" cy="32" r="23"/><path class="accent" d="m40 23-5 12-12 6 6-12Z"/><path d="M32 9v4m0 38v4M9 32h4m38 0h4"/>'),
 'animation':('Animation','<path d="M32 8c18 0 25 14 25 26S45 56 32 56 7 46 7 34 14 8 32 8Z"/><path d="M19 26c2-4 6-4 8 0m10 0c2-4 6-4 8 0"/><path class="accent" d="M20 36h24c-2 11-22 11-24 0Z"/>'),
 'comedy':('Comedy','<path d="M10 12c14 6 30 6 44 0v20c0 14-15 23-22 25-7-2-22-11-22-25Z"/><path d="M18 27c2-4 6-4 8 0m12 0c2-4 6-4 8 0"/><path class="accent" d="M20 35h24c-3 12-21 12-24 0Z"/>'),
 'crime':('Crime','<path d="m32 8 5 10 12-4-4 12 10 6-10 6 4 12-12-4-5 10-5-10-12 4 4-12-10-6 10-6-4-12 12 4Z"/><circle class="accent" cx="32" cy="32" r="8"/>'),
 'documentary':('Documentary','<path d="M9 14h46v38H9ZM18 9v10m13-10v10m15-10v10"/><path class="accent" d="M20 28h24m-24 8h24m-24 8h15"/>'),
 'drama':('Drama','<path d="M10 13c13 5 25 5 38 0v18c0 13-13 23-19 25-6-2-19-12-19-25Z"/><path d="M18 28h6m11 0h6"/><path class="accent" d="M20 45c3-7 13-7 17 0"/><path d="M48 13h6v19c0 10-7 19-12 23"/>'),
 'fantasy':('Fantasy','<path d="M32 8 16 47h34ZM10 48c15-5 29-5 45 0v7H10Z"/><path class="accent" d="m34 26 2 4 5 1-4 3 1 5-4-2-4 2 1-5-4-3 5-1Z"/>'),
 'history':('History','<path d="M10 23 32 9l22 14ZM10 53h44M14 28v19m12-19v19m12-19v19m12-19v19"/><path class="accent" d="M10 23h44M10 48h44"/>'),
 'horror':('Horror','<path d="M32 9a20 20 0 0 1 20 20c0 10-7 13-7 18v8H19v-8c0-5-7-8-7-18A20 20 0 0 1 32 9Z"/><ellipse class="accent" cx="23" cy="30" rx="5" ry="6"/><ellipse class="accent" cx="41" cy="30" rx="5" ry="6"/><path d="m32 38-3 6h6ZM26 49v6m12-6v6"/>'),
 'mystery':('Mystery','<circle cx="32" cy="32" r="23"/><path class="accent" d="M24 23c0-11 18-11 18 0 0 7-10 8-10 15m0 9v1"/>'),
 'romance':('Romance','<path d="M32 54 12 34C-3 16 19 4 32 20 45 4 67 16 52 34Z"/><path class="accent" d="M41 15c5-3 10 0 11 5"/>'),
 'thriller':('Thriller','<path d="M32 10 56 52H8Z"/><path class="accent" d="M32 24v14m0 7v2"/>'),
 'war':('War','<path d="M10 37h44V28a22 22 0 0 0-44 0ZM8 44h48M15 44v10h34V44"/><path class="accent" d="M32 10v27"/>'),
 'western':('Western','<path d="M18 38c3-7 2-17 4-24 7 8 13 8 20 0 2 7 1 17 4 24M8 35c9 6 39 6 48 0v12c-10 10-38 10-48 0Z"/><path class="accent" d="M18 34c9 3 19 3 28 0"/>'),
 'news':('News','<path d="M11 11h37v40a5 5 0 0 1-5 5H16a5 5 0 0 1-5-5ZM48 25h7v26a5 5 0 0 1-5 5H42"/><path class="accent" d="M19 20h21M19 29h8v10h-8Z"/><path d="M33 29h7m-7 9h7M19 47h21"/>'),
 'reality':('Reality','<path d="M8 32c12-21 36-21 48 0-12 21-36 21-48 0Z"/><circle class="accent" cx="32" cy="32" r="9"/>'),
 'talk':('Talk shows','<path d="M13 11h38v29H31L17 53V40h-4Z"/><path class="accent" d="M21 21h22m-22 10h15"/>'),
 'anime':('Anime','<path d="m13 30-2-12 11 4 10-14 6 13 15-4-4 15v10L32 56 15 42Z"/><path class="accent" d="m21 32 7 3m8 0 7-3M27 45h10"/>'),
 'biography':('Biography','<path d="M9 12h18a5 5 0 0 1 5 5 5 5 0 0 1 5-5h18v41H37a5 5 0 0 0-5 4 5 5 0 0 0-5-4H9ZM32 17v40"/><circle class="accent" cx="20" cy="26" r="5"/><path class="accent" d="M14 42v-3a6 6 0 0 1 12 0v3"/><path d="M39 24h9m-9 10h9m-9 10h9"/>'),
 'concerts':('Concerts','<rect x="25" y="8" width="14" height="28" rx="7"/><path d="M18 26v5a14 14 0 0 0 28 0v-5M32 45v11M23 56h18"/><path class="accent" d="M25 19h14m-14 7h14"/>'),
 'podcasts':('Podcasts','<circle cx="32" cy="27" r="6"/><path class="accent" d="M26 42a6 6 0 0 1 12 0l-2 13h-8Z"/><path d="M19 39a18 18 0 1 1 26 0M13 45a26 26 0 1 1 38 0"/>'),
 'downloads':('Downloads','<path d="M10 40v14h44V40"/><path class="accent" d="M32 9v32m-11-11 11 11 11-11"/>'),
 'playlist':('Playlists','<path d="M9 14h38M9 26h28M9 38h20M9 50h20"/><path class="accent" d="m40 33 15 10-15 10Z"/>'),
 'top-rated':('Top rated','<path d="M17 9h30v31L32 56 17 40ZM23 9v13m18-13v13"/><path class="accent" d="m32 24 3 6 7 1-5 5 1 7-6-3-6 3 1-7-5-5 7-1Z"/>'),
 'international':('International','<circle cx="32" cy="32" r="23"/><ellipse class="accent" cx="32" cy="32" rx="11" ry="23"/><path d="M9 32h46M13 19h38M13 45h38"/>'),
}
# Keep useful earlier symbols available while refining the genre defaults.
SHAPES['warning']=('Warning',SHAPES['thriller'][1])
SHAPES['drama-mask']=('Drama — mask',SHAPES['drama'][1])
SHAPES.update({
 'western':('Western','<path d="M19 37 22 17c1-7 6-7 10-3 4-4 9-4 10 3l3 20M19 31c8 3 18 3 26 0"/><path d="M8 35c-4 1-3 6 3 9 11 6 31 6 42 0 6-3 7-8 3-9-4 8-44 8-48 0Z"/><path class="accent" d="M20 35c8 3 16 3 24 0"/>'),
 'western-horse':('Western — horse','<path d="m15 53 3-16-6-12 10-4 7-12 2 12 9 2 12 12-5 8-11-6-3 16M29 9l7 9M18 37c10-4 13-10 13-16M36 37l-9 5"/><circle class="accent" cx="38" cy="29" r="1.5"/><path class="accent" d="m25 21-8 6"/>'),
 'western-tumbleweed':('Western — tumbleweed','<circle cx="31" cy="30" r="21"/><path d="M14 16c19-5 32 10 30 29M10 31c13-17 34-17 42-7M19 49c-1-17 5-30 24-37M11 39c17-5 29 0 34 9M23 11c13 9 15 28 9 40M16 22l33 14"/><path class="accent" d="M7 55h38m5 0h7"/>'),
 'crime':('Crime','<circle cx="18" cy="22" r="11"/><circle cx="46" cy="42" r="11"/><path d="M25 28 31 32M33 34l6 3M11 14l5-5m35 43 5-5"/><path class="accent" d="M12 24a6 6 0 0 0 11 1m17 17a6 6 0 0 0 11 1M28 30l5-1 3 4-2 5-5 1-3-4Z"/>'),
 'crime-lights':('Crime — police lights','<path d="M12 41V30a11 11 0 0 1 11-11h18a11 11 0 0 1 11 11v11M8 42h48v8H8ZM32 19v23"/><path class="accent" d="M18 31v6m25-6v6M32 7v5M11 10l5 5m32 0 5-5M4 28h4m48 0h4"/>'),
 'animation':('Animation','<path d="M32 9C17 9 7 19 7 33c0 14 13 23 24 23 8 0 12-5 8-10-3-4-2-8 4-8h5c7 0 9-7 7-13C52 15 43 9 32 9Z"/><circle cx="18" cy="29" r="3"/><circle cx="25" cy="19" r="3"/><circle cx="37" cy="18" r="3"/><circle cx="46" cy="25" r="3"/><path class="accent" d="m24 32 12 7-12 7Z"/>'),
 'drama':('Drama','<path d="m31 52-18-18C-1 20 17 8 29 21 41 7 62 18 49 34Z"/><path class="accent" d="m31 19-5 12 8 6-5 10M51 7c0 0-6 8-6 12a6 6 0 0 0 12 0c0-4-6-12-6-12Z"/>'),
 'mystery':('Mystery','<path d="m19 25 3-13 10 4 10-4 3 13M10 27c13-4 31-4 44 0M20 31v5c0 8 6 13 12 13s12-5 12-13v-5M12 56l8-12 12 7 12-7 8 12"/><path class="accent" d="M24 34h5m6 0h5m-11 0h6M32 51v7"/>'),
 'war':('War','<rect x="8" y="39" width="48" height="16" rx="8"/><path d="m12 39 5-11h27l8 11M23 28V17h18l4 11M41 20h16v6H44"/><circle cx="18" cy="47" r="4"/><circle cx="32" cy="47" r="4"/><circle cx="46" cy="47" r="4"/><path class="accent" d="M27 17v11M17 34h27"/>'),
 'documentary':('Documentary','<path d="M8 14h15c6 0 9 4 9 7 0-3 3-7 9-7h15v35H41c-6 0-9 4-9 7 0-3-3-7-9-7H8ZM32 21v35"/><path class="accent" d="M14 25h10m-10 9h10m16-9h10m-10 9h10"/>'),
 'documentary-graduate':('Documentary — graduate','<path d="m7 21 25-12 25 12-25 12ZM17 27v15c8 7 22 7 30 0V27"/><path class="accent" d="M57 21v24m-3 8 3-8 3 8"/>'),
 'adventure-mountains':('Adventure — mountains','<path d="m7 54 19-36 10 16 7-11 14 31ZM19 31l7 3 6-6M37 33l6 5 5-5"/><path class="accent" d="M26 18V6h16l-6 5 6 5H26"/>'),
 'adventure-backpack':('Adventure — backpack','<rect x="13" y="20" width="38" height="36" rx="9"/><path d="M23 20v-6a9 9 0 0 1 18 0v6M13 30H8v20h5m38-20h5v20h-5M19 34h26v16H19ZM26 21v8m12-8v8"/><path class="accent" d="M19 41h26m-13-3v6"/>'),
 'thriller':('Thriller','<path d="m44 8-21 25c2 6 6 9 11 11L54 19ZM23 33l-7 8 8 8 10-5M17 43 9 51a4 4 0 0 0 6 6l9-8"/><path class="accent" d="m31 33 14-17M10 13v8m-4-4h8"/>'),
 'stand-up':('Stand-up','<g transform="rotate(24 32 29)"><rect x="24" y="7" width="16" height="30" rx="8"/><path class="accent" d="M24 17h16m-16 7h16"/><path d="M28 36v17h8V36"/></g><path d="M33 51c14 6 16-2 23-1"/>'),
})

def normalize_icon(source):
 # Match the current gear's visible 216px extent, upscaling smaller glyphs.
 icon=source.convert('RGBA')
 bounds=icon.getchannel('A').point(lambda a:255 if a>=40 else 0).getbbox()
 if bounds is None:return Image.new('RGBA',(256,256))
 scale=216/max(bounds[2]-bounds[0],bounds[3]-bounds[1])
 padded=(max(0,bounds[0]-4),max(0,bounds[1]-4),min(icon.width,bounds[2]+4),min(icon.height,bounds[3]+4))
 icon=icon.crop(padded)
 icon=icon.resize((round(icon.width*scale),round(icon.height*scale)),Image.Resampling.LANCZOS)
 canvas=Image.new('RGBA',(256,256))
 canvas.alpha_composite(icon,((256-icon.width)//2,(256-icon.height)//2))
 return canvas

def main():
 manifest=[]
 for name,(title,sample) in APPROVED.items():
  shutil.copyfile(SAMPLES/(sample+'.svg'),ROOT/(name+'.svg'));manifest.append({'id':name,'label':title,'group':'Core' if name not in ('action','science-fiction') else 'Genres'})
 for name,(title,shape) in SHAPES.items():
  (ROOT/(name+'.svg')).write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256" viewBox="0 0 64 64"><title>{title}</title><defs><linearGradient id="metal" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#eef5f6"/><stop offset=".5" stop-color="#b1c4ce"/><stop offset="1" stop-color="#7e9ba8"/></linearGradient></defs><style>.accent{{stroke:#29d9ee}}</style><g fill="none" stroke="url(#metal)" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round">{shape}</g></svg>')
  group='Alternates' if name in ('warning','drama-mask','western-horse','western-tumbleweed','crime-lights','documentary-graduate','adventure-mountains','adventure-backpack') else 'Genres' if name in ('adventure','animation','comedy','crime','documentary','drama','fantasy','history','horror','mystery','romance','thriller','war','western','news','reality','talk','anime','biography','stand-up') else 'Sections and categories'
  manifest.append({'id':name,'label':title,'group':group})
 for name,sample,title in [('my-stuff','bookmark','My Stuff'),('action-lightning','action','Action — lightning'),('science-fiction-orbit','science-fiction','Science fiction — orbit')]:
  src=ROOT/'bookmark.svg' if sample=='bookmark' else SAMPLES/(sample+'.svg');shutil.copyfile(src,ROOT/(name+'.svg'));manifest.append({'id':name,'label':title,'group':'Alternates'})
 # Owner-approved revisions are durable masters, separate from review candidates.
 for name,title in [('thriller','Thriller'),('creature-features','Creature Features'),('western','Western'),('crime-handcuffs','Crime — handcuffs'),('drama','Drama'),('mystery','Mystery'),('stand-up','Stand-up'),('slashers','Slashers')]:
  source=ROOT/'approved'/(name+'.svg')
  if not source.exists():continue
  shutil.copyfile(source,ROOT/(name+'.svg'))
  if name not in {e['id'] for e in manifest}:manifest.append({'id':name,'label':title,'group':'Genres'})
 runtime=Path('/Users/ChrisFaulkner/.cache/codex-runtimes/codex-primary-runtime/dependencies/node')
 script="const fs=require('fs'),path=require('path'),sharp=require(process.argv[2]);const root=process.argv[1];Promise.all(fs.readdirSync(root).filter(n=>n.endsWith('.svg')).map(n=>sharp(path.join(root,n)).resize(256,256).png().toFile(path.join(root,n.replace('.svg','.png'))))).catch(e=>{console.error(e);process.exit(1)});"
 subprocess.run([str(runtime/'bin/node'),'-e',script,str(ROOT),str(runtime/'node_modules/sharp')],check=True)
 (ROOT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 native=ROOT/'native';native.mkdir(exist_ok=True)
 for entry in manifest:
  canvas=normalize_icon(Image.open(ROOT/(entry['id']+'.png')))
  canvas.save(native/(entry['id']+'.png'));shutil.copyfile(native/(entry['id']+'.png'),PROBE/'addon/resources/media'/(entry['id']+'.png'))
 font=lambda size,bold=False:ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial'+(' Bold' if bold else '')+'.ttf',size)
 for group,filename in [('Core and sections','sections'),('Genres','genres')]:
  entries=[e for e in manifest if (e['group']=='Genres')==(group=='Genres') and e['group']!='Alternates']
  rows=(len(entries)+5)//6;im=Image.new('RGB',(1320,140+rows*150),'#080b0e');d=ImageDraw.Draw(im)
  d.text((38,28),'BlackLanturn • '+group,font=font(30,True),fill='#eef5f6');d.text((38,76),'Original silver outlines and teal accents • 42px sidebar sample beside each icon',font=font(17),fill='#29d9ee')
  for i,e in enumerate(entries):
   x=30+(i%6)*215;y=120+(i//6)*150
   d.rounded_rectangle((x,y,x+200,y+138),radius=12,fill='#101820')
   icon=Image.open(ROOT/(e['id']+'.png')).convert('RGBA');big=icon.resize((76,76),Image.Resampling.LANCZOS);small=Image.open(native/(e['id']+'.png')).resize((42,42),Image.Resampling.LANCZOS)
   im.paste(big,(x+35,y+15),big);im.paste(small,(x+131,y+34),small)
   d.text((x+100,y+110),e['label'],font=font(15,True),fill='#dce7ec',anchor='mm')
  im.save(ROOT/('blacklanturn-icons-'+filename+'.png'))
 # A focused, native-scale review of the owner's requested refinements.
 review=['western','western-horse','western-tumbleweed','crime','crime-lights','animation','drama','mystery','war','documentary','documentary-graduate','stand-up','adventure','adventure-mountains','adventure-backpack','thriller','warning','settings','home','search']
 labels={e['id']:e['label'] for e in manifest}
 im=Image.new('RGB',(1200,1030),'#080b0e');d=ImageDraw.Draw(im)
 d.text((36,25),'BlackLanturn • revised icons',font=font(30,True),fill='#eef5f6')
 d.text((36,73),'Silver + teal • enlarged view and actual 42px sidebar size • all sizes normalized',font=font(17),fill='#29d9ee')
 for i,name in enumerate(review):
  x=25+(i%4)*295;y=115+(i//4)*180
  d.rounded_rectangle((x,y,x+280,y+164),radius=12,fill='#101820')
  icon=Image.open(native/(name+'.png'));big=icon.resize((100,100),Image.Resampling.LANCZOS);small=icon.resize((42,42),Image.Resampling.LANCZOS)
  im.paste(big,(x+53,y+12),big);im.paste(small,(x+187,y+43),small)
  d.text((x+140,y+141),labels[name],font=font(16,True),fill='#dce7ec',anchor='mm')
 im.save(ROOT/'blacklanturn-icons-refinements.png')
 print(f'{len(manifest)} original icons exported and installed in test media.')
if __name__=='__main__':main()
