package br.com.onda.mobile

import android.webkit.CookieManager
import androidx.test.core.app.ApplicationProvider
import androidx.test.core.app.ActivityScenario
import androidx.test.platform.app.InstrumentationRegistry
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

class InstagramSessionUiTest {
    private val context get()=ApplicationProvider.getApplicationContext<android.content.Context>()
    private fun main(action:()->Unit)=InstrumentationRegistry.getInstrumentation().runOnMainSync(action)
    private fun launch()=ActivityScenario.launch<InstagramLoginActivity>(android.content.Intent(context,InstagramLoginActivity::class.java))

    @Test fun realInstagramLoginFormLoads() {
        launch().use {scenario->
            var state=""
            var ready=false
            repeat(50) {
                if(!ready){
                    val latch=java.util.concurrent.CountDownLatch(1)
                    scenario.onActivity {it.browser.evaluateJavascript("JSON.stringify({inputs:document.querySelectorAll('input[type=password]').length})") {value->state=value;latch.countDown()}}
                    latch.await(2,java.util.concurrent.TimeUnit.SECONDS)
                    ready=state.contains("\\\"inputs\\\":1")
                    if(!ready)Thread.sleep(500)
                }
            }
            assertTrue("Formulário não carregou: $state",ready)
            Thread.sleep(1200)
            val latch=java.util.concurrent.CountDownLatch(1)
            var result=-1
            var image:android.graphics.Bitmap?=null
            scenario.onActivity {activity->
                val view=activity.browser
                val position=IntArray(2);view.getLocationInWindow(position)
                val rect=android.graphics.Rect(position[0],position[1],position[0]+view.width,position[1]+view.height)
                image=android.graphics.Bitmap.createBitmap(view.width,view.height,android.graphics.Bitmap.Config.ARGB_8888)
                android.view.PixelCopy.request(activity.window,rect,image!!,{code->result=code;latch.countDown()},android.os.Handler(android.os.Looper.getMainLooper()))
            }
            assertTrue(latch.await(5,java.util.concurrent.TimeUnit.SECONDS));assertEquals(android.view.PixelCopy.SUCCESS,result)
            val bitmap=image!!
            java.io.File(context.getExternalFilesDir(null),"instagram-form.png").outputStream().use {bitmap.compress(android.graphics.Bitmap.CompressFormat.PNG,100,it)}
            val colors=mutableSetOf<Int>()
            for(y in 0 until bitmap.height step 8)for(x in 0 until bitmap.width step 8)colors.add(bitmap.getPixel(x,y))
            assertTrue("WebView sem conteúdo visível: cores=${colors.size}",colors.size>20)
        }
    }

    @Test fun loginWindowDoesNotAcceptAnAnonymousSession() {
        val previous=JSONObject(OndaStore.settings.value.toString())
        main {clearWebSessionCookies(listOf("https://www.instagram.com","https://instagram.com"))}
        launch().use {scenario->
            scenario.onActivity {activity->
                fun nodes(view:android.view.View):List<android.view.View> = listOf(view)+(if(view is android.view.ViewGroup)(0 until view.childCount).flatMap {nodes(view.getChildAt(it))} else emptyList())
                val views=nodes(activity.findViewById(android.R.id.content))
                (views.first {it is android.widget.Button && it.text.toString()=="Usar esta sessão"} as android.widget.Button).performClick()
                assertTrue(views.any {it is android.widget.TextView && it.text.toString()=="O login ainda não foi concluído. Entre na conta e aguarde o Instagram carregar."})
            }
            assertEquals(previous.optString("instagram_cookies_file"),OndaStore.settings.value.optString("instagram_cookies_file"))
        }
    }

    @Test fun youtubeLogoutPreservesInstagramCookies() {
        main {
            val manager=CookieManager.getInstance();manager.setAcceptCookie(true)
            manager.setCookie("https://www.instagram.com","onda_probe=instagram; Domain=.instagram.com; Path=/; Secure; HttpOnly")
            manager.setCookie("https://www.youtube.com","__Secure-onda_probe=youtube; Domain=.youtube.com; Path=/; Secure; HttpOnly");manager.flush()
            try {
                clearWebSessionCookies(listOf("https://www.youtube.com","https://m.youtube.com"))
                assertTrue(manager.getCookie("https://www.instagram.com").orEmpty().contains("onda_probe=instagram"))
                assertFalse(manager.getCookie("https://www.youtube.com").orEmpty().contains("__Secure-onda_probe=youtube"))
            } finally {manager.setCookie("https://www.instagram.com","onda_probe=; Domain=.instagram.com; Path=/; Max-Age=0; Secure")}
        }
    }

    @Test fun protectedSessionReachesPythonWithoutPlaintextFile() {
        val text="# Netscape HTTP Cookie File\n.instagram.com\tTRUE\t/\tTRUE\t0\tsessionid\tsynthetic-only\n"
        main {SecureVault.initialize(context);SecureVault.put("instagram-session",text)}
        try {
            MobileEngine.initialize(context)
            val py=com.chaquo.python.Python.getInstance()
            val source=py.getModule("session_cookies").callAttr("cookie_source","onda-vault:instagram")
            assertEquals(text,source.callAttr("getvalue").toString())
            assertFalse(java.io.File(context.filesDir,"instagram-session.txt").exists())
            val encrypted=context.getSharedPreferences("vault",0).getString("instagram-session",null).orEmpty()
            assertFalse(encrypted.contains("synthetic-only"))
        } finally {SecureVault.remove("instagram-session")}
    }
}
