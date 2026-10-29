package br.com.onda.mobile

import androidx.compose.foundation.*
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import coil.compose.AsyncImage
import org.json.JSONObject
import java.io.File
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.first

@Composable fun ImagesPage(vm: OndaViewModel) {
    val settings by OndaStore.settings.collectAsStateWithLifecycle()
    val busy by vm.busy.collectAsStateWithLifecycle()
    val manifest by vm.onlineImageGallery.collectAsStateWithLifecycle()
    val embedded by vm.onlineImageEmbedded.collectAsStateWithLifecycle()
    val loading by vm.onlineImageLoading.collectAsStateWithLifecycle()
    val remoteError by vm.onlineImageError.collectAsStateWithLifecycle()
    val index by vm.onlineImageIndex.collectAsStateWithLifecycle()
    var link by rememberSaveable {mutableStateOf("")}
    var source by rememberSaveable {mutableStateOf("")}
    var preview by remember {mutableStateOf("")}
    var dimensions by remember {mutableStateOf("")}
    var more by remember {mutableStateOf(false)}
    fun clearPreview(){if(preview.isNotBlank())File(preview).delete();preview="";dimensions=""}
    fun clearRemote(){vm.cancelOnlineImagePreview();vm.closeOnlineImages()}
    val local=rememberImageSourcePicker(arrayOf("image/*")) {uri->
        clearRemote();clearPreview();source=""
        vm.importLocal(uri,"image"){source=it.absolutePath;link=""}
    }
    val gallery=manifest?.takeIf {embedded && source.isBlank() && link.isNotBlank()}
    val images=gallery?.optJSONArray("images")?.objects().orEmpty()
    val active=index.coerceIn(0,images.lastIndex.coerceAtLeast(0))
    val searching=embedded && loading.isNotBlank()
    fun imageConfig()=OndaStore.config(JSONObject(settings.toString()).put("mode","photos")).put("url",link).apply {
        if(source.isNotBlank())put("source",source).put("name",File(source).name.replaceFirst(Regex("^image-[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}-"),""))
    }
    fun previewOptions(config:JSONObject)=listOf("image_format","image_size","image_width","image_height","keep_ratio").joinToString("|"){config.optString(it)}
    val optionsKey=previewOptions(settings)
    var requestedLocalPreview by remember {mutableStateOf("")}
    fun loadPreview() {
        val inputSource=source;val inputLink=link;val inputOptions=previewOptions(settings)
        requestedLocalPreview=inputSource+"|"+inputOptions
        vm.operation("image_preview",imageConfig()){result->
            val path=result.getString("path")
            if(source==inputSource && link==inputLink && previewOptions(OndaStore.settings.value)==inputOptions) {
                if(preview.isNotBlank() && preview!=path)File(preview).delete()
                preview=path;dimensions="${result.optInt("width")} × ${result.optInt("height")} · ${result.optString("format")}"
            } else File(path).delete()
        }
    }
    fun search(){
        if(searching)vm.cancelOnlineImagePreview()
        else if(source.isNotBlank() && !busy)loadPreview()
        else if(link.isNotBlank() && !busy)vm.previewOnlineImages(link.trim(),embedded=true)
    }
    fun download(){
        if(source.isNotBlank())vm.operation("image_convert",imageConfig())
        else if(gallery!=null)vm.downloadOnlineImages(keepPreview=true)
        else if(link.isNotBlank()) {
            val id=OndaStore.enqueue(link,options=JSONObject(settings.toString()).put("mode","photos"),extra=JSONObject().put("_immediate",true))
            if(id.isNotBlank())DownloadService.start(OndaStore.context,id)
        }
    }
    val shareUrl=gallery?.optString("source_url").orEmpty().ifBlank {link.trim()}
    fun share(){
        if(shareUrl.isBlank())return
        val intent=android.content.Intent(android.content.Intent.ACTION_SEND).setType("text/plain").putExtra(android.content.Intent.EXTRA_TEXT,shareUrl)
        runCatching {OndaStore.context.startActivity(android.content.Intent.createChooser(intent,translateUi("Compartilhar link")).addFlags(android.content.Intent.FLAG_ACTIVITY_NEW_TASK))}
            .onFailure {vm.showNotice("Compartilhar","Não foi possível abrir este arquivo.")}
    }
    LaunchedEffect(source,optionsKey) {
        if(source.isNotBlank()) {
            delay(250);vm.busy.first {!it}
            if(requestedLocalPreview!=source+"|"+optionsKey)loadPreview()
        }
    }
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).imePadding().padding(horizontal=LayoutSpacing.inset).testTag("images-page"),verticalArrangement=Arrangement.spacedBy(12.dp)) {
        ToolHeading("Imagens") {
            Box {
                IconButton(onClick={more=true},modifier=Modifier.testTag("images-more-actions")){OndaIcon("more-vertical","Mais ações",Modifier.size(22.dp))}
                DropdownMenu(more,{more=false}) {
                    DropdownMenuItem(text={UiText("Escolher arquivo")},onClick={more=false;local()})
                    DropdownMenuItem(text={UiText("Adicionar à fila")},enabled=link.isNotBlank(),onClick={more=false;OndaStore.enqueue(link,options=JSONObject(settings.toString()).put("mode","photos"))})
                }
            }
        }
        Surface(shape=RoundedCornerShape(14.dp),color=MaterialTheme.colorScheme.surfaceContainerLow,border=BorderStroke(1.dp,MaterialTheme.colorScheme.outlineVariant),modifier=Modifier.fillMaxWidth()) {
            Column(Modifier.padding(12.dp),verticalArrangement=Arrangement.spacedBy(10.dp)) {
                val clipboard=androidx.compose.ui.platform.LocalClipboardManager.current
                OutlinedTextField(link,{value->link=value;source="";clearPreview();clearRemote()},placeholder={UiText("Link da imagem ou publicação",maxLines=1)},singleLine=true,shape=RoundedCornerShape(12.dp),
                    leadingIcon={OndaIcon("link",modifier=Modifier.size(20.dp))},
                    trailingIcon={IconButton(onClick={clipboard.getText()?.text?.let {link=it;source="";clearPreview();clearRemote()}}){OndaIcon("paste","Colar",Modifier.size(22.dp))}},
                    keyboardOptions=androidx.compose.foundation.text.KeyboardOptions(imeAction=androidx.compose.ui.text.input.ImeAction.Search),
                    keyboardActions=androidx.compose.foundation.text.KeyboardActions(onSearch={search()}),modifier=Modifier.fillMaxWidth().testTag("images-source-link").a11yLabel("Link da imagem ou publicação"))
                UiText("Imagens e carrosséis",style=MaterialTheme.typography.bodySmall,color=MaterialTheme.colorScheme.onSurfaceVariant)
                Button(onClick=::search,enabled=searching||(!busy&&(link.isNotBlank()||source.isNotBlank())),shape=RoundedCornerShape(12.dp),modifier=Modifier.align(Alignment.End).heightIn(min=48.dp).testTag("images-search")){UiText(if(searching)"Cancelar" else "Pesquisar")}
            }
        }
        Surface(shape=RoundedCornerShape(14.dp),color=MaterialTheme.colorScheme.surfaceContainerLow,border=BorderStroke(1.dp,MaterialTheme.colorScheme.outlineVariant),modifier=Modifier.fillMaxWidth().testTag("images-options")) {
            Column(Modifier.padding(12.dp),verticalArrangement=Arrangement.spacedBy(10.dp)) {
                UiText("Opções de imagem",style=MaterialTheme.typography.titleSmall)
                if(source.isNotBlank())Text(File(source).name,style=MaterialTheme.typography.bodySmall)
                if(dimensions.isNotBlank())Text(dimensions,style=MaterialTheme.typography.bodySmall)
                ImageOptions(settings,OndaStore::saveSettings,forceVisible=true)
                if(settings.optString("image_format")=="SVG")UiText("SVG incorpora a imagem original; não vetoriza. Animações usam o primeiro quadro.",style=MaterialTheme.typography.bodySmall,color=MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
        Row(Modifier.fillMaxWidth(),verticalAlignment=Alignment.CenterVertically) {
            UiText("Prévia",Modifier.weight(1f),style=MaterialTheme.typography.titleMedium)
            if(images.isNotEmpty())Text("${active+1} / ${images.size}",style=MaterialTheme.typography.bodySmall,color=MaterialTheme.colorScheme.onSurfaceVariant)
            else if(preview.isNotBlank())Text("1 / 1",style=MaterialTheme.typography.bodySmall,color=MaterialTheme.colorScheme.onSurfaceVariant)
        }
        when {
            gallery!=null && images.isNotEmpty()->InlineOnlineImageGallery(vm)
            preview.isNotBlank()->AsyncImage(File(preview),translateUi("Prévia da imagem"),Modifier.fillMaxWidth().aspectRatio(4f/3f).clip(RoundedCornerShape(14.dp)).testTag("images-local-preview"),contentScale=androidx.compose.ui.layout.ContentScale.Fit)
            remoteError.isNotBlank() && embedded->Surface(shape=RoundedCornerShape(14.dp),color=MaterialTheme.colorScheme.surfaceContainerLow,modifier=Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp)){UiErrorText(remoteError);TextButton(onClick=::search){UiText("Tentar novamente")}}
            }
            else->Box(Modifier.fillMaxWidth().aspectRatio(4f/3f).clip(RoundedCornerShape(14.dp)).background(MaterialTheme.colorScheme.surfaceContainerLow),contentAlignment=Alignment.Center) {
                if(searching)CircularProgressIndicator() else Column(horizontalAlignment=Alignment.CenterHorizontally,verticalArrangement=Arrangement.spacedBy(8.dp)) {
                    OndaIcon("image",modifier=Modifier.size(40.dp),tint=MaterialTheme.colorScheme.onSurfaceVariant)
                    UiText("Sua imagem aparece aqui",style=MaterialTheme.typography.bodyMedium,color=MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }
        }
        if(images.size>1) {
            val start=(active-3).coerceIn(0,(images.size-7).coerceAtLeast(0))
            Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.Center,verticalAlignment=Alignment.CenterVertically) {
                for(dot in start until minOf(start+7,images.size))IconButton(onClick={if(dot!=active)vm.previewOnlineImageAt(dot)},modifier=Modifier.size(28.dp).a11yLabel(translateUi("Prévia da imagem")+" ${dot+1} / ${images.size}")) {
                    Box(Modifier.size(if(dot==active)8.dp else 6.dp).background(if(dot==active)MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.outlineVariant,androidx.compose.foundation.shape.CircleShape))
                }
            }
        }
        Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(10.dp)) {
            OutlinedButton(onClick=::share,enabled=shareUrl.isNotBlank(),shape=RoundedCornerShape(12.dp),contentPadding=PaddingValues(horizontal=8.dp,vertical=12.dp),modifier=Modifier.weight(1f).testTag("images-share-link")) {
                OndaIcon("share",modifier=Modifier.size(18.dp));Spacer(Modifier.width(6.dp));UiText("Compartilhar link",style=MaterialTheme.typography.labelMedium)
            }
            Button(onClick=::download,enabled=!busy&&(source.isNotBlank()||link.isNotBlank()),shape=RoundedCornerShape(12.dp),contentPadding=PaddingValues(horizontal=8.dp,vertical=12.dp),modifier=Modifier.weight(1f).testTag("images-download")) {
                OndaIcon("download",modifier=Modifier.size(18.dp));Spacer(Modifier.width(6.dp));UiText(if(source.isNotBlank())"Exportar / baixar" else "Baixar imagens",style=MaterialTheme.typography.labelMedium)
            }
        }
        Spacer(Modifier.height(16.dp))
    }

}

@Composable fun ImageOptions(config: JSONObject, change: (JSONObject)->Unit, separated:Boolean=false,forceVisible:Boolean=false) {
    val preferences by OndaStore.settings.collectAsStateWithLifecycle()
    if(!forceVisible && !separated && preferences.optBoolean("simple_download_ui",false)) return
    fun put(key: String,value: Any) {change(JSONObject(config.toString()).put(key,value))}
    val sizes=linkedMapOf("Original" to (0 to 0),"Até 1920 × 1080" to (1920 to 1080),"Até 1280 × 720" to (1280 to 720),"Até 1080 × 1080" to (1080 to 1080),"Personalizado" to null)
    val selectedSize=config.optString("image_size").ifBlank {if(config.optInt("image_width")==0 && config.optInt("image_height")==0) "Original" else "Personalizado"}
    val formatControl:@Composable (Modifier)->Unit={modifier->Select("Formato",config.optString("image_format","Original"),listOf("Original","JPG","PNG","WebP","SVG"),modifier){put("image_format",it)}}
    val sizeControl:@Composable (Modifier)->Unit={modifier->Select("Tamanho máximo",selectedSize,sizes.keys.toList(),modifier){size->
        val next=JSONObject(config.toString()).put("image_size",size)
        sizes[size]?.let {next.put("image_width",it.first).put("image_height",it.second)}
        change(next)
    }}
    if(forceVisible && androidx.compose.ui.platform.LocalDensity.current.fontScale<=1.2f)Row(horizontalArrangement=Arrangement.spacedBy(12.dp)){formatControl(Modifier.weight(1f));sizeControl(Modifier.weight(1f))}
    else {formatControl(Modifier);if(separated)SettingsDivider();sizeControl(Modifier.fillMaxWidth())}
    if(selectedSize=="Personalizado") {
    UiText("Largura × altura (px)",style=MaterialTheme.typography.labelMedium)
    Row(horizontalArrangement=Arrangement.spacedBy(LayoutSpacing.controls)) {
        OutlinedTextField(config.optInt("image_width").takeIf {it>0}?.toString() ?: "",{put("image_width",it.toIntOrNull()?.coerceIn(0,16384) ?: 0)},label={UiText("Largura")},modifier=Modifier.weight(1f),singleLine=true)
        OutlinedTextField(config.optInt("image_height").takeIf {it>0}?.toString() ?: "",{put("image_height",it.toIntOrNull()?.coerceIn(0,16384) ?: 0)},label={UiText("Altura")},modifier=Modifier.weight(1f),singleLine=true)
    }
    }
    if(separated)SettingsDivider()
    ToolSwitch("Manter proporção",config.optBoolean("keep_ratio",true),"Sem ampliar ou distorcer"){put("keep_ratio",it)}
}
