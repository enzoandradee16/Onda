package br.com.onda.mobile

import android.app.Activity
import android.app.Application
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.app.ActivityManager
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.drawable.AdaptiveIconDrawable
import android.graphics.drawable.ColorDrawable
import android.os.Build
import org.json.JSONObject
import java.util.WeakHashMap

/** Vector-only launcher variants; the MainActivity itself always remains enabled. */
internal object LauncherIcons {
    private val colors=linkedMapOf(
        "Verde-Água" to "Aqua",
        "Azul" to "Blue",
        "Roxo" to "Purple",
        "Rosa" to "Pink",
        "Laranja" to "Orange",
        "Vermelho" to "Red",
        "Verde" to "Green",
        "Verde-limão" to "Lime",
        "Amarelo" to "Yellow",
        "Dourado" to "Gold",
        "Ciano" to "Cyan",
        "Turquesa" to "Turquoise",
        "Índigo" to "Indigo",
        "Lilás" to "Lilac",
        "Coral" to "Coral",
        "Cinza" to "Gray")
    private var pending:ComponentName?=null
    private var startedActivities=0
    private var registered=false
    private val handler=Handler(Looper.getMainLooper())
    private var backgroundChange:Runnable?=null

    fun initialize(application:Application) {
        if(registered)return
        registered=true
        application.registerActivityLifecycleCallbacks(object:Application.ActivityLifecycleCallbacks {
            override fun onActivityStarted(activity:Activity) {
                synchronized(this@LauncherIcons) {
                    startedActivities++
                    backgroundChange?.let {handler.removeCallbacks(it)}
                    backgroundChange=null
                }
            }
            override fun onActivityStopped(activity:Activity) {
                synchronized(this@LauncherIcons) {
                    startedActivities=(startedActivities-1).coerceAtLeast(0)
                    if(startedActivities==0 && !activity.isChangingConfigurations) {
                        backgroundChange?.let {handler.removeCallbacks(it)}
                        backgroundChange=Runnable {applyPending(application)}.also {handler.postDelayed(it,400)}
                    }
                }
            }
            override fun onActivityCreated(activity:Activity,state:Bundle?) {}
            override fun onActivityResumed(activity:Activity) {}
            override fun onActivityPaused(activity:Activity) {}
            override fun onActivitySaveInstanceState(activity:Activity,state:Bundle) {}
            override fun onActivityDestroyed(activity:Activity) {}
        })
    }
    private val taskIcons=WeakHashMap<Activity,String>()

    private val launcherPrefix=MainActivity::class.java.name.substringBeforeLast('.')+".Launcher"

    internal fun aliasFor(context:Context,settings:JSONObject):ComponentName {
        if(settings.optString("theme")=="Alto contraste")return ComponentName(context.packageName,"${launcherPrefix}Contrast")
        val mode=when(settings.optString("theme")) {"Claro"->"Light";"Escuro","Alto contraste"->"Dark";"Preto puro"->"Black";else->"System"}
        val color=colors[settings.optString("accent")] ?: "Aqua"
        return ComponentName(context.packageName,"$launcherPrefix$mode$color")
    }

    @Suppress("DEPRECATION")
    internal fun enabledAliases(context:Context)=context.packageManager.queryIntentActivities(
        Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_LAUNCHER).setPackage(context.packageName),0
    ).map {ComponentName(it.activityInfo.packageName,it.activityInfo.name)}

    @Synchronized fun sync(context:Context,settings:JSONObject) {
        // Disabling the alias which launched a visible task can finish that task,
        // even with DONT_KILL_APP on some launchers. Keep all component changes
        // out of the foreground; internal and recent-app icons update immediately.
        pending=aliasFor(context,settings)
    }

    @Synchronized internal fun applyPending(context:Context) {
        if(startedActivities>0)return
        val desired=pending ?: return
        try {
            val pm=context.packageManager
            val enabled=enabledAliases(context)
            if(enabled!=listOf(desired)) {
                // Enable the replacement before removing old entries on Android 8–12.
                if(Build.VERSION.SDK_INT>=33) {
                    val changes=mutableListOf(PackageManager.ComponentEnabledSetting(desired,PackageManager.COMPONENT_ENABLED_STATE_ENABLED,PackageManager.DONT_KILL_APP))
                    enabled.filter {it!=desired && it.className.startsWith(launcherPrefix)}.forEach {
                        changes+=PackageManager.ComponentEnabledSetting(it,PackageManager.COMPONENT_ENABLED_STATE_DISABLED,PackageManager.DONT_KILL_APP)
                    }
                    pm.setComponentEnabledSettings(changes)
                } else {
                    pm.setComponentEnabledSetting(desired,PackageManager.COMPONENT_ENABLED_STATE_ENABLED,PackageManager.DONT_KILL_APP)
                    enabled.filter {it!=desired && it.className.startsWith(launcherPrefix)}.forEach {
                        pm.setComponentEnabledSetting(it,PackageManager.COMPONENT_ENABLED_STATE_DISABLED,PackageManager.DONT_KILL_APP)
                    }
                }
            }
            pending=null
        } catch(error:RuntimeException) {
            android.util.Log.w("ONDA","Could not update launcher icon",error)
        }
    }

    @Suppress("DEPRECATION")
    internal fun drawable(context:Context,settings:JSONObject):AdaptiveIconDrawable {
        val info=context.packageManager.getActivityInfo(aliasFor(context,settings),PackageManager.MATCH_DISABLED_COMPONENTS)
        return context.getDrawable(info.icon) as AdaptiveIconDrawable
    }

    @Suppress("DEPRECATION")
    fun updateTaskIcon(activity:Activity,settings:JSONObject,dark:Boolean) {
        val key=aliasFor(activity,settings).className+dark
        if(taskIcons[activity]==key)return
        runCatching {
            val icon=drawable(activity,settings)
            val bitmap=Bitmap.createBitmap(108,108,Bitmap.Config.ARGB_8888)
            icon.setBounds(0,0,108,108);icon.draw(Canvas(bitmap))
            val background=(icon.background as? ColorDrawable)?.color ?: android.graphics.Color.BLACK
            activity.setTaskDescription(ActivityManager.TaskDescription("ONDA",bitmap,background))
            taskIcons[activity]=key
        }.onFailure {android.util.Log.w("ONDA","Could not update recent-app icon",it)}
    }
}
