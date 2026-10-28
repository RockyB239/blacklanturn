from tmdbhelper.lib.monitor.scrobble import ScrobbleRequest, ScrobbleResult


class ProviderScrobbler(ScrobbleRequest):
    def get_scrobbler_item(self):
        player = self.player
        if player.tmdb_type == 'movie':
            return {'movie': {'ids': {'tmdb': player.tmdb_id}}, 'progress': player.progress}
        if player.tmdb_type == 'tv' and player.season >= 0 and player.episode > 0:
            return {'show': {'ids': {'tmdb': player.tmdb_id}},
                    'episode': {'season': player.season, 'number': player.episode}, 'progress': player.progress}

    def send_request(self, method, payload):
        api = self.provider.api
        return api.get_api_request(api.get_request_url('scrobble', method),
                                   postdata=payload, headers=api.headers, method='json')

    def get_result(self, method, response):
        successful = response.status_code in (200, 201, 204)
        if not successful or method != 'stop' or response.status_code == 204:
            return ScrobbleResult(successful, False)
        try:
            data = response.json()
        except ValueError:
            return ScrobbleResult(False, False)
        return ScrobbleResult(True, data.get('action') == 'scrobble')
