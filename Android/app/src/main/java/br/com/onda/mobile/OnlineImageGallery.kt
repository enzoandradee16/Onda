package br.com.onda.mobile

import android.content.Intent
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import org.json.JSONObject
import java.io.File

internal fun canPreviewOnlineImages(config:JSONObject):Boolean {
    val uri=android.net.Uri.parse(config.optString("url"))
    val path=uri.path.orEmpty().lowercase()
    if(listOf(".mp4",".mkv",".webm",".mov",".mp3",".m4a",".flac",".wav",".ogg").any {path.endsWith(it)})return false
    return config.optString("mode") in listOf("photos","social") || historyKind("",path)=="Imagens"
}

@Composable internal fun OnlineImagePreviewButton(vm:OndaViewModel,url:String,modifier:Modifier=Modifier) {
    val loading by vm.onlineImageLoading.collectAsStateWithLifecycle()
    val active=loading.isNotBlank()&&loading==url
    OutlinedButton(onClick={if(active)vm.cancelOnlineImagePreview() else vm.previewOnlineImages(url)},enabled=url.isNotBlank(),contentPadding=PaddingValues(horizontal=12.dp,vertical=4.dp),modifier=modifier.heightIn(min=32.dp).testTag("online-image-preview-button")) {
        UiText(if(active)"Cancelar prévia" else "Prévia de imagens",style=MaterialTheme.typography.labelSmall)
    }
}

@Composable internal fun OnlineImageGallery(vm:OndaViewModel) {
    val manifest by vm.onlineImageGallery.collectAsStateWithLifecycle()
    val gallery=manifest ?: return
    val images=gallery.optJSONArray("images")?.objects().orEmpty()
    if(images.isEmpty())return
    val token=gallery.getString("token")
    val index by vm.onlineImageIndex.collectAsStateWithLifecycle()
    val result by vm.onlineImageThumbnail.collectAsStateWithLifecycle()
    var loaded by remember(token,index,result?.optString("path")) {mutableStateOf(false)}
    Dialog(onDismissRequest=vm::closeOnlineImages,properties=DialogProperties(usePlatformDefaultWidth=false)) {
        Surface(Modifier.fillMaxSize()) {
            Column(Modifier.safeDrawingPadding().padding(16.dp),verticalArrangement=Arrangement.spacedBy(12.dp)) {
                UiText("Prévia antes de baixar",style=MaterialTheme.typography.titleLarge)
                Text(images[index].optString("name"),maxLines=2)
                Box(Modifier.weight(1f).fillMaxWidth().gallerySwipe(previous={if(index>0)vm.previewOnlineImageAt(index-1)},next={if(index<images.lastIndex)vm.previewOnlineImageAt(index+1)}),contentAlignment=Alignment.Center) {
                    when {
                        result==null->CircularProgressIndicator()
                        result!!.has("error")->Column {UiErrorText(result!!.optString("error"));TextButton(onClick={vm.previewOnlineImageAt(index)}){UiText("Tentar novamente")}}
                        else->coil.compose.SubcomposeAsyncImage(File(result!!.getString("path")),translateUi("Prévia da imagem"),Modifier.fillMaxSize().testTag("online-gallery-image").semantics {stateDescription=if(loaded)"Imagem carregada" else "Carregando imagem…"},contentScale=ContentScale.Fit,onSuccess={loaded=true},loading={CircularProgressIndicator(Modifier.size(36.dp))},error={UiText("Não foi possível abrir este arquivo.")})
                    }
                    GalleryArrows(index,images.size,previous={if(index>0)vm.previewOnlineImageAt(index-1)},next={if(index<images.lastIndex)vm.previewOnlineImageAt(index+1)})
                }
                Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween) {
                    TextButton(onClick={vm.previewOnlineImageAt(index-1)},enabled=index>0){UiText("Anterior")}
                    Text("${index+1} / ${images.size}")
                    TextButton(onClick={vm.previewOnlineImageAt(index+1)},enabled=index<images.lastIndex){UiText("Próxima")}
                }
                Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(8.dp)) {
                    TextButton(onClick={
                        val share=Intent(Intent.ACTION_SEND).setType("text/plain").putExtra(Intent.EXTRA_TEXT,gallery.getString("source_url"))
                        runCatching {OndaStore.context.startActivity(Intent.createChooser(share,translateUi("Compartilhar link")).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))}.onFailure {vm.showNotice("Compartilhar","Não foi possível abrir este arquivo.")}
                    }){UiText("Compartilhar link")}
                    Button(onClick=vm::downloadOnlineImages){UiText("Baixar imagens")}
                }
                TextButton(onClick=vm::closeOnlineImages){UiText("Fechar")}
            }
        }
    }
}
