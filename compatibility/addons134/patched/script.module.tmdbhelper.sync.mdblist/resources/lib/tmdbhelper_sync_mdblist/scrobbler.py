from jurialmunkey.parser import try_int
from tmdbhelper.lib.monitor.scrobble import ScrobbleRequest, ScrobbleResult


class ProviderScrobbler(ScrobbleRequest):
    def get_scrobbler_item(self):
        player = self.player
        if player.tmdb_type == 'movie':
            return {'movie': {'ids': {'tmdb': try_int(player.tmdb_id)}}, 'progress': try_int(player.progress)}
        if player.tmdb_type == 'tv' and player.season >= 0 and player.episode > 0:
            return {'show': {'ids': {'tmdb': try_int(player.tmdb_id)},
                             'season': player.season, 'episode': player.episode}, 'progress': try_int(player.progress)}

    def send_request(self, method, payload):
        api = self.provider.api
        return api.get_simple_api_request(api.get_request_url('scrobble', method),
                                          postdata=payload, headers=api.headers, method='json')

    def get_result(self, method, response):
        result = super().get_result(method, response)
        if not result.successful or response.status_code == 204:
            return result
        try:
            data = response.json()
        except ValueError:
            return ScrobbleResult(False, False)
        successful = bool(data) and not (data.get('error') or data.get('errors')
                                        or any(data.get('not_found', {}).values()))
        return ScrobbleResult(successful, successful and result.history_changed)
