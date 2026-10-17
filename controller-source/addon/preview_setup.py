"""Only presence checks. No authentication data is returned or logged."""
def configured(settings,store,enabled=True):
    if not enabled:return False
    def complete(values):return all(isinstance(v,str) and bool(v.strip()) for v in values)
    if complete(settings.get(k) for k in ('youtube.api.key','youtube.api.id','youtube.api.secret')):return True
    if not isinstance(store,dict):return False
    keys=store.get('keys')
    if not isinstance(keys,dict):return False
    user=keys.get('user',keys.get('personal',{}))
    return isinstance(user,dict) and complete(user.get(k) for k in ('api_key','client_id','client_secret'))
