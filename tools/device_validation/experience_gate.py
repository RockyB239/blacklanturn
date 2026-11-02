"""Host-side visible experience gate; never imported by Kodi at runtime."""
import argparse,json,math,re,statistics
from pathlib import Path
ROUTES=('Home','Shows','Movies','Shows genre','Movies genre','Shows deep rows','Movies deep rows','Playback return','Options return')
PROTOCOL='blacklanturn-visible-v1'
def _pin(value):return isinstance(value,str) and re.fullmatch('[0-9a-f]{64}',value) is not None
def _number(value):return type(value) in (int,float) and math.isfinite(value) and value>=0

def summary(receipt):
 if receipt.get('passed') is not True or receipt.get('protocol')!=PROTOCOL:raise ValueError('Native visible protocol did not pass')
 if not _pin(receipt.get('source_sha256')):raise ValueError('Source identity is missing')
 if not receipt.get('device') or not receipt.get('profile_scope'):raise ValueError('Device/profile identity is missing')
 groups={route:[] for route in ROUTES}
 for sample in receipt.get('samples',[]):
  route=sample.get('route')
  if route not in groups:raise ValueError('Unexpected visible route')
  if sample.get('cache')!='warm':raise ValueError(route+': cold samples cannot qualify as cached navigation')
  if not all(_number(sample.get(k)) for k in ('visible_seconds','remote_seconds')):raise ValueError(route+': invalid timing')
  if type(sample.get('visible_cards')) is not int or sample['visible_cards']<1:raise ValueError(route+': no browsable cards')
  if sample.get('artwork_visible') is not True or sample.get('artwork_reviewed') is not True or not _pin(sample.get('frame_sha256')):raise ValueError(route+': visible artwork frame evidence missing')
  groups[route].append(sample)
 result={}
 for route,samples in groups.items():
  if len(samples)<3:raise ValueError(route+': at least three matched cached samples required')
  result[route]={}
  for metric in ('visible_seconds','remote_seconds'):
   values=sorted(s[metric] for s in samples);result[route][metric]={'median':statistics.median(values),'tail':values[math.ceil(.95*len(values))-1],'samples':len(values)}
 return result

def compare(before,after):
 result={'passed':False,'failures':[]}
 try:
  if any(before.get(k)!=after.get(k) for k in ('protocol','device','profile_scope')):raise ValueError('Device/profile/readiness protocols differ')
  old,new=summary(before),summary(after);result.update(before=old,after=new)
  for route in ROUTES:
   for metric in ('visible_seconds','remote_seconds'):
    prior,current=old[route][metric],new[route][metric]
    allowance=.20 if metric=='visible_seconds' else .08
    for field,ratio in [('median',1.2),('tail',1.25)]:
     limit=max(prior[field]*ratio,prior[field]+allowance)
     if current[field]>limit:result['failures'].append(route+' '+metric+' '+field+' regressed')
  result['passed']=not result['failures']
 except (ValueError,TypeError,KeyError) as exc:result['failures'].append(str(exc))
 return result

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('before',type=Path);p.add_argument('after',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=compare(json.loads(a.before.read_text()),json.loads(a.after.read_text()));a.output.write_text(json.dumps(r,indent=2)+'\n')
 if not r['passed']:raise SystemExit('; '.join(r['failures']))
