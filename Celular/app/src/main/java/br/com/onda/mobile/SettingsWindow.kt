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
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.platform.LocalSoftwareKeyboardController
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import org.json.JSONArray
import org.json.JSONObject

val categories=linkedMapOf(
    "Geral" to listOf("clipboard_links","language","remember","notice_duration","notice_animation"),
    "Aparência" to listOf("simple_download_ui","queue_actions_at_top","queue_view","queue_card_size","history_card_size","pure_black_separators","history_view","theme","accent","tab_order","hidden_tabs","interface_font","interface_font_size","interface_spacing"),
    "Downloads" to listOf("auto_select_media","social_best_quality","detect_duplicates","filename_template","concurrent_downloads","resume_downloads","resume_queue","normalize_volume","schedule_enabled","schedule_start","schedule_stop","mode","audio_quality","height","fps","playlist_limit","link_playlist","organization","duplicate_policy","output_uri","auto_metadata","auto_match","confirm_version","review_metadata"),
    "Imagens" to listOf("image_format","image_size","image_width","image_height","keep_ratio"),
    "Áudio" to listOf("search_preview","effects_preview","keep_preview"),
    "Contas" to listOf("spotify_client_id","cookies_file","youtube_cookies_file"),
    "Ferramentas" to listOf("check_updates"))

@Composable fun SettingsDivider() {
    HorizontalDivider(color=MaterialTheme.colorScheme.outlineVariant.copy(alpha=.65f))
}

@Composable fun SettingsWindow(vm: OndaViewModel, initialCategory: String="Geral", close: ()->Unit) {
    val settings by OndaStore.settings.collectAsStateWithLifecycle()
    val busy by vm.busy.collectAsStateWithLifecycle()
    val status by vm.status.collectAsStateWithLifecycle()
    val names=remember {settingsCategoryOrder()}
    val pager=rememberPagerState(initialPage=names.indexOf(initialCategory).takeIf {it>=0} ?: 0,pageCount={names.size})
    val scope=rememberCoroutineScope()
    var reset by remember {mutableStateOf(false)}
    var searchQuery by rememberSaveable {mutableStateOf("")}
    var searchTarget by remember {mutableStateOf("")}
    val searchEntries=remember {settingsSearchEntries()}
    val language=LocalUiLanguage.current
    val keyboard=LocalSoftwareKeyboardController.current
    val searchResults=remember(searchQuery,language) {if(searchQuery.isBlank())emptyList() else searchEntries.filter {entry->
        settingsSearchMatches(searchQuery,listOf(entry.category,entry.label,entry.keywords).joinToString(" "){translateUi(it,language)})
    }.sortedWith(compareBy<SettingsSearchEntry> {!settingsSearchMatches(searchQuery,translateUi(it.label,language))}.thenBy {it.label.length})}
    fun put(key: String,value: Any) {OndaStore.saveSettings(JSONObject(settings.toString()).put(key,value))}
    val folder=rememberLauncherForActivityResult(ActivityResultContracts.OpenDocumentTree()) {uri->if(uri!=null) {
        OndaStore.context.contentResolver.takePersistableUriPermission(uri,Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_GRANT_WRITE_URI_PERMISSION)
        put("output_uri",uri.toString())
    }}
    val cookies=rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) {uri->if(uri!=null) vm.importLocal(uri,"cookies",dialog=true) {put("cookies_file",it.absolutePath)}}
    val youtubeCookies=rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) {uri->
        if(uri!=null)vm.importLocal(uri,"cookies",dialog=true) {file->
            if(isYouTubeCookieFile(file))OndaStore.saveSettings(JSONObject(OndaStore.settings.value.toString()).put("youtube_cookies_file",file.absolutePath).put("youtube_user_agent",""))
            else {file.delete();vm.showNotice("Importar cookies do YouTube","Arquivo de cookies do YouTube inválido. Exporte cookies.txt no formato Netscape a partir de uma sessão do YouTube.")}
        }
    }

    Dialog(onDismissRequest=close) {
        Surface(modifier=Modifier.clip(RoundedCornerShape(28.dp)),shape=RoundedCornerShape(28.dp)) {Column(Modifier.fillMaxWidth().fillMaxHeight(.94f).padding(LayoutSpacing.inset),verticalArrangement=Arrangement.spacedBy(LayoutSpacing.text)) {
            UiText("Do seu jeito.",style=MaterialTheme.typography.headlineSmall)
            UiText("Escolha uma categoria para ajustar o Onda.",style=MaterialTheme.typography.bodySmall)
            OutlinedTextField(searchQuery,{searchQuery=it;searchTarget=""},label={UiText("Pesquisar configurações")},singleLine=true,modifier=Modifier.fillMaxWidth().testTag("settings-search"))
            if(searchQuery.isNotBlank()) {
                if(searchResults.isEmpty())UiText("Nenhuma configuração encontrada.",style=MaterialTheme.typography.bodySmall)
                Column(Modifier.fillMaxWidth().heightIn(max=170.dp).verticalScroll(rememberScrollState())) {
                    searchResults.forEach {entry->
                        TextButton(onClick={
                            searchTarget=entry.label;searchQuery="";keyboard?.hide()
                            scope.launch {pager.scrollToPage(names.indexOf(entry.category).coerceAtLeast(0))}
                        },modifier=Modifier.fillMaxWidth()) {
                            Text(translateUi(entry.category,language)+" · "+translateUi(entry.label,language))
                        }
                    }
                }
            }
            if(busy) {LinearProgressIndicator(Modifier.fillMaxWidth());UiText(status,style=MaterialTheme.typography.bodySmall,maxLines=2);TextButton(onClick={vm.cancel()}){UiText("Cancelar")}}
            ScrollableTabRow(selectedTabIndex=pager.currentPage,edgePadding=0.dp) { names.forEachIndexed {index,name->Tab(selected=pager.currentPage==index,onClick={scope.launch {pager.scrollToPage(index)}},text={UiText(name,maxLines=1)})} }
            CompositionLocalProvider(LocalSettingsSearchTarget provides searchTarget) {
            HorizontalPager(state=pager,modifier=Modifier.weight(1f).testTag("settings-pages"),verticalAlignment=androidx.compose.ui.Alignment.Top) { page->
            Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(top=LayoutSpacing.controls),verticalArrangement=Arrangement.spacedBy(LayoutSpacing.controls)) {
                when(names[page]) {
                    "Geral"->{
                        Toggle("Reconhecer links copiados automaticamente",settings.optBoolean("clipboard_links",true)){put("clipboard_links",it)}
                        UiText("Preferências",style=MaterialTheme.typography.titleMedium)
                        Select("Idioma",settings.optString("language","pt-BR"),UI_LANGUAGES){put("language",it)}
                        SettingsDivider()
                        Toggle("Lembrar configurações",settings.optBoolean("remember",true)){put("remember",it)}
                        UiText("Ative para recuperar suas opções ao abrir o aplicativo novamente.",style=MaterialTheme.typography.bodySmall)
                        SettingsDivider()
                        Toggle("Animar avisos",settings.optBoolean("notice_animation",true)){put("notice_animation",it)}
                        Select("Duração dos avisos",settings.optString("notice_duration","Após 3 segundos"),noticeDurations.keys.toList()){put("notice_duration",it)}
                        UiText("Avisos de operações em andamento permanecem até terminar. O botão × permite fechar manualmente.",style=MaterialTheme.typography.bodySmall)
                        PreferenceTransfer(vm)
                        SettingsDivider()
                        UiText("Restaurar configurações",style=MaterialTheme.typography.titleMedium)
                        TextButton(onClick={reset=true}){UiText("Restaurar TODAS as configurações ao padrão")}
                        SettingsDivider()
                        TextButton(onClick={reset=true}){UiText("Escolher quais configurações restaurar…")}
                    }
                    "Aparência"->{
                        Toggle("Simplificar controles de download",settings.optBoolean("simple_download_ui",false)){put("simple_download_ui",it)}
                        UiText("Oculta formato e qualidade nas abas de download e usa a maior qualidade disponível. Não altera o espaçamento nem as abas visíveis.",style=MaterialTheme.typography.bodySmall)
                        SettingsDivider()
                        UiText("Tema e cores",style=MaterialTheme.typography.titleMedium)
                        SettingsDivider()
                        Select("Modo de aparência",settings.optString("theme"),listOf("Seguir o sistema","Escuro","Preto puro","Claro","Alto contraste")){put("theme",it)}
                        Toggle("Mostrar bordas e separações no Preto puro",settings.optBoolean("pure_black_separators",false)){put("pure_black_separators",it)}
                        SettingsDivider()
                        Select("Cor de destaque",settings.optString("accent"),accents.keys.toList()){put("accent",it)}
                        SettingsDivider()
                        Select("Espaçamento da interface",settings.optString("interface_spacing","Padrão"),spacingModes){put("interface_spacing",it)}
                        SettingsDivider()
                        Select("Alterar tamanho da fonte",settings.optString("interface_font_size","100%"),interfaceFontSizes){put("interface_font_size",it)}
                        SettingsDivider()
                        Select("Fonte da interface",settings.optString("interface_font",DEFAULT_INTERFACE_FONT),interfaceFonts.keys.toList()){put("interface_font",it)}
                        UiText(FONT_PREVIEW,style=MaterialTheme.typography.bodyLarge,modifier=Modifier.testTag("font-preview"))
                        UiText("A fonte muda na hora. Ative Lembrar configurações para manter sua escolha ao reabrir.",style=MaterialTheme.typography.bodySmall)
                        SettingsDivider()
                        Toggle("Mostrar ações antes das listas",settings.optBoolean("queue_actions_at_top",true)){put("queue_actions_at_top",it)}
                        Select("Mostrar itens na fila",settings.optString("queue_view","Completa"),listOf("Compacto","Completa")){put("queue_view",it)}
                        Select("Tamanho dos cards da fila",settings.optString("queue_card_size","Grande"),listOf("Pequeno","Médio","Grande")){put("queue_card_size",it)}
                        Select("Mostrar músicas no histórico",settings.optString("history_view","Compacto"),listOf("Compacto","Completa")){put("history_view",it)}
                        UiText("Compacto: exibição atual. Completa: cards com capa e informações disponíveis da música e do álbum.",style=MaterialTheme.typography.bodySmall)
                        Select("Tamanho dos cards do histórico",settings.optString("history_card_size","Grande"),listOf("Pequeno","Médio","Grande")){put("history_card_size",it)}
                        SettingsDivider()
                        UiText("Ordem das abas",style=MaterialTheme.typography.titleMedium)
                        val order=settings.getJSONArray("tab_order").let {a->(0 until a.length()).map {a.getString(it)}}
                        order.forEachIndexed {index,name->Row {
                            UiText(tabLabel(name),Modifier.weight(1f).padding(vertical=12.dp))
                            TextButton(enabled=index>0,onClick={val copy=order.toMutableList();java.util.Collections.swap(copy,index,index-1);put("tab_order",JSONArray(copy))}){AccessibleSymbol("↑","Mover ${translateUi(tabLabel(name),LocalUiLanguage.current)} para cima")}
                            TextButton(enabled=index<order.lastIndex,onClick={val copy=order.toMutableList();java.util.Collections.swap(copy,index,index+1);put("tab_order",JSONArray(copy))}){AccessibleSymbol("↓","Mover ${translateUi(tabLabel(name),LocalUiLanguage.current)} para baixo")}
                        }}
                        TextButton(onClick={put("tab_order",OndaStore.defaults().getJSONArray("tab_order"))}){UiText("Restaurar ordem das abas")}
                        UiText("Mostrar ou ocultar abas",style=MaterialTheme.typography.titleMedium)
                        UiText("Pesquisar músicas, Links e Fila ficam sempre disponíveis.",style=MaterialTheme.typography.bodySmall)
                        val hidden=hiddenTabs(settings)
                        order.forEach {name->
                            if(name in requiredTabs) UiText(tabLabel(name),Modifier.padding(vertical=8.dp))
                            else Toggle(tabLabel(name),name !in hidden) {shown->
                                put("hidden_tabs",JSONArray(if(shown) hidden.filter {it!=name} else hidden+name))
                            }
                        }

                    }
                    "Downloads"->{
                        Toggle("Selecionar todas as mídias ao abrir a publicação",settings.optBoolean("auto_select_media",true)){put("auto_select_media",it)}
                        UiText("Instagram, TikTok e Kwai: você pode desmarcar fotos e vídeos individualmente antes de confirmar.",style=MaterialTheme.typography.bodySmall)
                        SettingsDivider()
                        Toggle("Baixar mídias sociais automaticamente na maior qualidade",settings.optBoolean("social_best_quality",true)){put("social_best_quality",it)}
                        UiText("Instagram, TikTok e Kwai: escolhe automaticamente a maior qualidade. Você ainda pode escolher quais itens baixar.",style=MaterialTheme.typography.bodySmall)
                        SettingsDivider()
                        UiText("Downloads e arquivos",style=MaterialTheme.typography.titleMedium)
                        UiText("As opções são aplicadas aos próximos links adicionados.",style=MaterialTheme.typography.bodySmall)
                        FormatOptions(settings,OndaStore::saveSettings,separated=true)
                        SettingsDivider()
                        UiText("Pasta de destino",style=MaterialTheme.typography.labelMedium)
                        Button(onClick={folder.launch(null)}){UiText("Alterar")}
                        UiText(settings.optString("output_uri").ifBlank {"Downloads/ONDA no Android 10+. No Android 8/9, escolha uma pasta para preservar os arquivos ao desinstalar."},style=MaterialTheme.typography.bodySmall)
                        TextButton(onClick={put("output_uri","")}){UiText("Usar pasta padrão")}
                        SettingsDivider()
                        OrganizationOptions(settings,::put)
                        val duplicates=linkedMapOf("Perguntar" to "ask","Manter ambos" to "keep","Substituir" to "replace","Pular" to "skip")
                        SettingsDivider()
                        Select("Quando o arquivo já existir",duplicates.entries.firstOrNull {it.value==settings.optString("duplicate_policy")}?.key ?: "Perguntar",duplicates.keys.toList()){put("duplicate_policy",duplicates.getValue(it))}
                        SettingsDivider()
                        Toggle("Baixar playlist de vídeo",settings.optBoolean("link_playlist")){put("link_playlist",it)}
                        OutlinedTextField(settings.optInt("playlist_limit").toString(),{put("playlist_limit",(it.toIntOrNull() ?: 2000).coerceIn(1,5000))},label={UiText("Máximo de itens por playlist")},modifier=Modifier.fillMaxWidth(),singleLine=true)
                        SettingsDivider()
                        Toggle("Escolher automaticamente os metadados mais semelhantes",settings.optBoolean("auto_metadata")){put("auto_metadata",it)}
                        UiText("Seleciona o primeiro resultado de maior similaridade entre os metadados compatíveis, sem abrir a escolha. Sem correspondência compatível, informa o erro. Não altera a escolha da versão de áudio.",style=MaterialTheme.typography.bodySmall)
                        SettingsDivider()
                        Toggle("Escolher automaticamente a versão mais semelhante no YouTube",settings.optBoolean("auto_match")){put("auto_match",it)}
                        SettingsDivider()
                        UiText("Vale para os próximos downloads iniciados, inclusive itens já na fila e álbuns. Escolhe a maior similaridade entre as versões compatíveis.",style=MaterialTheme.typography.bodySmall)
                        if(settings.optBoolean("auto_match")) {
                            UiText("A confirmação de versão fica desativada enquanto a escolha automática está ligada.",style=MaterialTheme.typography.bodySmall)
                        }
                        Toggle("Confirmar a versão do YouTube de cada música antes de baixar",settings.optBoolean("confirm_version")){put("confirm_version",it)}
                        SettingsDivider()
                        Toggle("Revisar metadados antes de baixar",settings.optBoolean("review_metadata")){put("review_metadata",it)}
                        UiText("Spotify, Deezer e Apple Music fornecem metadados; o áudio correspondente é obtido do YouTube.",style=MaterialTheme.typography.bodySmall)
                        AdvancedDownloadOptions(settings,::put)
                    }
                    "Imagens"->ImageOptions(settings,OndaStore::saveSettings,separated=true)
                    "Áudio"->{
                        UiText("Reprodução e prévias",style=MaterialTheme.typography.titleMedium)
                        UiText("Duração das prévias",style=MaterialTheme.typography.titleSmall)
                        for((key,label) in listOf("search_preview" to "Músicas nas pesquisas","effects_preview" to "Slowed / Sped Up e Reverb")) {
                            SettingsDivider()
                            val current=settings.optInt(key,25)
                            val durations=listOf(10,15,25,30,45,60,90,120,180).let {if(current in it)it else it+current}
                            Select(label,"$current segundos",durations.map {"$it segundos"}){put(key,it.substringBefore(' ').toInt())}
                        }
                        UiText("Vale para a próxima prévia. Nas pesquisas, o catálogo pode fornecer um trecho menor.",style=MaterialTheme.typography.bodySmall)
                        SettingsDivider()
                        Toggle("Continuar prévia dos efeitos em outras abas",settings.optBoolean("keep_preview")){put("keep_preview",it)}
                    }
                    "Contas"->{
                        UiText("Contas e acesso",style=MaterialTheme.typography.titleMedium)
                        UiText("Spotify · opcional",style=MaterialTheme.typography.titleSmall)
                        var secret by remember {mutableStateOf("")}
                        var secretReady by remember {mutableStateOf(false)}
                        LaunchedEffect(Unit) {
                            secret=withContext(Dispatchers.IO) {SecureVault.get("spotify-api") ?: ""}
                            secretReady=true
                        }
                        SettingsDivider()
                        OutlinedTextField(settings.optString("spotify_client_id"),{put("spotify_client_id",it)},label={UiText("Client ID")},modifier=Modifier.fillMaxWidth(),singleLine=true)
                        SettingsDivider()
                        OutlinedTextField(secret,{secret=it;SecureVault.put("spotify-api",it)},label={UiText("Client Secret · opcional")},enabled=secretReady,visualTransformation=androidx.compose.ui.text.input.PasswordVisualTransformation(),modifier=Modifier.fillMaxWidth(),singleLine=true)
                        Button(onClick={vm.connectSpotify()}){UiText("Conectar")}
                        TextButton(onClick={runCatching {OndaStore.context.startActivity(Intent(Intent.ACTION_VIEW,android.net.Uri.parse("https://developer.spotify.com/dashboard")).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))}.onFailure {vm.showNotice("Abrir Spotify Developers","Nenhum navegador disponível para abrir o Spotify Developers.")}}){UiText("Abrir Spotify Developers")}
                        TextButton(onClick={vm.operation("spotify_disconnect",JSONObject(),dialog=true)}){UiText("Desconectar")}
                        UiText("No Spotify Developers, cadastre o retorno http://127.0.0.1:8765/callback. A conexão usa PKCE e abre o navegador do celular. A disponibilidade das playlists depende das permissões da API.",style=MaterialTheme.typography.bodySmall)
                        SettingsDivider()
                        OutlinedButton(onClick={youtubeCookies.launch(arrayOf("text/plain","application/octet-stream"))}){UiText("Importar cookies do YouTube")}
                        OutlinedButton(onClick={cookies.launch(arrayOf("text/plain","application/octet-stream"))}){UiText("Importar cookies.txt")}
                        UiText(if(settings.optString("cookies_file").isBlank()) "Nenhum cookie importado" else "Cookies salvos no armazenamento privado do ONDA",style=MaterialTheme.typography.bodySmall)
                        TextButton(onClick={val path=settings.optString("cookies_file");if(path.isNotBlank()) java.io.File(path).delete();put("cookies_file","")}){UiText("Remover cookies")}
                        if(settings.optString("youtube_cookies_file").isNotBlank()) SettingsDivider()
                        if(settings.optString("youtube_cookies_file").isNotBlank()) TextButton(onClick={java.io.File(settings.getString("youtube_cookies_file")).delete();put("youtube_cookies_file","");put("youtube_user_agent","");android.webkit.CookieManager.getInstance().removeAllCookies(null)}) {UiText("Remover sessão do YouTube")}
                    }
                    "Ferramentas"->{
                        CacheControls(vm)
                        SettingsDivider()
                        AppUpdateControls(vm)
                        SettingsDivider()
                        UiText("Ferramentas e atualizações",style=MaterialTheme.typography.titleMedium)
                        UiText("Python, FFmpeg, FFprobe e QuickJS já estão incluídos no aplicativo. Não é necessário instalar Termux.")
                        Button(onClick={vm.operation("update",JSONObject(),dialog=true)}){UiText("Atualizar ferramentas")}
                        SettingsDivider()
                        OutlinedButton(onClick={vm.operation("self_test",JSONObject(),dialog=true){vm.showNotice("Verificar ferramentas","Ferramentas verificadas: ${it.optString("yt_dlp")}")}}){UiText("Verificar ferramentas")}
                        UiText("ONDA Android ${BuildConfig.VERSION_NAME}" + if(BuildConfig.DEBUG) " · versão de desenvolvimento" else "",style=MaterialTheme.typography.bodySmall)
                    }
                }

            }
            }
            }
            TextButton(onClick=close,modifier=Modifier.fillMaxWidth()){UiText("Pronto")}
        }}
    }
    if(reset) ResetWindow {reset=false}
}

@Composable fun ResetWindow(close: ()->Unit) {
    var selected by remember {mutableStateOf(categories.keys.toSet())}
    AlertDialog(containerColor=ondaDialogContainerColor(),onDismissRequest=close,title={UiText("Restaurar configurações")},text={Column(Modifier.verticalScroll(rememberScrollState())) {
        UiText("Escolha quais categorias voltar ao padrão. A fila, o histórico e seus arquivos são preservados.")
        Toggle("TODAS as configurações",selected.size==categories.size){selected=if(it) categories.keys.toSet() else emptySet()}
        categories.keys.forEach {name->Toggle(name,name in selected){selected=if(it) selected+name else selected-name}}
    }},confirmButton={TextButton(onClick={
        val defaults=OndaStore.defaults();val config=if(selected.size==categories.size) JSONObject(defaults.toString()) else JSONObject(OndaStore.settings.value.toString())
        selected.forEach {name->categories.getValue(name).forEach {config.put(it,defaults.get(it))}}
        if("Contas" in selected) SecureVault.clear()
        OndaStore.saveSettings(config)
        if("Downloads" in selected) OndaStore.resetCollectionOptions()
        close()
    }){UiText("Restaurar")}},dismissButton={TextButton(onClick=close){UiText("Cancelar")}})
}
