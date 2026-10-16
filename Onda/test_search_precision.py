import unittest
from unittest.mock import MagicMock, Mock, patch
from matching import find_youtube, score_candidate, NoCompatibleMatch

class SearchPrecisionTests(unittest.TestCase):
    def test_secondary_credited_artist_matches_without_rewriting_metadata(self):
        record=dict(title="Uccidere in silenzio 3",artists=["Nora Orlandi","Stelvio Cipriani"],duration_ms=91546)
        video=dict(id="YkVZmZN-rU8",title="STELVIO CIPRIANI - Uccidere in silenzio 3",duration=90)
        self.assertGreater(score_candidate(record,video),.84)
        self.assertEqual(record["artists"],["Nora Orlandi","Stelvio Cipriani"])
        for changes in [dict(duration=200),dict(title="STELVIO CIPRIANI - Uccidere in silenzio 22"),dict(title="STELVIO CIPRIANI - Uccidere in silenzio 3 Remix")]:
            self.assertIsNone(score_candidate(record,dict(video,**changes)))
    def test_exact_search_recovers_hidden_topic_upload(self):
        record=dict(title="Our Lives",artists=["David T. Walker"],duration_ms=260640)
        video=dict(id="UzB1NqAFY94",title="Our Lives",channel="David T. Walker - Topic",duration=261)
        downloader=MagicMock();extract=downloader.__enter__.return_value.extract_info
        extract.side_effect=[dict(entries=[]),dict(entries=[video])]
        with patch("yt_dlp.YoutubeDL",return_value=downloader),patch("artist_alias_lookup.discover_aliases") as aliases:
            self.assertEqual(find_youtube(record,Mock(),prefer_best=True)["id"],video["id"])
        self.assertEqual(extract.call_count,2);aliases.assert_not_called()
        self.assertEqual(extract.call_args.args[0], 'ytsearch8:"David T. Walker" "Our Lives"')
    def test_exact_search_does_not_accept_another_version(self):
        record=dict(title="Our Lives",artists=["David T. Walker"],duration_ms=260640)
        video=dict(id="UzB1NqAFY94",title="Our Lives Remix",channel="David T. Walker - Topic",duration=261)
        downloader=MagicMock();extract=downloader.__enter__.return_value.extract_info
        extract.side_effect=[dict(entries=[]),dict(entries=[video])]
        with patch("yt_dlp.YoutubeDL",return_value=downloader),patch("artist_alias_lookup.discover_aliases",return_value=[]),patch("catalog_aliases.alternate_records",return_value=[]):
            with self.assertRaises(NoCompatibleMatch):find_youtube(record,Mock(),prefer_best=True)
        self.assertEqual(extract.call_count,2)

if __name__=="__main__":unittest.main()
