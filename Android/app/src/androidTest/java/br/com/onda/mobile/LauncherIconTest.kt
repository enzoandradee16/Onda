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
import org.junit.Before
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class LauncherIconTest {
    private val context get()=InstrumentationRegistry.getInstrumentation().targetContext
    @Before fun allowNotifications() {
        if(android.os.Build.VERSION.SDK_INT>=33)InstrumentationRegistry.getInstrumentation().uiAutomation.grantRuntimePermission(context.packageName,android.Manifest.permission.POST_NOTIFICATIONS)
    }

    @Test fun allAccentAndThemeCombinationsResolveExactlyOneLauncher() {
        val before=JSONObject(OndaStore.settings.value.toString())
        try {
            for(theme in appearanceModes) {
                for(accent in accents.keys) {
                    val settings=JSONObject(before.toString()).put("theme",theme).put("accent",accent)
                    LauncherIcons.sync(context,settings)
                    LauncherIcons.applyPending(context)
                    assertEquals("$theme / $accent",listOf(LauncherIcons.aliasFor(context,settings)),LauncherIcons.enabledAliases(context))
                    assertNotEquals(PackageManager.COMPONENT_ENABLED_STATE_DISABLED,context.packageManager.getComponentEnabledSetting(ComponentName(context,MainActivity::class.java)))
                    assertEquals("ONDA",context.packageManager.getActivityInfo(LauncherIcons.aliasFor(context,settings),0).loadLabel(context.packageManager).toString())
                }
            }
            val invalid=JSONObject().put("theme","invalid").put("accent","invalid")
            assertTrue(LauncherIcons.aliasFor(context,invalid).className.endsWith("LauncherSystemAqua"))
        } finally {LauncherIcons.sync(context,before);LauncherIcons.applyPending(context)}
    }

    @Test fun actualDrawableColorsMatchAccentAndAppearanceIncludingSystemNight() {
        val before=JSONObject(OndaStore.settings.value.toString())
        for(dark in listOf(false,true)) {
            val config=Configuration(context.resources.configuration).apply {
                uiMode=(uiMode and Configuration.UI_MODE_NIGHT_MASK.inv()) or if(dark)Configuration.UI_MODE_NIGHT_YES else Configuration.UI_MODE_NIGHT_NO
            }
            val configured=context.createConfigurationContext(config)
            for(theme in appearanceModes) {
                for(accent in accents.keys) {
                    val settings=JSONObject(before.toString()).put("theme",theme).put("accent",accent)
                    val icon=LauncherIcons.drawable(configured,settings)
                    val isDark=when(theme){"Claro","Claro puro"->false;"Escuro","Preto puro","Alto contraste"->true;else->dark}
                    val expected=if(theme=="Alto contraste")Color.Yellow.toArgb() else Color((if(isDark)accents else lightAccents).getValue(accent)).toArgb()
                    val bitmap=Bitmap.createBitmap(108,108,Bitmap.Config.ARGB_8888)
                    icon.foreground.setBounds(0,0,108,108);icon.foreground.draw(Canvas(bitmap))
                    val pixels=IntArray(108*108);bitmap.getPixels(pixels,0,108,0,0,108,108)
                    assertTrue("$theme / $accent / dark=$dark",pixels.any {it==expected})
                    assertTrue("Safe adaptive mask bounds",pixels.withIndex().filter {android.graphics.Color.alpha(it.value)>0}.all {it.index%108 in 24..84 && it.index/108 in 24..84})
                    if(android.os.Build.VERSION.SDK_INT>=33)assertNotNull(icon.monochrome)
                    bitmap.recycle()
                    val expectedBackground=when {theme in listOf("Preto puro","Alto contraste")->android.graphics.Color.BLACK;theme=="Claro puro"->android.graphics.Color.WHITE;isDark->0xFF161E29.toInt();else->lightColorScheme().surface.toArgb()}
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
                        val description=activity.getSystemService(android.app.ActivityManager::class.java).appTasks.first {it.taskInfo.taskId==activity.taskId}.taskInfo.taskDescription ?: error("Missing task description")
                        assertEquals("ONDA",description.label)
                        // Android may harmonize the task color; drawable palette is checked above.
                        assertEquals(255,android.graphics.Color.alpha(description.primaryColor))
                        assertFalse(activity.isFinishing)
                        assertEquals(pid,android.os.Process.myPid())
                    }
                }
            }
        } finally {OndaStore.saveSettings(before);LauncherIcons.applyPending(context)}
    }

    @Suppress("DEPRECATION")
    @Test fun settingsApplyImmediatelyWithoutChangingShareOrSpotifyEntryPoints() {
        val before=JSONObject(OndaStore.settings.value.toString())
        try {
            val changed=JSONObject(before.toString()).put("theme","Preto puro").put("accent","Rosa")
            OndaStore.saveSettings(changed)
            LauncherIcons.applyPending(context)
            assertEquals(listOf(LauncherIcons.aliasFor(context,changed)),LauncherIcons.enabledAliases(context))
            val desired=LauncherIcons.aliasFor(context,changed)
            LauncherIcons.sync(context,changed)
            LauncherIcons.applyPending(context)
            assertEquals(listOf(desired),LauncherIcons.enabledAliases(context))
            val share=Intent(Intent.ACTION_SEND).setType("text/plain").setPackage(context.packageName)
            assertTrue(context.packageManager.queryIntentActivities(share,0).any {it.activityInfo.name==MainActivity::class.java.name})
            val callback=Intent(Intent.ACTION_VIEW,android.net.Uri.parse("onda://spotify-return")).addCategory(Intent.CATEGORY_BROWSABLE).setPackage(context.packageName)
            assertTrue(context.packageManager.queryIntentActivities(callback,0).any {it.activityInfo.name==MainActivity::class.java.name})
        } finally {OndaStore.saveSettings(before);LauncherIcons.applyPending(context)}
    }
    @Test fun themeAndAccentChangesKeepTheLaunchingAliasEnabledWhileVisible() {
        val before=JSONObject(OndaStore.settings.value.toString())
        try {
            LauncherIcons.sync(context,before);LauncherIcons.applyPending(context)
            val launching=LauncherIcons.aliasFor(context,before)
            val intent=Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_LAUNCHER)
                .setComponent(launching).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK)
            androidx.test.core.app.ActivityScenario.launch<MainActivity>(intent).use {scenario->
                for((theme,accent) in listOf("Claro" to "Azul","Escuro" to "Rosa","Preto puro" to "Dourado","Seguir o sistema" to "Verde-Água")) {
                    scenario.onActivity {activity->
                        val enabled=LauncherIcons.enabledAliases(context)
                        OndaStore.saveSettings(JSONObject(before.toString()).put("theme",theme).put("accent",accent))
                        LauncherIcons.applyPending(context)
                        assertEquals("No launcher mutation while visible",enabled,LauncherIcons.enabledAliases(context))
                        assertTrue(LauncherIcons.enabledAliases(context).contains(launching))
                        assertFalse(activity.isFinishing)
                    }
                    android.os.SystemClock.sleep(600)
                    scenario.onActivity {assertFalse(it.isFinishing);assertFalse(it.isDestroyed)}
                }
                scenario.moveToState(androidx.lifecycle.Lifecycle.State.STARTED)
                scenario.moveToState(androidx.lifecycle.Lifecycle.State.RESUMED)
                android.os.SystemClock.sleep(600)
                scenario.onActivity {assertTrue(LauncherIcons.enabledAliases(context).contains(launching));assertFalse(it.isFinishing)}
            }
            android.os.SystemClock.sleep(700)
            assertEquals(listOf(LauncherIcons.aliasFor(context,OndaStore.settings.value)),LauncherIcons.enabledAliases(context))
        } finally {OndaStore.saveSettings(before);LauncherIcons.applyPending(context)}
    }

}
