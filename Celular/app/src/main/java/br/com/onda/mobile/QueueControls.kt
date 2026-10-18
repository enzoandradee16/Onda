package br.com.onda.mobile

import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import android.net.Uri
import android.provider.DocumentsContract
import androidx.compose.foundation.gestures.detectDragGesturesAfterLongPress
import androidx.compose.foundation.gestures.scrollBy
import androidx.compose.foundation.lazy.LazyListState
import androidx.compose.foundation.layout.sizeIn
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.*
import org.json.JSONObject

internal val queueOrders=listOf("Ordem original","Título","Menor duração","Maior duração","Menor tamanho estimado")
private fun number(value:Double)=value.takeIf {it.isFinite() && it>0}
internal fun queueDuration(item:DownloadItem):Double? {
    val info=item.config.optJSONObject("catalog_record") ?: item.config.optJSONObject("queue_info") ?: return null
    return number(info.optDouble("duration_ms"))?.div(1000) ?: number(info.optDouble("duration"))
}
internal fun queueBytes(item:DownloadItem):Long? {
    val config=item.config
    if(config.optBoolean("playlist") || config.optBoolean("link_playlist"))return null
    number(config.optDouble("_queue_estimate"))?.let {return it.toLong()}
    val mode=config.optString("mode")
    if(mode !in listOf("mp3","m4a"))return null
    val duration=queueDuration(item) ?: return null
    val quality=config.optString("audio_quality").substringBefore(' ').toIntOrNull()
    val bitrate=quality?.takeIf {it in 8..512} ?: if(mode=="mp3")320 else 256
    return (duration*bitrate*1000/8*1.02+8192).toLong()
}
internal fun orderedPending(items:List<DownloadItem>,order:String,original:List<String>):List<String> {
    val pending=items.filter {it.state=="Pendente" && it.id !in DownloadRuntime.ids}
    val ranks=original.withIndex().associate {it.value to it.index}
    return when(order) {
        "Ordem original"->pending.sortedBy {ranks[it.id] ?: Int.MAX_VALUE}
        "Título"->pending.sortedBy {it.title.lowercase()}
        else->pending.sortedWith(compareBy<DownloadItem> {if(order=="Menor tamanho estimado")queueBytes(it)==null else queueDuration(it)==null}
            .thenBy {if(order=="Menor tamanho estimado")queueBytes(it)?.toDouble() ?: 0.0 else (queueDuration(it) ?: 0.0)*(if(order=="Maior duração")-1 else 1)})
    }.map {it.id}
}
internal fun pendingOrder(items:List<DownloadItem>,ids:List<String>):List<DownloadItem>? {
    val pending=items.filter {it.state=="Pendente" && it.id !in DownloadRuntime.ids}.map {it.id}
    if(ids.size!=pending.size || ids.toSet()!=pending.toSet())return null
    val records=items.associateBy {it.id};val iterator=ids.iterator();val pendingSet=pending.toSet()
    return items.map {if(it.id in pendingSet)records.getValue(iterator.next()) else it}
}
private fun sizeText(bytes:Long):String=if(bytes>=1073741824) "%.2f GB".format(bytes/1073741824.0) else "%.1f MB".format(bytes/1048576.0)

internal data class QueueSpace(val bytes:Long,val unknown:Int,val required:Long,val free:Long?,val stagingFree:Long) {
    val low:Boolean get()=required>stagingFree || free!=null && required>free
    fun text(language:String):String=translateUi("Espaço estimado: {size} · Com temporários: {required} · Sem estimativa: {unknown}",language)
        .replace("{size}",sizeText(bytes)).replace("{required}",sizeText(required)).replace("{unknown}",unknown.toString())
}
private var lastDestination=""
private var lastDestinationFree:Long?=null
private var lastSpaceCheck=0L

@Synchronized internal fun queueSpace(items:List<DownloadItem>,inspectDestination:Boolean=false):QueueSpace {
    val sizes=items.filter {it.state in listOf("Pendente","Baixando","Aguardando escolha")}.map {queueBytes(it)}
    val known=sizes.filterNotNull();val total=known.sum()
    val required=total+2*known.sortedDescending().take(OndaStore.settings.value.optInt("concurrent_downloads",1).coerceIn(1,4)).sum()
    val staging=OndaStore.context.filesDir.usableSpace
    var free:Long?=null
    val destination=OndaStore.settings.value.optString("output_uri")
    if(destination.isBlank())free=staging
    else if(destination==lastDestination && System.currentTimeMillis()-lastSpaceCheck<15000)free=lastDestinationFree
    else if(inspectDestination)runCatching {
        val tree=Uri.parse(destination);val authority=tree.authority ?: return@runCatching
        val identity=DocumentsContract.getTreeDocumentId(tree).substringBefore(':')
        OndaStore.context.contentResolver.query(DocumentsContract.buildRootsUri(authority),arrayOf(DocumentsContract.Root.COLUMN_ROOT_ID,DocumentsContract.Root.COLUMN_AVAILABLE_BYTES),null,null,null)?.use {rows->
            while(rows.moveToNext())if(rows.getString(0)==identity && !rows.isNull(1))free=rows.getLong(1).takeIf {it>=0}
        }
    }
    if(inspectDestination && (destination!=lastDestination || System.currentTimeMillis()-lastSpaceCheck>=15000)) {lastDestination=destination;lastDestinationFree=free;lastSpaceCheck=System.currentTimeMillis()}
    return QueueSpace(total,sizes.count {it==null},required,free,staging)
}
internal fun queueConnected():Boolean {
    val manager=OndaStore.context.getSystemService(ConnectivityManager::class.java)
    val network=manager.activeNetwork ?: return false
    return manager.getNetworkCapabilities(network)?.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)==true
}
internal fun queueActivity(item:DownloadItem,running:Boolean,settings:JSONObject,connected:Boolean,paused:String=""):String=when(item.state) {
    "Pendente"->when {
        paused.isNotBlank()->paused
        settings.optBoolean("schedule_enabled") && !scheduleAllowed(settings)->"Aguardando horário"
        !connected->"Sem conexão"
        running->"Aguardando vaga"
        else->"Aguardando início"
    }
    "Aguardando escolha"->"Aguardando sua escolha"
    "Baixando"->item.activity.ifBlank {"Consultando a plataforma…"}
    else->item.state
}

@Composable internal fun QueueDragHandle(item:DownloadItem,state:LazyListState) {
    var dragging by remember {mutableStateOf(false)}
    val language=LocalUiLanguage.current
    val label=translateUi("Arrastar para reordenar",language)
    Text("↕",color=if(dragging)MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurfaceVariant,
        modifier=Modifier.sizeIn(minWidth=48.dp,minHeight=48.dp).padding(12.dp).semantics {contentDescription=label}.pointerInput(item.id,item.state) {
            coroutineScope {
                var y=0f;var target:String?=null;var scroll:Job?=null
                fun targetAtPointer() {
                    target=state.layoutInfo.visibleItemsInfo.firstOrNull {y>=it.offset && y<it.offset+it.size && it.key is String && OndaStore.items.value.any {row->row.id==it.key && row.state=="Pendente"}}?.key as? String
                }
                try {detectDragGesturesAfterLongPress(
                    onDragStart={
                        if(item.state=="Pendente") {
                            dragging=true
                            y=state.layoutInfo.visibleItemsInfo.firstOrNull {it.key==item.id}?.let {it.offset+it.size/2f} ?: 0f
                            scroll=launch {while(isActive) {
                                val layout=state.layoutInfo
                                val speed=when {y<layout.viewportStartOffset+70->-18f;y>layout.viewportEndOffset-70->18f;else->0f}
                                if(speed!=0f) {state.scrollBy(speed);targetAtPointer()}
                                delay(16)
                            }}
                        }
                    },onDrag={change,amount->if(dragging){change.consume();y+=amount.y;targetAtPointer()}},
                    onDragEnd={scroll?.cancel();if(dragging)target?.let {OndaStore.movePendingBefore(item.id,it)};dragging=false;target=null},
                    onDragCancel={scroll?.cancel();dragging=false;target=null})
                } finally {scroll?.cancel()}
            }
        })
}
