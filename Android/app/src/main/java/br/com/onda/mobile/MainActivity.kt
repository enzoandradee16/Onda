package br.com.onda.mobile

import android.Manifest
import android.content.Intent
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.BackHandler
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.compose.foundation.*
import androidx.compose.foundation.layout.*
import androidx.compose.ui.semantics.*
import androidx.compose.foundation.selection.toggleable
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.input.key.*
import androidx.compose.ui.platform.LocalSoftwareKeyboardController
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.saveable.rememberSaveableStateHolder
import kotlinx.coroutines.launch
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.repeatOnLifecycle
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import coil.compose.AsyncImage
import kotlinx.coroutines.delay
import org.json.JSONArray
import org.json.JSONObject
import java.io.File

class MainActivity : ComponentActivity() {
    private val model: OndaViewModel by viewModels()
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        receive(intent)
        setContent { OndaApp(model) }
    }
    override fun onStop() {super.onStop();if(!OndaStore.settings.value.optBoolean("jukebox_background",true))model.jukebox.pause()}
    override fun onNewIntent(intent: Intent) { super.onNewIntent(intent); setIntent(intent); receive(intent) }
    // Public Activity override; AndroidX's bridge carries an internal annotation.
    @android.annotation.SuppressLint("RestrictedApi")
    override fun dispatchKeyEvent(event: android.view.KeyEvent): Boolean {
        if(event.action==android.view.KeyEvent.ACTION_DOWN && event.isAltPressed && event.keyCode==android.view.KeyEvent.KEYCODE_A) {
            OndaStore.selectAll.tryEmit(Unit);return true
        }
        return super.dispatchKeyEvent(event)
    }
    private fun receive(intent: Intent?) {
        if(intent?.getBooleanExtra("open_queue",false)==true) {model.queueNavigation.value=true;intent.removeExtra("open_queue")}
        if(intent?.action==Intent.ACTION_SEND) OndaStore.sharedLink.value=intent.getStringExtra(Intent.EXTRA_TEXT) ?: ""
    }
}

val accents=linkedMapOf("Verde-Água" to 0xFF79E2C4,"Azul" to 0xFF8DBBFF,"Roxo" to 0xFFC0A4FF,
    "Rosa" to 0xFFF5A4CD,"Laranja" to 0xFFFFBD85,"Vermelho" to 0xFFFFA2A2,"Verde" to 0xFF94DFA8,
    "Verde-limão" to 0xFFC8ED83,"Amarelo" to 0xFFF6E58D,"Dourado" to 0xFFE9CA82,"Ciano" to 0xFF8DE1ED,
    "Turquesa" to 0xFF71D8D8,"Índigo" to 0xFFA5AFFF,"Lilás" to 0xFFDEC1FF,"Coral" to 0xFFFFAE9B,"Cinza" to 0xFFBCC5D3)


val lightAccents=mapOf("Verde-Água" to 0xFF087E69,"Azul" to 0xFF245FBE,"Roxo" to 0xFF7544B8,"Rosa" to 0xFFAF286D,"Laranja" to 0xFFA6500B,"Vermelho" to 0xFFB42F3B,"Verde" to 0xFF257342,"Verde-limão" to 0xFF537512,"Amarelo" to 0xFF806600,"Dourado" to 0xFF8C650F,"Ciano" to 0xFF07758A,"Turquesa" to 0xFF087575,"Índigo" to 0xFF4856B9,"Lilás" to 0xFF865098,"Coral" to 0xFFB34332,"Cinza" to 0xFF576475)

@OptIn(ExperimentalMaterial3Api::class)
@Composable fun OndaApp(vm: OndaViewModel) {
    val settings by OndaStore.settings.collectAsStateWithLifecycle()
    val question by OndaStore.question.collectAsStateWithLifecycle()
    val busy by vm.busy.collectAsStateWithLifecycle()
    val tools by MobileEngine.toolsState.collectAsStateWithLifecycle()
    val notice by vm.dialogNotice.collectAsStateWithLifecycle()
    val status by vm.status.collectAsStateWithLifecycle()
    var statusVisible by rememberStatusNotice(status,busy,settings.optString("notice_duration","Após 3 segundos"))
    val effectsSource by vm.effectsSource.collectAsStateWithLifecycle()
    val shared by OndaStore.sharedLink.collectAsStateWithLifecycle()
    val pureBlack=settings.optString("theme")=="Preto puro"
    val dark=when(settings.optString("theme")) { "Claro"->false; "Escuro","Preto puro","Alto contraste"->true; else->isSystemInDarkTheme() }
    val palette=if(dark) accents else lightAccents
    val accent=Color(palette[settings.optString("accent")] ?: palette.getValue("Verde-Água"))
    val baseScheme=if(dark) darkColorScheme(primary=accent,background=Color(0xFF0E131B),surface=Color(0xFF161E29),onPrimary=Color(0xFF10171F),surfaceContainerLowest=Color(0xFF0B1016),surfaceContainerLow=Color(0xFF18212B),surfaceContainer=Color(0xFF1C2631),surfaceContainerHigh=Color(0xFF242F3B),surfaceContainerHighest=Color(0xFF2B3744),onBackground=Color(0xFFE9EEF5),onSurface=Color(0xFFE9EEF5),onSurfaceVariant=Color(0xFFAFBBC9),surfaceVariant=Color(0xFF25303D),secondaryContainer=Color(0xFF25303D),outline=Color(0xFF425161),outlineVariant=Color(0xFF303C49)) else lightColorScheme(primary=accent)
    val tabs=visibleTabs(settings)
    val blackScheme=if(pureBlack) baseScheme.copy(
        background=Color.Black,surface=Color.Black,surfaceTint=Color.Transparent,
        surfaceDim=Color.Black,surfaceBright=Color(0xFF181818),
        surfaceContainerLowest=Color.Black,surfaceContainerLow=Color.Black,surfaceContainer=Color.Black,
        surfaceContainerHigh=Color(0xFF101010),surfaceContainerHighest=Color(0xFF181818),
        surfaceVariant=Color(0xFF181818),outlineVariant=Color(0xFF303030)
    ) else baseScheme
    val scheme=if(settings.optString("theme")=="Alto contraste") highContrastScheme() else if(pureBlack) pureBlackSurfaces(blackScheme,settings.optBoolean("pure_black_separators",false)) else blackScheme
    val iconActivity=androidx.activity.compose.LocalActivity.current
    LaunchedEffect(settings.optString("theme"),settings.optString("accent"),dark,iconActivity) {
        LauncherIcons.sync(OndaStore.context,settings)
        iconActivity?.let {LauncherIcons.updateTaskIcon(it,settings,dark)}
    }
    val activityWindow=iconActivity?.window
    SideEffect {activityWindow?.let {applyNavigationBarTheme(it,scheme.background,dark)}}
    val homeTab="Pesquisar"
    var tab by rememberSaveable { mutableStateOf(homeTab) }
    LaunchedEffect(tab,tabs.toString()) {if(tab!="Mais" && (0 until tabs.length()).none {tabs.getString(it)==tab}) tab=homeTab}
    val queueRequested by vm.queueNavigation.collectAsStateWithLifecycle()
    LaunchedEffect(queueRequested) {if(queueRequested) {tab="Fila";vm.queueNavigation.value=false}}
    var metadataUri by rememberSaveable {mutableStateOf<String?>(null)}
    var showSettings by rememberSaveable { mutableStateOf(false) }
    var settingsCategory by rememberSaveable { mutableStateOf("Geral") }
    var youtubeSession by rememberSaveable {mutableStateOf(false)}
    var showLicenses by rememberSaveable {mutableStateOf(false)}
    val pages=rememberSaveableStateHolder()
    var showLinks by rememberSaveable {mutableStateOf(false)}
    val preferences=OndaStore.context.getSharedPreferences("preferences",0)
    var welcome by remember { mutableStateOf(!preferences.getBoolean("welcome_seen",false)) }
    val permission=rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) {}
    BackHandler(enabled=(showLinks || tab!=homeTab) && !showSettings && !youtubeSession && !showLicenses && !welcome && question==null && notice==null) {
        if(showLinks)showLinks=false else tab=if(tab in listOf("Imagens","Conversor de vídeos","Playlists / Álbuns","Histórico","Metadados")) "Mais" else homeTab
    }
    LaunchedEffect(Unit) { if(Build.VERSION.SDK_INT>=33) permission.launch(Manifest.permission.POST_NOTIFICATIONS) }
    LaunchedEffect(shared) { if(shared.isNotBlank()) {tab="Fila";showLinks=true} }
    LaunchedEffect(effectsSource) {if(effectsSource.isNotBlank()) tab="Efeitos"}
    LaunchedEffect(tab) {
        if(tab!="Efeitos") {
            if(!settings.optBoolean("keep_preview"))vm.stopPreview(stopJukebox=false)
            if(!settings.optBoolean("jukebox_background",true))vm.jukebox.pause()
        }
    }
    val typography=remember(settings.optString("interface_font"),settings.optString("interface_font_size")) {interfaceTypography(settings.optString("interface_font",DEFAULT_INTERFACE_FONT),settings.optString("interface_font_size","100%"))}
    LocalizedTheme(language=settings.optString("language","pt-BR"),colorScheme=scheme,typography=typography,spacing=settings.optString("interface_spacing","Padrão")) {
        Scaffold(
            topBar={OndaAppBar {settingsCategory="Geral";showSettings=true}},
            bottomBar={Column {
                if(tab!="Efeitos" || showSettings)OndaMiniPlayer(vm) {showSettings=false;tab="Efeitos"}
                OndaBottomNavigation(if(showSettings)"Mais" else tab,tabs) {destination->showSettings=false;tab=destination}
            }},
            floatingActionButton={if(!showSettings && (tab=="Fila" || tab=="Links e fila"))FloatingActionButton(onClick={showLinks=true},containerColor=MaterialTheme.colorScheme.primary,shape=RoundedCornerShape(50)) {OndaIcon("add","Adicionar links",Modifier.size(24.dp))}}
        ) { padding ->
            Column(Modifier.fillMaxSize().padding(padding)) {
                if(busy && !tools.running) LinearProgressIndicator(Modifier.fillMaxWidth())
                if(tools.running)ToolCard(Modifier.padding(horizontal=LayoutSpacing.inset,vertical=8.dp).testTag("tools-preparation-progress")) {
                    UiText(tools.message,style=MaterialTheme.typography.bodyMedium)
                    if(tools.total>0) {
                        val progress=(tools.done.toFloat()/tools.total).coerceIn(0f,1f)
                        LinearProgressIndicator(progress={progress},modifier=Modifier.fillMaxWidth())
                        UiText("${(progress*100).toInt()}%",style=MaterialTheme.typography.bodySmall)
                    } else LinearProgressIndicator(Modifier.fillMaxWidth())
                }
                TopStatusNotice(status,statusVisible,busy,settings.optBoolean("notice_animation",true),onCancel={vm.cancel()},onDismiss={statusVisible=false},cancellable=!tools.running,onOpenSettings={category->if(category=="Sessão do YouTube")youtubeSession=true else {settingsCategory=category;showSettings=true}})
                if(showSettings)Box(Modifier.weight(1f).fillMaxWidth()){SettingsWindow(vm,initialCategory=settingsCategory){showSettings=false}} else SwipePageHost(current=tab,pages=mainDestinations(tabs,bottomBarOrder(settings)),onNavigate={tab=it},modifier=Modifier.weight(1f).fillMaxWidth()) {
                    pages.SaveableStateProvider(tab) {when(tab) {
                        "Pesquisar"->SearchPage(vm,onConnectSpotify={settingsCategory="Contas";showSettings=true})
                        "Links e fila","Fila"->DownloadsHome(vm)
                        "Mais"->MorePage(tabs,onNavigate={tab=it},onYouTube={youtubeSession=true},onLicenses={showLicenses=true},onFailures={OndaStore.failureSummary.value=OndaStore.items.value.filter {it.state=="Erro"}.map {it.id}.takeIf {it.isNotEmpty()}})
                        "Imagens"->ImagesPage(vm)
                        "Playlists / Álbuns"->CollectionsPage(vm)
                        "Histórico"->HistoryPage(vm,onEditMetadata={metadataUri=it.uri;tab="Metadados"})
                        "Efeitos"->PlaybackPage(vm)
                        "Metadados"->MetadataPage(vm,metadataUri){metadataUri=null}
                        "Conversor de vídeos"->VideoConverterPage(vm)
                    }}
                }
            }
        }
        if(showLinks)ModalBottomSheet(onDismissRequest={showLinks=false},sheetState=rememberModalBottomSheetState(skipPartiallyExpanded=true)) {
            Box(Modifier.fillMaxWidth().fillMaxHeight(.88f).imePadding()) {LinksPage(vm,onAdded={showLinks=false;tab="Fila"})}
        }
        val failureIds by OndaStore.failureSummary.collectAsStateWithLifecycle()
        if(question==null && notice==null && !showSettings && !youtubeSession && !showLicenses && !welcome) {
            failureIds?.let {FailureSummaryWindow(it,vm){OndaStore.failureSummary.value=null}}
        }
        ClipboardDownloadPrompt(settings.optBoolean("clipboard_links",true),!busy && question==null && notice==null && !showSettings && !youtubeSession && !showLicenses && !welcome && !showLinks,onAdd={candidate->
            if(candidate.optBoolean("collection"))vm.loadCollection(candidate.getString("url"),OndaStore.collectionOptions(),queueOnly=true)
            else vm.enqueueLinks(listOf(candidate.getString("url")),false)
            tab="Fila"
        }) {candidate->
            if(candidate.optBoolean("collection"))vm.loadCollection(candidate.getString("url"),OndaStore.collectionOptions(),startDownload=true)
            else vm.enqueueLinks(listOf(candidate.getString("url")),true)
        }
        question?.let { ChoiceWindow(it,vm) }
        if(youtubeSession) YouTubeSessionWindow {youtubeSession=false}
        if(showLicenses) LicensesWindow {showLicenses=false}
        if(welcome) AlertDialog(containerColor=ondaDialogContainerColor(),onDismissRequest={preferences.edit().putBoolean("welcome_seen",true).apply();welcome=false},title={UiText("Bem-vindo ao Onda")},
            text={UiText("Ajuste o básico para começar. Você pode fechar esta janela e configurar tudo depois.")},
            confirmButton={TextButton(onClick={preferences.edit().putBoolean("welcome_seen",true).apply();welcome=false;settingsCategory="Geral";showSettings=true}){UiText("Configurações")}},
            dismissButton={TextButton(onClick={preferences.edit().putBoolean("welcome_seen",true).apply();welcome=false}){UiText("Agora não")}})
        notice?.let {current->
            val destination=noticeDestination(current.message)
            AlertDialog(containerColor=ondaDialogContainerColor(),onDismissRequest=vm::dismissNotice,title={UiText(current.title)},
                text={Column(Modifier.heightIn(max=320.dp).verticalScroll(rememberScrollState())){UiText(current.message)}},
                confirmButton={TextButton(onClick=vm::dismissNotice){UiText("OK")}},
                dismissButton={if(destination!=null)TextButton(onClick={
                    vm.dismissNotice()
                    if(destination=="Sessão do YouTube")youtubeSession=true else {settingsCategory=destination;showSettings=true}
                }){UiText(if(destination=="Sessão do YouTube")"Sessão do YouTube" else "Configurações")}})
        }
    }
}
fun tabLabel(tab: String)=when(tab) {"Conversor de vídeos"->"Conversor";"Links e fila"->"Links";"Metadados"->"Editar metadados";"Pesquisar"->"Pesquisar músicas";"Efeitos"->"Reprodução e efeitos";"Playlists / Álbuns"->"Álbuns e playlists";else->tab}

@Composable fun PageTitle(title: String, description: String) {
    Column(Modifier.fillMaxWidth().padding(vertical=8.dp),horizontalAlignment=Alignment.Start) {
        UiText(title,modifier=Modifier.semantics {heading()},style=MaterialTheme.typography.titleLarge,fontWeight=FontWeight.Bold,textAlign=TextAlign.Start)
        if(description.isNotBlank())UiText(description,style=MaterialTheme.typography.bodySmall,textAlign=TextAlign.Start,modifier=Modifier.padding(top=LayoutSpacing.details))
    }
}
@Composable fun Select(label: String, value: String, choices: List<String>, modifier: Modifier=Modifier, changed: (String)->Unit) {
    var open by remember { mutableStateOf(false) }
    val displayValue=if(value=="pt-BR") "Português (Brasil)" else if(value=="es") "Español" else if(value=="en") "English" else translateUi(value,LocalUiLanguage.current)
    Column(modifier,verticalArrangement=Arrangement.spacedBy(LayoutSpacing.text)) {
        if(label.isNotBlank()) UiText(label,style=MaterialTheme.typography.labelMedium)
        Box { OutlinedButton(onClick={open=true},modifier=Modifier.fillMaxWidth().heightIn(min=48.dp).a11yLabel(if(label.isBlank()) displayValue else translateUi(label,LocalUiLanguage.current)+": "+displayValue,if(open) "Expandido" else "Recolhido"),colors=ButtonDefaults.outlinedButtonColors(contentColor=MaterialTheme.colorScheme.onSurface),shape=RoundedCornerShape(16.dp),contentPadding=PaddingValues(horizontal=12.dp,vertical=6.dp)) {UiText(if(value=="pt-BR")"Português (Brasil)" else if(value=="es")"Español" else if(value=="en")"English" else value,Modifier.weight(1f),maxLines=1,style=MaterialTheme.typography.bodyMedium);UiText("▾",Modifier.padding(start=6.dp).clearAndSetSemantics {})}
            DropdownMenu(expanded=open,onDismissRequest={open=false}) { choices.forEach { choice-> DropdownMenuItem(text={UiText(if(choice=="pt-BR")"Português (Brasil)" else if(choice=="es")"Español" else if(choice=="en")"English" else choice)},onClick={changed(choice);open=false}) } }
        }
    }
}
@Composable fun Toggle(text: String, checked: Boolean, changed: (Boolean)->Unit) {
    ToolSwitch(text,checked,changed=changed)
}

val modes=linkedMapOf("Vídeo · melhor qualidade (MKV)" to "video","Vídeo · MP4" to "mp4",
    "Áudio · original, sem recodificar" to "original","Áudio · MP3" to "mp3",
    "Áudio · M4A (AAC)" to "m4a","Áudio · FLAC" to "flac","Fotos · todas do carrossel" to "photos",
    "Publicação · fotos e vídeos originais" to "social")
@Composable fun FormatOptions(config: JSONObject, changed: (JSONObject)->Unit, separated:Boolean=false) {
    val preferences by OndaStore.settings.collectAsStateWithLifecycle()
    if(!separated && preferences.optBoolean("simple_download_ui",false)) return
    fun put(key: String, value: Any) {changed(JSONObject(config.toString()).put(key,value))}
    val mode=config.optString("mode","mp3")
    Row(horizontalArrangement=Arrangement.spacedBy(LayoutSpacing.controls)) {
        Select("Formato",modes.entries.firstOrNull {it.value==mode}?.key ?: "Áudio · MP3",modes.keys.toList(),Modifier.weight(1f)) {put("mode",modes.getValue(it))}
        if(mode in listOf("mp3","m4a")) {
            val qualities=if(mode=="mp3") listOf("320 kbps","256 kbps","192 kbps","128 kbps","96 kbps") else listOf("256 kbps","192 kbps","128 kbps","96 kbps")
            Select("Qualidade de áudio",config.optString("audio_quality").takeIf {it in qualities} ?: qualities.first(),qualities,Modifier.weight(1f)) {put("audio_quality",it)}
        }
    }
    if(separated && mode in listOf("mp4","video","social")) SettingsDivider()
    if(mode in listOf("mp4","video","social")) Row(horizontalArrangement=Arrangement.spacedBy(LayoutSpacing.controls)) {
        val heights=listOf("Melhor disponível","2160p / 4K","1440p","1080p","720p","480p")
        Select("Resolução máxima",if(config.isNull("height")) "Melhor disponível" else if(config.optInt("height")==2160) "2160p / 4K" else "${config.optInt("height",1080)}p",heights,Modifier.weight(1f)) {put("height",it.substringBefore(" / ").removeSuffix("p").toIntOrNull() ?: JSONObject.NULL)}
        Select("FPS máximo",if(config.isNull("fps")) "Original" else "${config.optInt("fps")} fps",listOf("Original","24 fps","30 fps","60 fps","120 fps"),Modifier.weight(1f)) {put("fps",it.substringBefore(' ').toIntOrNull() ?: JSONObject.NULL)}
    }
    if(mode=="flac") UiText("Links de catálogo em FLAC baixam diretamente do Monochrome, quando disponíveis. Outros links são convertidos; isso não melhora fontes com perdas.",style=MaterialTheme.typography.bodySmall)
}

@Composable fun SearchPage(vm: OndaViewModel, onConnectSpotify: ()->Unit) {
    val settings by OndaStore.settings.collectAsStateWithLifecycle()
    val queue by OndaStore.items.collectAsStateWithLifecycle()
    val searchQueue=remember(queue) {queue.filter {it.config.optString("_origin")=="search"}}
    val active by OndaStore.active.collectAsStateWithLifecycle()
    val running by OndaStore.running.collectAsStateWithLifecycle()
    val results by vm.searchResults.collectAsStateWithLifecycle()
    var query by rememberSaveable { mutableStateOf("") }
    var provider by rememberSaveable { mutableStateOf("Deezer") }
    var showSearchFilters by rememberSaveable { mutableStateOf(false) }
    var searchArtist by rememberSaveable { mutableStateOf("") }
    var searchAlbum by rememberSaveable { mutableStateOf("") }
    var searchVersion by rememberSaveable { mutableStateOf("") }
    var searchYear by rememberSaveable { mutableStateOf("") }
    var searchDuration by rememberSaveable { mutableStateOf("") }
    var exactSearch by rememberSaveable { mutableStateOf(false) }
    var comparison by remember { mutableStateOf(listOf<JSONObject>()) }
    var downloadTrack by rememberSaveable {mutableStateOf<String?>(null)}
    val busy by vm.busy.collectAsStateWithLifecycle()
    val spotifyConnected by vm.spotifyConnected.collectAsStateWithLifecycle()
    var spotifySecretConfigured by remember {mutableStateOf(false)}
    LaunchedEffect(settings,spotifyConnected) {spotifySecretConfigured=kotlinx.coroutines.withContext(kotlinx.coroutines.Dispatchers.IO) {!SecureVault.get("spotify-api").isNullOrBlank()}}
    val keyboard=LocalSoftwareKeyboardController.current
    fun submitSearch() {
        val text=query.lineSequence().joinToString(" ").trim()
        if(text.isNotBlank() && !vm.busy.value) {keyboard?.hide();vm.search(text,provider)}
    }
    if(comparison.size==2) AlertDialog(onDismissRequest={comparison=emptyList()},title={UiText("Comparar resultados")},text={
        Column(Modifier.verticalScroll(rememberScrollState())) {
            comparison.forEach {row->
                Text(row.cleanString("title"),fontWeight=FontWeight.Bold)
                Text(row.stringList("artists"))
                Text(row.cleanString("album"))
                MetadataPlatformBadge(row)
                Text(listOf(row.cleanString("release_date"),mediaClock(row.optLong("duration_ms")/1000),row.cleanString("isrc")).filter {it.isNotBlank()}.joinToString(" · "))
                HorizontalDivider(Modifier.padding(vertical=12.dp))
            }
        }
    },confirmButton={TextButton(onClick={comparison=emptyList()}){UiText("Voltar")}})
    if(showSearchFilters) AlertDialog(onDismissRequest={showSearchFilters=false},title={UiText("Filtros da busca")},text={
        Column(Modifier.verticalScroll(rememberScrollState()),verticalArrangement=Arrangement.spacedBy(LayoutSpacing.controls)) {
            OutlinedTextField(searchArtist,{searchArtist=it},label={UiText("Artista")},singleLine=true)
            OutlinedTextField(searchAlbum,{searchAlbum=it},label={UiText("Álbum")},singleLine=true)
            OutlinedTextField(searchVersion,{searchVersion=it},label={UiText("Versão")},singleLine=true)
            OutlinedTextField(searchYear,{searchYear=it},label={UiText("Ano ou intervalo")},singleLine=true)
            OutlinedTextField(searchDuration,{searchDuration=it},label={UiText("Duração ou intervalo")},singleLine=true)
            Text("ano:2020-2022 · duracao:3:00-4:00")
            Row(verticalAlignment=Alignment.CenterVertically) {Checkbox(exactSearch,{exactSearch=it},modifier=Modifier.padding(end=LayoutSpacing.checkboxLabel));UiText("Exatamente este título")}
        }
    },confirmButton={TextButton(onClick={
        val base=query.replace(Regex("(?<!\\S)(?:artista|album|versao|ano|duracao|exata):(\"[^\"]*\"|\\S+)"),"").trim()
        val fields=listOf("artista" to searchArtist,"album" to searchAlbum,"versao" to searchVersion,"ano" to searchYear,"duracao" to searchDuration)
        query=(listOf(base)+fields.filter {it.second.isNotBlank()}.map {it.first+":\""+it.second.replace("\"","").trim()+"\""}+(if(exactSearch)listOf("exata:sim") else emptyList())).filter {it.isNotBlank()}.joinToString(" ")
        showSearchFilters=false;submitSearch()
    }){UiText("Pesquisar")}},dismissButton={TextButton(onClick={showSearchFilters=false}){UiText("Voltar")}})
    downloadTrack?.let {raw->key(raw) {
        val track=remember(raw) {JSONObject(raw)}
        TrackDownloadDialog(track,settings,onDismiss={downloadTrack=null},onSubmit={options,now->
            try {
                val id=vm.queueTrack(track,options=options,origin="search",immediate=now)
                if(now)DownloadService.start(OndaStore.context,id)
                downloadTrack=null
            } catch(error:Exception) {vm.showNotice(if(now) "Baixar agora" else "Adicionar à fila",error.message ?: "Não foi possível adicionar a música.")}
        })
    }}
    LazyColumn(Modifier.fillMaxSize().padding(horizontal=LayoutSpacing.inset),verticalArrangement=Arrangement.spacedBy(LayoutSpacing.controls)) {
        item {PageTitle("Pesquisar músicas","")}
        item {OutlinedTextField(query,{query=it},placeholder={UiText("Música, artista ou link")},singleLine=true,shape=RoundedCornerShape(14.dp),
            leadingIcon={OndaIcon("search",modifier=Modifier.size(21.dp))},
            trailingIcon={IconButton(onClick={if(busy)vm.cancel() else submitSearch()},enabled=busy || query.isNotBlank()){OndaIcon(if(busy)"stop" else "search",if(busy)"Cancelar" else "Pesquisar",Modifier.size(22.dp))}},
            keyboardOptions=KeyboardOptions(imeAction=ImeAction.Search),keyboardActions=KeyboardActions(onSearch={submitSearch()}),
            modifier=Modifier.fillMaxWidth().testTag("music-query").onPreviewKeyEvent {event->
                if(event.key==Key.Enter || event.key==Key.NumPadEnter) {
                    if(event.type==KeyEventType.KeyDown && event.nativeKeyEvent.repeatCount==0) submitSearch()
                    true
                } else false
            })}
        item {Row(Modifier.fillMaxWidth(),verticalAlignment=Alignment.CenterVertically) {
            Row(Modifier.weight(1f).horizontalScroll(rememberScrollState()),horizontalArrangement=Arrangement.spacedBy(8.dp)) {
                for(name in listOf("Todos","Deezer","Apple / iTunes","Spotify"))FilterChip(selected=provider==name,onClick={provider=name},label={UiText(name)},colors=FilterChipDefaults.filterChipColors(selectedContainerColor=MaterialTheme.colorScheme.primary,selectedLabelColor=MaterialTheme.colorScheme.onPrimary))
            }
            var actions by remember {mutableStateOf(false)}
            Box {IconButton(onClick={actions=true}){OndaIcon("more","Opções da pesquisa",Modifier.size(22.dp))};DropdownMenu(actions,{actions=false}) {
                DropdownMenuItem(text={UiText("Filtros")},onClick={actions=false;showSearchFilters=true})
                DropdownMenuItem(text={UiText("Atualizar busca")},enabled=query.isNotBlank()&&!busy,onClick={actions=false;vm.search(query,provider,true)})
                HorizontalDivider()
                DropdownMenuItem(text={UiText("Tamanho dos cards")},enabled=false,onClick={})
                listOf("Pequeno","Médio","Grande").forEach {size->DropdownMenuItem(text={UiText(size)},onClick={OndaStore.saveSettings(JSONObject(settings.toString()).put("catalog_card_size",size));actions=false})}

            }}
        }}
        if(results.isNotEmpty())item {UiText("Resultados",style=MaterialTheme.typography.titleMedium,fontWeight=FontWeight.Bold)}
        if(provider=="Spotify" && !spotifyConnected && !(settings.optString("spotify_client_id").isNotBlank() && spotifySecretConfigured)) item {
            Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(LayoutSpacing.controls),verticalAlignment=Alignment.CenterVertically) {
                OutlinedButton(onClick=onConnectSpotify,modifier=Modifier.testTag("search-connect-spotify")) {UiText("Configurar Spotify")}
                UiText("Configure a API em Configurações → Contas para pesquisar músicas no Spotify.",Modifier.weight(1f),style=MaterialTheme.typography.bodySmall)
            }
        }
        if(searchQueue.isNotEmpty())item {TextButton(onClick={vm.queueNavigation.value=true}){UiText("Ver fila")}}
        if(results.isEmpty()) item {UiText("Sua biblioteca começa com uma busca",fontWeight=FontWeight.Bold);UiText("Encontre a música e escolha a versão que você quer.",style=MaterialTheme.typography.bodySmall)}
        if(comparison.size==1)item {UiText("Selecione outro resultado para comparar.")}
        items(results,contentType={"search_track"}) {record-> TrackCard(record,vm,onDownload={downloadTrack=record.toString()},onCompare={
            val source=record.cleanString("source_url")
            val repeated=comparison.any {it===record || (source.isNotBlank() && sourceKey(it.cleanString("source_url"))==sourceKey(source))}
            if(repeated)vm.showNotice("Comparar resultados","Essa música já foi selecionada. Escolha outro resultado para comparar.")
            else comparison=(comparison+record).takeLast(2)
        }) }
        item {Spacer(Modifier.height(LayoutSpacing.controls))}
    }
}
internal fun displayReleaseDate(value:String):String {
    val text=value.trim()
    if(Regex("\\d{4}-\\d{2}-\\d{2}(?:T.*)?").matches(text)) {
        try {
            val date=java.time.LocalDate.parse(text.take(10))
            return "%02d/%02d/%04d".format(java.util.Locale.ROOT,date.dayOfMonth,date.monthValue,date.year)
        } catch(_:java.time.DateTimeException) {}
    }
    if(Regex("\\d{4}-\\d{2}").matches(text) && text.takeLast(2).toInt() in 1..12)return text.takeLast(2)+"/"+text.take(4)
    return text
}

@Composable fun TrackCard(record: JSONObject, vm: OndaViewModel, onDownload:()->Unit, onCompare:(()->Unit)?=null) {
    val cardSettings by OndaStore.settings.collectAsStateWithLifecycle()
    val cardSize=cardSettings.optString("catalog_card_size","Grande")
    val coverSide=when(cardSize){"Pequeno"->56.dp;"Médio"->76.dp;else->94.dp}

    val playing by vm.previewActive.collectAsStateWithLifecycle()
    val playingUrl by vm.previewUrl.collectAsStateWithLifecycle()
    var releaseDate by remember(record) {mutableStateOf(record.cleanString("release_date"))}
    LaunchedEffect(record) {releaseDate=vm.releaseDate(record)}
    val url=record.cleanString("preview_url")
    val thisPlaying=playing && playingUrl==url
    var actions by remember {mutableStateOf(false)}
    Surface(Modifier.fillMaxWidth(),shape=RoundedCornerShape(18.dp),color=MaterialTheme.colorScheme.surfaceContainerLow) {
        Row(Modifier.padding(if(cardSize=="Pequeno")10.dp else 14.dp),verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.spacedBy(12.dp)) {
            AsyncImage(record.cleanString("cover_url"),translateUi("Capa do álbum"),Modifier.size(coverSide).clip(RoundedCornerShape(10.dp)),contentScale=androidx.compose.ui.layout.ContentScale.Crop)
            Column(Modifier.weight(1f),verticalArrangement=Arrangement.spacedBy(5.dp)) {
                Row(Modifier.fillMaxWidth(),verticalAlignment=Alignment.Top) {
                    Text(record.cleanString("title"),modifier=Modifier.weight(1f).padding(top=10.dp),fontWeight=FontWeight.SemiBold,maxLines=2,overflow=androidx.compose.ui.text.style.TextOverflow.Ellipsis,style=if(cardSize=="Pequeno")MaterialTheme.typography.bodyMedium else MaterialTheme.typography.titleSmall)
                    IconButton(onClick=onDownload){
                        Box(Modifier.size(30.dp).border(1.dp,MaterialTheme.colorScheme.onSurfaceVariant,androidx.compose.foundation.shape.CircleShape),contentAlignment=Alignment.Center){OndaIcon("download","Baixar agora",Modifier.size(18.dp))}
                    }
                    Box {
                        IconButton(onClick={actions=true}){OndaIcon("more-vertical","Mais ações",Modifier.size(20.dp))}
                DropdownMenu(expanded=actions,onDismissRequest={actions=false}) {
                    DropdownMenuItem(text={UiText("Baixar agora")},onClick={actions=false;onDownload()})
                    DropdownMenuItem(text={UiText("Adicionar à fila")},onClick={actions=false;vm.queueTrack(record,origin="search")})
                    DropdownMenuItem(text={UiText(if(thisPlaying)"Parar prévia" else "Ouvir prévia")},enabled=thisPlaying || url.isNotBlank(),onClick={actions=false;if(thisPlaying)vm.stopPreview() else vm.preview(url,OndaStore.settings.value.optInt("search_preview",25))})
                    DropdownMenuItem(text={UiText("Ver no catálogo")},onClick={actions=false;val source=record.cleanString("source_url");if(source.startsWith("https://"))OndaStore.context.startActivity(Intent(Intent.ACTION_VIEW,android.net.Uri.parse(source)).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))})
                    if(onCompare!=null)DropdownMenuItem(text={UiText("Comparar resultados")},onClick={actions=false;onCompare()})
                    if(record.cleanString("album").isNotBlank())DropdownMenuItem(text={Text(record.cleanString("album"))},enabled=false,onClick={})
                    DropdownMenuItem(text={MetadataPlatformBadge(record)},enabled=false,onClick={})
                    if(releaseDate.isNotBlank())DropdownMenuItem(text={Text(translateUi("Data de lançamento")+": "+displayReleaseDate(releaseDate))},enabled=false,onClick={})
                }
                    }
                }
                Text(record.stringList("artists"),style=MaterialTheme.typography.bodySmall,color=MaterialTheme.colorScheme.onSurfaceVariant,maxLines=1,overflow=androidx.compose.ui.text.style.TextOverflow.Ellipsis)
                record.cleanString("album").takeIf {it.isNotBlank()}?.let {album->
                    Text(album,style=MaterialTheme.typography.bodySmall,color=MaterialTheme.colorScheme.onSurfaceVariant,maxLines=1,overflow=androidx.compose.ui.text.style.TextOverflow.Ellipsis)
                }
                if(releaseDate.isNotBlank())Text(translateUi("Data de lançamento")+": "+displayReleaseDate(releaseDate),style=MaterialTheme.typography.labelSmall,color=MaterialTheme.colorScheme.onSurfaceVariant)
                MetadataPlatformBadge(record)
                val duration=record.optLong("duration_ms")
                val detail=translateUi("Música")+if(duration>0)" · "+mediaClock(duration/1000) else ""
                Text(detail,style=MaterialTheme.typography.labelSmall,color=MaterialTheme.colorScheme.onSurfaceVariant,maxLines=1)

            }
        }
    }
}

@Composable fun LinksPage(vm: OndaViewModel,onAdded:()->Unit={}) {
    val settings by OndaStore.settings.collectAsStateWithLifecycle()
    val adding by vm.addingToQueue.collectAsStateWithLifecycle()
    val shared by OndaStore.sharedLink.collectAsStateWithLifecycle()
    var link by rememberSaveable {mutableStateOf("")}
    LaunchedEffect(shared) {if(shared.isNotBlank()) {link=shared;OndaStore.sharedLink.value=""}}
    fun add(now:Boolean) {
        val urls=link.lines().map {it.trim()}.filter {it.isNotBlank()}
        vm.enqueueLinks(urls,now)
        link="";onAdded()
    }
    NavigableList(Modifier.fillMaxSize().padding(horizontal=LayoutSpacing.inset),navigationId="links") {
        item {PageTitle("Adicionar links","YouTube, Instagram, TikTok e outros sites.")}
        item {OutlinedTextField(link,{link=it},label={UiText("LINKS")},placeholder={UiText("YouTube, Instagram, TikTok, Kwai… um link por linha")},shape=RoundedCornerShape(14.dp),minLines=2,modifier=Modifier.fillMaxWidth().testTag("links-input"),singleLine=false)}
        item {FormatOptions(settings,OndaStore::saveSettings)}
        item {Toggle("Baixar playlist de vídeo",settings.optBoolean("link_playlist")){OndaStore.saveSettings(JSONObject(settings.toString()).put("link_playlist",it))}}
        item {Row(horizontalArrangement=Arrangement.spacedBy(LayoutSpacing.controls)) {
            OutlinedButton(onClick={add(false)},enabled=link.isNotBlank() && !adding,modifier=Modifier.testTag("links-add")){UiText("Adicionar à fila")}
            Button(onClick={add(true)},enabled=link.isNotBlank() && !adding,modifier=Modifier.testTag("links-download")){UiText("Baixar agora")}
        }}
        if(adding)item {LinearProgressIndicator(Modifier.fillMaxWidth())}
        item {TextButton(onClick={vm.queueNavigation.value=true;onAdded()},modifier=Modifier.testTag("view-queue")){UiText("Ver fila")}}
    }
}

@Composable fun QueuePage(vm: OndaViewModel) {
    val active by OndaStore.active.collectAsStateWithLifecycle()
    val settings by OndaStore.settings.collectAsStateWithLifecycle()
    val complete=settings.optString("queue_view","Completa")=="Completa"
    val cardSize=settings.optString("queue_card_size","Grande")
    val small=cardSize=="Pequeno"
    val cardPadding=if(!complete)4.dp else if(small)6.dp else if(cardSize=="Médio")10.dp else LayoutSpacing.section
    val queue by OndaStore.items.collectAsStateWithLifecycle()
    val queueListState=androidx.compose.foundation.lazy.rememberLazyListState()
    var queueOrder by rememberSaveable {mutableStateOf(queueOrders.first())}
    var query by rememberSaveable {mutableStateOf("")}
    var stateFilter by rememberSaveable {mutableStateOf("Todos")}
    val matcher=remember(query,stateFilter) {QueueMatcher(query,stateFilter)}
    val visible=remember(queue,matcher) {queue.filter {matcher.matches(it.title,it.state,it.config)}}
    val visibleIds=remember(visible) {visible.map {it.id}.toSet()}
    val completed=remember(queue) {queue.count {it.state=="Concluído"}}
    val running by OndaStore.running.collectAsStateWithLifecycle()
    var clockTick by remember {mutableLongStateOf(0L)}
    val clockOwner=LocalLifecycleOwner.current
    LaunchedEffect(clockOwner) {clockOwner.lifecycle.repeatOnLifecycle(Lifecycle.State.STARTED) {while(true) {clockTick++;delay(1000)}}}
    var space by remember {mutableStateOf<QueueSpace?>(null)}
    LaunchedEffect(clockTick,queue.size) {space=kotlinx.coroutines.withContext(kotlinx.coroutines.Dispatchers.IO){queueSpace(queue,true)}}
    val connected=remember(clockTick) {queueConnected()}
    val queueTimes=remember(queue,running,clockTick) {OndaStore.queueTiming.snapshot(queue.size-completed,queue.isNotEmpty())}
    val remainingTime=queueTimes.remaining?.let {if(it==0L) "00:00" else "≈ "+queueDuration(it)} ?: if(running)translateUi("Calculando…",LocalUiLanguage.current) else "—"
    val adding by vm.addingToQueue.collectAsStateWithLifecycle()
    val pauseReason by OndaStore.queuePause.collectAsStateWithLifecycle()
    val actionsAtTop=settings.optBoolean("queue_actions_at_top",true)
    val logs by OndaStore.messages.collectAsStateWithLifecycle()
    var selected by remember {mutableStateOf(setOf<String>())}
    val metadataHistory by OndaStore.history.collectAsStateWithLifecycle()
    var metadataBatch by remember {mutableStateOf<List<String>?>(null)}
    metadataBatch?.let {sources->
        if(sources.size>1)BatchMetadataEditor(vm,sources){metadataBatch=null}
        else Dialog(onDismissRequest={metadataBatch=null}) {
            Surface(shape=MaterialTheme.shapes.large) {
                Column(Modifier.fillMaxWidth().fillMaxHeight(0.9f)) {
                    TextButton(onClick={metadataBatch=null}){UiText("Pronto")}
                    Box(Modifier.weight(1f)){MetadataPage(vm,sources.single())}
                }
            }
        }
    }
    val metadataUris=metadataHistory.filter {record->historyKind(record.mode)=="Áudio" && OndaStore.items.value.any {item->
        item.id in selected && item.state=="Concluído" && jobSource(item.config).isNotBlank() && jobSource(item.config)==record.source && item.config.optString("mode").equals(record.mode,true)
    }}.map {it.uri}.distinct()

    var showLogs by remember {mutableStateOf(false)}
    var clear by remember {mutableStateOf(false)}
    LaunchedEffect(visibleIds) {selected=selected.intersect(visibleIds);OndaStore.selectAll.collect {selected=visible.filterNot {it.config.optBoolean("_immediate")}.map {it.id}.toSet()}}
    val queueActions:@Composable ()->Unit = {
        Column(Modifier.fillMaxWidth(),verticalArrangement=Arrangement.spacedBy(LayoutSpacing.controls)) {
            Button(onClick={DownloadService.start(OndaStore.context)},enabled=queue.any {it.state=="Pendente"},
                modifier=Modifier.fillMaxWidth().heightIn(min=48.dp)){UiText("Baixar fila")}
            Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(LayoutSpacing.section),verticalAlignment=Alignment.CenterVertically) {
                if(running)TextButton(onClick={DownloadService.control(OndaStore.context,if(DownloadRuntime.paused)"resume" else "pause")},modifier=Modifier.weight(1f).heightIn(min=48.dp)){UiText(if(DownloadRuntime.paused)"Retomar fila" else "Pausar fila")}
                OutlinedButton(onClick={DownloadService.stop(OndaStore.context)},enabled=running,
                    modifier=Modifier.weight(1f).heightIn(min=48.dp)){UiText("Parar")}
                TextButton(onClick={showLogs=!showLogs},
                    modifier=Modifier.weight(1f).heightIn(min=48.dp)){UiText("Ver detalhes")}
            }
        }
    }
    NavigableList(Modifier.fillMaxSize().padding(horizontal=LayoutSpacing.inset),navigationId="queue",state=queueListState) {
        item {PageTitle("Fila de downloads","Acompanhe, organize e gerencie seus downloads.")}
        item {OutlinedTextField(query,{query=it},label={UiText("Buscar na fila")},singleLine=true,modifier=Modifier.fillMaxWidth().testTag("queue-search"))}
        item {Row(Modifier.fillMaxWidth(),verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.spacedBy(LayoutSpacing.controls)) {
            Select("Estado",stateFilter,queueFilters,Modifier.weight(1f)){stateFilter=it}
            TextButton(onClick={query="";stateFilter="Todos"}){UiText("Limpar filtros")}
        }}
        item {Row(Modifier.fillMaxWidth(),verticalAlignment=Alignment.CenterVertically) {
            Select("Ordenar pendentes",queueOrder,queueOrders,Modifier.weight(1f)){queueOrder=it}
            TextButton(onClick={OndaStore.sortPending(queueOrder)}){UiText("Aplicar")}
        }}
        item {Text(space?.text(LocalUiLanguage.current) ?: translateUi("Calculando…",LocalUiLanguage.current),style=MaterialTheme.typography.bodySmall)}
        if(space?.low==true)item {UiText("Espaço possivelmente insuficiente",color=MaterialTheme.colorScheme.error)}
        item {UiText("Exibindo ${visible.size} de ${queue.size} itens.",style=MaterialTheme.typography.bodySmall)}
        if(visible.isEmpty() && queue.isNotEmpty())item {UiText("Nenhum item corresponde aos filtros.")}
        item {Row(Modifier.horizontalScroll(rememberScrollState())) {
            TextButton(onClick={selected=visible.filterNot {it.config.optBoolean("_immediate")}.map {it.id}.toSet()}) {UiText("Selecionar visíveis")}
            TextButton(onClick={OndaStore.remove(selected);selected=emptySet()}) {UiText("Remover selecionados")}
            TextButton(onClick={clear=true}) {UiText("Limpar fila")}
            TextButton(onClick={OndaStore.retry(selected)}) {UiText("Tentar novamente")}
            TextButton(enabled=metadataUris.isNotEmpty(),onClick={metadataBatch=metadataUris}) {UiText("Editar metadados")}
        }}
        item {UiText("Concluídos: $completed/${queue.size} · Restantes: ${queue.size-completed}",style=MaterialTheme.typography.labelMedium,modifier=Modifier.testTag("queue-count"))}
        item {UiText("Tempo decorrido: ${queueDuration(queueTimes.elapsed)} · Tempo restante: $remainingTime",style=MaterialTheme.typography.labelSmall,modifier=Modifier.testTag("queue-time"))}
        if(actionsAtTop)item {queueActions()}
        if(adding)item {LinearProgressIndicator(Modifier.fillMaxWidth())}
        item {QueueDisplayControls(settings)}
        items(visible,key={it.id}) {item->
            LaunchedEffect(item.id,complete) {if(complete && item.config.optJSONObject("queue_info")?.cleanString("cover_url").isNullOrBlank())vm.loadQueueInformation(item)}
            val immediate=item.config.optBoolean("_immediate")
            val cardModifier=Modifier.fillMaxWidth().let {base->if(immediate) base else base.toggleable(value=item.id in selected,role=Role.Checkbox,onValueChange={checked->selected=if(checked) selected+item.id else selected-item.id})}
            ElevatedCard(cardModifier.a11yState(if(immediate) item.state else if(item.id in selected) "Selecionado" else "Não selecionado").testTag("queue-card-${item.id}")) {
            Column(Modifier.padding(cardPadding),verticalArrangement=Arrangement.spacedBy(LayoutSpacing.text)) {
                Row(verticalAlignment=Alignment.CenterVertically) {
                    if(item.state=="Pendente")QueueDragHandle(item,queueListState)
                    if(!immediate) Checkbox(item.id in selected,null,modifier=Modifier.padding(end=LayoutSpacing.checkboxLabel))
                    if(complete)QueueTrackInformation(item,cardSize,Modifier.weight(1f))
                    else Text(item.title,Modifier.weight(1f),maxLines=1,overflow=androidx.compose.ui.text.style.TextOverflow.Ellipsis,style=MaterialTheme.typography.bodyMedium)
                }
                if((complete || item.id in selected) && item.state !in listOf("Baixando","Aguardando escolha")) Row {
                    TextButton(enabled=item.state=="Pendente",onClick={OndaStore.move(item.id,-1)}){AccessibleSymbol("↑","Mover ${item.title} para cima")}
                    TextButton(enabled=item.state=="Pendente",onClick={OndaStore.move(item.id,1)}){AccessibleSymbol("↓","Mover ${item.title} para baixo")}
                    TextButton(onClick={OndaStore.move(item.id,0)}){UiText("Próximo")}
                    if(immediate) TextButton(onClick={OndaStore.remove(setOf(item.id))},enabled=item.id!=active && item.state !in listOf("Baixando","Aguardando escolha")){UiText("Remover")}
                }
                if(immediate && item.state=="Erro") TextButton(onClick={OndaStore.retry(setOf(item.id))}) {UiText("Tentar novamente")}
                if(item.state=="Erro" && item.message.contains("Nenhuma versão suficientemente compatível",ignoreCase=true)) {
                    TextButton(onClick={OndaStore.retryWithVersionChoice(item.id)}) {UiText("Escolher versão")}
                }
                MetadataPlatformBadge(item.config.optJSONObject("catalog_record") ?: item.config.optJSONObject("queue_info"))
                UiText("${item.config.optString("mode").uppercase()} · ${item.state}",style=MaterialTheme.typography.labelMedium)
                UiText(queueActivity(item,running,settings,connected,pauseReason),style=MaterialTheme.typography.bodySmall)
                if(item.state in listOf("Baixando","Aguardando escolha")) LinearProgressIndicator(progress={item.progress/100},modifier=Modifier.fillMaxWidth().padding(vertical=6.dp))
                if(item.message.isNotBlank() && (complete || item.state=="Erro")) UiText(item.message,style=MaterialTheme.typography.bodySmall,maxLines=if(small)1 else 3)
            }
        }}
        if(!actionsAtTop)item {queueActions()}
        if(showLogs) item {UiText(logs.takeLast(35).joinToString("\n"),style=MaterialTheme.typography.bodySmall)}
    }
    if(clear) AlertDialog(containerColor=ondaDialogContainerColor(),onDismissRequest={clear=false},title={UiText("Limpar fila?")},text={UiText("Remove todos os itens, exceto o download em andamento. Seus arquivos são preservados.")},confirmButton={TextButton(onClick={OndaStore.remove(queue.map {it.id}.toSet());clear=false}){UiText("Limpar")}},dismissButton={TextButton(onClick={clear=false}){UiText("Cancelar")}})
}

fun historySupportsEffects(item: HistoryItem):Boolean {
    val formats=setOf("mp3","m4a","aac","flac","wav","ogg","opus","wma","aiff","alac","mp4","mkv","webm","mov","m4v","video","original")
    return item.mode.lowercase() in formats || item.title.substringAfterLast('.',"").lowercase() in formats
}

fun mediaClock(seconds:Long):String {val value=seconds.coerceAtLeast(0);return "%d:%02d".format(value/60,value%60)}

@Composable fun PlayerControls(vm: OndaViewModel) {
    var position by remember {mutableStateOf(0f)}
    var duration by remember {mutableStateOf(1f)}
    var playing by remember {mutableStateOf(false)}
    val lifecycleOwner=LocalLifecycleOwner.current
    LaunchedEffect(vm,lifecycleOwner) {
        lifecycleOwner.lifecycle.repeatOnLifecycle(Lifecycle.State.STARTED) {
            while(true) {position=vm.player.currentPosition/1000f;duration=(vm.player.duration/1000f).coerceAtLeast(1f);playing=vm.player.isPlaying;delay(200)}
        }
    }
    RoundSlider(value=position.coerceIn(0f,duration),onValueChange={vm.player.seekTo((it*1000).toLong())},valueRange=0f..duration,modifier=Modifier.a11yLabel("Posição da prévia","${mediaClock(position.toLong())} de ${mediaClock(duration.toLong())}"))
    Row(verticalAlignment=Alignment.CenterVertically) {TextButton(onClick={if(playing) vm.player.pause() else vm.player.play()}){UiText(if(playing) "Pausar" else "Reproduzir")};UiText("${mediaClock(position.toLong())} / ${mediaClock(duration.toLong())}",style=MaterialTheme.typography.bodySmall);TextButton(onClick={vm.stopPreview()}){UiText("Parar")}}
}

@Composable fun EffectsPage(vm: OndaViewModel,heading:Boolean=true) {
    var lyrics by remember {mutableStateOf<List<Pair<Double,String>>>(emptyList())}
    var lyricLine by remember {mutableStateOf("")}
    var lyricsName by remember {mutableStateOf("")}
    val lyricSettings by OndaStore.settings.collectAsStateWithLifecycle()
    val pickLyrics=rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) {uri->if(uri!=null)vm.importLocal(uri,"lyrics",dialog=true) {file->
        vm.operation("lyrics_read",JSONObject().put("source",file.absolutePath),dialog=true) {result->
            val parsed=result.optJSONArray("lines")?.let {rows->(0 until rows.length()).map {index->rows.getJSONArray(index).let {it.getDouble(0) to it.getString(1)}}} ?: emptyList()
            val name=file.name.replaceFirst(Regex("^lyrics-[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}-"),"")
            file.delete()
            if(parsed.isEmpty())vm.showNotice("Importar letra LRC","Nenhum tempo válido na letra LRC.")
            else {
                lyrics=parsed;lyricsName=name
                OndaStore.saveSettings(JSONObject(OndaStore.settings.value.toString()).put("synced_lyrics",true))
            }
        }
    }}
    LaunchedEffect(lyrics,lyricSettings.optBoolean("synced_lyrics")) {
        if(!lyricSettings.optBoolean("synced_lyrics")) {lyricLine="";return@LaunchedEffect}
        while(true) {lyricLine=lyrics.lastOrNull {it.first<=vm.lyricsPosition()}?.second ?: "";delay(200)}
    }
    var source by rememberSaveable {mutableStateOf("")}
    LaunchedEffect(source) {lyrics=emptyList();lyricLine="";lyricsName=""}
    var speed by rememberSaveable {mutableFloatStateOf(85f)}
    var reverb by rememberSaveable {mutableFloatStateOf(25f)}
    var pitch by rememberSaveable {mutableStateOf(false)}
    var start by rememberSaveable {mutableFloatStateOf(0f)}
    var duration by rememberSaveable {mutableFloatStateOf(1f)}
    var format by rememberSaveable {mutableStateOf("mp3")}
    val liveEffects by vm.effectsPreviewEnabled.collectAsStateWithLifecycle()
    LaunchedEffect(source,speed,reverb,pitch,start) {
        if(liveEffects && source.isNotBlank()) vm.previewEffects(source,speed.toInt(),reverb.toInt(),pitch,start.toInt())
    }
    val incomingSource by vm.effectsSource.collectAsStateWithLifecycle()
    LaunchedEffect(incomingSource) {
        if(incomingSource.isNotBlank() && incomingSource!=source) {
            source=incomingSource;start=0f;duration=1f
            vm.operation("probe",JSONObject().put("source",source)){duration=it.optJSONObject("format")?.optDouble("duration",1.0)?.toFloat() ?: 1f}
        }
    }
    val choose=rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) {uri->if(uri!=null) {
        source=""
        vm.importLocal(uri,"audio") {file->
            source=file.absolutePath;vm.effectsSource.value=source
            vm.operation("probe",JSONObject().put("source",source)){duration=it.optJSONObject("format")?.optDouble("duration",1.0)?.toFloat() ?: 1f;start=0f}
        }
    }}
    fun effectName(): String {val name=if(speed<100) "Slowed" else if(speed>100) "Sped Up" else "";return if(reverb>0) if(name.isNotEmpty()) "$name + Reverb" else "Reverb" else name}
    var effectsQuery by rememberSaveable {mutableStateOf("")}
    var effectsResults by remember {mutableStateOf<List<JSONObject>>(emptyList())}
    val searchBusy by vm.busy.collectAsStateWithLifecycle()
    Column(Modifier.verticalScroll(rememberScrollState()).padding(LayoutSpacing.inset),verticalArrangement=Arrangement.spacedBy(LayoutSpacing.controls)) {
        if(heading)ToolHeading("Efeitos")
        ToolCard(Modifier.testTag("effects-source-card")) {
            UiText("Sua música",style=MaterialTheme.typography.titleMedium,fontWeight=FontWeight.Bold)
            UiText("Desacelere ou acelere sua música. Adicione reverb se quiser.",style=MaterialTheme.typography.bodySmall,color=MaterialTheme.colorScheme.onSurfaceVariant)
            OutlinedButton(enabled=!searchBusy,onClick={choose.launch(arrayOf("audio/*"))},modifier=Modifier.fillMaxWidth()){UiText(if(source.isBlank()) "Abrir áudio" else importedAudioName(source),maxLines=2)}
            OutlinedTextField(effectsQuery,{effectsQuery=it},label={UiText("Pesquise uma música ou cole um link")},singleLine=true,modifier=Modifier.fillMaxWidth())
            OutlinedButton(enabled=searchBusy || effectsQuery.isNotBlank(),onClick={
                if(searchBusy)vm.cancel() else
                vm.operation("effects_search",JSONObject().put("query",effectsQuery).put("provider",OndaStore.settings.value.optString("catalog_provider","Deezer")),dialog=false) {result->
                    effectsResults=result.optJSONArray("tracks")?.let {array->(0 until array.length()).map {array.getJSONObject(it)}} ?: emptyList()
                }
            }){UiText(if(searchBusy) "Cancelar" else "Pesquisar")}
            if(searchBusy)LinearProgressIndicator(Modifier.fillMaxWidth())
            effectsResults.forEach {record->
                OutlinedButton(enabled=!searchBusy,onClick={
                    vm.operation("effects_load",JSONObject().put("record",record),dialog=false) {result->
                        vm.stopPreview();vm.effectsSource.value=result.getString("source");effectsResults=emptyList()
                    }
                },modifier=Modifier.fillMaxWidth()){Text(record.optString("title")+" · "+record.stringList("artists"))}
            }
            LyricsButton(vm,source,{vm.lyricsPosition()},duration.toDouble(),{start=it.toFloat();if(liveEffects)vm.previewEffects(source,speed.toInt(),reverb.toInt(),pitch,start.toInt())},{if(liveEffects)vm.stopPreview() else vm.previewEffects(source,speed.toInt(),reverb.toInt(),pitch,start.toInt())})
            if(lyricsName.isNotBlank())Text(lyricsName,style=MaterialTheme.typography.bodySmall)
            if(lyricLine.isNotBlank())Text(lyricLine,style=MaterialTheme.typography.titleMedium)
        }
        ToolCard(Modifier.testTag("effects-adjustments-card")) {
            UiText("Ajustes",style=MaterialTheme.typography.titleMedium,fontWeight=FontWeight.Bold)
            val presets=remember {linkedMapOf("Original" to (100f to 0f),"Slowed leve" to (90f to 0f),"Slowed intenso" to (75f to 0f),"Sped Up leve" to (115f to 0f),"Sped Up intenso" to (130f to 0f),"Sped Up + Reverb" to (120f to 25f),"Só Reverb" to (100f to 30f),"Clássico" to (85f to 25f),"Atmosférico" to (75f to 50f))}
            val preset=presets.entries.firstOrNull {it.value.first.toInt()==speed.toInt() && it.value.second.toInt()==reverb.toInt()}?.key ?: "Personalizado"
            Select("Preset",preset,presets.keys.toList()) {val value=presets.getValue(it);speed=value.first;reverb=value.second}
            UiText("Velocidade · ${speed.toInt()}% · ${if(speed<100) "Slowed" else if(speed>100) "Sped Up" else "original"}",fontWeight=FontWeight.Bold)
            RoundSlider(speed,{speed=it.toInt().toFloat()},valueRange=50f..150f,modifier=Modifier.testTag("effects-speed").a11yLabel("Velocidade da música","${speed.toInt()}%"))
            UiText("Reverb · ${reverb.toInt()}%${if(reverb==0f) " · desligado" else ""}",fontWeight=FontWeight.Bold)
            RoundSlider(reverb,{reverb=it.toInt().toFloat()},valueRange=0f..100f,modifier=Modifier.testTag("effects-reverb").a11yLabel("Intensidade do reverb","${reverb.toInt()}%"))
            ToolSwitch("Manter tom",pitch,"Preservar o tom ao alterar a velocidade"){pitch=it}
        }
        ToolCard(Modifier.testTag("effects-preview-card")) {
            UiText("Prévia",style=MaterialTheme.typography.titleMedium,fontWeight=FontWeight.Bold)
            UiText("Posição na música · ${mediaClock(start.toLong())} / ${mediaClock(duration.toLong())}")
            RoundSlider(start.coerceIn(0f,duration.coerceAtLeast(1f)),{start=it},valueRange=0f..duration.coerceAtLeast(1f),modifier=Modifier.a11yLabel("Posição inicial da prévia","${mediaClock(start.toLong())} de ${mediaClock(duration.toLong())}"))
            Column(Modifier.fillMaxWidth(),verticalArrangement=Arrangement.spacedBy(8.dp)) {
            TextButton(onClick={vm.stopPreview();vm.preview(source,OndaStore.settings.value.optInt("effects_preview",25),start.toInt())},enabled=source.isNotBlank(),modifier=Modifier.fillMaxWidth()){UiText("Ouvir original")}
            Button(onClick={vm.previewEffects(source,speed.toInt(),reverb.toInt(),pitch,start.toInt())},enabled=source.isNotBlank(),modifier=Modifier.fillMaxWidth()){UiText("Ouvir com efeitos")}
        }
        val previewUrl by vm.previewUrl.collectAsStateWithLifecycle()
        if(previewUrl.isNotBlank()) PlayerControls(vm)
        UiText("Arraste a barra para escolher o trecho. A duração da prévia pode ser alterada em Configurações. Ajuste os efeitos enquanto ouve.",style=MaterialTheme.typography.bodySmall)
        }
        ToolCard(Modifier.testTag("effects-export-card")) {
            UiText("Exportar",style=MaterialTheme.typography.titleMedium,fontWeight=FontWeight.Bold)
            Select("Salvar como",format.uppercase(),listOf("MP3","M4A","FLAC","WAV")){format=it.lowercase()}
            Button(onClick={
                val name=importedAudioName(source).substringBeforeLast('.')
                val suffix=effectName().let {if(it.isBlank()) "" else " - $it"}
                val output=File(OndaStore.config().getString("folder"),"$name$suffix.$format")
                val config=OndaStore.config().put("source",source).put("output",output.absolutePath).put("speed",speed.toInt()).put("reverb",reverb.toInt()).put("keep_pitch",pitch)
                config.put("_operation","effects")
                val id=OndaStore.enqueue(source,output.name,extra=config)
                DownloadService.start(OndaStore.context,id)
                vm.status.value="Exportação adicionada à fila. Acompanhe na aba Fila."
            },enabled=source.isNotBlank(),modifier=Modifier.fillMaxWidth()){UiText("Exportar música")}
        }
    }
}

fun importedAudioName(path: String): String = File(path).name.replaceFirst(Regex("^audio-[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}-"),"")
