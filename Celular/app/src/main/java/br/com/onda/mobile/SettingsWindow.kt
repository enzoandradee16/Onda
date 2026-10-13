package br.com.onda.mobile

import android.content.Intent
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.*
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.pager.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.testTag
import kotlinx.coroutines.launch
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import org.json.JSONArray
import org.json.JSONObject

val categories=linkedMapOf(
    "Geral" to listOf("remember","check_updates","notice_duration"),
    "Aparência" to listOf("theme","accent","tab_order","interface_font","interface_font_size"),
    "Downloads" to listOf("concurrent_downloads","resume_downloads","resume_queue","normalize_volume","schedule_enabled","schedule_start","schedule_stop","mode","audio_quality","height","fps","playlist_limit","organization","duplicate_policy","output_uri","auto_match","confirm_version","review_metadata"),
    "Imagens" to listOf("image_format","image_width","image_height","keep_ratio"),
    "Áudio" to listOf("search_preview","effects_preview","keep_preview"),
    "Contas" to listOf("spotify_client_id","cookies_file","youtube_cookies_file"))

@Composable fun SettingsDivider() {
    HorizontalDivider(color=MaterialTheme.colorScheme.outlineVariant.copy(alpha=.65f))
}

@Composable fun SettingsWindow(vm: OndaViewModel, initialCategory: String="Aparência", close: ()->Unit) {
    val settings by OndaStore.settings.collectAsStateWithLifecycle()
    val busy by vm.busy.collectAsStateWithLifecycle()
    val status by vm.status.collectAsStateWithLifecycle()
    val names=remember {categories.keys.toList()+"Ferramentas"}
    val pager=rememberPagerState(initialPage=names.indexOf(initialCategory).takeIf {it>=0} ?: 1,pageCount={names.size})
    val scope=rememberCoroutineScope()
    var reset by remember {mutableStateOf(false)}
    fun put(key: String,value: Any) {OndaStore.saveSettings(JSONObject(settings.toString()).put(key,value))}
    val folder=rememberLauncherForActivityResult(ActivityResultContracts.OpenDocumentTree()) {uri->if(uri!=null) {
        OndaStore.context.contentResolver.takePersistableUriPermission(uri,Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_GRANT_WRITE_URI_PERMISSION)
        put("output_uri",uri.toString())
    }}
    val cookies=rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) {uri->if(uri!=null) vm.importLocal(uri,"cookies",dialog=true) {put("cookies_file",it.absolutePath)}}
    Dialog(onDismissRequest=close) {
        Surface(modifier=Modifier.clip(RoundedCornerShape(28.dp)),shape=RoundedCornerShape(28.dp)) {Column(Modifier.fillMaxWidth().fillMaxHeight(.94f).padding(16.dp)) {
            Text("Do seu jeito.",style=MaterialTheme.typography.headlineSmall)
            Text("Escolha uma categoria para ajustar o Onda.",style=MaterialTheme.typography.bodySmall)
            if(busy) {LinearProgressIndicator(Modifier.fillMaxWidth());Text(status,style=MaterialTheme.typography.bodySmall,maxLines=2);TextButton(onClick={vm.cancel()}){Text("Cancelar")}}
            ScrollableTabRow(selectedTabIndex=pager.currentPage,edgePadding=0.dp) { names.forEachIndexed {index,name->Tab(selected=pager.currentPage==index,onClick={scope.launch {pager.scrollToPage(index)}},text={Text(name,maxLines=1)})} }
            HorizontalPager(state=pager,modifier=Modifier.weight(1f).testTag("settings-pages"),verticalAlignment=androidx.compose.ui.Alignment.Top) { page->
            Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(top=10.dp),verticalArrangement=Arrangement.spacedBy(10.dp)) {
                when(names[page]) {
                    "Geral"->{
                        Text("Preferências",style=MaterialTheme.typography.titleMedium)
                        SettingsDivider()
                        Toggle("Lembrar configurações",settings.optBoolean("remember",true)){put("remember",it)}
                        Text("Ative para recuperar suas opções ao abrir o aplicativo novamente.",style=MaterialTheme.typography.bodySmall)
                        SettingsDivider()
                        Select("Duração dos avisos",settings.optString("notice_duration","Fechar manualmente"),noticeDurations.keys.toList()){put("notice_duration",it)}
                        Text("Avisos de operações em andamento permanecem até terminar. O botão × permite fechar manualmente.",style=MaterialTheme.typography.bodySmall)
                        PreferenceTransfer(vm)
                        SettingsDivider()
                        Text("Restaurar configurações",style=MaterialTheme.typography.titleMedium)
                        TextButton(onClick={reset=true}){Text("Restaurar TODAS as configurações ao padrão")}
                        SettingsDivider()
                        TextButton(onClick={reset=true}){Text("Escolher quais configurações restaurar…")}
                    }
                    "Aparência"->{
                        Text("Tema e cores",style=MaterialTheme.typography.titleMedium)
                        SettingsDivider()
                        Select("Modo de aparência",settings.optString("theme"),listOf("Seguir o sistema","Escuro","Preto puro","Claro")){put("theme",it)}
                        SettingsDivider()
                        Select("Cor de destaque",settings.optString("accent"),accents.keys.toList()){put("accent",it)}
                        SettingsDivider()
                        Select("Alterar tamanho da fonte",settings.optString("interface_font_size","100%"),interfaceFontSizes){put("interface_font_size",it)}
                        SettingsDivider()
                        Select("Fonte da interface",settings.optString("interface_font",DEFAULT_INTERFACE_FONT),interfaceFonts.keys.toList()){put("interface_font",it)}
                        Text(FONT_PREVIEW,style=MaterialTheme.typography.bodyLarge,modifier=Modifier.testTag("font-preview"))
                        Text("A fonte muda na hora. Ative Lembrar configurações para manter sua escolha ao reabrir.",style=MaterialTheme.typography.bodySmall)
                        SettingsDivider()
                        Text("Ordem das abas",style=MaterialTheme.typography.titleMedium)
                        val order=settings.getJSONArray("tab_order").let {a->(0 until a.length()).map {a.getString(it)}}
                        order.forEachIndexed {index,name->Row {
                            Text(tabLabel(name),Modifier.weight(1f).padding(vertical=12.dp))
                            TextButton(enabled=index>0,onClick={val copy=order.toMutableList();java.util.Collections.swap(copy,index,index-1);put("tab_order",JSONArray(copy))}){Text("↑")}
                            TextButton(enabled=index<order.lastIndex,onClick={val copy=order.toMutableList();java.util.Collections.swap(copy,index,index+1);put("tab_order",JSONArray(copy))}){Text("↓")}
                        }}
                    }
                    "Downloads"->{
                        Text("Downloads e arquivos",style=MaterialTheme.typography.titleMedium)
                        Text("As opções são aplicadas aos próximos links adicionados.",style=MaterialTheme.typography.bodySmall)
                        AdvancedDownloadOptions(settings,::put)
                        SettingsDivider()
                        FormatOptions(settings,OndaStore::saveSettings,separated=true)
                        SettingsDivider()
                        Text("Pasta de destino",style=MaterialTheme.typography.labelMedium)
                        Button(onClick={folder.launch(null)}){Text("Alterar")}
                        Text(settings.optString("output_uri").ifBlank {"Downloads/ONDA no Android 10+. No Android 8/9, escolha uma pasta para preservar os arquivos ao desinstalar."},style=MaterialTheme.typography.bodySmall)
                        TextButton(onClick={put("output_uri","")}){Text("Usar pasta padrão")}
                        SettingsDivider()
                        OutlinedTextField(settings.optInt("playlist_limit").toString(),{put("playlist_limit",(it.toIntOrNull() ?: 2000).coerceIn(1,5000))},label={Text("Máximo de itens por playlist")},modifier=Modifier.fillMaxWidth(),singleLine=true)
                        val structures=linkedMapOf("Pasta de destino" to "Pasta de destino","Artista" to "Artista","Artista / Álbum" to "Artista / Álbum")
                        SettingsDivider()
                        Select("Organizar músicas em",structures.entries.firstOrNull {it.value==settings.optString("organization")}?.key ?: "Pasta de destino",structures.keys.toList()){put("organization",structures.getValue(it))}
                        val duplicates=linkedMapOf("Perguntar" to "ask","Manter ambos" to "keep","Substituir" to "replace","Pular" to "skip")
                        SettingsDivider()
                        Select("Quando o arquivo já existir",duplicates.entries.firstOrNull {it.value==settings.optString("duplicate_policy")}?.key ?: "Perguntar",duplicates.keys.toList()){put("duplicate_policy",duplicates.getValue(it))}
                        SettingsDivider()
                        Toggle("Escolher automaticamente a versão mais semelhante no YouTube",settings.optBoolean("auto_match")){put("auto_match",it)}
                        SettingsDivider()
                        Toggle("Confirmar a versão do YouTube de cada música antes de baixar",settings.optBoolean("confirm_version")){put("confirm_version",it)}
                        SettingsDivider()
                        Toggle("Revisar metadados antes de baixar",settings.optBoolean("review_metadata")){put("review_metadata",it)}
                        Text("Spotify, Deezer e Apple Music fornecem metadados; o áudio correspondente é obtido do YouTube.",style=MaterialTheme.typography.bodySmall)
                    }
                    "Imagens"->ImageOptions(settings,OndaStore::saveSettings,separated=true)
                    "Áudio"->{
                        Text("Reprodução e prévias",style=MaterialTheme.typography.titleMedium)
                        Text("Duração das prévias",style=MaterialTheme.typography.titleSmall)
                        for((key,label) in listOf("search_preview" to "Músicas nas pesquisas","effects_preview" to "Slowed / Sped Up e Reverb")) {
                            var duration by remember(key,settings.optInt(key,25)) {mutableFloatStateOf(settings.optInt(key,25).toFloat())}
                            SettingsDivider()
                            Text("$label · ${duration.toInt()} segundos")
                            Slider(duration,{duration=it},valueRange=10f..180f,onValueChangeFinished={put(key,duration.toInt())})
                        }
                        Text("Vale para a próxima prévia. Nas pesquisas, o catálogo pode fornecer um trecho menor.",style=MaterialTheme.typography.bodySmall)
                        SettingsDivider()
                        Toggle("Continuar prévia dos efeitos em outras abas",settings.optBoolean("keep_preview")){put("keep_preview",it)}
                    }
                    "Contas"->{
                        Text("Contas e acesso",style=MaterialTheme.typography.titleMedium)
                        Text("Spotify · opcional",style=MaterialTheme.typography.titleSmall)
                        var secret by remember {mutableStateOf("")}
                        var secretReady by remember {mutableStateOf(false)}
                        LaunchedEffect(Unit) {
                            secret=withContext(Dispatchers.IO) {SecureVault.get("spotify-api") ?: ""}
                            secretReady=true
                        }
                        SettingsDivider()
                        OutlinedTextField(settings.optString("spotify_client_id"),{put("spotify_client_id",it)},label={Text("Client ID")},modifier=Modifier.fillMaxWidth(),singleLine=true)
                        SettingsDivider()
                        OutlinedTextField(secret,{secret=it;SecureVault.put("spotify-api",it)},label={Text("Client Secret · opcional")},enabled=secretReady,visualTransformation=androidx.compose.ui.text.input.PasswordVisualTransformation(),modifier=Modifier.fillMaxWidth(),singleLine=true)
                        Button(onClick={vm.connectSpotify()}){Text("Conectar")}
                        TextButton(onClick={runCatching {OndaStore.context.startActivity(Intent(Intent.ACTION_VIEW,android.net.Uri.parse("https://developer.spotify.com/dashboard")).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))}.onFailure {vm.showNotice("Abrir Spotify Developers","Nenhum navegador disponível para abrir o Spotify Developers.")}}){Text("Abrir Spotify Developers")}
                        TextButton(onClick={vm.operation("spotify_disconnect",JSONObject(),dialog=true)}){Text("Desconectar")}
                        Text("No Spotify Developers, cadastre o retorno http://127.0.0.1:8765/callback. A conexão usa PKCE e abre o navegador do celular. A disponibilidade das playlists depende das permissões da API.",style=MaterialTheme.typography.bodySmall)
                        SettingsDivider()
                        OutlinedButton(onClick={cookies.launch(arrayOf("text/plain","application/octet-stream"))}){Text("Importar cookies.txt")}
                        Text(if(settings.optString("cookies_file").isBlank()) "Nenhum cookie importado" else "Cookies salvos no armazenamento privado do ONDA",style=MaterialTheme.typography.bodySmall)
                        TextButton(onClick={val path=settings.optString("cookies_file");if(path.isNotBlank()) java.io.File(path).delete();put("cookies_file","")}){Text("Remover cookies")}
                        if(settings.optString("youtube_cookies_file").isNotBlank()) SettingsDivider()
                        if(settings.optString("youtube_cookies_file").isNotBlank()) TextButton(onClick={java.io.File(settings.getString("youtube_cookies_file")).delete();put("youtube_cookies_file","");android.webkit.CookieManager.getInstance().removeAllCookies(null)}) {Text("Remover sessão do YouTube")}
                    }
                    "Ferramentas"->{
                        AppUpdateControls(vm)
                        SettingsDivider()
                        Text("Ferramentas e atualizações",style=MaterialTheme.typography.titleMedium)
                        Text("Python, FFmpeg, FFprobe e QuickJS acompanham esta versão Android de desenvolvimento. Não é necessário instalar Termux.")
                        Button(onClick={vm.operation("update",JSONObject(),dialog=true)}){Text("Atualizar ferramentas")}
                        SettingsDivider()
                        OutlinedButton(onClick={vm.operation("self_test",JSONObject(),dialog=true){vm.showNotice("Verificar ferramentas","Ferramentas verificadas: ${it.optString("yt_dlp")}")}}){Text("Verificar ferramentas")}
                        Text("ONDA Android ${BuildConfig.VERSION_NAME}" + if(BuildConfig.DEBUG) " · versão de desenvolvimento" else "",style=MaterialTheme.typography.bodySmall)
                    }
                }

            }
            }
            TextButton(onClick=close,modifier=Modifier.fillMaxWidth()){Text("Pronto")}
        }}
    }
    if(reset) ResetWindow {reset=false}
}

@Composable fun ResetWindow(close: ()->Unit) {
    var selected by remember {mutableStateOf(categories.keys.toSet())}
    AlertDialog(onDismissRequest=close,title={Text("Restaurar configurações")},text={Column(Modifier.verticalScroll(rememberScrollState())) {
        Text("Escolha quais categorias voltar ao padrão. A fila, o histórico e seus arquivos são preservados.")
        Toggle("TODAS as configurações",selected.size==categories.size){selected=if(it) categories.keys.toSet() else emptySet()}
        categories.keys.forEach {name->Toggle(name,name in selected){selected=if(it) selected+name else selected-name}}
    }},confirmButton={TextButton(onClick={
        val defaults=OndaStore.defaults();val config=if(selected.size==categories.size) JSONObject(defaults.toString()) else JSONObject(OndaStore.settings.value.toString())
        selected.forEach {name->categories.getValue(name).forEach {config.put(it,defaults.get(it))}}
        if("Contas" in selected) SecureVault.clear()
        OndaStore.saveSettings(config)
        if("Downloads" in selected) OndaStore.resetCollectionOptions()
        close()
    }){Text("Restaurar")}},dismissButton={TextButton(onClick=close){Text("Cancelar")}})
}
