"""Reject stale and half-replaced rows when measuring native section readiness."""
from urllib.parse import urlsplit, parse_qs

COMPARE_PROTOCOL = 'Fresh-row native sidebar timing v2; batched GUI dispatch, expected labels and provider/type checked; four cycles; first excluded from warm summaries'
SOAK_PROTOCOL = 'Fresh-row native navigation v2; batched GUI dispatch, labels and provider/type checked; four warmup cycles then twenty measured'


def media_route(path):
    parsed = urlsplit(path)
    query = parse_qs(parsed.query)
    return {'provider': parsed.hostname or '', 'kind': query.get('tmdb_type', query.get('type', ['']))[0]}


def settled(snapshot, heading, labels, routes):
    if snapshot['eyebrow'] != heading:
        return False
    for i in range(2):
        state = snapshot['states'][i]
        label = snapshot['labels'][i]
        if state not in ('ready', 'empty'):
            return False
        if state == 'empty':
            if snapshot['counts'][i] != 0 or label != labels[i] + '  ·  No titles':
                return False
        if state == 'ready':
            if snapshot['counts'][i] <= 0 or label != labels[i]:
                return False
            expected = routes[i]
            actual = snapshot['routes'][i]
            if expected and any(actual.get(k) != v for k, v in expected.items() if v):
                return False
    return True
