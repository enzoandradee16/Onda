package br.com.onda.mobile
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
@RunWith(AndroidJUnit4::class)
class DailyNotificationTest {
    @Test fun optionalControlsKeepTheOpenIntent() {
        assertTrue(OndaStore.defaults().getBoolean("notification_controls"))
        assertFalse(OndaStore.defaults().getBoolean("wifi_only"))
        val saved=OndaStore.settings.value
        val context=InstrumentationRegistry.getInstrumentation().targetContext
        try {
            OndaStore.settings.value=JSONObject(saved.toString()).put("notification_controls",true)
            assertEquals(3,downloadNotification(context,"Teste",50).actions.size)
            OndaStore.settings.value=JSONObject(saved.toString()).put("notification_controls",false)
            val notification=downloadNotification(context,"Teste",50)
            assertTrue(notification.actions.isNullOrEmpty());assertNotNull(notification.contentIntent)
        } finally {OndaStore.settings.value=saved}
    }
}
