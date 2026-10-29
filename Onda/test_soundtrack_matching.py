import unittest
from unittest.mock import MagicMock, Mock, patch
from matching import score_candidate, find_youtube, version_signature


class SoundtrackMatchingTests(unittest.TestCase):
    def record(
        self,
        title,
        duration=200000,
        album='Example Film (Original Motion Picture Soundtrack)',
    ):
        return dict(
            title=title, artists=['Piero Piccioni'], duration_ms=duration, album=album
        )

    def video(self, title, duration=200):
        return dict(
            id='abcdefghijk', title=title, channel='Piero Piccioni', duration=duration
        )

    def test_film_presentation_prefix_is_not_a_different_title(self):
        for title in [
            'Film Music | "La Famiglia" ● Piero Piccioni (HD Audio)',
            'RETRO TV Music | "La Famiglia" - Piero Piccioni',
        ]:
            self.assertGreater(
                score_candidate(self.record('La Famiglia'), self.video(title)), 0.94
            )

    def test_music_brand_and_original_score_are_presentation_only(self):
        self.assertGreater(
            score_candidate(
                self.record('Project for a Dream'),
                self.video(
                    'Project for a Dream - Piero Piccioni (Original Score) [LoFilm Music]'
                ),
            ),
            0.94,
        )

    def test_artist_anniversary_campaign_keeps_actual_cue(self):
        title = '#PieroPiccioni100 - Miss Luna Special (100th Anniversary Edition) - The Story of Cinema Italiano'
        self.assertGreater(
            score_candidate(self.record('Miss Luna Special'), self.video(title)), 0.94
        )
        self.assertIsNone(
            score_candidate(
                self.record('Miss Luna Special'),
                self.video(title.replace('PieroPiccioni100', 'OtherArtist100')),
            )
        )

    def test_actor_credits_require_known_film_and_artist(self):
        record = self.record(
            'Golpe Errado',
            album='Professor Kranz Tedesco di Germania (Original Motion Picture Soundtrack)',
        )
        title = 'Paolo Villaggio ● Professor Kranz Tedesco di Germania - Golpe Errado ● Piero Piccioni'
        self.assertGreater(score_candidate(record, self.video(title)), 0.94)
        self.assertIsNone(
            score_candidate(
                record,
                self.video(
                    title.replace('Professor Kranz Tedesco di Germania', 'Other Movie')
                ),
            )
        )

    def test_standalone_cue_between_artist_and_known_film(self):
        record = self.record(
            'Addio, amore mio',
            album='Amore mio aiutami (Original Motion Picture Soundtrack)',
        )
        title = 'Piero Piccioni - Alberto Sordi ● Addio amore mio ● Amore mio aiutami (High Quality Audio)'
        self.assertGreater(score_candidate(record, self.video(title)), 0.94)

    def test_version_numbers_remain_distinct_across_presentation_styles(self):
        record = self.record('Amore mio aiutami - Version 2')
        title = 'Alberto Sordi 100 - Amore mio aiutami #2 - by Piero Piccioni (Colonna Sonora Originale)'
        self.assertGreater(score_candidate(record, self.video(title)), 0.94)
        self.assertIsNone(
            score_candidate(record, self.video(title.replace('#2', '#3')))
        )
        self.assertIsNone(
            score_candidate(record, self.video('Piero Piccioni - Amore mio aiutami'))
        )
        self.assertEqual(
            version_signature('Cue Version 3'), version_signature('Cue part.3')
        )
        self.assertNotEqual(
            version_signature('Cue Version 2'), version_signature('Cue part.3')
        )

    def test_joined_repeated_camelcase_syllables(self):
        self.assertGreater(
            score_candidate(
                self.record('Do You ChaChaCha'),
                self.video('Film Music | "Do You Cha Cha Cha" ● Piero Piccioni'),
            ),
            0.94,
        )
        self.assertIsNone(
            score_candidate(
                self.record('Do You ChaChaCha'),
                self.video('Piero Piccioni - Do You Tango'),
            )
        )

    def test_edition_duration_and_wrong_song_guards_are_not_relaxed(self):
        record = self.record('La Famiglia')
        for title in [
            'Film Music | La Famiglia Remix',
            'Film Music | La Famiglia Live',
            'Film Music | La Famiglia Medley',
            'Film Music | La Famiglia Looped',
            'Film Music | La Famiglia Reverb',
            'Film Music | La Famiglia Other Song',
        ]:
            with self.subTest(title=title):
                self.assertIsNone(score_candidate(record, self.video(title)))
        self.assertIsNone(
            score_candidate(
                record,
                self.video('Film Music | La Famiglia ● Piero Piccioni', duration=400),
            )
        )

    def test_from_movie_label_requires_matching_album(self):
        record = self.record(
            'Classic Lover', album='Camille 2000 (Original Motion Picture Soundtrack)'
        )
        self.assertGreater(
            score_candidate(record, self.video('Classic Lover (From "Camille 2000")')),
            0.94,
        )
        self.assertIsNone(
            score_candidate(record, self.video('Classic Lover (From "Another Film")'))
        )

    def test_album_query_is_bounded_and_only_used_after_other_paths_fail(self):
        record = self.record(
            'Classic Lover', album='Camille 2000 (Original Motion Picture Soundtrack)'
        )
        video = self.video('Classic Lover (From "Camille 2000")')
        downloader = MagicMock()
        extract = downloader.__enter__.return_value.extract_info
        extract.side_effect = [
            dict(entries=[]),
            dict(entries=[]),
            dict(entries=[video]),
        ]
        with (
            patch('yt_dlp.YoutubeDL', return_value=downloader),
            patch('artist_alias_lookup.discover_aliases', return_value=[]),
            patch('catalog_aliases.alternate_records', return_value=[]),
        ):
            self.assertEqual(
                find_youtube(record, Mock(), prefer_best=True)['id'], video['id']
            )
        self.assertEqual(extract.call_count, 3)
        self.assertIn('Camille 2000', extract.call_args.args[0])
        self.assertNotIn(
            'Original Motion Picture Soundtrack', extract.call_args.args[0]
        )


if __name__ == '__main__':
    unittest.main()
