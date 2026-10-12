import unittest
from unittest.mock import Mock
from social_media import GalleryLogger, access_error
from tiktok_media import post_items


class TikTokPhotoTests(unittest.TestCase):
    def test_photos_keep_order_and_do_not_use_cover_or_music(self):
        post = {"id": "123", "author": {"uniqueId": "user"}, "desc": "Photos",
                "video": {"cover": "https://cdn.example/cover.jpg"}, "music": {"playUrl": "https://cdn.example/music.mp3"},
                "imagePost": {"images": [
                    {"imageURL": {"urlList": ["https://cdn.example/one.webp"]}, "imageWidth": 1080, "imageHeight": 1920},
                    {"imageURL": {"urlList": ["https://cdn.example/two.jpg"]}}]}}
        result = list(post_items(Mock(), post, "https://www.tiktok.com/@user/video/123"))
        self.assertEqual([m["extension"] for _, m in result], ["webp", "jpg"])
        self.assertEqual([m["num"] for _, m in result], [1, 2])
        self.assertEqual(result[0][1]["height"], 1920)
        self.assertEqual([url for url, _ in result], ["https://cdn.example/one.webp", "https://cdn.example/two.jpg"])

    def test_missing_photo_is_not_silently_omitted(self):
        for image_post in ({"images": []}, {"images": [{"imageURL": {"urlList": ["file:///bad.jpg"]}}]}):
            with self.subTest(post=image_post), self.assertRaises(ValueError):
                list(post_items(Mock(), {"id": "123", "imagePost": image_post}, "https://www.tiktok.com/@user/video/123"))

    def test_gallery_logger_exposes_original_failure_without_crashing(self):
        emit = Mock()
        logger = GalleryLogger(emit)
        logger.traceback(ValueError("invalid metadata"))
        logger.error("Failed to extract post (%s)", "invalid metadata")
        self.assertEqual(logger.errors, ["Failed to extract post (invalid metadata)"])
        self.assertIn("ValueError: invalid metadata", emit.call_args_list[0].kwargs["message"])

    def test_programming_errors_do_not_claim_login_required(self):
        error = access_error(AttributeError("'Logger' object has no attribute 'traceback'"))
        self.assertNotIn("cookies", error)
        self.assertIn("traceback", error)
        self.assertIn("cookies", access_error(ValueError("Login required")))


if __name__ == "__main__":
    unittest.main()
