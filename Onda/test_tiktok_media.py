import unittest
from unittest.mock import Mock, MagicMock
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


class MobileTikTokTests(unittest.TestCase):
    def test_mobile_html_uses_mobile_agent_and_validates_requested_id(self):
        from tiktok_media import mobile_post,MOBILE_USER_AGENT
        source=Mock();source._match_id.return_value='123'
        source._get_universal_data.return_value={'webapp.video-detail':{'statusCode':0,'itemInfo':{'itemStruct':{'id':'123','desc':'Correct post'}}}}
        session=MagicMock();response=session.get.return_value.__enter__.return_value
        response.iter_content.return_value=[b'<html>fixture</html>']
        self.assertEqual(mobile_post(source,session,'https://www.tiktok.com/@user/video/123')['id'],'123')
        self.assertEqual(session.get.call_args.kwargs['headers']['User-Agent'],MOBILE_USER_AGENT)
        response.raise_for_status.assert_called_once()
    def test_mobile_html_rejects_other_posts_and_unavailable_posts(self):
        from tiktok_media import mobile_post
        from yt_dlp.utils import ExtractorError
        source=Mock();source._match_id.return_value='123'
        session=MagicMock();session.get.return_value.__enter__.return_value.iter_content.return_value=[b'fixture']
        for detail in ({'statusCode':0,'itemInfo':{'itemStruct':{'id':'999'}}},{'statusCode':10216},{}):
            source._get_universal_data.return_value={'webapp.video-detail':detail}
            with self.assertRaises(ExtractorError):mobile_post(source,session,'https://www.tiktok.com/@user/video/123')
    def test_public_embed_preserves_id_author_and_video_stream(self):
        from tiktok_media import embedded_post
        item={'id':'123','text':'Test','video':{'urls':['https://cdn.example/video.mp4'],'videoMeta':{'width':576,'height':1024,'duration':57}}}
        state={'source':{'data':{'/embed/v2/123':{'videoData':{'itemInfos':item,'authorInfos':{'uniqueId':'author'}}}}}}
        result=embedded_post(state,'123')
        self.assertEqual(result['author']['uniqueId'],'author')
        self.assertEqual(result['video']['playAddr'],[{'src':'https://cdn.example/video.mp4'}])
        self.assertEqual(result['video']['duration'],57)
        for field in ('secret','forFriend'):
            item[field]=True
            from yt_dlp.utils import ExtractorError
            with self.assertRaises(ExtractorError):embedded_post(state,'123')
            item.pop(field)
        item['id']='999'
        with self.assertRaises(ExtractorError):embedded_post(state,'123')

    def test_embed_photos_use_explicit_images_not_cover(self):
        from tiktok_media import embedded_post
        state={'source':{'data':{'/embed/v2/123':{'videoData':{'itemInfos':{'id':'123','covers':['https://cdn.example/cover.jpg']},'imagePostInfo':{'displayImages':[{'urlList':['https://cdn.example/one.jpg'],'width':720,'height':1280},{'urlList':['https://cdn.example/two.jpg']}]}}}}}}
        result=embedded_post(state,'123')
        rows=list(post_items(Mock(),result,'https://www.tiktok.com/@user/video/123'))
        self.assertEqual([url for url,_ in rows],['https://cdn.example/one.jpg','https://cdn.example/two.jpg'])
        self.assertEqual(rows[0][1]['height'],1280)
    def test_mobile_page_retries_transient_error_once(self):
        from tiktok_media import mobile_post
        from unittest.mock import patch
        source=Mock();source._match_id.return_value='123';source._get_universal_data.return_value={'webapp.video-detail':{'statusCode':0,'itemInfo':{'itemStruct':{'id':'123'}}}}
        first=MagicMock();first.__enter__.return_value=first;first.status_code=503;first.headers={'Retry-After':'0'}
        second=MagicMock();second.__enter__.return_value=second;second.status_code=200;second.iter_content.return_value=[b'fixture']
        session=Mock();session.get.side_effect=[first,second]
        with patch('time.sleep') as sleep:self.assertEqual(mobile_post(source,session,'https://www.tiktok.com/@user/video/123')['id'],'123')
        self.assertEqual(session.get.call_count,2);sleep.assert_called_once_with(.5)

    def test_mobile_page_has_bounded_size(self):
        from tiktok_media import mobile_post
        source=Mock();source._match_id.return_value='123';session=MagicMock()
        session.get.return_value.__enter__.return_value.iter_content.return_value=[b'x'*(8*1024*1024+1)]
        with self.assertRaisesRegex(ValueError,'limite'):mobile_post(source,session,'https://www.tiktok.com/@user/video/123')


if __name__ == "__main__":
    unittest.main()
