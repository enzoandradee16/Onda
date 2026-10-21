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
    "Geral" to listOf("remember","language","clipboard_links","notice_duration","notice_animation"),
    "Aparência" to listOf("simple_download_ui","queue_actions_at_top","queue_view","queue_card_size","catalog_card_size","history_card_size","pure_black_separators","history_view","theme","accent","playback_tab_order","bottom_bar_order","tab_order","hidden_tabs","interface_font","interface_font_size","interface_spacing"),
    "Downloads" to listOf("wifi_only","wifi_loss","finish_action","notification_controls","auto_select_media","social_best_quality","detect_duplicates","filename_template","concurrent_downloads","resume_downloads","resume_queue","normalize_volume","schedule_enabled","schedule_start","schedule_stop","mode","audio_quality","height","fps","playlist_limit","link_playlist","organization","duplicate_policy","output_uri","auto_metadata","auto_match","review_metadata"),
    "Imagens" to listOf("image_format","image_size","image_width","image_height","keep_ratio"),
    "Áudio" to listOf("search_preview","effects_preview","keep_preview","jukebox_background","synced_lyrics","jukebox_equalizer","jukebox_gradual_transition","jukebox_transition_seconds"),
    "Contas" to listOf("spotify_client_id","cookies_file","youtube_cookies_file"),
    "Ferramentas" to listOf("check_updates"))

@Composable fun SettingsDivider() {
    HorizontalDivider(color=MaterialTheme.colorScheme.outlineVariant.copy(alpha=.65f))
}

@Composable fun SettingsWindow(vm: OndaViewModel, initialCategory: String="Geral", close: ()->Unit) {
    val settings by OndaStore.settings.collectAsStateWithLifecycle()
    val busy by vm.busy.collectAsStateWithLifecycle()
    val status by vm.status.collectAsStateWithLifecycle()
    val names=remember {settingsCategoryOrder()+"Desempenho"}
    val pager=rememberPagerState(initialPage=names.indexOf(initialCategory).takeIf {it>=0} ?: 0,pageCount={names.size})
    var overview by rememberSaveable {mutableStateOf(initialCategory=="Geral")}
    val scope=rememberCoroutineScope()
    var reset by remember {mutableStateOf(false)}
    var searchQuery by rememberSaveable {mutableStateOf("")}
    var searchTarget by remember {mutableStateOf("")}
    androidx.activity.compose.BackHandler {if(!overview){overview=true;searchTarget=""} else close()}
    val searchEntries=remember {settingsSearchEntries()}
    val language=LocalUiLanguage.current
    val keyboard=LocalSoftwareKeyboardController.current
    val searchResults=remember(searchQuery,language,settings.optString("theme")) {if(searchQuery.isBlank())emptyList() else searchEntries.filter {entry->
        (entry.label!="Mostrar bordas e separações no Preto puro" || settings.optString("theme")=="Preto puro") && settingsSearchMatches(searchQuery,listOf(entry.category,entry.label,entry.keywords).joinToString(" "){translateUi(it,language)})
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

    Surface(Modifier.fillMaxSize(),color=MaterialTheme.colorScheme.background) {
        Column(Modifier.fillMaxSize().imePadding().padding(horizontal=20.dp),verticalArrangement=Arrangement.spacedBy(12.dp)) {
            Row(verticalAlignment=androidx.compose.ui.Alignment.CenterVertically) {
                IconButton(onClick={if(overview)close() else {overview=true;searchTarget=""}}){OndaIcon("back","Voltar",Modifier.size(24.dp))}
                ToolHeading(if(overview)"Configurações" else names[pager.currentPage])
            }
            OutlinedTextField(searchQuery,{searchQuery=it;searchTarget=""},label={UiText("Pesquisar configurações")},singleLine=true,shape=RoundedCornerShape(16.dp),modifier=Modifier.fillMaxWidth().testTag("settings-search"))
            if(searchQuery.isNotBlank()) {
                if(searchResults.isEmpty())UiText("Nenhuma configuração encontrada.",style=MaterialTheme.typography.bodySmall)
                Column(Modifier.fillMaxWidth().heightIn(max=170.dp).verticalScroll(rememberScrollState())) {
                    searchResults.forEach {entry->
                        TextButton(onClick={
                            searchTarget=entry.label;searchQuery="";overview=false;keyboard?.hide()
                            scope.launch {pager.scrollToPage(names.indexOf(entry.category).coerceAtLeast(0))}
                        },modifier=Modifier.fillMaxWidth()) {
                            Text(translateUi(entry.category,language)+" · "+translateUi(entry.label,language))
                        }
                    }
                }
            }
            if(busy) {LinearProgressIndicator(Modifier.fillMaxWidth());UiText(status,style=MaterialTheme.typography.bodySmall,maxLines=2);TextButton(onClick={vm.cancel()}){UiText("Cancelar")}}
            if(overview && searchQuery.isBlank()) {
                Column(Modifier.weight(1f).verticalScroll(rememberScrollState()),verticalArrangement=Arrangement.spacedBy(16.dp)) {
                    for((group,groupNames) in listOf("Preferências" to listOf("Geral","Aparência","Áudio","Downloads","Imagens"),"Aplicativo" to listOf("Contas","Ferramentas","Desempenho"))) {
                        UiText(group,style=MaterialTheme.typography.titleSmall,color=MaterialTheme.colorScheme.onSurfaceVariant)
                        ToolCard {
                            groupNames.filter {it in names}.forEachIndexed {index,name->
                                if(index>0)HorizontalDivider(color=MaterialTheme.colorScheme.outlineVariant.copy(alpha=.35f))
                                Row(Modifier.fillMaxWidth().heightIn(min=54.dp).clickable {overview=false;scope.launch {pager.scrollToPage(names.indexOf(name))}},verticalAlignment=androidx.compose.ui.Alignment.CenterVertically,horizontalArrangement=Arrangement.spacedBy(16.dp)) {
                                    OndaIcon(when(name){"Aparência"->"image";"Áudio"->"equalizer";"Downloads"->"download";"Imagens"->"image";"Contas"->"tag";"Ferramentas"->"convert";else->"settings"},modifier=Modifier.size(24.dp))
                                    Column(Modifier.weight(1f)) {UiText(name,style=MaterialTheme.typography.titleMedium);if(name=="Áudio")UiText("Prévias, transições e reprodução",style=MaterialTheme.typography.bodySmall,color=MaterialTheme.colorScheme.onSurfaceVariant)}
                                    OndaIcon("chevron",modifier=Modifier.size(20.dp))
                                }
                            }
                        }
                    }
                    Spacer(Modifier.height(12.dp))
                }
            } else {
            CompositionLocalProvider(LocalSettingsSearchTarget provides searchTarget) {
            HorizontalPager(state=pager,modifier=Modifier.weight(1f).testTag("settings-pages"),verticalAlignment=androidx.compose.ui.Alignment.Top) { page->
            Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(bottom=16.dp).background(MaterialTheme.colorScheme.surfaceVariant.copy(alpha=.25f),RoundedCornerShape(18.dp)).padding(16.dp),verticalArrangement=Arrangement.spacedBy(LayoutSpacing.controls)) {
                when(names[page]) {
                    "Geral"->{
                        Toggle("Lembrar configurações",settings.optBoolean("remember",true)){put("remember",it)}
                        UiText("Ative para recuperar suas opções ao abrir o aplicativo novamente.",style=MaterialTheme.typography.bodySmall)
                        SettingsDivider()
                        UiText("Preferências",style=MaterialTheme.typography.titleMedium)
                        Select("Idioma",settings.optString("language","pt-BR"),UI_LANGUAGES){put("language",it)}
                        SettingsDivider()
                        Toggle("Reconhecer links copiados automaticamente",settings.optBoolean("clipboard_links",true)){put("clipboard_links",it)}
                        Select("Duração dos avisos",settings.optString("notice_duration","Após 3 segundos"),noticeDurations.keys.toList()){put("notice_duration",it)}
                        UiText("Avisos de operações em andamento permanecem até terminar. O botão × permite fechar manualmente.",style=MaterialTheme.typography.bodySmall)
                        Toggle("Animar avisos",settings.optBoolean("notice_animation",true)){put("notice_animation",it)}
                        PreferenceTransfer(vm)
                        SettingsDivider()
                        UiText("Restaurar configurações",style=MaterialTheme.typography.titleMedium)
                        TextButton(onClick={reset=true}){UiText("Escolher quais configurações restaurar…")}
                        SettingsDivider()
                        TextButton(onClick={reset=true}){UiText("Restaurar TODAS as configurações ao padrão")}
                    }
                    "Aparência"->{
                        UiText("Tema e cores",style=MaterialTheme.typography.titleMedium)
                        SettingsDivider()
                        Select("Modo de aparência",settings.optString("theme"),listOf("Seguir o sistema","Escuro","Preto puro","Claro","Alto contraste")){put("theme",it)}
                        Select("Cor de destaque",settings.optString("accent"),accents.keys.toList()){put("accent",it)}
                        SettingsDivider()
                        if(settings.optString("theme")=="Preto puro") Toggle("Mostrar bordas e separações no Preto puro",settings.optBoolean("pure_black_separators",false)){put("pure_black_separators",it)}
                        SettingsDivider()
                        UiText("Texto e espaçamento",style=MaterialTheme.typography.titleMedium)
                        Select("Alterar tamanho da fonte",settings.optString("interface_font_size","100%"),interfaceFontSizes){put("interface_font_size",it)}
                        SettingsDivider()
                        Select("Fonte da interface",settings.optString("interface_font",DEFAULT_INTERFACE_FONT),interfaceFonts.keys.toList()){put("interface_font",it)}
                        UiText(FONT_PREVIEW,style=MaterialTheme.typography.bodyLarge,modifier=Modifier.testTag("font-preview"))
                        UiText("A fonte muda na hora. Ative Lembrar configurações para manter sua escolha ao reabrir.",style=MaterialTheme.typography.bodySmall)
                        SettingsDivider()
                        Select("Espaçamento da interface",settings.optString("interface_spacing","Padrão"),spacingModes){put("interface_spacing",it)}
                        SettingsDivider()
                        UiText("Cards e listas",style=MaterialTheme.typography.titleMedium)
                        Select("Tamanho dos cards da pesquisa",settings.optString("catalog_card_size","Grande"),listOf("Pequeno","Médio","Grande")){put("catalog_card_size",it)}
                        Toggle("Simplificar controles de download",settings.optBoolean("simple_download_ui",false)){put("simple_download_ui",it)}
                        UiText("Oculta formato e qualidade ao adicionar links pelo botão + e ao baixar músicas da pesquisa. Usa a maior qualidade disponível.",style=MaterialTheme.typography.bodySmall)
                        SettingsDivider()
                        Select("Mostrar itens na fila",settings.optString("queue_view","Completa"),listOf("Compacto","Completa")){put("queue_view",it)}
                        Select("Tamanho dos cards da fila",settings.optString("queue_card_size","Grande"),listOf("Pequeno","Médio","Grande")){put("queue_card_size",it)}
                        Select("Mostrar músicas no histórico",settings.optString("history_view","Compacto"),listOf("Compacto","Completa")){put("history_view",it)}
                        UiText("Compacto mostra título e andamento. Completa inclui capa e informações disponíveis da música e do álbum.",style=MaterialTheme.typography.bodySmall)
                        Select("Tamanho dos cards do histórico",settings.optString("history_card_size","Grande"),listOf("Pequeno","Médio","Grande")){put("history_card_size",it)}
                        SettingsDivider()
                        UiText("Navegação",style=MaterialTheme.typography.titleMedium)
                        Select("Ordem das abas de reprodução",settings.optString("playback_tab_order","Efeitos primeiro"),listOf("Efeitos primeiro","Jukebox infinito primeiro")){put("playback_tab_order",it)}
                        UiText("Pesquisar, Downloads e Mais ficam na barra inferior. Use + em Downloads para adicionar links. As ferramentas ficam no menu Mais.",style=MaterialTheme.typography.bodySmall)
                        UiText("Ordem da barra inferior",style=MaterialTheme.typography.titleSmall)
                        val bottomOrder=bottomBarOrder(settings)
                        bottomOrder.forEachIndexed {index,name->Row(verticalAlignment=androidx.compose.ui.Alignment.CenterVertically) {
                            UiText(when(name){"Fila"->"Downloads";"Efeitos"->"Reprodução";else->"Pesquisar"},Modifier.weight(1f))
                            fun moveBottom(delta:Int) {val copy=bottomOrder.toMutableList();java.util.Collections.swap(copy,index,index+delta);put("bottom_bar_order",JSONArray(copy))}
                            TextButton(enabled=index>0,onClick={moveBottom(-1)},modifier=Modifier.testTag("bottom-up-$name")){AccessibleSymbol("↑","Mover para cima")}
                            TextButton(enabled=index<bottomOrder.lastIndex,onClick={moveBottom(1)},modifier=Modifier.testTag("bottom-down-$name")){AccessibleSymbol("↓","Mover para baixo")}
                        }}
                        UiText("Mais permanece sempre no final. A navegação por arraste acompanha a ordem escolhida.",style=MaterialTheme.typography.bodySmall)
                        TextButton(onClick={put("bottom_bar_order",JSONArray(bottomBarDefaults))}){UiText("Restaurar ordem da barra inferior")}
                        val hidden=hiddenTabs(settings)
                        Toggle("Mostrar Reprodução na barra inferior","Efeitos" !in hidden) {shown->
                            put("hidden_tabs",JSONArray(if(shown)hidden.filter {it!="Efeitos"} else hidden+"Efeitos"))
                        }
                        val order=settings.getJSONArray("tab_order").let {a->(0 until a.length()).map {a.getString(it)}}
                        for((heading,keys) in listOf("Ferramentas no menu Mais" to listOf("Imagens","Conversor de vídeos","Metadados"),"Biblioteca no menu Mais" to listOf("Playlists / Álbuns","Histórico"))) {
                            SettingsDivider()
                            UiText(heading,style=MaterialTheme.typography.titleSmall)
                            val group=order.filter {it in keys}
                            group.forEachIndexed {index,name->Row(verticalAlignment=androidx.compose.ui.Alignment.CenterVertically) {
                                Box(Modifier.weight(1f)) {Toggle(tabLabel(name),name !in hidden) {shown->put("hidden_tabs",JSONArray(if(shown)hidden.filter {it!=name} else hidden+name))}}
                                fun move(delta:Int) {val copy=order.toMutableList();java.util.Collections.swap(copy,order.indexOf(name),order.indexOf(group[index+delta]));put("tab_order",JSONArray(copy))}
                                TextButton(enabled=index>0,onClick={move(-1)}){AccessibleSymbol("↑","Mover ${translateUi(tabLabel(name),LocalUiLanguage.current)} para cima")}
                                TextButton(enabled=index<group.lastIndex,onClick={move(1)}){AccessibleSymbol("↓","Mover ${translateUi(tabLabel(name),LocalUiLanguage.current)} para baixo")}
                            }}
                        }
                        TextButton(onClick={put("tab_order",OndaStore.defaults().getJSONArray("tab_order"))}){UiText("Restaurar ordem do menu Mais")}
                        SettingsDivider()
                        UiText("Gerenciamento avançado",style=MaterialTheme.typography.titleMedium)
                        Toggle("Mostrar ações antes das listas",settings.optBoolean("queue_actions_at_top",true)){put("queue_actions_at_top",it)}
                        UiText("Aplica-se à tela Gerenciar fila e ao histórico. Em Downloads, as ações ficam no menu de três pontos.",style=MaterialTheme.typography.bodySmall)

                    }
                    "Downloads"->{
                        UiText("Downloads e arquivos",style=MaterialTheme.typography.titleMedium)
                        UiText("As opções são aplicadas aos próximos links adicionados.",style=MaterialTheme.typography.bodySmall)
                        UiText("Pasta de destino",style=MaterialTheme.typography.labelMedium)
                        Button(onClick={folder.launch(null)}){UiText("Alterar")}
                        UiText(settings.optString("output_uri").ifBlank {"Downloads/ONDA no Android 10+. No Android 8/9, escolha uma pasta para preservar os arquivos ao desinstalar."},style=MaterialTheme.typography.bodySmall)
                        TextButton(onClick={put("output_uri","")}){UiText("Usar pasta padrão")}
                        SettingsDivider()
                        FormatOptions(settings,OndaStore::saveSettings,separated=true)
                        DownloadConcurrencyOptions(settings,::put)
                        WifiDownloadControls(settings,::put)
                        SettingsDivider()
                        Toggle("Escolher automaticamente os metadados mais semelhantes",settings.optBoolean("auto_metadata")){put("auto_metadata",it)}
                        UiText("Seleciona o primeiro resultado de maior similaridade entre os metadados compatíveis, sem abrir a escolha. Sem correspondência compatível, informa o erro. Não altera a escolha da versão de áudio.",style=MaterialTheme.typography.bodySmall)
                        SettingsDivider()
                        Toggle("Escolher automaticamente a versão mais semelhante no YouTube",settings.optBoolean("auto_match")){put("auto_match",it)}
                        SettingsDivider()
                        UiText("Vale para os próximos downloads iniciados, inclusive itens já na fila e álbuns. Escolhe a maior similaridade entre as versões compatíveis.",style=MaterialTheme.typography.bodySmall)
                        SettingsDivider()
                        Toggle("Revisar metadados antes de baixar",settings.optBoolean("review_metadata")){put("review_metadata",it)}
                        UiText("Spotify, Deezer e Apple Music fornecem metadados; o áudio correspondente é obtido do YouTube.",style=MaterialTheme.typography.bodySmall)
                        OrganizationOptions(settings,::put)
                        val duplicates=linkedMapOf("Perguntar" to "ask","Manter ambos" to "keep","Substituir" to "replace","Pular" to "skip")
                        SettingsDivider()
                        Select("Quando o arquivo já existir",duplicates.entries.firstOrNull {it.value==settings.optString("duplicate_policy")}?.key ?: "Perguntar",duplicates.keys.toList()){put("duplicate_policy",duplicates.getValue(it))}
                        SettingsDivider()
                        Toggle("Baixar mídias sociais automaticamente na maior qualidade",settings.optBoolean("social_best_quality",true)){put("social_best_quality",it)}
                        UiText("Instagram, TikTok e Kwai: escolhe automaticamente a maior qualidade. Você ainda pode escolher quais itens baixar.",style=MaterialTheme.typography.bodySmall)
                        SettingsDivider()
                        Toggle("Selecionar todas as mídias ao abrir a publicação",settings.optBoolean("auto_select_media",true)){put("auto_select_media",it)}
                        UiText("Instagram, TikTok e Kwai: você pode desmarcar fotos e vídeos individualmente antes de confirmar.",style=MaterialTheme.typography.bodySmall)
                        SettingsDivider()
                        Toggle("Baixar playlist de vídeo",settings.optBoolean("link_playlist")){put("link_playlist",it)}
                        OutlinedTextField(settings.optInt("playlist_limit").toString(),{put("playlist_limit",(it.toIntOrNull() ?: 2000).coerceIn(1,5000))},label={UiText("Máximo de itens por playlist")},modifier=Modifier.fillMaxWidth(),singleLine=true)
                        SettingsDivider()
                        AdvancedDownloadOptions(settings,::put)
                    }
                    "Imagens"->ImageOptions(settings,OndaStore::saveSettings,separated=true)
                    "Áudio"->{
                        UiText("Reprodução e prévias",style=MaterialTheme.typography.titleMedium)
                        Toggle("Continuar prévia dos efeitos em outras abas",settings.optBoolean("keep_preview")){put("keep_preview",it)}
                        UiText("Mantém a prévia dos efeitos ao trocar de página. Não controla a reprodução do Jukebox.",style=MaterialTheme.typography.bodySmall)
                        Toggle("Continuar Jukebox em outras abas e em segundo plano",settings.optBoolean("jukebox_background")){put("jukebox_background",it)}
                        Toggle("Mostrar letra sincronizada (LRC)",settings.optBoolean("synced_lyrics")){put("synced_lyrics",it)}
                        SettingsDivider()
                        Select("Duração da transição entre músicas (segundos)",settings.optInt("jukebox_transition_seconds",2).toString(),(1..10).map {it.toString()}){put("jukebox_transition_seconds",it.toInt())}
                        UiText("Tempo de sobreposição entre a música atual e a próxima. Vale para trocas pelo timer e pela fila.",style=MaterialTheme.typography.bodySmall)
                        SettingsDivider()
                        UiText("Duração das prévias",style=MaterialTheme.typography.titleSmall)
                        for((key,label) in listOf("search_preview" to "Músicas nas pesquisas","effects_preview" to "Slowed / Sped Up e Reverb")) {
                            SettingsDivider()
                            val current=settings.optInt(key,25)
                            val durations=listOf(10,15,25,30,45,60,90,120,180).let {if(current in it)it else it+current}
                            Select(label,"$current segundos",durations.map {"$it segundos"}){put(key,it.substringBefore(' ').toInt())}
                        }
                        UiText("Vale para a próxima prévia. Nas pesquisas, o catálogo pode fornecer um trecho menor.",style=MaterialTheme.typography.bodySmall)
                        SettingsDivider()
                    }
                    "Contas"->{
                        UiText("Contas e acesso",style=MaterialTheme.typography.titleMedium)
                        UiText("Spotify · opcional",style=MaterialTheme.typography.titleSmall)
                        Button(onClick={vm.connectSpotify()}){UiText("Conectar")}
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
                    "Desempenho"->{
                        CacheControls(vm)
                    }
                    "Ferramentas"->{
                        AppUpdateControls(vm)
                        SettingsDivider()
                        UiText("Ferramentas e atualizações",style=MaterialTheme.typography.titleMedium)
                        UiText("Python, FFmpeg, FFprobe e QuickJS já estão incluídos no aplicativo. Não é necessário instalar Termux.")
                        Button(onClick={vm.operation("update",JSONObject(),dialog=true)}){UiText("Atualizar ferramentas")}
                        SettingsDivider()
                        OutlinedButton(onClick={vm.operation("self_test",JSONObject(),dialog=true){vm.showNotice("Verificar ferramentas","Ferramentas verificadas: ${it.optString("yt_dlp")}")}}){UiText("Verificar ferramentas")}
                        CacheControls(vm)
                        SettingsDivider()
                        UiText("ONDA Android ${BuildConfig.VERSION_NAME}" + if(BuildConfig.DEBUG) " · versão de desenvolvimento" else "",style=MaterialTheme.typography.bodySmall)
                    }
                }

            }
            }
            }
            }
        }
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
