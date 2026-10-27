"""Release gate for sanitized native receipts, tied to the reviewed source."""
import argparse,hashlib,json
from pathlib import Path
try:from .performance_gate import compare,soak
except ImportError:from performance_gate import compare,soak
try:from .row_readiness import COMPARE_PROTOCOL,SOAK_PROTOCOL
except ImportError:from row_readiness import COMPARE_PROTOCOL,SOAK_PROTOCOL

def verify(bundle,manifest):
    if bundle.get('schema')!=1 or bundle.get('source_manifest_sha256')!=hashlib.sha256(manifest.read_bytes()).hexdigest():raise ValueError('Native performance evidence does not match the reviewed source')
    if set(bundle.get('devices',{}))!={'mac','apple','fire'}:raise ValueError('All three native device receipts are required')
    result={}
    for device,receipts in bundle['devices'].items():
        if (any(receipts.get(key,{}).get('protocol')!=COMPARE_PROTOCOL for key in ('before','after'))
                or receipts.get('soak',{}).get('protocol')!=SOAK_PROTOCOL):raise ValueError('Fresh-row readiness protocol required for '+device)
        result[device]={'comparison':compare(receipts['before'],receipts['after']),'extended':soak(receipts['soak'])}
        if not all(r['passed'] for r in result[device].values()):raise ValueError('Native performance acceptance failed for '+device)
    return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('bundle',type=Path);p.add_argument('--manifest',type=Path,required=True);args=p.parse_args()
    result=verify(json.loads(args.bundle.read_bytes()),args.manifest);print(json.dumps({'passed':True,'devices':list(result)}))
