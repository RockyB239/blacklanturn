import importlib.util
from pathlib import Path
import unittest


MODULE = Path(__file__).resolve().parents[1] / 'controller-source/addon/adaptive_services.py'
HELPER = 'plugin://plugin.video.themoviedb.helper/?'


def movie(ident):
    return {'file': f'{HELPER}info=play&tmdb_type=movie&tmdb_id={ident}', 'filetype': 'file'}


def movies(*identifiers):
    return [movie(ident) for ident in identifiers]


class AdaptiveServicesTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(MODULE.is_file(), 'The adaptive service rules module has not been implemented')
        spec = importlib.util.spec_from_file_location('adaptive_services', MODULE)
        self.rules = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.rules)

    def test_movie_profile_does_not_follow_name_or_channel_variant(self):
        self.assertTrue(self.rules.film_first('11'))
        self.assertTrue(self.rules.film_first(258))
        self.assertFalse(self.rules.film_first('MUBI'))
        self.assertFalse(self.rules.film_first(350))
        self.assertEqual(self.rules.candidate_filters('tv', 11), ())
        self.assertEqual(self.rules.candidate_filters('movie', 350), ())
        self.assertEqual(self.rules.candidate_filters('episode', 283), ())

    def test_filters_match_the_audited_movie_and_show_meaning(self):
        cinema = dict(self.rules.candidate_filters('movie', 11))
        self.assertEqual(cinema['World Cinema']['with_origin_country'], 'FR|IT|JP|KR|DE|ES|IN|BR|MX|SE|HK|DK|IR|TW')
        self.assertEqual(cinema['Classics Before 1990'], {
            'primary_release_date.lte': '1989-12-31', 'vote_average.gte': '6.5', 'vote_count.gte': '15',
        })
        self.assertEqual(cinema['Film Noir'], {'with_keywords': '9807'})
        shows = dict(self.rules.candidate_filters('tv', '283'))
        self.assertEqual(shows['Anime Action'], {'with_genres': '16,10759', 'with_original_language': 'ja'})
        self.assertEqual(shows['Classic Anime Before 2000']['first_air_date.lte'], '1999-12-31')
        cooking = dict(self.rules.candidate_filters('tv', 2068))
        self.assertEqual(cooking['Food & Travel'], {'with_keywords': '10637,9935'})

    def test_history_documents_need_a_specific_subject(self):
        shows = dict(self.rules.candidate_filters('tv', 190))
        self.assertNotIn('History Documentaries', shows)
        self.assertEqual(shows['World War II Documentaries'], {'with_genres': '99', 'with_keywords': '1956'})

    def test_only_exact_provider_media_and_filter_combinations_are_approved(self):
        valid = {'with_genres': '27', 'with_keywords': '6152|10224|15001'}
        self.assertTrue(self.rules.valid_specialty_filters('movie', '99', valid))
        self.assertFalse(self.rules.valid_specialty_filters('tv', '99', valid))
        self.assertFalse(self.rules.valid_specialty_filters('movie', '80', valid))
        self.assertFalse(self.rules.valid_specialty_filters('movie', '099', valid))
        self.assertFalse(self.rules.valid_specialty_filters('movie', 99, {}))
        self.assertFalse(self.rules.valid_specialty_filters('movie', 99, {'with_keywords': '6152|10224|15001'}))
        self.assertFalse(self.rules.valid_specialty_filters('movie', 99, dict(valid, include_adult='true')))
        self.assertFalse(self.rules.valid_specialty_filters('movie', 99, dict(valid, with_keywords='6152%7C10224%7C15001')))
        self.assertFalse(self.rules.valid_specialty_filters('movie', 190, {'with_genres': '99', 'with_keywords': '282633'}))

    def test_returned_filters_cannot_change_what_later_requests_approve(self):
        label, filters = self.rules.candidate_filters('movie', 99)[0]
        self.assertEqual(label, 'Slashers')
        filters['with_keywords'] = '1'
        self.assertFalse(self.rules.valid_specialty_filters('movie', 99, filters))
        self.assertTrue(self.rules.valid_specialty_filters('movie', 99, {'with_genres': '27', 'with_keywords': '12339'}))

    def test_preview_requires_four_unique_titles_and_ignores_paging(self):
        alternate_path = {'type': 'movie', 'uniqueid': {'tmdb': '1'}}
        next_page = {
            'file': f'{HELPER}info=discover&tmdb_type=movie&page=2',
            'filetype': 'directory', 'uniqueid': {'tmdb': '91'},
        }
        previous = dict(movie(92), _page_control='previous')
        candidate = [*movies(1, 2, 3), alternate_path, next_page, previous]
        self.assertFalse(self.rules.qualify_shelf([], [], candidate))
        self.assertTrue(self.rules.qualify_shelf([], [], [*candidate, movie(4)]))

    def test_at_least_half_the_preview_differs_from_each_preceding_shelf(self):
        baseline = movies(1, 2, 3, 4)
        candidate = movies(1, 2, 5, 6)
        self.assertTrue(self.rules.qualify_shelf(baseline, [], candidate))
        self.assertTrue(self.rules.qualify_shelf(baseline, [movies(5, 7, 8, 9)], candidate))
        self.assertFalse(self.rules.qualify_shelf(baseline, [movies(1, 5, 6, 9)], candidate))
        self.assertFalse(self.rules.qualify_shelf(movies(1, 2, 3, 4, 5, 6), [], movies(1, 2, 5, 7, 8)))

    def test_only_first_eight_distinct_preview_titles_measure_overlap(self):
        candidate = movies(1, 1, 2, 3, 4, 5, 6, 7, 8, 100, 101)
        self.assertFalse(self.rules.qualify_shelf(movies(1, 2, 3, 4, 5), [], candidate))
        earlier = [movies(11, 12, 13, 14, 15, 16, 17, 18, 5)]
        self.assertTrue(self.rules.qualify_shelf(movies(1, 2, 3, 4), earlier, candidate))

    def test_show_path_and_unique_id_represent_the_same_title(self):
        baseline = [
            {'file': f'{HELPER}info=seasons&tmdb_type=tv&tmdb_id=1', 'filetype': 'directory'},
            {'type': 'tvshow', 'uniqueid': {'tvshow.tmdb': 2}},
            {'type': 'tvshow', 'uniqueid': {'tmdb': 3}},
        ]
        candidate = [{'type': 'tvshow', 'uniqueid': {'tvshow.tmdb': n}} for n in range(1, 5)]
        self.assertFalse(self.rules.qualify_shelf(baseline, [], candidate))
        self.assertTrue(self.rules.qualify_shelf(movies(1, 2, 3), [], candidate))
