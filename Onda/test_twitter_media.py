import json
import unittest
from unittest.mock import Mock, patch
from twitter_media import is_twitter, tweet_items, twitter_items
from social_media import download_post, is_social


class TwitterTests(unittest.TestCase):
    def test_hosts_and_profile_rejection(self):
        for host in ("x.com", "twitter.com", "mobile.twitter.com", "www.x.com"):
            self.assertTrue(is_twitter(f"https://{host}/artist/status/123"))
            self.assertTrue(is_social(f"https://{host}/artist/status/123"))
        self.assertFalse(is_twitter("https://x.com.example.org/a/status/123"))
        with self.assertRaisesRegex(ValueError, "publicação"):
            twitter_items("https://x.com/artist", Mock())

    def test_mixed_order_original_photos_and_all_video_variants(self):
        source = Mock()
        source._extract_variant_formats.side_effect = lambda variant, _: ([variant], {})
        status = {
            "text": "Post misto",
            "user": {"screen_name": "artista"},
            "extended_entities": {
                "media": [
                    {
                        "type": "photo",
                        "media_url_https": "https://pbs.twimg.com/media/first.jpg?name=small",
                    },
                    {
                        "type": "video",
                        "media_url_https": "https://pbs.twimg.com/media/cover.jpg",
                        "video_info": {
                            "duration_millis": 3000,
                            "variants": [
                                {"url": "https://video.twimg.com/low.mp4"},
                                {"url": "https://video.twimg.com/high.mp4"},
                            ],
                        },
                    },
                    {
                        "type": "photo",
                        "media_url_https": "https://pbs.twimg.com/media/last.png",
                    },
                ]
            },
        }
        result = list(tweet_items(source, status, "123"))
        self.assertEqual(
            [metadata["extension"] for _, metadata in result], ["jpg", "mp4", "png"]
        )
        self.assertIn("name=orig", result[0][0])
        self.assertEqual(result[1][1]["_video_info"]["duration"], 3)
        self.assertEqual(len(result[1][1]["_video_info"]["formats"]), 2)
        self.assertEqual([metadata["num"] for _, metadata in result], [1, 2, 3])

    def test_syndication_does_not_include_quote(self):
        photo = {
            "type": "photo",
            "media_url_https": "https://pbs.twimg.com/media/own.jpg",
        }
        quote = {
            "type": "photo",
            "media_url_https": "https://pbs.twimg.com/media/quote.jpg",
        }
        result = list(
            tweet_items(
                Mock(),
                {
                    "mediaDetails": [photo],
                    "extended_entities": {"media": [photo, quote]},
                },
                "123",
            )
        )
        self.assertEqual(len(result), 1)
        self.assertIn("own.jpg", result[0][0])
        self.assertEqual(
            list(
                tweet_items(
                    Mock(),
                    {"mediaDetails": [], "extended_entities": {"media": [quote]}},
                    "123",
                )
            ),
            [],
        )

    def test_unified_card_keeps_photos_and_videos(self):
        source = Mock()
        source._extract_variant_formats.return_value = (
            [{"url": "https://video.twimg.com/a.mp4"}],
            {},
        )
        card = {
            "media_entities": {
                "video": {
                    "id_str": "1",
                    "type": "video",
                    "video_info": {
                        "variants": [{"url": "https://video.twimg.com/a.mp4"}]
                    },
                },
                "image": {
                    "id_str": "2",
                    "type": "photo",
                    "media_url_https": "https://pbs.twimg.com/media/a.jpg",
                },
            }
        }
        status = {
            "card": {
                "binding_values": [
                    {"key": "unified_card", "value": {"string_value": json.dumps(card)}}
                ]
            }
        }
        self.assertEqual(
            [m["extension"] for _, m in tweet_items(source, status, "123")],
            ["mp4", "jpg"],
        )

    def test_video_mode_routes_twitter_to_shared_selection(self):
        items = [("https://pbs.twimg.com/media/a.jpg", {"extension": "jpg"})]
        choose = Mock()
        with (
            patch("twitter_media.twitter_items", return_value=items),
            patch("social_media.download_selected", return_value=["saved"]) as selected,
        ):
            self.assertTrue(
                download_post(
                    {"url": "https://x.com/artist/status/123", "mode": "mp4"},
                    Mock(),
                    Mock(),
                    choose,
                )
            )
            self.assertEqual(selected.call_args.args[0], items)
            self.assertIs(selected.call_args.args[-1], choose)


if __name__ == "__main__":
    unittest.main()
