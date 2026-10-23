package br.com.onda.mobile
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import coil.imageLoader
import org.json.JSONObject
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.launch
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

@OptIn(coil.annotation.ExperimentalCoilApi::class)
@Composable internal fun CacheControls(vm:OndaViewModel) {
    val busy by vm.busy.collectAsStateWithLifecycle()
    val active by OndaStore.active.collectAsStateWithLifecycle()
    var bytes by remember {mutableStateOf<Long?>(null)}
    var cleaned by remember {mutableStateOf(false)}
    val scope=rememberCoroutineScope()
    var cleaning by remember {mutableStateOf(false)}
    var reading by remember {mutableStateOf(false)}
    var readError by remember {mutableStateOf("")}
    val loader=OndaStore.context.imageLoader
    suspend fun readSize() {
        if(reading)return
        reading=true;readError=""
        try {
            val result=withContext(Dispatchers.IO) {
                MobileEngine.call(OndaStore.context,"cache-info-"+java.util.UUID.randomUUID(),"cache_info",JSONObject(),EventCallback {})
            }
            if(result.has("error"))readError=result.optString("error")
            else bytes=result.optLong("bytes")+(loader.diskCache?.size ?: 0L)
        } catch(cancelled:CancellationException) {throw cancelled}
        catch(error:Exception) {readError=error.message ?: "Erro na operação"}
        finally {reading=false}
    }
    fun clear() {
        if(busy || cleaning || reading || active.isNotBlank())return
        readError="";vm.stopPreview()
        vm.operation("cache_clear",JSONObject(),dialog=false) {result->
            cleaning=true
            scope.launch {
                try {
                    withContext(Dispatchers.IO) {loader.memoryCache?.clear();loader.diskCache?.clear()}
                    invalidateHistoryDetails();cleaned=true
                    bytes=result.optLong("bytes")+(loader.diskCache?.size ?: 0L)
                } finally {cleaning=false}
            }
        }
    }
    LaunchedEffect(Unit) {readSize()}
    UiText("Cache",style=MaterialTheme.typography.titleMedium)
    UiText("Limpa capas, buscas e caches temporários. Downloads, fila, histórico, contas e escolhas salvas são preservados.",style=MaterialTheme.typography.bodySmall)
    bytes?.let {UiText((if(cleaned) "Cache limpo. Restante em disco: {size} MB." else "Cache em disco: {size} MB.").replace("{size}","%.2f".format(it/1048576.0)))}
    if(readError.isNotBlank())UiText(readError,style=MaterialTheme.typography.bodySmall,color=MaterialTheme.colorScheme.error)
    OutlinedButton(enabled=!busy && !cleaning && !reading && active.isBlank(),onClick={clear()}){UiText("Limpar cache")}
    TextButton(enabled=!busy && !cleaning && !reading,onClick={scope.launch {readSize()}}){UiText("Atualizar tamanho")}
    if(active.isNotBlank())UiText("Aguarde as operações em andamento antes de limpar o cache.",style=MaterialTheme.typography.bodySmall)
}
