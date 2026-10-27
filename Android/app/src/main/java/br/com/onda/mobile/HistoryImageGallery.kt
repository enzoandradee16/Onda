package br.com.onda.mobile

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties

@Composable internal fun HistoryImageGallery(initial:HistoryItem,vm:OndaViewModel,close:()->Unit) {
    val history by OndaStore.history.collectAsStateWithLifecycle()
    val images=remember(initial.id,history) {history.filter {
        historyKind(it.mode,it.title)=="Imagens" && (it.id==initial.id || initial.source.isNotBlank() && it.source==initial.source)
    }.ifEmpty {listOf(initial)}.distinctBy {it.uri}.sortedBy {it.id}}
    var currentId by remember(initial.id) {mutableLongStateOf(initial.id)}
    val index=images.indexOfFirst {it.id==currentId}.coerceAtLeast(0)
    val current=images[index]
    var loaded by remember(current.uri) {mutableStateOf(false)}
    Dialog(close,properties=DialogProperties(usePlatformDefaultWidth=false)) {
        Surface(Modifier.fillMaxSize()) {
            Column(Modifier.safeDrawingPadding().padding(16.dp)) {
                Text(current.title,maxLines=2)
                Box(Modifier.fillMaxWidth().weight(1f)) {
                coil.compose.SubcomposeAsyncImage(current.uri,translateUi("Prévia da imagem"),Modifier.fillMaxSize().gallerySwipe(previous={if(index>0)currentId=images[index-1].id},next={if(index<images.lastIndex)currentId=images[index+1].id}).testTag("gallery-image").semantics {stateDescription=if(loaded)"Imagem carregada" else "Carregando imagem…"},contentScale=ContentScale.Fit,onSuccess={loaded=true},loading={CircularProgressIndicator(Modifier.size(36.dp))},
                    error={UiText("Não foi possível abrir este arquivo.")})
                    GalleryArrows(index,images.size,previous={if(index>0)currentId=images[index-1].id},next={if(index<images.lastIndex)currentId=images[index+1].id})
                }
                Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween) {
                    TextButton(onClick={currentId=images[index-1].id},enabled=index>0){UiText("Anterior")}
                    Text("${index+1} / ${images.size}")
                    TextButton(onClick={currentId=images[index+1].id},enabled=index<images.lastIndex){UiText("Próxima")}
                }
                Row {
                    TextButton(onClick={runCatching {OndaStore.share(current.uri,current.title)}.onFailure {vm.showNotice("Compartilhar","Não foi possível abrir este arquivo.")}}){UiText("Compartilhar")}
                    TextButton(onClick=close){UiText("Fechar")}
                }
            }
        }
    }
}
