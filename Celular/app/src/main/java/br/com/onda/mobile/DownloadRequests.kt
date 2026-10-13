package br.com.onda.mobile

import java.util.concurrent.ConcurrentLinkedQueue

internal data class DownloadRequest(val ids:Set<String>?)

internal class DownloadRequests {
    private val pending=ConcurrentLinkedQueue<DownloadRequest>()
    fun submit(only:String?=null,batch:Set<String>?=null) {
        pending.add(DownloadRequest(when {only!=null->setOf(only);batch!=null->batch.toSet();else->null}))
    }
    fun poll():DownloadRequest?=pending.poll()
    fun hasPending():Boolean=pending.isNotEmpty()
    fun clear()=pending.clear()
}

internal class DownloadScope(all:Boolean=false,ids:Set<String> = emptySet()) {
    private var allQueued=all
    private val allowed=ids.toMutableSet()
    fun include(request:DownloadRequest) {
        if(request.ids==null)allQueued=true else allowed.addAll(request.ids)
    }
    fun accepts(id:String):Boolean=allQueued || id in allowed
}
