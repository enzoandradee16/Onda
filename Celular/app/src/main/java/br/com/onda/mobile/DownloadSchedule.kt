package br.com.onda.mobile

import android.content.Context
import android.content.pm.ServiceInfo
import android.os.Build
import androidx.work.*
import kotlinx.coroutines.*
import org.json.JSONObject
import java.time.*
import java.util.concurrent.TimeUnit

fun scheduleAllowed(options:JSONObject,clock:LocalTime=LocalTime.now()):Boolean {
    if(!options.optBoolean("schedule_enabled"))return true
    val start=runCatching {LocalTime.parse(options.optString("schedule_start"))}.getOrNull() ?: return false
    val stop=runCatching {LocalTime.parse(options.optString("schedule_stop"))}.getOrNull() ?: return false
    if(start==stop)return false
    return if(start<stop)clock>=start && clock<stop else clock>=start || clock<stop
}

object DownloadSchedule {
    private const val NAME="onda-scheduled-downloads"
    fun configure(context:Context,options:JSONObject,nextDay:Boolean=false,keepExisting:Boolean=false) {
        val manager=WorkManager.getInstance(context)
        if(!options.optBoolean("schedule_enabled")) {manager.cancelUniqueWork(NAME);return}
        val start=runCatching {LocalTime.parse(options.optString("schedule_start"))}.getOrNull() ?: return
        val stop=runCatching {LocalTime.parse(options.optString("schedule_stop"))}.getOrNull() ?: return
        if(start==stop)return
        val now=ZonedDateTime.now();var next=now.with(start)
        if(next<=now)next=next.plusDays(1)
        val wait=if(!nextDay && scheduleAllowed(options))0L else Duration.between(now,next).toMillis().coerceAtLeast(0)
        val request=OneTimeWorkRequestBuilder<ScheduledDownloadWorker>().setInitialDelay(wait,TimeUnit.MILLISECONDS)
            .setConstraints(Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build()).build()
        manager.enqueueUniqueWork(NAME,if(nextDay)ExistingWorkPolicy.APPEND_OR_REPLACE else if(keepExisting)ExistingWorkPolicy.KEEP else ExistingWorkPolicy.REPLACE,request)
    }
}

class ScheduledDownloadWorker(context:Context,params:WorkerParameters):CoroutineWorker(context,params) {
    override suspend fun doWork():Result {
        if(!OndaStore.settings.value.optBoolean("schedule_enabled"))return Result.success()
        if(!scheduleAllowed(OndaStore.settings.value)) {DownloadSchedule.configure(applicationContext,OndaStore.settings.value,true);return Result.success()}
        if(DownloadRuntime.running.get())return Result.retry()
        val initial=downloadNotification(applicationContext,"Downloads agendados",null)
        setForeground(if(Build.VERSION.SDK_INT>=29)ForegroundInfo(2,initial,ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC) else ForegroundInfo(2,initial))
        try {runDownloads(applicationContext,scheduled=true) {text,percent->applicationContext.getSystemService(android.app.NotificationManager::class.java).notify(2,downloadNotification(applicationContext,text,percent))}}
        finally {DownloadSchedule.configure(applicationContext,OndaStore.settings.value,true)}
        return Result.success()
    }
}
