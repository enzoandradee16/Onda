package br.com.onda.mobile

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder
import android.os.PowerManager
import androidx.core.app.NotificationCompat
import kotlinx.coroutines.*
import org.json.JSONObject

class DownloadService : Service() {
    private val scope = CoroutineScope(SupervisorJob()+Dispatchers.IO)
    private var worker: Job? = null
    private var stopRequested = false
    private var lock: PowerManager.WakeLock? = null
    override fun onBind(intent: Intent?): IBinder? = null
    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if(intent?.action=="stop") {
            stopRequested=true
            OndaStore.dismissQuestions(OndaStore.active.value)
            MobileEngine.cancel(OndaStore.active.value)
            if(worker?.isActive!=true) stopSelf()
            return START_NOT_STICKY
        }
        if(worker?.isActive==true) return START_NOT_STICKY
        val manager=getSystemService(NotificationManager::class.java)
        manager.createNotificationChannel(NotificationChannel("downloads","Downloads do ONDA",NotificationManager.IMPORTANCE_LOW))
        val initial=notification("Preparando download…",null)
        if(Build.VERSION.SDK_INT>=29) startForeground(1,initial,ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC) else startForeground(1,initial)
        stopRequested=false
        OndaStore.running.value=true
        worker=scope.launch {
            try {
                lock=(getSystemService(Context.POWER_SERVICE) as PowerManager).newWakeLock(PowerManager.PARTIAL_WAKE_LOCK,"ONDA:Downloads").apply { acquire(6*60*60*1000L) }
                val preferred=intent?.getStringExtra("only")
                val batch=intent?.getStringArrayListExtra("batch")?.toHashSet()
                while(!stopRequested) {
                    val item=OndaStore.items.value.firstOrNull { it.state=="Pendente" && (preferred==null || it.id==preferred) && (batch==null || it.id in batch) } ?: break
                    OndaStore.active.value=item.id
                    OndaStore.update(item.id,"Baixando")
                    val config=JSONObject(item.config.toString()).put("spotify_client_secret",SecureVault.get("spotify-api") ?: "").put("_identity",item.id)
                    var failed=false
                    val result=MobileEngine.call(this@DownloadService,item.id,config.optString("_operation","download"),config,EventCallback { text ->
                        val event=JSONObject(text)
                        when(event.optString("type")) {
                            "progress"->{
                                val total=event.optDouble("total",0.0)
                                val percent=if(total>0) (event.optDouble("downloaded")/total*100).toFloat().coerceIn(0f,100f) else 0f
                                OndaStore.update(item.id,"Baixando",percent,event.optString("title"))
                                manager.notify(1,notification(item.title,percent.toInt()))
                            }
                            "file"->{
                                if(!event.optBoolean("skipped")) {
                                    val uri=OndaStore.publish(event.getString("path"),OndaStore.publicationConfig(config,event),event.optString("mode"))
                                    OndaStore.log("Salvo: $uri")
                                }
                            }
                            "done"->if(event.has("path")) OndaStore.publish(event.getString("path"),OndaStore.publicationConfig(config,event),event.getString("path").substringAfterLast('.'))
                            "error"->{ failed=true; OndaStore.update(item.id,"Erro",message=event.optString("message")); OndaStore.log(event.optString("message")) }
                            "choose_version","choose_catalog","choose_duplicate","choose_media","review_metadata"->{
                                OndaStore.update(item.id,"Aguardando escolha")
                                OndaStore.ask(item.id,event)
                                manager.notify(1,notification("Abra o ONDA para confirmar sua escolha",null))
                            }
                            "estimate"->{
                                val size=event.optDouble("size",0.0)/1048576
                                if(size>0) OndaStore.update(item.id,"Baixando",message="Tamanho estimado: ≈ %.1f MB".format(size))
                            }
                            else->{ val message=event.optString("message"); if(message.isNotEmpty()) { OndaStore.log(message); OndaStore.update(item.id,"Baixando",message=message) } }
                        }
                    })
                    if(stopRequested || result.optBoolean("cancelled")) OndaStore.update(item.id,"Pendente",message="Download interrompido; pode tentar novamente.")
                    else if(result.has("error")) OndaStore.update(item.id,"Erro",message=result.optString("error"))
                    else if(!failed && result.optInt("code")==0) OndaStore.update(item.id,"Concluído",100f)
                    else OndaStore.update(item.id,"Erro")
                    OndaStore.dismissQuestions(item.id)
                    if(preferred!=null) break
                }
            } catch(error: Exception) {
                OndaStore.log(error.message ?: "Falha no download")
                OndaStore.update(OndaStore.active.value,"Erro",message=error.message ?: "Falha")
            } finally {
                OndaStore.dismissQuestions(OndaStore.active.value)
                OndaStore.active.value=""
                OndaStore.running.value=false
                if(lock?.isHeld==true) lock?.release()
                stopForeground(STOP_FOREGROUND_REMOVE)
                stopSelf()
            }
        }
        return START_NOT_STICKY
    }
    private fun notification(text: String, percent: Int?): android.app.Notification {
        val open=PendingIntent.getActivity(this,0,Intent(this,MainActivity::class.java),PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)
        val stop=PendingIntent.getService(this,1,Intent(this,DownloadService::class.java).setAction("stop"),PendingIntent.FLAG_IMMUTABLE)
        return NotificationCompat.Builder(this,"downloads").setSmallIcon(R.drawable.ic_onda_notification).setContentTitle("ONDA")
            .setContentText(text.take(180)).setContentIntent(open).setOnlyAlertOnce(true).setOngoing(true)
            .setProgress(100,percent ?: 0,percent==null).addAction(0,"Parar fila",stop).build()
    }
    override fun onTimeout(startId: Int, fgsType: Int) {
        stopRequested=true
        OndaStore.dismissQuestions(OndaStore.active.value)
        MobileEngine.cancel(OndaStore.active.value)
        stopForeground(STOP_FOREGROUND_REMOVE)
        stopSelf()
    }
    override fun onDestroy() {
        stopRequested=true
        OndaStore.dismissQuestions(OndaStore.active.value)
        MobileEngine.cancel(OndaStore.active.value)
        if(lock?.isHeld==true) lock?.release()
        scope.cancel()
        super.onDestroy()
    }
    companion object {
        fun start(context: Context, only: String?=null) {
            context.startForegroundService(Intent(context,DownloadService::class.java).putExtra("only",only))
        }
        fun batch(context: Context, ids: List<String>) {
            context.startForegroundService(Intent(context,DownloadService::class.java).putStringArrayListExtra("batch",ArrayList(ids)))
        }
        fun stop(context: Context) { if(OndaStore.running.value) context.startService(Intent(context,DownloadService::class.java).setAction("stop")) }
    }
}
