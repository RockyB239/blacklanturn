import unittest

import watch_tonight as queue

HELPER = 'plugin://plugin.video.themoviedb.helper/?'
MOVIE = {'file': HELPER+'info=play&tmdb_type=movie&tmdb_id=25', 'title': 'Movie'}
EPISODE = {
    'file': HELPER+'info=play&tmdb_type=tv&tmdb_id=25&season=1&episode=2',
    'title': 'Episode', 'showtitle': 'Show',
}


class WatchTonight(unittest.TestCase):
    def test_queue_distinguishes_movie_and_individual_episodes(self):
        config = {'Saved': [MOVIE]}
        result = queue.toggle(queue.toggle(config, MOVIE), EPISODE)
        self.assertEqual([queue.item_key(item) for item in queue.entries(result)],
                         [('movie', 25), ('episode', 25, 1, 2)])
        self.assertEqual(result['Saved'], config['Saved'])
        self.assertEqual(config, {'Saved': [MOVIE]})
        self.assertEqual(queue.label(EPISODE), 'Show · S01 · E02 — Episode')

    def test_reorder_and_remove_keep_next_item_and_other_preferences(self):
        config = queue.toggle(queue.toggle({'Keep': True}, MOVIE), EPISODE)
        reordered = queue.edit(config, queue.item_key(EPISODE), 'up')
        self.assertEqual(queue.entries(reordered)[0]['title'], 'Episode')
        self.assertEqual(queue.edit(reordered, queue.item_key(EPISODE), 'up'), reordered)
        removed = queue.toggle(reordered, EPISODE)
        self.assertEqual([item['title'] for item in queue.entries(removed)], ['Movie'])
        self.assertTrue(removed['Keep'])

    def test_queue_never_saves_a_series_or_playback_override(self):
        self.assertIsNone(queue.item_key({'file': HELPER+'info=seasons&tmdb_type=tv&tmdb_id=25'}))
        original = dict(EPISODE, file=EPISODE['file']+'&ignore_default=true', _resolver='private')
        item = queue.entries(queue.toggle({}, original))[0]
        self.assertEqual(item['file'], EPISODE['file'])
        self.assertNotIn('_resolver', item)
        with self.assertRaises(ValueError):
            queue.toggle({'WatchTonight': [None]}, MOVIE)
