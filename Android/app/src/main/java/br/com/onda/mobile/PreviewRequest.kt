package br.com.onda.mobile

import java.util.UUID
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Job
import kotlinx.coroutines.launch

/** Main-thread owner of the latest preview lookup, including blocking backend work. */
internal class PreviewRequest(private val scope:CoroutineScope,private val cancelBackend:(String)->Unit) {
    private var generation=0L
    private var operationId:String?=null
    private var job:Job?=null

    fun cancel() {
        generation++
        val previous=operationId
        operationId=null
        job?.cancel();job=null
        if(previous!=null)cancelBackend(previous)
    }

    fun <T> start(resolve:suspend (String)->T,onResult:(T)->Unit,onError:(Exception)->Unit) {
        cancel()
        val revision=generation
        val id=UUID.randomUUID().toString()
        operationId=id
        job=scope.launch {
            try {
                val result=resolve(id)
                if(revision==generation)onResult(result)
            } catch(error:CancellationException) {
                throw error
            } catch(error:Exception) {
                if(revision==generation)onError(error)
            } finally {
                if(revision==generation)operationId=null
            }
        }
    }
}
