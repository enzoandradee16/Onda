package br.com.onda.mobile

import android.content.Intent
import android.content.pm.ActivityInfo
import androidx.test.core.app.ActivityScenario
import androidx.test.core.app.ApplicationProvider
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Assert.*
import org.junit.Test

class InstagramSessionLifecycleTest {
    private val context get()=ApplicationProvider.getApplicationContext<android.content.Context>()
    private fun script(scenario:ActivityScenario<InstagramLoginActivity>,js:String):String {
        val latch=java.util.concurrent.CountDownLatch(1);var value=""
        scenario.onActivity {it.browser.evaluateJavascript(js){result->value=result;latch.countDown()}}
        assertTrue(latch.await(3,java.util.concurrent.TimeUnit.SECONDS));return value
    }
    private fun form(scenario:ActivityScenario<InstagramLoginActivity>) {
        repeat(50){if(script(scenario,"!!document.querySelector('input[type=password]')")=="true")return;Thread.sleep(500)}
        fail("Formulário do Instagram não carregou")
    }
    private fun typeUser(scenario:ActivityScenario<InstagramLoginActivity>,text:String):Int {
            var oldHeight=0
            val point=org.json.JSONArray(script(scenario,"(()=>{const e=Array.from(document.querySelectorAll('input')).find(e=>e.type!=='password'&&e.type!=='hidden'&&e.getBoundingClientRect().height>0);const r=e.getBoundingClientRect();return [r.x+r.width/2,r.y+r.height/2,innerWidth]})()"))
            var x=0f;var y=0f
            scenario.onActivity {activity->
                val web=activity.browser;oldHeight=web.height
                val pos=IntArray(2);web.getLocationOnScreen(pos)
                val scale=web.width/point.getDouble(2)
                x=(pos[0]+point.getDouble(0)*scale).toFloat();y=(pos[1]+point.getDouble(1)*scale).toFloat()
            }
            val instrumentation=InstrumentationRegistry.getInstrumentation()
            val now=android.os.SystemClock.uptimeMillis()
            instrumentation.sendPointerSync(android.view.MotionEvent.obtain(now,now,android.view.MotionEvent.ACTION_DOWN,x,y,0))
            instrumentation.sendPointerSync(android.view.MotionEvent.obtain(now,now+50,android.view.MotionEvent.ACTION_UP,x,y,0))
            scenario.onActivity {activity->(activity.getSystemService(android.content.Context.INPUT_METHOD_SERVICE) as android.view.inputmethod.InputMethodManager).showSoftInput(activity.browser,android.view.inputmethod.InputMethodManager.SHOW_FORCED)}
        InstrumentationRegistry.getInstrumentation().sendStringSync(text)
        Thread.sleep(400)
        assertTrue(script(scenario,"document.activeElement.value").contains(text))
        return oldHeight
    }
    @Test fun rotationPreservesAnonymousFormAndBackCloses() {
        ActivityScenario.launch<InstagramLoginActivity>(Intent(context,InstagramLoginActivity::class.java)).use {scenario->
            form(scenario)
            typeUser(scenario,"onda-test-user")
            scenario.onActivity {activity->(activity.getSystemService(android.content.Context.INPUT_METHOD_SERVICE) as android.view.inputmethod.InputMethodManager).hideSoftInputFromWindow(activity.browser.windowToken,0)}
            Thread.sleep(600)
            var instance:InstagramLoginActivity?=null
            scenario.onActivity {instance=it}
            var initial=0
            scenario.onActivity {initial=it.resources.configuration.orientation}
            val target=if(initial==android.content.res.Configuration.ORIENTATION_LANDSCAPE)ActivityInfo.SCREEN_ORIENTATION_PORTRAIT else ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE
            try {
            scenario.onActivity {it.requestedOrientation=target}
            Thread.sleep(2500);form(scenario)
            scenario.onActivity {assertNotEquals("A orientação não mudou",initial,it.resources.configuration.orientation);assertSame("Navegador foi recriado",instance,it)}
            assertEquals("\"onda-test-user\"",script(scenario,"Array.from(document.querySelectorAll('input')).find(e=>e.type!=='password'&&e.type!=='hidden'&&e.getBoundingClientRect().height>0).value"))
            } finally {scenario.onActivity {it.requestedOrientation=ActivityInfo.SCREEN_ORIENTATION_PORTRAIT};Thread.sleep(1000)}
            InstrumentationRegistry.getInstrumentation().sendKeyDownUpSync(android.view.KeyEvent.KEYCODE_BACK)
            Thread.sleep(500)
            assertEquals(androidx.lifecycle.Lifecycle.State.DESTROYED,scenario.state)
        }
    }
    @Test fun keyboardTypingAndBackKeepBrowserOpen() {
        ActivityScenario.launch<InstagramLoginActivity>(Intent(context,InstagramLoginActivity::class.java)).use {scenario->
            form(scenario)
            val oldHeight=typeUser(scenario,"onda-test")
            val instrumentation=InstrumentationRegistry.getInstrumentation()
            try {
                Thread.sleep(1000)
                scenario.onActivity {assertTrue("Teclado não redimensionou a área",it.browser.height<oldHeight)}
                instrumentation.sendKeyDownUpSync(android.view.KeyEvent.KEYCODE_BACK)
                Thread.sleep(500)
                scenario.onActivity {assertFalse("Voltar fechou o navegador com o teclado aberto",it.isFinishing)}
            } finally {
                scenario.onActivity {activity->(activity.getSystemService(android.content.Context.INPUT_METHOD_SERVICE) as android.view.inputmethod.InputMethodManager).hideSoftInputFromWindow(activity.browser.windowToken,0)}
            }
        }
    }
    @Test fun accountSwitchAndDisconnectDoNotReuseOldVaultSession() {
        fun text(account:String)="# Netscape HTTP Cookie File\n.instagram.com\tTRUE\t/\tTRUE\t0\tsessionid\t$account\n"
        val main=InstrumentationRegistry.getInstrumentation()
        main.runOnMainSync {SecureVault.put("instagram-session",text("account-a"))}
        try {
            MobileEngine.initialize(context)
            val module=com.chaquo.python.Python.getInstance().getModule("session_cookies")
            val active=module.callAttr("cookie_source","onda-vault:instagram")
            main.runOnMainSync {SecureVault.put("instagram-session",text("account-b"))}
            assertEquals(text("account-a"),active.callAttr("getvalue").toString())
            assertEquals(text("account-b"),module.callAttr("cookie_source","onda-vault:instagram").callAttr("getvalue").toString())
            main.runOnMainSync {disconnectInstagram()}
            assertEquals(text("account-a"),active.callAttr("getvalue").toString())
            try {module.callAttr("cookie_source","onda-vault:instagram");fail("Sessão desconectada reutilizada")}catch(expected:com.chaquo.python.PyException){assertTrue(expected.message.orEmpty().contains("Atualize"))}
        } finally {SecureVault.remove("instagram-session")}
    }
}
