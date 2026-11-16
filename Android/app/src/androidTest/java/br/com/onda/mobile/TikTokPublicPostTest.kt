package br.com.onda.mobile

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.chaquo.python.Python
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class TikTokPublicPostTest {
    @Test fun publicMobileFallbackDownloadsReportedVideo() {
        val context=InstrumentationRegistry.getInstrumentation().targetContext
        MobileEngine.initialize(context)
        val py=Python.getInstance()
        val globals=py.getModule("builtins").callAttr("dict")
        globals.callAttr("__setitem__","output_dir",context.cacheDir.absolutePath)
        py.getModule("builtins").callAttr("exec", """
import requests
from pathlib import Path
from unittest.mock import patch
from yt_dlp.utils import ExtractorError
from tiktok_media import TikTokMediaIE, tiktok_items
session=requests.Session()
response=session.get('https://vt.tiktok.com/ZSpQEAs7E/',timeout=25)
response.raise_for_status()
assert '/video/7025252595191106821' in response.url
with patch.object(TikTokMediaIE,'extract',side_effect=ExtractorError('Unable to extract universal data for rehydration')):
    items=tiktok_items(response.url,session)
assert len(items)==1 and items[0][1]['extension']=='mp4'
output=Path(output_dir)/'tiktok-public-fallback.mp4'
try:
    with session.get(items[0][0],headers=items[0][1].get('_http_headers',{}),stream=True,timeout=(15,30)) as media:
        media.raise_for_status()
        size=0
        with output.open('wb') as stream:
            for chunk in media.iter_content(65536):
                size+=len(chunk)
                assert size<=25*1024*1024
                stream.write(chunk)
    assert output.stat().st_size>10000
    assert b'ftyp' in output.open('rb').read(64)
    verified=True
finally:
    output.unlink(missing_ok=True)
""".trimIndent(),globals)
        assertTrue(globals.callAttr("__getitem__","verified").toBoolean())
    }
}
