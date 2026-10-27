"""Compare matched native readiness receipts; never treat first visits as cold."""
import argparse,json,math,statistics
from pathlib import Path
SECTIONS=('Home','Shows','Movies','YouTube','My Stuff')

def summary(receipt):
    if receipt.get('passed') is not True:raise ValueError('Native acceptance did not pass')
    result={}
    for section in SECTIONS:
        visits=[x.get('seconds') for x in receipt.get('row_visits',[]) if x.get('section')==section]
        if len(visits)<4 or any(type(n) not in (int,float) or n<0 or not math.isfinite(n) for n in visits):raise ValueError('Missing or invalid native samples')
        warm=sorted(visits[1:]);result[section]={'first_visit':visits[0],'median':statistics.median(warm),'p95':warm[math.ceil(.95*len(warm))-1]}
    return result

def compare(before,after):
    result={'passed':False,'failures':[]}
    try:
        if not before.get('protocol') or before['protocol']!=after.get('protocol'):raise ValueError('Readiness protocols differ')
        old,new=summary(before),summary(after);result.update(before=old,after=new)
        for section in SECTIONS:
            baseline=old[section];current=new[section]
            median_limit=max(baseline['median']*1.2,baseline['median']+.20)
            tail_limit=max(baseline['p95']*1.25,baseline['p95']+.35)
            if current['median']>median_limit:result['failures'].append(section+' warm median regressed')
            if current['p95']>tail_limit:result['failures'].append(section+' warm tail regressed')
        result['passed']=not result['failures']
    except (ValueError,TypeError,KeyError) as exc:result['failures'].append(str(exc))
    return result

def soak(receipt):
    result={'passed':False,'failures':[]}
    try:
        values=summary(receipt)
        if any(sum(x.get('section')==section for x in receipt.get('row_visits',[]))<20 for section in SECTIONS):raise ValueError('Extended navigation needs at least 20 visits to every section')
        for section,value in values.items():
            if value['p95']>(5 if section=='YouTube' else 2):result['failures'].append(section+' extended-use tail exceeds budget')
        memory=receipt.get('memory',{})
        if memory.get('rss_start') is None or memory.get('rss_end') is None:raise ValueError('Native process memory evidence is missing')
        if memory['rss_end']-memory['rss_start']>64*1024*1024:result['failures'].append('Process memory grew more than 64 MiB')
        result['passed']=not result['failures'];result['summary']=values
    except (ValueError,TypeError,KeyError) as exc:result['failures'].append(str(exc))
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('before',type=Path);parser.add_argument('after',type=Path);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    result=compare(json.loads(args.before.read_bytes()),json.loads(args.after.read_bytes()));args.output.write_text(json.dumps(result,indent=2))
    if not result['passed']:raise SystemExit('; '.join(result['failures']))
