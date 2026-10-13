import json
import unittest
from unittest.mock import Mock
from album_import import finish
from playlist_import import spotify_playlist, load_playlist
from spotify_account import SpotifyAccount

class CollectionCardTests(unittest.TestCase):
    def test_album_card_keeps_artist_and_album_artwork(self):
        result=finish("Album",[{"artists":["Artist"],"cover_url":"album-cover"}],1,100,"")
        self.assertEqual(result["cover_url"],"album-cover")
        self.assertEqual(result["subtitle"],"Artist")
        self.assertEqual(result["folder_title"],"Artist - Album")

    def test_public_playlist_uses_its_own_cover(self):
        identity="A"*22
        entity={"id":identity,"type":"playlist","title":"List","subtitle":"Owner",
                "trackList":[{"uri":"spotify:track:"+"B"*22,"title":"Song"}],
                "visualIdentity":{"image":[{"url":"large","maxHeight":640},{"url":"small","maxHeight":64}]}}
        html='<script id="__NEXT_DATA__" type="application/json">'+json.dumps({"props":{"pageProps":{"state":{"data":{"entity":entity}}}}})+'</script>'
        result=spotify_playlist(html,identity)
        self.assertEqual(result["cover_url"],"large")
        self.assertEqual(result["subtitle"],"Owner")
        self.assertEqual(len(result["tracks"]),1)

    def test_deezer_playlist_does_not_use_a_track_album_cover(self):
        client=Mock()
        client.get_json.side_effect=[{"title":"List","picture_xl":"playlist-cover","creator":{"name":"Owner"}},
                                    {"data":[{"id":1,"title":"Song","artist":{"name":"Artist"},"album":{"cover_xl":"different-album"}}]}]
        result=load_playlist("https://www.deezer.com/playlist/123",client)
        self.assertEqual(result["cover_url"],"playlist-cover")
        self.assertEqual(result["subtitle"],"Owner")

    def test_connected_spotify_playlist_without_artwork_has_placeholder_data(self):
        account=Mock(spec=SpotifyAccount)
        account.get.side_effect=[{"name":"List","owner":{"display_name":"Owner"}}, {"items":[],"total":0}]
        result=SpotifyAccount.playlist(account,"A"*22)
        self.assertIsNone(result["cover_url"])
        self.assertEqual(result["subtitle"],"Owner")
        self.assertEqual(result["tracks"],[])
