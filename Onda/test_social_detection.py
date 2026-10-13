import io
import json
import os
import unittest
from unittest.mock import Mock, patch

from engine import ask_media
from instagram_media import product_items
from kwai import find_post, nuxt_objects, OndaKwaiIE
from social_media import download_selected, access_error, download_post


NUXT = '''<script>window.__NUXT__=(function(a,w,h,x){x[0]={photo_id:5209126029585908000,photo_id_str:"5209126029585907740",user_name:"Autor",kwai_id:"autor",caption:"Texto {com} chaves, w: preservado",ext_params:{cw:w,ch:h,interval:30,video:1000},transcode_manifest_info:{adaptationSet:[{representation:[{id:1,url:"https:\\u002F\\u002Fcdn.example.com\\u002Fvideo.mp4",width:w,height:h,frameRate:30,avgBitrate:800,fileSize:100000,videoCodec:"avc",sharpness:.4}]}]}};x[1]={photo_id_str:"outra",main_mv_urls:[{url:"https://cdn.example.com/errado.mp4"}]};return {videoList:x}}(false,720,1280,Array(2)));</script>'''


class DetectionTests(unittest.TestCase):
    def test_video_only_post_overrides_photo_mode_and_keeps_picker(self):
        items = [(f"https://cdn.example/{i}.mp4", {"extension": "mp4", "num": i,
                  "_video_info": {"formats": [{"url": f"https://cdn.example/{i}.mp4"}]}}) for i in range(1, 4)]
        config = {"mode": "photos", "height": 720, "fps": 30}
        emit, choose = Mock(), Mock(return_value=["2"])
        with patch("social_media.save_video", return_value="saved.mp4") as save:
            self.assertEqual(download_selected(items, Mock(), config, emit, Mock(), choose), ["saved.mp4"])
        self.assertEqual(save.call_args.args[2], {"mode": "mp4", "height": 720, "fps": 30})
        self.assertEqual(config["mode"], "photos")
        self.assertEqual(save.call_args.args[-1], 2)
        self.assertEqual(len(choose.call_args.args[0]), 3)

    def test_photo_only_post_ignores_video_format(self):
        items = [("https://cdn.example/a.jpg", {"extension": "jpg"})]
        with patch("social_media.save_media", return_value="saved.jpg") as save:
            self.assertEqual(download_selected(items, Mock(), {"mode": "mp4"}, Mock(), Mock()), ["saved.jpg"])
        save.assert_called_once()

    def test_mixed_post_still_allows_explicit_photos_filter(self):
        items = [("https://cdn.example/a.mp4", {"extension": "mp4"}),
                 ("https://cdn.example/b.jpg", {"extension": "jpg", "num": 2})]
        with patch("social_media.save_media", return_value="saved.jpg") as save:
            self.assertEqual(download_selected(items, Mock(), {"mode": "photos"}, Mock(), Mock()), ["saved.jpg"])
        self.assertEqual(save.call_args.args[1], "https://cdn.example/b.jpg")
        self.assertEqual(save.call_args.args[-1], 2)

    def test_tiktok_detects_actual_media_even_in_photo_mode(self):
        config = {"url": "https://www.tiktok.com/@autor/video/1234567890123456789", "mode": "photos"}
        items = [("https://cdn.example/a.mp4", {"extension": "mp4", "_video_info": {}})]
        with patch("gallery_dl.extractor.find") as find, patch("tiktok_media.tiktok_items", return_value=items), patch("social_media.save_media", return_value="saved.mp4") as save:
            self.assertTrue(download_post(config, Mock(), Mock()))
        self.assertEqual(save.call_args.args[3]["mode"], "mp4")
        find.assert_not_called()

    def test_kwai_alias_keys_decimals_and_exact_id(self):
        post = find_post(NUXT, "5209126029585907740")
        self.assertIsNotNone(post)
        self.assertEqual(post["ext_params"]["cw"], 720)
        self.assertEqual(post["ext_params"]["ch"], 1280)
        self.assertIn("w: preservado", post["caption"])
        representation = post["transcode_manifest_info"]["adaptationSet"][0]["representation"][0]
        self.assertEqual(representation["sharpness"], .4)
        self.assertIsNone(find_post(NUXT, "missing"))

    def test_kwai_does_not_evaluate_arbitrary_scripts(self):
        self.assertEqual(nuxt_objects('window.__NUXT__=(function(a){x[0]={photo_id_str:a}}(alert("test")));'), [])

    def test_kwai_extractor_metadata(self):
        from yt_dlp import YoutubeDL
        with YoutubeDL({"quiet": True}) as downloader:
            source = OndaKwaiIE(downloader)
            with patch.object(source, "_download_webpage_handle", return_value=(NUXT, Mock(url="https://www.kwai.com/@autor/video/5209126029585907740"))):
                info = source._real_extract("https://kwai-video.com/p/test")
        self.assertEqual(info["id"], "5209126029585907740")
        self.assertEqual(info["formats"][0]["width"], 720)
        self.assertEqual(info["formats"][0]["tbr"], 800)
        self.assertEqual(info["duration"], 1)
        self.assertNotIn("errado", info["formats"][0]["url"])

    def test_instagram_keeps_mixed_media_and_largest_photo(self):
        source = Mock()
        source._extract_product_media.return_value = {"id": "video", "formats": [{"url": "https://cdn.example/video.mp4"}]}
        product = {"user": {"username": "autor"}, "caption": {"text": "Minha publicação"}, "carousel_media": [
            {"media_type": 1, "image_versions2": {"candidates": [
                {"url": "https://cdn.example/small.jpg", "width": 100, "height": 100},
                {"url": "https://cdn.example/large.jpg", "width": 1200, "height": 1600}]}},
            {"media_type": 2, "video_versions": [{"url": "https://cdn.example/video.mp4"}],
             "image_versions2": {"candidates": [{"url": "https://cdn.example/cover.jpg"}]}},
            {"media_type": 1, "image_versions2": {"candidates": [{"url": "https://cdn.example/last.jpg"}]}}]}
        items = list(product_items(source, product))
        self.assertEqual([metadata["extension"] for _, metadata in items], ["jpg", "mp4", "jpg"])
        self.assertEqual(items[0][0], "https://cdn.example/large.jpg")
        self.assertEqual([metadata["num"] for _, metadata in items], [1, 2, 3])

    def test_only_chosen_items_download_in_original_order(self):
        items = [(f"https://cdn.example/{i}.jpg", {"extension": "jpg", "num": i}) for i in range(1, 5)]
        choose = Mock(return_value=["4", "2"])
        with patch("social_media.save_media", side_effect=lambda *args: str(args[-1])) as save:
            result = download_selected(items, Mock(), {"mode": "social"}, Mock(), Mock(), choose)
        self.assertEqual(result, ["2", "4"])
        self.assertEqual(save.call_count, 2)
        self.assertEqual(len(choose.call_args.args[0]), 4)

    def test_one_or_two_items_download_without_selection_dialog(self):
        choose = Mock()
        for count in (1, 2):
            items = [(f"https://cdn.example/{i}.jpg", {"extension": "jpg"}) for i in range(count)]
            with patch("social_media.save_media", return_value="saved"):
                self.assertEqual(len(download_selected(items, Mock(), {"mode": "social"}, Mock(), Mock(), choose)), count)
        choose.assert_not_called()

    def test_selection_ipc_validation(self):
        candidates = [{"id": "1"}, {"id": "2"}, {"id": "3"}]
        with patch("engine.emit"):
            self.assertEqual(ask_media(candidates, io.StringIO('{"selected_ids":["1","3"]}\n')), ["1", "3"])
            for selected in ([], ["4"], ["1", "1"], [1], "1"):
                with self.subTest(selected=selected), self.assertRaises(ValueError):
                    ask_media(candidates, io.StringIO(json.dumps({"selected_ids": selected})))

    def test_ip_block_has_specific_explanation(self):
        self.assertIn("bloqueou o acesso desta conexão", access_error(ValueError("Your IP address is blocked from accessing this post")))


@unittest.skipUnless(os.environ.get("ONDA_UI_TESTS"), "Set ONDA_UI_TESTS for picker UI tests")
class PickerUiTests(unittest.TestCase):
    def test_confirmation_button_and_multiple_selection(self):
        import tkinter as tk
        from media_picker import MediaPicker
        root = tk.Tk()
        root.social_cookies = tk.StringVar()
        root.geometry("900x650")
        root.update()
        result = Mock()
        event = {"candidates": [{"id": str(i), "number": i, "kind": "Foto", "title": "Teste"} for i in range(1, 5)]}
        picker = MediaPicker(root, event, result, Mock())
        try:
            root.update()
            self.assertTrue(picker.download_button.winfo_ismapped())
            picker.select_all(False)
            self.assertEqual(str(picker.download_button["state"]), "disabled")
            picker.variables["2"].set(True)
            picker.variables["4"].set(True)
            picker.changed()
            picker.download_button.invoke()
            result.assert_called_once_with(["2", "4"])
        finally:
            picker.destroy()
            root.destroy()


if __name__ == "__main__":
    unittest.main()
