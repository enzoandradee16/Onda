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
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import coil.compose.AsyncImage
import org.json.JSONObject
import java.io.File
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.first

@Composable fun ImagesPage(vm: OndaViewModel) {
    val settings by OndaStore.settings.collectAsStateWithLifecycle()
    var link by rememberSaveable {mutableStateOf("")}
    var source by rememberSaveable {mutableStateOf("")}
    var preview by remember {mutableStateOf("")}
    var dimensions by remember {mutableStateOf("")}
    var previewRatio by remember {mutableFloatStateOf(16f/9f)}
    val local=rememberImageSourcePicker(arrayOf("image/*")) {uri->source="";vm.importLocal(uri,"image") {source=it.absolutePath;link="";preview=""}}
    fun imageConfig()=OndaStore.config(JSONObject(settings.toString()).put("mode","photos")).put("url",link).apply {
        if(source.isNotBlank()) put("source",source).put("name",File(source).name.replaceFirst(Regex("^image-[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}-"),""))
    }
    fun previewOptions(config:JSONObject)=listOf("image_format","image_size","image_width","image_height","keep_ratio").joinToString("|"){config.optString(it)}
    val optionsKey=previewOptions(settings)
    fun loadPreview() {
        val inputSource=source;val inputLink=link;val inputOptions=previewOptions(settings)
        vm.operation("image_preview",imageConfig()){result->
            val path=result.getString("path")
            if(source==inputSource && link==inputLink && previewOptions(OndaStore.settings.value)==inputOptions){
                if(preview.isNotBlank() && preview!=path)File(preview).delete()
                preview=path;previewRatio=(result.optInt("width",16).toFloat()/result.optInt("height",9).coerceAtLeast(1)).coerceIn(.6f,2.5f)
                dimensions="${result.optInt("width")} × ${result.optInt("height")} · ${result.optString("format")}"
            } else File(path).delete()
        }
    }
    LaunchedEffect(source,optionsKey) {if(source.isNotBlank()){delay(250);vm.busy.first {!it};loadPreview()}}
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).imePadding().padding(horizontal=20.dp),verticalArrangement=Arrangement.spacedBy(16.dp)) {
        ToolHeading("Imagens")
        ToolLink(link,{link=it;source="";preview="";dimensions=""},"Cole um link de imagem")
        OutlinedButton(onClick={local()},modifier=Modifier.fillMaxWidth(),shape=RoundedCornerShape(16.dp)) {OndaIcon("image",modifier=Modifier.size(20.dp));Spacer(Modifier.width(8.dp));UiText("Escolher arquivo")}
        if(preview.isNotBlank()) {
            ToolCard {
                AsyncImage(File(preview),translateUi("Prévia da imagem",LocalUiLanguage.current),Modifier.fillMaxWidth().heightIn(max=240.dp).aspectRatio(previewRatio).clip(RoundedCornerShape(12.dp)),contentScale=androidx.compose.ui.layout.ContentScale.Fit)
                UiText(dimensions,style=MaterialTheme.typography.bodySmall,color=MaterialTheme.colorScheme.onSurfaceVariant)
            }
        } else ToolEmpty("image","Sua imagem aparece aqui","Escolha um arquivo ou cole um link para visualizar e exportar.")
        if(source.isNotBlank())Text(File(source).name.replaceFirst(Regex("^image-[0-9a-f-]{36}-"),""),style=MaterialTheme.typography.bodySmall,maxLines=2)
        if(link.isNotBlank())OutlinedButton(onClick={loadPreview()},modifier=Modifier.fillMaxWidth()){UiText("Visualizar")}
        ToolCard {ImageOptions(settings,OndaStore::saveSettings,forceVisible=true)}
        Button(onClick={if(source.isNotBlank()) vm.operation("image_convert",imageConfig()) else {val id=OndaStore.enqueue(link,options=JSONObject(settings.toString()).put("mode","photos"),extra=JSONObject().put("_immediate",true));DownloadService.start(OndaStore.context,id);link="";preview=""}},modifier=Modifier.fillMaxWidth().heightIn(min=52.dp),enabled=link.isNotBlank() || source.isNotBlank()) {UiText("Exportar / baixar")}
        if(link.isNotBlank())OutlinedButton(onClick={OndaStore.enqueue(link,options=JSONObject(settings.toString()).put("mode","photos"));link="";preview=""},modifier=Modifier.fillMaxWidth()){UiText("Adicionar à fila")}
        UiText("SVG incorpora a imagem original; não vetoriza. Animações usam o primeiro quadro.",style=MaterialTheme.typography.bodySmall,color=MaterialTheme.colorScheme.onSurfaceVariant)
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
    else {formatControl(Modifier);if(separated)SettingsDivider();sizeControl(Modifier)}
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
