package br.com.onda.mobile

import android.app.*
import android.content.*
import android.content.pm.ServiceInfo
import android.os.*
import androidx.core.app.NotificationCompat
import kotlinx.coroutines.*

fun downloadNotification(context:Context,text:String,percent:Int?):Notification {
    val manager=context.getSystemService(NotificationManager::class.java)
    val channelName=translateUi("Downloads do ONDA")
    val existingChannel=manager.getNotificationChannel("downloads")
    if(existingChannel==null || existingChannel.name.toString()!=channelName) {
        val channel=existingChannel ?: NotificationChannel("downloads",channelName,NotificationManager.IMPORTANCE_LOW)
        channel.name=channelName
        manager.createNotificationChannel(channel)
    }
    val open=PendingIntent.getActivity(context,0,openQueueIntent(context),PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)
    val stop=PendingIntent.getService(context,1,Intent(context,DownloadService::class.java).setAction("stop"),PendingIntent.FLAG_IMMUTABLE)
    val pause=PendingIntent.getService(context,2,Intent(context,DownloadService::class.java).setAction(if(DownloadRuntime.paused)"resume" else "pause"),PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)
    val builder=NotificationCompat.Builder(context,"downloads").setSmallIcon(R.drawable.ic_onda_notification).setContentTitle("ONDA")
        .setContentText(translateUi(text).take(180)).setContentIntent(open).setOnlyAlertOnce(true).setOngoing(true)
        .setProgress(100,percent ?: 0,percent==null)
    for(action in notificationActions(OndaStore.settings.value.optBoolean("notification_controls",true),DownloadRuntime.paused))
        builder.addAction(0,translateUi(action),when(action){"Parar fila"->stop;"Abrir fila"->open;else->pause})
    return builder.build()
}

internal fun refreshDownloadNotification(context:Context) {
    val manager=context.getSystemService(NotificationManager::class.java)
    runCatching {
        manager.activeNotifications.filter {it.id in listOf(1,2)}.forEach {active->
            val extras=active.notification.extras
            val text=extras.getCharSequence(Notification.EXTRA_TEXT)?.toString().orEmpty()
            val percent=if(extras.getBoolean(Notification.EXTRA_PROGRESS_INDETERMINATE,true))null else extras.getInt(Notification.EXTRA_PROGRESS)
            manager.notify(active.id,downloadNotification(context,text,percent))
        }
    }
}

class DownloadService:Service() {
    private val scope=CoroutineScope(SupervisorJob()+Dispatchers.IO)
    private var worker:Job?=null
    private var lock:PowerManager.WakeLock?=null
    @Synchronized private fun power(needed:Boolean) {
        if(needed && scope.isActive && !DownloadRuntime.stopped && lock?.isHeld!=true) {
            if(lock==null)lock=(getSystemService(POWER_SERVICE) as PowerManager).newWakeLock(PowerManager.PARTIAL_WAKE_LOCK,"ONDA:Downloads")
            lock?.acquire(6*60*60*1000L)
        } else if(!needed && lock?.isHeld==true)lock?.release()
    }
    override fun onBind(intent:Intent?):IBinder?=null
    override fun onStartCommand(intent:Intent?,flags:Int,startId:Int):Int {
        if(intent?.action=="stop") {DownloadRuntime.stop();if(worker?.isActive!=true)stopSelf();return START_NOT_STICKY}
        if(intent?.action in listOf("pause","resume")) {
            if(DownloadRuntime.running.get()) {
                if(intent?.action=="pause")DownloadRuntime.pause() else DownloadRuntime.resume()
                getSystemService(NotificationManager::class.java).notify(if(worker==null)2 else 1,downloadNotification(this,if(DownloadRuntime.paused)"Fila pausada" else "Retomando fila…",null))
            }
            if(worker==null)stopSelf()
            return START_NOT_STICKY
        }
        val batch=try {intent?.getStringExtra("batch_token")?.let {DownloadBatchFiles.consume(this,it)} ?: intent?.getStringArrayListExtra("batch")?.toSet()}
        catch(_:Exception) {OndaStore.log("Não foi possível recuperar a seleção. Selecione os itens e tente novamente.");stopSelf(startId);return START_NOT_STICKY}
        DownloadRuntime.requests.submit(intent?.getStringExtra("only"),batch)
        if(worker?.isActive==true)return START_NOT_STICKY
        launchWorker()
        return START_NOT_STICKY
    }
    private fun launchWorker() {
        val initial=downloadNotification(this,"Preparando download…",null)
        if(Build.VERSION.SDK_INT>=29)startForeground(1,initial,ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC) else startForeground(1,initial)
        worker=scope.launch {
            val power=launch {
                while(isActive) {
                    power(DownloadRuntime.ids.isNotEmpty())
                    delay(1000)
                }
            }
            try {
                // A scheduled worker may own the engine; it also consumes requests.
                while(DownloadRuntime.running.get())delay(100)
                runDownloads(this@DownloadService,requestsOnly=true) {text,percent->getSystemService(NotificationManager::class.java).notify(1,downloadNotification(this@DownloadService,text,percent))}
            } catch(error:Exception) {OndaStore.log(error.message ?: "Falha no download")}
            finally {
                power.cancel()
                power(false)
                withContext(NonCancellable+Dispatchers.Main.immediate) {
                    worker=null
                    // A request can arrive after the runner's last idle check.
                    if(scope.isActive && DownloadRuntime.requests.hasPending())launchWorker()
                    else {stopForeground(STOP_FOREGROUND_REMOVE);stopSelf()}
                }
            }
        }
    }
    override fun onTimeout(startId:Int,fgsType:Int) {DownloadRuntime.stop();stopForeground(STOP_FOREGROUND_REMOVE);stopSelf()}
    override fun onDestroy() {if(worker!=null)DownloadRuntime.stop();scope.cancel();power(false);super.onDestroy()}
    companion object {
        fun start(context:Context,only:String?=null,spaceChecked:Boolean=false) {if(!spaceChecked && !OndaStore.confirmQueueSpace(only?.let {setOf(it)}) {start(context,only,true)})return;if(only!=null && OndaStore.deferDuplicateStart(only))return;context.startForegroundService(Intent(context,DownloadService::class.java).putExtra("only",only))}
        fun batch(context:Context,ids:List<String>,spaceChecked:Boolean=false) {if(!spaceChecked && !OndaStore.confirmQueueSpace(ids.toSet()) {batch(context,ids,true)})return;val ready=ids.filterNot {OndaStore.deferDuplicateStart(it)};if(ready.isEmpty())return;val request=DownloadBatchFiles.intent(context,ready);try {context.startForegroundService(request)} catch(error:Exception) {DownloadBatchFiles.discard(context,request);throw error}}
        fun control(context:Context,action:String) {if(action in listOf("pause","resume"))context.startService(Intent(context,DownloadService::class.java).setAction(action))}
        fun stop(context:Context) {DownloadRuntime.stop();if(OndaStore.running.value)context.startService(Intent(context,DownloadService::class.java).setAction("stop"))}
    }
}
