package br.com.onda.mobile
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import coil.imageLoader
import org.json.JSONObject
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
    val loader=OndaStore.context.imageLoader
    fun refresh(clear:Boolean) {
        if(busy || cleaning || (clear && active.isNotBlank()))return
        if(clear)vm.stopPreview()
        vm.operation(if(clear) "cache_clear" else "cache_info",JSONObject(),dialog=false) {result->
            cleaning=true
            scope.launch {
                try {
                    if(clear) {withContext(Dispatchers.IO) {loader.memoryCache?.clear();loader.diskCache?.clear()};invalidateHistoryDetails();cleaned=true}
                    bytes=result.optLong("bytes")+(loader.diskCache?.size ?: 0L)
                } finally {cleaning=false}
            }
        }
    }
    LaunchedEffect(Unit) {refresh(false)}
    UiText("Cache",style=MaterialTheme.typography.titleMedium)
    UiText("Limpa capas, buscas e caches temporários. Downloads, fila, histórico, contas e escolhas salvas são preservados.",style=MaterialTheme.typography.bodySmall)
    bytes?.let {UiText((if(cleaned) "Cache limpo. Restante em disco: {size} MB." else "Cache em disco: {size} MB.").replace("{size}","%.2f".format(it/1048576.0)))}
    OutlinedButton(enabled=!busy && !cleaning && active.isBlank(),onClick={refresh(true)}){UiText("Limpar cache")}
    TextButton(enabled=!busy && !cleaning,onClick={refresh(false)}){UiText("Atualizar tamanho")}
    if(active.isNotBlank())UiText("Aguarde as operações em andamento antes de limpar o cache.",style=MaterialTheme.typography.bodySmall)
}
