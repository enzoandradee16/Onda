package br.com.onda.mobile

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.chaquo.python.Python
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class ToolUpdatesFlowTest {
    @Test fun bundledToolsAndVerifiedUpdateWorkOnAndroid() {
        val context=InstrumentationRegistry.getInstrumentation().targetContext
        OndaStore.initialize(context);MobileEngine.initialize(context)
        val result=MobileEngine.call(context,"tools-update-test","update",JSONObject(),EventCallback {})
        assertFalse(result.toString(),result.has("error"))
        val versions=result.getJSONObject("versions")
        for(name in listOf("yt-dlp","yt-dlp-ejs","gallery-dl","mutagen","requests"))assertTrue(name,versions.has(name))
        val checked=MobileEngine.call(context,"tools-check-test","tools_check",JSONObject(),EventCallback {})
        assertFalse(checked.toString(),checked.has("error"))
        assertTrue(checked.toString(),checked.getJSONObject("display").getBoolean("can_restart"))
        val scope=Python.getInstance().getModule("builtins").callAttr("dict")
        scope.callAttr("__setitem__","root",context.filesDir.absolutePath)
        Python.getInstance().getModule("builtins").callAttr("exec","""
import importlib.metadata as md
from pathlib import Path
from PIL import Image
from io import BytesIO
from mobile_tool_updates import activate
assert md.version('gallery-dl') == '1.32.20'
assert md.version('mutagen') == '1.48.1'
assert md.version('requests') == '2.34.2'
image = Image.new('RGB', (16, 16), 'red')
buffer = BytesIO()
image.save(buffer, format='JPEG')
assert Image.open(BytesIO(buffer.getvalue())).size == (16, 16)
# Identical packages must not override the copies in a newer APK.
assert not activate(root)
assert (Path(root)/'tools/python-updates/active').is_file()
import requests
from unittest.mock import patch
from mobile_tool_updates import prepare
pointer = Path(root)/'tools/python-updates/active'
generation = pointer.read_text()
download = requests.get
def metadata_only(url, **kwargs):
    assert url.startswith('https://pypi.org/pypi/'), url
    return download(url, **kwargs)
with patch.object(requests, 'get', side_effect=metadata_only):
    prepare(root)
assert pointer.read_text() == generation
""".trimIndent(),scope)
    }
}
