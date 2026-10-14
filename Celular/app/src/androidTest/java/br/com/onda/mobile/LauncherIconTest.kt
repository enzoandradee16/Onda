package br.com.onda.mobile

import android.content.ComponentName
import android.content.Intent
import android.content.pm.PackageManager
import android.content.res.Configuration
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.drawable.ColorDrawable
import androidx.compose.material3.lightColorScheme
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.toArgb
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class LauncherIconTest {
    private val context get()=InstrumentationRegistry.getInstrumentation().targetContext

    @Test fun allAccentAndThemeCombinationsResolveExactlyOneLauncher() {
        val before=JSONObject(OndaStore.settings.value.toString())
        try {
            for(theme in listOf("Escuro","Claro","Preto puro","Seguir o sistema")) {
                for(accent in accents.keys) {
                    val settings=JSONObject(before.toString()).put("theme",theme).put("accent",accent)
                    LauncherIcons.sync(context,settings)
                    assertEquals("$theme / $accent",listOf(LauncherIcons.aliasFor(context,settings)),LauncherIcons.enabledAliases(context))
                    assertNotEquals(PackageManager.COMPONENT_ENABLED_STATE_DISABLED,context.packageManager.getComponentEnabledSetting(ComponentName(context,MainActivity::class.java)))
                    assertEquals("ONDA",context.packageManager.getActivityInfo(LauncherIcons.aliasFor(context,settings),0).loadLabel(context.packageManager).toString())
                }
            }
            val invalid=JSONObject().put("theme","invalid").put("accent","invalid")
            assertTrue(LauncherIcons.aliasFor(context,invalid).className.endsWith("LauncherSystemAqua"))
        } finally {LauncherIcons.sync(context,before)}
    }

    @Test fun actualDrawableColorsMatchAccentAndAppearanceIncludingSystemNight() {
        val before=JSONObject(OndaStore.settings.value.toString())
        for(dark in listOf(false,true)) {
            val config=Configuration(context.resources.configuration).apply {
                uiMode=(uiMode and Configuration.UI_MODE_NIGHT_MASK.inv()) or if(dark)Configuration.UI_MODE_NIGHT_YES else Configuration.UI_MODE_NIGHT_NO
            }
            val configured=context.createConfigurationContext(config)
            for(theme in listOf("Escuro","Claro","Preto puro","Seguir o sistema")) {
                for(accent in accents.keys) {
                    val settings=JSONObject(before.toString()).put("theme",theme).put("accent",accent)
                    val icon=LauncherIcons.drawable(configured,settings)
                    val isDark=when(theme){"Claro"->false;"Escuro","Preto puro"->true;else->dark}
                    val expected=Color((if(isDark)accents else lightAccents).getValue(accent)).toArgb()
                    val bitmap=Bitmap.createBitmap(108,108,Bitmap.Config.ARGB_8888)
                    icon.foreground.setBounds(0,0,108,108);icon.foreground.draw(Canvas(bitmap))
                    assertEquals("$theme / $accent / dark=$dark",expected,bitmap.getPixel(54,54))
                    bitmap.recycle()
                    val expectedBackground=when {theme=="Preto puro"->android.graphics.Color.BLACK;isDark->0xFF161E29.toInt();else->lightColorScheme().surface.toArgb()}
                    assertEquals("background $theme / dark=$dark",expectedBackground,(icon.background as ColorDrawable).color)
                }
            }
        }
    }

    @Suppress("DEPRECATION")
    @Test fun recentAppsIconAndActivitySurviveThemeChanges() {
        val before=JSONObject(OndaStore.settings.value.toString())
        val pid=android.os.Process.myPid()
        try {
            androidx.test.core.app.ActivityScenario.launch(MainActivity::class.java).use {scenario->
                scenario.onActivity {activity->
                    for(theme in listOf("Escuro","Claro","Preto puro")) {
                        val value=JSONObject(before.toString()).put("theme",theme).put("accent","Rosa")
                        OndaStore.saveSettings(value)
                        LauncherIcons.updateTaskIcon(activity,value,theme!="Claro")
                        val description=activity.getSystemService(android.app.ActivityManager::class.java).appTasks.first().taskInfo.taskDescription ?: error("Missing task description")
                        assertEquals("ONDA",description.label)
                        val expected=when(theme){"Claro"->lightColorScheme().surface.toArgb();"Preto puro"->android.graphics.Color.BLACK;else->0xFF161E29.toInt()}
                        assertEquals(expected,description.primaryColor)
                        assertFalse(activity.isFinishing)
                        assertEquals(pid,android.os.Process.myPid())
                    }
                }
            }
        } finally {OndaStore.saveSettings(before)}
    }

    @Suppress("DEPRECATION")
    @Test fun settingsApplyImmediatelyWithoutChangingShareOrSpotifyEntryPoints() {
        val before=JSONObject(OndaStore.settings.value.toString())
        try {
            val changed=JSONObject(before.toString()).put("theme","Preto puro").put("accent","Rosa")
            OndaStore.saveSettings(changed)
            assertEquals(listOf(LauncherIcons.aliasFor(context,changed)),LauncherIcons.enabledAliases(context))
            val desired=LauncherIcons.aliasFor(context,changed)
            LauncherIcons.sync(context,changed)
            assertEquals(listOf(desired),LauncherIcons.enabledAliases(context))
            val share=Intent(Intent.ACTION_SEND).setType("text/plain").setPackage(context.packageName)
            assertTrue(context.packageManager.queryIntentActivities(share,0).any {it.activityInfo.name==MainActivity::class.java.name})
            val callback=Intent(Intent.ACTION_VIEW,android.net.Uri.parse("onda://spotify-return")).addCategory(Intent.CATEGORY_BROWSABLE).setPackage(context.packageName)
            assertTrue(context.packageManager.queryIntentActivities(callback,0).any {it.activityInfo.name==MainActivity::class.java.name})
        } finally {OndaStore.saveSettings(before)}
    }
}
