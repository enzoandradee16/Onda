package br.com.onda.mobile

import android.app.*
import android.content.*
import android.content.pm.ServiceInfo
import android.os.*
import androidx.core.app.NotificationCompat
import kotlinx.coroutines.*

fun downloadNotification(context:Context,text:String,percent:Int?):Notification {
    val manager=context.getSystemService(NotificationManager::class.java)
    if(manager.getNotificationChannel("downloads")==null) manager.createNotificationChannel(NotificationChannel("downloads","Downloads do ONDA",NotificationManager.IMPORTANCE_LOW))
    val open=PendingIntent.getActivity(context,0,Intent(context,MainActivity::class.java),PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)
    val stop=PendingIntent.getService(context,1,Intent(context,DownloadService::class.java).setAction("stop"),PendingIntent.FLAG_IMMUTABLE)
    return NotificationCompat.Builder(context,"downloads").setSmallIcon(R.drawable.ic_onda_notification).setContentTitle("ONDA")
        .setContentText(text.take(180)).setContentIntent(open).setOnlyAlertOnce(true).setOngoing(true)
        .setProgress(100,percent ?: 0,percent==null).addAction(0,"Parar fila",stop).build()
}

class DownloadService:Service() {
    private val scope=CoroutineScope(SupervisorJob()+Dispatchers.IO)
    private var worker:Job?=null
    private var lock:PowerManager.WakeLock?=null
    override fun onBind(intent:Intent?):IBinder?=null
    override fun onStartCommand(intent:Intent?,flags:Int,startId:Int):Int {
        if(intent?.action=="stop") {DownloadRuntime.stop();if(worker?.isActive!=true)stopSelf();return START_NOT_STICKY}
        if(worker?.isActive==true)return START_NOT_STICKY
        if(DownloadRuntime.running.get()) {stopSelf();return START_NOT_STICKY}
        val initial=downloadNotification(this,"Preparando download…",null)
        if(Build.VERSION.SDK_INT>=29)startForeground(1,initial,ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC) else startForeground(1,initial)
        worker=scope.launch {
            try {
                lock=(getSystemService(POWER_SERVICE) as PowerManager).newWakeLock(PowerManager.PARTIAL_WAKE_LOCK,"ONDA:Downloads").apply {acquire(6*60*60*1000L)}
                runDownloads(this@DownloadService,intent?.getStringExtra("only"),intent?.getStringArrayListExtra("batch")?.toSet()) {text,percent->getSystemService(NotificationManager::class.java).notify(1,downloadNotification(this@DownloadService,text,percent))}
            } catch(error:Exception) {OndaStore.log(error.message ?: "Falha no download")}
            finally {if(lock?.isHeld==true)lock?.release();stopForeground(STOP_FOREGROUND_REMOVE);stopSelf()}
        }
        return START_NOT_STICKY
    }
    override fun onTimeout(startId:Int,fgsType:Int) {DownloadRuntime.stop();stopForeground(STOP_FOREGROUND_REMOVE);stopSelf()}
    override fun onDestroy() {if(worker!=null)DownloadRuntime.stop();if(lock?.isHeld==true)lock?.release();scope.cancel();super.onDestroy()}
    companion object {
        fun start(context:Context,only:String?=null) {context.startForegroundService(Intent(context,DownloadService::class.java).putExtra("only",only))}
        fun batch(context:Context,ids:List<String>) {context.startForegroundService(Intent(context,DownloadService::class.java).putStringArrayListExtra("batch",ArrayList(ids)))}
        fun stop(context:Context) {DownloadRuntime.stop();if(OndaStore.running.value)context.startService(Intent(context,DownloadService::class.java).setAction("stop"))}
    }
}
