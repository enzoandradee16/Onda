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
        volumeControlStream=android.media.AudioManager.STREAM_MUSIC
        receive(intent)
        setContent { OndaApp(model) }
    }
    override fun onStop() {model.savePlaybackSession();model.jukebox.savePlaybackSession();super.onStop()}
    override fun onResume() {super.onResume();model.restartReturned()}
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
        if(intent?.getBooleanExtra("open_effects",false)==true) {model.playbackMode.value=0;model.effectsNavigation.value=true;intent.removeExtra("open_effects")}
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
    val playbackMode by vm.playbackMode.collectAsStateWithLifecycle()
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
    val effectsRequested by vm.effectsNavigation.collectAsStateWithLifecycle()
    var metadataUri by rememberSaveable {mutableStateOf<String?>(null)}
    var showSettings by rememberSaveable { mutableStateOf(false) }
    var showAppearance by rememberSaveable { mutableStateOf(false) }
    LaunchedEffect(effectsRequested) {if(effectsRequested){tab="Efeitos";showSettings=false;vm.effectsNavigation.value=false}}
    var settingsCategory by rememberSaveable { mutableStateOf("Geral") }
    var youtubeSession by rememberSaveable {mutableStateOf(false)}
    var showLicenses by rememberSaveable {mutableStateOf(false)}
    val pages=rememberSaveableStateHolder()
    var showLinks by rememberSaveable {mutableStateOf(false)}
    val preferences=OndaStore.context.getSharedPreferences("preferences",0)
    var welcome by remember { mutableStateOf(!preferences.getBoolean("welcome_seen",false)) }
    val permission=rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) {}
    BackHandler(enabled=(showLinks || tab!=homeTab) && !showSettings && !showAppearance && !youtubeSession && !showLicenses && !welcome && question==null && notice==null) {
        if(showLinks)showLinks=false else tab=if(tab in listOf("Imagens","Conversor de vídeos","Playlists / Álbuns","Histórico","Metadados")) "Mais" else homeTab
    }
    LaunchedEffect(Unit) { if(Build.VERSION.SDK_INT>=33) permission.launch(Manifest.permission.POST_NOTIFICATIONS) }
    LaunchedEffect(shared) { if(shared.isNotBlank()) {tab="Fila";showLinks=true} }
    LaunchedEffect(tab) {
        if(tab!="Efeitos") {
            vm.stopTransientPreview()
        }
    }
    val typography=remember(settings.optString("interface_font"),settings.optString("interface_font_size")) {interfaceTypography(settings.optString("interface_font",DEFAULT_INTERFACE_FONT),settings.optString("interface_font_size","100%"))}
    LocalizedTheme(language=settings.optString("language","pt-BR"),colorScheme=scheme,typography=typography,spacing=settings.optString("interface_spacing","Padrão")) {
        Scaffold(
            topBar={OndaAppBar(onAppearance={showAppearance=true},onSettings={settingsCategory="Geral";showSettings=true})},
            bottomBar={Column {
                AndroidPlaybackSurface(vm)
                OndaBottomNavigation(if(showSettings)"Mais" else tab,tabs) {destination->showSettings=false;tab=destination}
            }},
            floatingActionButton={if(!showSettings && (tab=="Fila" || tab=="Links e fila"))FloatingActionButton(onClick={showLinks=true},containerColor=MaterialTheme.colorScheme.primary,shape=RoundedCornerShape(50)) {OndaIcon("add","Adicionar links",Modifier.size(24.dp))}}
        ) { padding ->
            Column(Modifier.fillMaxSize().padding(padding)) {
                if(busy && !tools.running) LinearProgressIndicator(Modifier.fillMaxWidth())
                if(tools.running)ToolCard(Modifier.padding(horizontal=LayoutSpacing.inset,vertical=8.dp).testTag("tools-preparation-progress")) {
                    if(!tools.message.trim().startsWith("Preparando",ignoreCase=true))UiText(tools.message,style=MaterialTheme.typography.bodyMedium)
                    if(tools.total>0) {
                        val progress=(tools.done.toFloat()/tools.total).coerceIn(0f,1f)
                        LinearProgressIndicator(progress={progress},modifier=Modifier.fillMaxWidth())
                        UiText("${(progress*100).toInt()}%",style=MaterialTheme.typography.bodySmall)
                    } else LinearProgressIndicator(Modifier.fillMaxWidth())
                }
                TopStatusNotice(status,statusVisible && !(busy && status.trim().startsWith("Preparando",ignoreCase=true)),busy,settings.optBoolean("notice_animation",true),onCancel={vm.cancel()},onDismiss={statusVisible=false},cancellable=!tools.running && (showSettings || tab !in listOf("Pesquisar","Efeitos","Playlists / Álbuns")),onOpenSettings={category->if(category=="Sessão do YouTube")youtubeSession=true else {settingsCategory=category;showSettings=true}})
                if(showSettings)Box(Modifier.weight(1f).fillMaxWidth()){SettingsWindow(vm,initialCategory=settingsCategory){showSettings=false}} else SwipePageHost(current=tab,pages=mainDestinations(tabs,bottomBarOrder(settings)),onNavigate={tab=it},modifier=Modifier.weight(1f).fillMaxWidth()) {
                    pages.SaveableStateProvider(tab) {when(tab) {
                        "Pesquisar"->SearchPage(vm,onConnectSpotify={settingsCategory="Contas";showSettings=true})
                        "Links e fila","Fila"->DownloadsHome(vm)
                        "Mais"->MorePage(tabs,tabGroupOrder(settings),onNavigate={tab=it},onYouTube={youtubeSession=true},onLicenses={showLicenses=true},onFailures={OndaStore.failureSummary.value=OndaStore.items.value.filter {it.state=="Erro"}.map {it.id}.takeIf {it.isNotEmpty()}})
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
        if(question==null && notice==null && !showSettings && !showAppearance && !youtubeSession && !showLicenses && !welcome) {
            failureIds?.let {FailureSummaryWindow(it,vm){OndaStore.failureSummary.value=null}}
        }
        ClipboardDownloadPrompt(settings.optBoolean("clipboard_links",true),!busy && question==null && notice==null && !showSettings && !showAppearance && !youtubeSession && !showLicenses && !welcome && !showLinks,onAdd={candidate->
            if(candidate.optBoolean("collection"))vm.loadCollection(candidate.getString("url"),OndaStore.collectionOptions(),queueOnly=true)
            else vm.enqueueLinks(listOf(candidate.getString("url")),false)
            tab="Fila"
        }) {candidate->
            if(candidate.optBoolean("collection"))vm.loadCollection(candidate.getString("url"),OndaStore.collectionOptions(),startDownload=true)
            else vm.enqueueLinks(listOf(candidate.getString("url")),true)
        }
        question?.let { ChoiceWindow(it,vm) }
        if(showAppearance) AppearanceWindow {showAppearance=false}
        if(youtubeSession) YouTubeSessionWindow {youtubeSession=false}
        if(showLicenses) LicensesWindow {showLicenses=false}
        if(welcome) AlertDialog(containerColor=ondaDialogContainerColor(),onDismissRequest={preferences.edit().putBoolean("welcome_seen",true).apply();welcome=false},title={UiText("Bem-vindo ao Onda")},
            text={UiText("Ajuste o básico para começar. Você pode fechar esta janela e configurar tudo depois.")},
            confirmButton={TextButton(onClick={preferences.edit().putBoolean("welcome_seen",true).apply();welcome=false;settingsCategory="Geral";showSettings=true}){UiText("Configurações")}},
            dismissButton={TextButton(onClick={preferences.edit().putBoolean("welcome_seen",true).apply();welcome=false}){UiText("Agora não")}})
        OnlineImageGallery(vm)
        notice?.let {current->
            val destination=noticeDestination(current.message)
            AlertDialog(containerColor=ondaDialogContainerColor(),onDismissRequest=vm::dismissNotice,title={UiText(current.title)},
                text={Column(Modifier.heightIn(max=320.dp).verticalScroll(rememberScrollState())){if(current.error)UiErrorText(current.message) else UiText(current.message)}},
                confirmButton={TextButton(onClick=vm::dismissNotice){UiText("OK")}},
                dismissButton={if(destination!=null)TextButton(onClick={
                    vm.dismissNotice()
                    if(destination=="Sessão do YouTube")youtubeSession=true else {settingsCategory=destination;showSettings=true}
                }){UiText(if(destination=="Sessão do YouTube")"Sessão do YouTube" else "Configurações")}})
        }
    }
}
fun tabLabel(tab: String)=when(tab) {"Conversor de vídeos"->"Conversor";"Links e fila"->"Links";"Metadados"->"Editar metadados";"Pesquisar"->"Pesquisar músicas";"Efeitos"->"Reprodução";"Playlists / Álbuns"->"Álbuns e playlists";else->tab}

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
            } catch(error:Exception) {vm.showNotice(if(now) "Baixar agora" else "Adicionar à fila",uiExceptionMessage(error,"Não foi possível adicionar a música."))}
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

@Composable fun TrackCard(original: JSONObject, vm: OndaViewModel, onDownload:()->Unit, onCompare:(()->Unit)?=null) {
    val record=rememberCardMetadata(original,vm)
    val cardSettings by OndaStore.settings.collectAsStateWithLifecycle()
    val cardSize=cardSettings.optString("catalog_card_size","Grande")
    val coverSide=when(cardSize){"Pequeno"->56.dp;"Médio"->76.dp;else->94.dp}

    val playing by vm.previewActive.collectAsStateWithLifecycle()
    val playingUrl by vm.previewUrl.collectAsStateWithLifecycle()
    val releaseDate=record.cleanString("release_date")
    val url=record.cleanString("preview_url")
    val thisPlaying=playing && playingUrl==url
    var actions by remember {mutableStateOf(false)}
    Surface(Modifier.fillMaxWidth().onSecondaryClick(record.cleanString("source_url")){actions=true},shape=RoundedCornerShape(18.dp),color=MaterialTheme.colorScheme.surfaceContainerLow) {
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
                    if(albumReleaseText(record).isNotBlank())DropdownMenuItem(text={Text(albumReleaseText(record))},enabled=false,onClick={})
                    DropdownMenuItem(text={MetadataPlatformBadge(record)},enabled=false,onClick={})
                }
                    }
                }
                Text(record.stringList("artists"),style=MaterialTheme.typography.bodySmall,color=MaterialTheme.colorScheme.onSurfaceVariant,maxLines=1,overflow=androidx.compose.ui.text.style.TextOverflow.Ellipsis)
                AlbumDateLabel(record)
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
        if(canPreviewOnlineImages(OndaStore.config(settings).put("url",link)))item {OnlineImagePreviewButton(vm,link)}
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
    val initialControls=remember(vm){vm.effectsControlSnapshot()}
    val compactMode by vm.compactPlaybackMode.collectAsStateWithLifecycle()
    val lyricSettings by OndaStore.settings.collectAsStateWithLifecycle()
    var source by rememberSaveable {mutableStateOf("")}
    val lyricCache by vm.lyricsCache.collectAsStateWithLifecycle()
    val infos by vm.effectsInfo.collectAsStateWithLifecycle()
    var speed by rememberSaveable {mutableFloatStateOf(initialControls.first.toFloat())}
    var reverb by rememberSaveable {mutableFloatStateOf(initialControls.second.toFloat())}
    var pitch by rememberSaveable {mutableStateOf(initialControls.third)}
    var duration by rememberSaveable {mutableFloatStateOf(0f)}
    var format by rememberSaveable {mutableStateOf("mp3")}
    val liveEffects by vm.effectsPreviewEnabled.collectAsStateWithLifecycle()
    val preparing by vm.effectsPreparing.collectAsStateWithLifecycle()
    val playing by vm.previewActive.collectAsStateWithLifecycle()
    val position by vm.effectsPosition.collectAsStateWithLifecycle()
    val volume by vm.effectsVolume.collectAsStateWithLifecycle()
    val playlist by vm.effectsPlaylist.collectAsStateWithLifecycle()
    val ended by vm.effectsEnded.collectAsStateWithLifecycle()
    fun seek(seconds:Double) {vm.seekEffectsPlayback(seconds,source,speed.toInt(),reverb.toInt(),pitch)}
    fun toggle() {vm.toggleEffectsPlayback(source,speed.toInt(),reverb.toInt(),pitch)}
    fun moveTrack(index:Int) {vm.playEffectsQueueTrack(index)}
    LaunchedEffect(speed,reverb,pitch) {
        val changed=!vm.effectsControlsMatch(speed.toInt(),reverb.toInt(),pitch)
        vm.rememberEffectsControls(speed.toInt(),reverb.toInt(),pitch)
        if(changed && liveEffects && source.isNotBlank()) vm.previewEffects(source,speed.toInt(),reverb.toInt(),pitch,position,fullTrack=true)
    }
    val incomingSource by vm.effectsSource.collectAsStateWithLifecycle()
    LaunchedEffect(incomingSource) {
        if(incomingSource.isBlank()) {vm.stopEffectsPlayback();source="";duration=0f}
        if(incomingSource.isNotBlank() && incomingSource!=source) {
            source=incomingSource;duration=0f
            vm.selectEffectsSource(source,0.0)
            vm.loadEffectsInfo(listOf(source))
        }
    }
    LaunchedEffect(source,infos[source]) {
        infos[source]?.let {info->
            duration=info.optDouble("duration",0.0).toFloat();vm.selectEffectsSource(source,duration.toDouble())
        }
    }
    val choose=rememberLauncherForActivityResult(ActivityResultContracts.OpenMultipleDocuments()) {uris->if(uris.isNotEmpty()) {
        vm.importConversionBatch(uris) {files->
            vm.appendEffectsFiles(files)
            if(source.isBlank())files.firstOrNull()?.let {vm.effectsSource.value=it}
        }
    }}
    fun effectName(): String {val name=if(speed<100) "Slowed" else if(speed>100) "Sped Up" else "";return if(reverb>0) if(name.isNotEmpty()) "$name + Reverb" else "Reverb" else name}
    var effectsQuery by rememberSaveable {mutableStateOf("")}
    var effectsResults by remember {mutableStateOf<List<JSONObject>>(emptyList())}
    val searchBusy by vm.busy.collectAsStateWithLifecycle()
    val collectionBusy by vm.loadingPlaybackCollection.collectAsStateWithLifecycle()
    fun searchEffects() {
        if(collectionBusy)vm.cancelPlaybackCollection() else if(searchBusy)vm.cancel() else if(effectsQuery.isNotBlank())vm.operation("effects_search",JSONObject().put("query",effectsQuery).put("provider",OndaStore.settings.value.optString("catalog_provider","Deezer"))) {result->
            val rows=result.optJSONArray("tracks")?.objects().orEmpty()
            if(result.optBoolean("is_collection")){effectsResults=emptyList();vm.addPlaybackCollection(rows,false)}else effectsResults=rows
        }
    }
    Column(Modifier.fillMaxSize()) {
    Column(Modifier.weight(1f).verticalScroll(rememberScrollState()).padding(LayoutSpacing.inset),verticalArrangement=Arrangement.spacedBy(LayoutSpacing.section)) {
        if(heading)ToolHeading("Efeitos")
        ToolCard(Modifier.testTag("effects-source-card")) {
            UiText("Suas músicas",style=MaterialTheme.typography.titleMedium,fontWeight=FontWeight.Bold)
            UiText("Ajuste velocidade e reverb das suas músicas, álbuns e playlists.",style=MaterialTheme.typography.bodySmall,color=MaterialTheme.colorScheme.onSurfaceVariant)
            OutlinedTextField(effectsQuery,{effectsQuery=it},label={UiText(PLAYBACK_INPUT_HINT)},singleLine=true,modifier=Modifier.fillMaxWidth(),keyboardOptions=KeyboardOptions(imeAction=ImeAction.Search),keyboardActions=KeyboardActions(onSearch={searchEffects()}))
            Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(LayoutSpacing.controls)) {
                OutlinedButton(enabled=searchBusy || collectionBusy || effectsQuery.isNotBlank(),onClick=::searchEffects){UiText(if(searchBusy || collectionBusy) "Cancelar" else "Pesquisar")}
                OutlinedButton(enabled=!searchBusy && !collectionBusy,onClick={choose.launch(arrayOf("audio/*"))}){UiText("Abrir arquivo")}
            }
            if(effectsResults.isNotEmpty())Row(Modifier.fillMaxWidth(),verticalAlignment=Alignment.CenterVertically){UiText("Resultados",Modifier.weight(1f));IconButton(onClick={effectsResults=emptyList()}){OndaIcon("close","Fechar pesquisa",Modifier.size(22.dp))}}
            effectsResults.forEach {record->
                fun load(play:Boolean) {vm.operation("effects_load",JSONObject().put("record",record)) {result->val path=result.getString("source");vm.appendEffectsRecord(path,result.optJSONObject("record") ?: record);if(play)vm.playEffectsQueueTrack(vm.effectsPlaylist.value.indexOf(path))}}
                PlaybackSearchResult(record,vm,!searchBusy&&!collectionBusy,{load(true)},{load(false)})
            }
        }
        infos[source]?.let {info->EffectsTrackInformation(info,source){
            if(info.has("error")) {
                UiErrorText(info.optString("error"),color=MaterialTheme.colorScheme.error)
                TextButton(onClick={vm.loadEffectsInfo(listOf(source),retryErrors=true)},modifier=Modifier.testTag("effects-info-retry")){UiText("Tentar novamente")}
            }
            if(compactMode==1&&source.isNotBlank())OutlinedButton(onClick=::toggle,enabled=duration>0f,modifier=Modifier.testTag("effects-page-play")){UiText("Reproduzir em Efeitos")}
        }}
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
        if(lyricSettings.optBoolean("synced_lyrics")) {
            val lines=lyricCache[source].orEmpty()
            val timeline=remember(lines){LyricTimeline(lines)}
            val index=timeline.activeIndex(position)
            if(index>=0)Text(timeline.verses[index].plain,modifier=Modifier.fillMaxWidth().lyricAnimation(index,lyricSettings.optString("lyrics_animation","Suave")),style=MaterialTheme.typography.titleMedium,color=MaterialTheme.colorScheme.primary)
        }
    }

    }
}

fun importedAudioName(path: String): String = File(path).name.replaceFirst(Regex("^(?:audio|conversion-batch)-[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}-"),"")
