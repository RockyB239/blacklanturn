"""One-time, offline upgrades of recognized default discovery row definitions.

Custom lists and all non-discovery data remain owned by the user. Never read
accounts or fetch recommendations here; the normal provider does that later.
"""
import copy,hashlib,json
from pathlib import Path
CATALOG=json.loads((Path(__file__).parents[1]/'discovery-lineup.json').read_text(encoding='utf-8'))
def fingerprint(value):
 return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')).hexdigest()
def upgrade(raw,catalog=None):
 catalog=CATALOG if catalog is None else catalog
 if catalog.get('schema')!=1 or catalog.get('revision')!='discovery-first-page-1':raise ValueError('Unrecognized discovery defaults')
 value=json.loads(raw);changed=False;defaults=catalog['defaults'];recognized=catalog['recognized']
 for section in ('Movies','Shows'):
  if section not in value:continue
  if fingerprint(value[section]) in recognized['sections'].get(section,[]):
   replacement=defaults[section]
   if value[section]!=replacement:value[section]=copy.deepcopy(replacement);changed=True
 for group in ('Genres','Categories'):
  if not isinstance(value.get(group),list):continue
  targets={(p['section'],p['id']):p for p in defaults[group]}
  for page in value[group]:
   if not isinstance(page,dict):continue
   section=page.get('section');ident=page.get('id')
   if not isinstance(section,str) or not isinstance(ident,str):continue
   target=targets.get((section,ident));key=group+':'+section+':'+ident
   if target and fingerprint(page.get('rows')) in recognized['pages'].get(key,[]):
    if page.get('rows')!=target['rows']:page['rows']=copy.deepcopy(target['rows']);changed=True
 return json.dumps(value,indent=2,ensure_ascii=False) if changed else raw

def apply_clean(config):
 """Use the reviewed clean row catalogue, preserving every other default."""
 result=copy.deepcopy(config)
 for key,value in CATALOG['defaults'].items():result[key]=copy.deepcopy(value)
 return result

def verify_archive(archive):
 """Validate new defaults before cleanup can touch an existing installation."""
 name='userdata/addon_data/script.blacklanturn.preview/rows.json'
 if archive.getinfo(name).file_size>4*1024*1024:raise ValueError('Discovery defaults exceed limit')
 config=json.loads(archive.read(name))
 if not isinstance(config,dict) or any(config.get(key)!=value for key,value in CATALOG['defaults'].items()):
  raise ValueError('The build discovery defaults need a compatible Installer. Your current build has been kept.')
