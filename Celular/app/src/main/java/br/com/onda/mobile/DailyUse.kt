package br.com.onda.mobile

import android.Manifest
import android.app.*
import android.content.*
import android.content.pm.PackageManager
import android.media.AudioManager
import android.media.RingtoneManager
import android.media.ToneGenerator
import android.net.*
import android.os.*
import androidx.core.app.NotificationCompat
import androidx.core.content.ContextCompat
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import org.json.JSONObject

internal val finishActions=listOf("Nenhuma","Som","Notificação","Som e notificação")
internal val wifiLossActions=listOf("Pausar downloads","Concluir downloads ativos")
internal enum class QueueGate { RUN, PAUSE, WIFI }
internal fun queueGate(wifiOnly:Boolean,paused:Boolean,connected:Boolean,wifi:Boolean):QueueGate=when {
    paused->QueueGate.PAUSE
    wifiOnly && (!connected || !wifi)->QueueGate.WIFI
    else->QueueGate.RUN
}
internal fun interruptForGate(gate:QueueGate,loss:String)=gate==QueueGate.PAUSE || gate==QueueGate.WIFI && loss!="Concluir downloads ativos"
internal fun interruptedDownload(stopped:Boolean,cancelled:Boolean,pausedCancellation:Boolean,hasError:Boolean,code:Int)=stopped || cancelled || pausedCancellation && (hasError || code!=0)
internal fun notificationActions(enabled:Boolean,paused:Boolean)=if(!enabled)emptyList() else listOf(if(paused)"Retomar fila" else "Pausar fila","Parar fila","Abrir fila")

internal class QueueNetwork(context:Context):AutoCloseable {
    private val manager=context.getSystemService(ConnectivityManager::class.java)
    @Volatile private var current:Network?=manager.activeNetwork
    @Volatile var connected=false;private set
    @Volatile var wifi=false;private set
    private fun update(capabilities:NetworkCapabilities?) {
        connected=capabilities?.hasCapability(NetworkCapabilities.NET_CAPABILITY_VALIDATED)==true
        wifi=capabilities?.hasTransport(NetworkCapabilities.TRANSPORT_WIFI)==true
        val settings=OndaStore.settings.value
        if(DownloadRuntime.running.get() && settings.optBoolean("wifi_only") && (!connected || !wifi) && settings.optString("wifi_loss")!="Concluir downloads ativos")DownloadRuntime.interruptActive()
    }
    private val callback=object:ConnectivityManager.NetworkCallback() {
        override fun onAvailable(network:Network) {if(network!=current){current=network;update(null)}}
        override fun onCapabilitiesChanged(network:Network,capabilities:NetworkCapabilities) {if(network==current)update(capabilities)}
        override fun onLost(network:Network) {if(network==current){current=null;update(null)}}
    }
    private val registered:Boolean
    init {update(current?.let {manager.getNetworkCapabilities(it)});registered=runCatching {manager.registerDefaultNetworkCallback(callback);true}.getOrDefault(false)}
    fun gate(settings:JSONObject):QueueGate {
        if(!registered)update(manager.activeNetwork?.let {manager.getNetworkCapabilities(it)})
        return queueGate(settings.optBoolean("wifi_only"),DownloadRuntime.paused,connected,wifi)
    }
    override fun close() {if(registered)runCatching {manager.unregisterNetworkCallback(callback)}}
}

internal fun openQueueIntent(context:Context)=Intent(context,MainActivity::class.java).putExtra("open_queue",true).addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP or Intent.FLAG_ACTIVITY_CLEAR_TOP)

internal fun queueFinished(context:Context,done:Int,total:Int) {
    if(total==0)return
    val action=OndaStore.settings.value.optString("finish_action","Notificação")
    if(action=="Som") {
        runCatching {
            val sound=ToneGenerator(AudioManager.STREAM_NOTIFICATION,60)
            sound.startTone(ToneGenerator.TONE_PROP_ACK,250)
            Handler(Looper.getMainLooper()).postDelayed({sound.release()},500)
        }
        return
    }
    if(action !in listOf("Notificação","Som e notificação"))return
    if(Build.VERSION.SDK_INT>=33 && ContextCompat.checkSelfPermission(context,Manifest.permission.POST_NOTIFICATIONS)!=PackageManager.PERMISSION_GRANTED)return
    val manager=context.getSystemService(NotificationManager::class.java)
    val channelId=if(action=="Som e notificação")"queue-finished-sound" else "queue-finished-silent"
    val name=translateUi("Conclusão da fila")
    val channel=manager.getNotificationChannel(channelId) ?: NotificationChannel(channelId,name,NotificationManager.IMPORTANCE_DEFAULT).apply {
        if(action=="Som e notificação")setSound(RingtoneManager.getDefaultUri(RingtoneManager.TYPE_NOTIFICATION),android.media.AudioAttributes.Builder().setUsage(android.media.AudioAttributes.USAGE_NOTIFICATION).build())
        else setSound(null,null)
    }
    channel.name=name;manager.createNotificationChannel(channel)
    val open=PendingIntent.getActivity(context,31,openQueueIntent(context),PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)
    val message=translateUi("Fila finalizada: {done}/{total} concluídos.").replace("{done}",done.toString()).replace("{total}",total.toString())
    val notification=NotificationCompat.Builder(context,channelId).setSmallIcon(R.drawable.ic_onda_notification).setContentTitle("ONDA").setContentText(message).setContentIntent(open).setAutoCancel(true).build()
    runCatching {manager.notify(31,notification)}
}

@Composable internal fun DailyDownloadControls(settings:JSONObject,put:(String,Any)->Unit) {
    SettingsDivider()
    Toggle("Somente Wi-Fi",settings.optBoolean("wifi_only")){put("wifi_only",it)}
    if(settings.optBoolean("wifi_only"))Select("Ao perder o Wi-Fi",settings.optString("wifi_loss","Pausar downloads"),wifiLossActions){put("wifi_loss",it)}
    UiText("Sem Wi-Fi, a fila aguarda e retoma automaticamente quando a conexão volta.",style=MaterialTheme.typography.bodySmall)
    if(settings.optBoolean("wifi_only") && settings.optString("wifi_loss")=="Concluir downloads ativos")UiText("Concluir ativos pode usar dados móveis; novos downloads aguardam Wi-Fi.",style=MaterialTheme.typography.bodySmall)
    SettingsDivider()
    Select("Ação ao terminar a fila",settings.optString("finish_action","Notificação"),finishActions){put("finish_action",it)}
    Toggle("Controles na notificação",settings.optBoolean("notification_controls",true)){put("notification_controls",it)}
}
