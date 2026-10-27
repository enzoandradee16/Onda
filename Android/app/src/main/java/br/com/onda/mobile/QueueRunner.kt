package br.com.onda.mobile

import android.content.Context
import kotlinx.coroutines.*
import org.json.JSONObject
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.atomic.AtomicBoolean

object DownloadRuntime {
    val running=AtomicBoolean(false)
    val ids:MutableSet<String> = ConcurrentHashMap.newKeySet()
    @Volatile var stopped=false
    @Volatile var paused=false
    val pauseCancelled:MutableSet<String> = ConcurrentHashMap.newKeySet()
    fun pause() {paused=true;OndaStore.queuePause.value="Fila pausada";interruptActive()}
    fun resume() {paused=false;OndaStore.queuePause.value=""}
    fun interruptActive() {ids.toList().forEach {pauseCancelled.add(it);OndaStore.dismissQuestions(it);MobileEngine.cancel(it)}}
    internal val requests=DownloadRequests()
    fun stop() {stopped=true;paused=false;OndaStore.queuePause.value="";requests.clear();ids.toList().forEach {OndaStore.dismissQuestions(it);MobileEngine.cancel(it)}}
}

suspend fun runDownloads(context:Context,only:String?=null,batch:Set<String>?=null,scheduled:Boolean=false,requestsOnly:Boolean=false,notify:(String,Int?)->Unit):Boolean=coroutineScope {
    if(scheduled && queueSpace(OndaStore.items.value).low) {notify("Espaço possivelmente insuficiente",null);return@coroutineScope false}
    if(!DownloadRuntime.running.compareAndSet(false,true)) return@coroutineScope false
    DownloadRuntime.stopped=false;DownloadRuntime.paused=false;DownloadRuntime.pauseCancelled.clear();OndaStore.queuePause.value="";OndaStore.queueTiming.setRunning(true);OndaStore.running.value=true
    val tasks=mutableMapOf<String,Job>()
    val attempted=mutableSetOf<String>();var finishedNormally=false
    val selection=DownloadScope(!requestsOnly && only==null && batch==null,batch ?: only?.let {setOf(it)} ?: emptySet())
    val notificationGate=ProgressGate(500)
    val network=QueueNetwork(context)
    var waitReason=""
    try {
        while(isActive && !DownloadRuntime.stopped) {
            while(true) {val request=DownloadRuntime.requests.poll() ?: break;selection.include(request)}
            if(scheduled && !scheduleAllowed(OndaStore.settings.value)) {DownloadRuntime.stop();break}
            tasks.entries.removeAll {it.value.isCompleted}
            val gate=network.gate(OndaStore.settings.value)
            if(gate!=QueueGate.RUN) {
                val reason=if(gate==QueueGate.PAUSE)"Fila pausada" else "Aguardando Wi-Fi"
                OndaStore.queuePause.value=reason
                OndaStore.queueTiming.setRunning(tasks.isNotEmpty())
                if(interruptForGate(gate,OndaStore.settings.value.optString("wifi_loss")))DownloadRuntime.interruptActive()
                if(reason!=waitReason || notificationGate.allow()) {notify(reason,null);waitReason=reason}
                val pending=OndaStore.items.value.any {it.state=="Pendente" && selection.accepts(it.id)}
                if(tasks.isEmpty() && !pending && !DownloadRuntime.requests.hasPending())break
                delay(500);continue
            }
            waitReason="";OndaStore.queuePause.value="";OndaStore.queueTiming.setRunning(true)
            val limit=OndaStore.settings.value.optInt("concurrent_downloads",1).coerceIn(1,4)
            while(tasks.size<limit) {
                val item=OndaStore.items.value.firstOrNull {it.state=="Pendente" && it.id !in DownloadRuntime.ids && selection.accepts(it.id)} ?: break
                attempted.add(item.id)
                DownloadRuntime.ids.add(item.id);OndaStore.active.value=DownloadRuntime.ids.firstOrNull().orEmpty()
                OndaStore.update(item.id,"Baixando",activity="Consultando a plataforma…")
                tasks[item.id]=launch(Dispatchers.IO) {
                    try {
                        val config=applyVersionSelection(OndaStore.executionConfig(item.config),OndaStore.settings.value).put("spotify_client_secret",SecureVault.get("spotify-api") ?: "").put("_identity",item.id)
                        if(interruptForGate(network.gate(OndaStore.settings.value),OndaStore.settings.value.optString("wifi_loss"))) {
                            DownloadRuntime.pauseCancelled.add(item.id);OndaStore.update(item.id,"Pendente");return@launch
                        }
                        var failed=false
                        val progressGate=ProgressGate(150)
                        val result=MobileEngine.call(context,item.id,config.optString("_operation","download"),config,EventCallback {raw->
                            val event=JSONObject(raw)
                            when(event.optString("type")) {
                                "progress"->{val total=event.optDouble("total",0.0);val percent=if(total>0)(event.optDouble("downloaded")/total*100).toFloat().coerceIn(0f,100f) else 0f
                                    val finished=event.optString("status")=="finished"
                                    if(progressGate.allow(finished)) OndaStore.update(item.id,"Baixando",percent,event.optString("title"),downloadDetail(event))
                                    if(notificationGate.allow(finished)) notify("${DownloadRuntime.ids.size} em andamento · ${item.title}",percent.toInt())}
                                "stage"->OndaStore.update(item.id,"Baixando",message=event.optString("message"),activity=event.optString("message"))
                                "processing"->OndaStore.update(item.id,"Baixando",activity="Convertendo arquivo…")
                                "file"->if(!event.optBoolean("skipped")) {OndaStore.update(item.id,"Baixando",activity="Salvando");val uri=OndaStore.publish(event.getString("path"),OndaStore.publicationConfig(config,event),event.optString("mode"));OndaStore.log("Salvo: $uri")}
                                "done"->{
                                    if(event.has("path")) OndaStore.publish(event.getString("path"),OndaStore.publicationConfig(config,event),event.getString("path").substringAfterLast('.'))
                                    OndaStore.update(item.id,"Baixando",100f,"Arquivo salvo; finalizando a execução…",activity="Finalizando arquivo…")
                                }
                                "error"->{if(item.id !in DownloadRuntime.pauseCancelled) {failed=true;OndaStore.update(item.id,"Erro",message=event.optString("message"));OndaStore.log(event.optString("message"))}}
                                "choose_flac","choose_version","choose_catalog","choose_duplicate","choose_media","review_metadata"->{OndaStore.update(item.id,"Aguardando escolha",activity="Aguardando sua escolha");OndaStore.ask(item.id,event);notify("Abra o ONDA para confirmar sua escolha",null)}
                                "estimate"->{if(!event.optBoolean("playlist"))OndaStore.queueEstimate(item.id,event.optLong("size"));val size=event.optDouble("size",0.0)/1048576;if(size>0)OndaStore.update(item.id,"Baixando",message="Tamanho estimado: ≈ %.1f MB".format(size))}
                                else->{val message=event.optString("message");if(message.isNotBlank()){OndaStore.log(message);OndaStore.update(item.id,"Baixando",message=message)}}
                            }
                        })
                        if(interruptedDownload(DownloadRuntime.stopped,result.optBoolean("cancelled"),item.id in DownloadRuntime.pauseCancelled,result.has("error"),result.optInt("code",-1))) OndaStore.update(item.id,"Pendente",message="Interrompido; o arquivo será retomado quando possível.")
                        else if(result.has("error")) OndaStore.update(item.id,"Erro",message=result.optString("error"))
                        else if(!failed && result.optInt("code")==0) OndaStore.update(item.id,"Concluído",100f,"Arquivo salvo")
                        else OndaStore.update(item.id,"Erro")
                    } catch(error:CancellationException) {OndaStore.update(item.id,"Pendente");throw error}
                    catch(error:Exception) {OndaStore.update(item.id,if(item.id in DownloadRuntime.pauseCancelled)"Pendente" else "Erro",message=error.message ?: "Falha no download")}
                    finally {OndaStore.dismissQuestions(item.id);DownloadRuntime.ids.remove(item.id);DownloadRuntime.pauseCancelled.remove(item.id);OndaStore.active.value=DownloadRuntime.ids.firstOrNull().orEmpty()}
                }
            }
            if(tasks.isEmpty())break
            delay(200)
        }
        if(DownloadRuntime.stopped) DownloadRuntime.ids.toList().forEach {MobileEngine.cancel(it)}
        tasks.values.joinAll()
        finishedNormally=!DownloadRuntime.stopped && isActive
        true
    } finally {
        network.close();DownloadRuntime.paused=false;DownloadRuntime.pauseCancelled.clear();OndaStore.queuePause.value=""
        DownloadRuntime.ids.toList().forEach {MobileEngine.cancel(it);OndaStore.dismissQuestions(it);OndaStore.update(it,"Pendente")}
        DownloadRuntime.ids.clear();OndaStore.active.value="";OndaStore.queueTiming.setRunning(false);OndaStore.running.value=false;DownloadRuntime.running.set(false)
        if(finishedNormally && attempted.isNotEmpty())queueFinished(context,OndaStore.items.value.count {it.id in attempted && it.state=="Concluído"},attempted.size)
        if(finishedNormally) OndaStore.failureSummary.value=finishedFailureIds(attempted,OndaStore.items.value.map {it.id to it.state},true).takeIf {it.isNotEmpty()}
    }
}
