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
    override fun onStop() {super.onStop();if(!OndaStore.settings.value.optBoolean("jukebox_background"))model.jukebox.pause()}
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
    val notice by vm.dialogNotice.collectAsStateWithLifecycle()
    val status by vm.status.collectAsStateWithLifecycle()
    var statusVisible by rememberStatusNotice(status,busy,settings.optString("notice_duration","Após 3 segundos"))
    val effectsSource by vm.effectsSource.collectAsStateWithLifecycle()
    val shared by OndaStore.sharedLink.collectAsStateWithLifecycle()
    val pureBlack=settings.optString("theme")=="Preto puro"
    val dark=when(settings.optString("theme")) { "Claro"->false; "Escuro","Preto puro","Alto contraste"->true; else->isSystemInDarkTheme() }
    val palette=if(dark) accents else lightAccents
    val accent=Color(palette[settings.optString("accent")] ?: palette.getValue("Verde-Água"))
    val baseScheme=if(dark) darkColorScheme(primary=accent,background=Color(0xFF0E131B),surface=Color(0xFF161E29),onPrimary=Color(0xFF10171F)) else lightColorScheme(primary=accent)
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
    val homeTab=tabs.optString(0,"Pesquisar")
    var tab by rememberSaveable { mutableStateOf(homeTab) }
    LaunchedEffect(tab,tabs.toString()) {if((0 until tabs.length()).none {tabs.getString(it)==tab}) tab=homeTab}
    val queueRequested by vm.queueNavigation.collectAsStateWithLifecycle()
    LaunchedEffect(queueRequested) {if(queueRequested) {tab="Fila";vm.queueNavigation.value=false}}
    var metadataUri by rememberSaveable {mutableStateOf<String?>(null)}
    var showSettings by rememberSaveable { mutableStateOf(false) }
    var settingsCategory by rememberSaveable { mutableStateOf("Geral") }
    var youtubeSession by rememberSaveable {mutableStateOf(false)}
    var showLicenses by rememberSaveable {mutableStateOf(false)}
    val drawer=rememberDrawerState(DrawerValue.Closed)
    val scope=rememberCoroutineScope()
    val pages=rememberSaveableStateHolder()
    val keyboard=LocalSoftwareKeyboardController.current
    val view=androidx.compose.ui.platform.LocalView.current
    val inputMethod=remember(view) {view.context.getSystemService(android.content.Context.INPUT_METHOD_SERVICE) as android.view.inputmethod.InputMethodManager}
    val currentTab by rememberUpdatedState(tab)
    var navigationPending by remember {mutableStateOf(false)}
    val keyboardBlocked by rememberUpdatedState(navigationPending || showSettings || youtubeSession || showLicenses || question!=null || notice!=null)
    fun navigateFromDrawer(action: ()->Unit) {
        if(navigationPending) return
        navigationPending=true
        scope.launch {
            try {drawer.close();action()} finally {navigationPending=false}
        }
    }
    LaunchedEffect(drawer,keyboard,view) {
        var opened=false
        var restoreKeyboard=false
        var inputTab=""
        snapshotFlow {drawer.currentValue to drawer.targetValue}.collect { (current,target)->
            if(!opened && (current==DrawerValue.Open || target==DrawerValue.Open)) {
                opened=true
                restoreKeyboard=inputMethod.isAcceptingText
                inputTab=currentTab
                keyboard?.hide()
            } else if(opened && current==DrawerValue.Closed && target==DrawerValue.Closed) {
                opened=false
                if(restoreKeyboard && inputTab==currentTab && !keyboardBlocked && inputMethod.isAcceptingText) {
                    withFrameNanos { }
                    if(inputTab==currentTab && !keyboardBlocked && inputMethod.isAcceptingText) keyboard?.show()
                }
                restoreKeyboard=false
            }
        }
    }

    val preferences=OndaStore.context.getSharedPreferences("preferences",0)
    var welcome by remember { mutableStateOf(!preferences.getBoolean("welcome_seen",false)) }
    val permission=rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) {}
    BackHandler(enabled=(drawer.isOpen || drawer.targetValue==DrawerValue.Open || tab!=homeTab) && !showSettings && !youtubeSession && !showLicenses && !welcome && question==null && notice==null) {
        if(drawer.isOpen || drawer.targetValue==DrawerValue.Open) scope.launch {drawer.close()} else tab=homeTab
    }
    LaunchedEffect(Unit) { if(Build.VERSION.SDK_INT>=33) permission.launch(Manifest.permission.POST_NOTIFICATIONS) }
    LaunchedEffect(shared) { if(shared.isNotBlank()) tab="Links e fila" }
    LaunchedEffect(effectsSource) {if(effectsSource.isNotBlank()) tab="Efeitos"}
    LaunchedEffect(tab) { if(!settings.optBoolean("keep_preview")) vm.stopPreview(!settings.optBoolean("jukebox_background")) }
    val typography=remember(settings.optString("interface_font"),settings.optString("interface_font_size")) {interfaceTypography(settings.optString("interface_font",DEFAULT_INTERFACE_FONT),settings.optString("interface_font_size","100%"))}
    LocalizedTheme(language=settings.optString("language","pt-BR"),colorScheme=scheme,typography=typography,spacing=settings.optString("interface_spacing","Padrão")) {
        ModalNavigationDrawer(drawerState=drawer,drawerContent={ModalDrawerSheet(Modifier.width(300.dp)) {
            Row(Modifier.fillMaxWidth().padding(20.dp),horizontalArrangement=Arrangement.Center,verticalAlignment=Alignment.CenterVertically) {OndaLogo(Modifier.size(36.dp).clip(RoundedCornerShape(25)));UiText("ONDA",style=MaterialTheme.typography.titleLarge,fontWeight=FontWeight.Bold,modifier=Modifier.padding(start=8.dp))}
            Column(Modifier.weight(1f).verticalScroll(rememberScrollState())) {
                for(index in 0 until tabs.length()) {val name=tabs.getString(index)
                    NavigationDrawerItem(label={UiText(tabLabel(name))},selected=tab==name,onClick={navigateFromDrawer {tab=name}},modifier=Modifier.padding(horizontal=10.dp).testTag("tab-$name"))
                }
                HorizontalDivider(Modifier.padding(12.dp))
                NavigationDrawerItem(label={UiText("Configurações")},selected=false,onClick={navigateFromDrawer {settingsCategory="Geral";showSettings=true}})
                NavigationDrawerItem(label={UiText("Sessão do YouTube")},selected=false,onClick={navigateFromDrawer {youtubeSession=true}})
                NavigationDrawerItem(label={UiText("Licenças e fontes")},selected=false,onClick={navigateFromDrawer {showLicenses=true}})
                NavigationDrawerItem(label={UiText("Falhas da fila")},selected=false,onClick={navigateFromDrawer {OndaStore.failureSummary.value=OndaStore.items.value.filter {it.state=="Erro"}.map {it.id}.takeIf {it.isNotEmpty()}}})
                UiText("Seus downloads",style=MaterialTheme.typography.labelLarge,modifier=Modifier.padding(LayoutSpacing.inset))
                val queue by OndaStore.items.collectAsStateWithLifecycle()
                UiText("${queue.count {it.state=="Pendente"}} pendentes · ${queue.count {it.state=="Concluído"}} concluídos",modifier=Modifier.padding(horizontal=LayoutSpacing.inset),style=MaterialTheme.typography.bodySmall)
                if(statusVisible) UiText(status,modifier=Modifier.padding(LayoutSpacing.inset),style=MaterialTheme.typography.bodySmall)
            }
            UiText("ONDA Android ${BuildConfig.VERSION_NAME}",Modifier.padding(LayoutSpacing.inset),style=MaterialTheme.typography.labelSmall)
        }}) {
        Scaffold(topBar={ TopAppBar(navigationIcon={IconButton(onClick={scope.launch {drawer.open()}},modifier=Modifier.testTag("open-menu")){AccessibleSymbol("☰","Abrir menu de navegação",style=MaterialTheme.typography.titleLarge)}},title={Row(verticalAlignment=Alignment.CenterVertically) {OndaLogo(Modifier.size(28.dp).clip(RoundedCornerShape(25)),"Ícone ONDA");Column(Modifier.padding(start=8.dp)){UiText("ONDA",color=MaterialTheme.colorScheme.primary,fontWeight=FontWeight.Bold,style=MaterialTheme.typography.titleMedium);UiText(tabLabel(tab),style=MaterialTheme.typography.labelSmall)}}}) }) { padding ->
            Column(Modifier.fillMaxSize().padding(padding)) {
                if(busy) LinearProgressIndicator(Modifier.fillMaxWidth())
                TopStatusNotice(status,statusVisible,busy,settings.optBoolean("notice_animation",true),onCancel={vm.cancel()},onDismiss={statusVisible=false},onOpenSettings={category->if(category=="Sessão do YouTube")youtubeSession=true else {settingsCategory=category;showSettings=true}})
                Box(Modifier.weight(1f)) {
                    pages.SaveableStateProvider(tab) {when(tab) {
                        "Pesquisar"->SearchPage(vm,onConnectSpotify={settingsCategory="Contas";showSettings=true})
                        "Links e fila"->LinksPage(vm)
                        "Fila"->QueuePage(vm)
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
        }
        val failureIds by OndaStore.failureSummary.collectAsStateWithLifecycle()
        if(question==null && notice==null && !showSettings && !youtubeSession && !showLicenses && !welcome) {
            failureIds?.let {FailureSummaryWindow(it,vm){OndaStore.failureSummary.value=null}}
        }
        ClipboardDownloadPrompt(settings.optBoolean("clipboard_links",true),!busy && question==null && notice==null && !showSettings && !youtubeSession && !showLicenses && !welcome) {candidate->
            if(candidate.optBoolean("collection"))vm.loadCollection(candidate.getString("url"),OndaStore.collectionOptions(),startDownload=true)
            else vm.enqueueLinks(listOf(candidate.getString("url")),true)
        }
        question?.let { ChoiceWindow(it,vm) }
        if(showSettings) SettingsWindow(vm,initialCategory=settingsCategory) {showSettings=false}
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
    Column(Modifier.fillMaxWidth().padding(vertical=8.dp),horizontalAlignment=Alignment.CenterHorizontally) {
        UiText(title,modifier=Modifier.semantics {heading()},style=MaterialTheme.typography.titleLarge,fontWeight=FontWeight.Bold,textAlign=TextAlign.Center)
        UiText(description,style=MaterialTheme.typography.bodySmall,textAlign=TextAlign.Center,modifier=Modifier.padding(top=LayoutSpacing.details))
    }
}
@Composable fun Select(label: String, value: String, choices: List<String>, modifier: Modifier=Modifier, changed: (String)->Unit) {
    var open by remember { mutableStateOf(false) }
    val displayValue=if(value=="pt-BR") "Português (Brasil)" else if(value=="es") "Español" else if(value=="en") "English" else translateUi(value,LocalUiLanguage.current)
    Column(modifier,verticalArrangement=Arrangement.spacedBy(LayoutSpacing.text)) {
        if(label.isNotBlank()) UiText(label,style=MaterialTheme.typography.labelMedium)
        Box { OutlinedButton(onClick={open=true},modifier=Modifier.fillMaxWidth().heightIn(min=48.dp).a11yLabel(if(label.isBlank()) displayValue else translateUi(label,LocalUiLanguage.current)+": "+displayValue,if(open) "Expandido" else "Recolhido"),shape=RoundedCornerShape(10.dp),contentPadding=PaddingValues(horizontal=12.dp,vertical=6.dp)) {UiText(if(value=="pt-BR")"Português (Brasil)" else if(value=="es")"Español" else if(value=="en")"English" else value,Modifier.weight(1f),maxLines=1,style=MaterialTheme.typography.bodyMedium);UiText("▾",Modifier.padding(start=6.dp).clearAndSetSemantics {})}
            DropdownMenu(expanded=open,onDismissRequest={open=false}) { choices.forEach { choice-> DropdownMenuItem(text={UiText(if(choice=="pt-BR")"Português (Brasil)" else if(choice=="es")"Español" else if(choice=="en")"English" else choice)},onClick={changed(choice);open=false}) } }
        }
    }
}
@Composable fun Toggle(text: String, checked: Boolean, changed: (Boolean)->Unit) {
    Row(Modifier.fillMaxWidth().heightIn(min=48.dp).toggleable(value=checked,role=Role.Checkbox,onValueChange=changed).a11yState(if(checked) "Selecionado" else "Não selecionado"),verticalAlignment=Alignment.CenterVertically) {
        Checkbox(checked=checked,onCheckedChange=null,modifier=Modifier.padding(end=LayoutSpacing.checkboxLabel)); UiText(text,Modifier.weight(1f),style=MaterialTheme.typography.bodyMedium)
    }
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
        item {PageTitle("Encontre sua próxima música.","Pesquise artista ou música, ou cole um link de faixa.")}
        item {OutlinedTextField(query,{query=it},label={UiText("Música, artista ou link")},singleLine=true,
            keyboardOptions=KeyboardOptions(imeAction=ImeAction.Search),keyboardActions=KeyboardActions(onSearch={submitSearch()}),
            modifier=Modifier.fillMaxWidth().testTag("music-query").onPreviewKeyEvent {event->
                if(event.key==Key.Enter || event.key==Key.NumPadEnter) {
                    if(event.type==KeyEventType.KeyDown && event.nativeKeyEvent.repeatCount==0) submitSearch()
                    true
                } else false
            })}
        item {Column {
            UiText("Catálogo",style=MaterialTheme.typography.labelMedium)
            Row(horizontalArrangement=Arrangement.spacedBy(LayoutSpacing.controls),verticalAlignment=Alignment.CenterVertically) {
                Select("",provider,listOf("Todos","Deezer","Apple / iTunes","Spotify"),Modifier.weight(1f)){provider=it}
                Button(onClick={submitSearch()},enabled=query.isNotBlank() && !busy) {UiText("Pesquisar")}
            }
            Row {
                TextButton(onClick={showSearchFilters=true},enabled=!busy){UiText("Filtros")}
                TextButton(onClick={vm.search(query,provider,true)},enabled=query.isNotBlank() && !busy){UiText("Atualizar busca")}
                if(busy)TextButton(onClick={vm.cancel()}){UiText("Cancelar")}
            }
        }}
        if(provider=="Spotify") item {
            Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(LayoutSpacing.controls),verticalAlignment=Alignment.CenterVertically) {
                OutlinedButton(onClick=onConnectSpotify,modifier=Modifier.testTag("search-connect-spotify")) {UiText("Conectar Spotify")}
                UiText("Client ID em Configurações → Contas.",Modifier.weight(1f),style=MaterialTheme.typography.bodySmall)
            }
        }
        if(searchQueue.isNotEmpty()) item {
            ElevatedCard(Modifier.fillMaxWidth().testTag("search-queue")) {Column(Modifier.padding(10.dp),verticalArrangement=Arrangement.spacedBy(LayoutSpacing.details)) {
                UiText("Fila da pesquisa · ${searchQueue.count {it.state=="Concluído"}} de ${searchQueue.size} concluídas",style=MaterialTheme.typography.titleSmall)
                LazyColumn(Modifier.fillMaxWidth().heightIn(max=180.dp)) {items(searchQueue,key={it.id}) {item->Column(Modifier.padding(vertical=6.dp)) {
                    Row(Modifier.fillMaxWidth(),verticalAlignment=Alignment.CenterVertically) {
                        Text(item.title,Modifier.weight(1f),maxLines=2,style=MaterialTheme.typography.bodyMedium)
                        TextButton(onClick={OndaStore.remove(setOf(item.id))},enabled=item.id!=active && item.state !in listOf("Baixando","Aguardando escolha"),modifier=Modifier.testTag("remove-search-${item.id}")){UiText("Remover")}
                    }
                    if(item.state=="Erro" && item.message.contains("Nenhuma versão suficientemente compatível",ignoreCase=true)) {
                        TextButton(onClick={OndaStore.retryWithVersionChoice(item.id)}) {UiText("Escolher versão")}
                    }
                    UiText(item.state,style=MaterialTheme.typography.labelMedium)
                    if(item.state in listOf("Baixando","Aguardando escolha")) LinearProgressIndicator(progress={item.progress/100},modifier=Modifier.fillMaxWidth())
                    if(item.message.isNotBlank()) UiText(item.message,style=MaterialTheme.typography.bodySmall,maxLines=2)
                }}}
                Row(Modifier.horizontalScroll(rememberScrollState())) {
                    TextButton(onClick={DownloadService.batch(OndaStore.context,searchQueue.filter {it.state=="Pendente"}.map {it.id})},enabled=searchQueue.any {it.state=="Pendente"}){UiText("Baixar fila da pesquisa")}
                    TextButton(onClick={OndaStore.retry(searchQueue.filter {it.state=="Erro"}.map {it.id}.toSet())},enabled=searchQueue.any {it.state=="Erro"}){UiText("Tentar novamente")}
                    TextButton(onClick={OndaStore.remove(searchQueue.filter {it.id!=OndaStore.active.value}.map {it.id}.toSet())}){UiText("Limpar fila da pesquisa")}
                }
            }}
        }
        if(results.isEmpty()) item {UiText("Sua biblioteca começa com uma busca",fontWeight=FontWeight.Bold);UiText("Encontre a música e escolha a versão que você quer.",style=MaterialTheme.typography.bodySmall)}
        if(comparison.size==1)item {UiText("Selecione outro resultado para comparar.")}
        items(results,contentType={"search_track"}) {record-> TrackCard(record,vm,onDownload={downloadTrack=record.toString()},onCompare={
            val source=record.cleanString("source_url")
            val repeated=comparison.any {it===record || (source.isNotBlank() && sourceKey(it.cleanString("source_url"))==sourceKey(source))}
            if(repeated)vm.showNotice("Comparar resultados","Essa música já foi selecionada. Escolha outro resultado para comparar.")
            else comparison=(comparison+record).takeLast(2)
        }) }
        item {UiText("Catálogo e capa: plataforma selecionada  •  Áudio: YouTube / FLAC: Monochrome",style=MaterialTheme.typography.bodySmall)}
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
    val playing by vm.previewActive.collectAsStateWithLifecycle()
    val playingUrl by vm.previewUrl.collectAsStateWithLifecycle()
    var releaseDate by remember(record) {mutableStateOf(record.cleanString("release_date"))}
    LaunchedEffect(record) {releaseDate=vm.releaseDate(record)}
    val url=record.cleanString("preview_url")
    val thisPlaying=playing && playingUrl==url
    Card(Modifier.fillMaxWidth(),colors=CardDefaults.cardColors(containerColor=MaterialTheme.colorScheme.background,contentColor=MaterialTheme.colorScheme.onBackground),elevation=CardDefaults.cardElevation(defaultElevation=0.dp)) { Column(Modifier.padding(12.dp)) {
        Row(verticalAlignment=Alignment.CenterVertically) {
            AsyncImage(model=record.cleanString("cover_url"),contentDescription=translateUi("Capa do álbum",LocalUiLanguage.current),modifier=Modifier.size(60.dp))
            Column(Modifier.padding(start=12.dp).weight(1f)) {Text(record.cleanString("title"),fontWeight=FontWeight.Bold);Text(record.stringList("artists"),style=MaterialTheme.typography.bodySmall);Text(record.cleanString("album"),style=MaterialTheme.typography.bodySmall)
                releaseDate.takeIf {it.isNotBlank()}?.let { date ->
                    Text(translateUi("Data de lançamento",LocalUiLanguage.current)+": "+displayReleaseDate(date),modifier=Modifier.padding(top=4.dp),style=MaterialTheme.typography.bodyMedium,fontWeight=FontWeight.Medium)
                }
                if(record.optLong("duration_ms")>0) UiText(mediaClock(record.optLong("duration_ms")/1000),style=MaterialTheme.typography.labelSmall)
            }
        }
        Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceEvenly,verticalAlignment=Alignment.CenterVertically) {
            TextButton(contentPadding=PaddingValues(horizontal=4.dp,vertical=8.dp),onClick={if(thisPlaying) vm.stopPreview() else if(url.isNotBlank()) vm.preview(url,OndaStore.settings.value.optInt("search_preview",25)) else vm.status.value="Esta faixa não oferece prévia no catálogo."}) {UiText(if(thisPlaying) "Parar prévia" else "Ouvir prévia")}
            TextButton(contentPadding=PaddingValues(horizontal=4.dp,vertical=8.dp),onClick={vm.queueTrack(record,origin="search")}) {UiText("Adicionar à fila")}
            Button(contentPadding=PaddingValues(horizontal=10.dp,vertical=8.dp),onClick=onDownload) {UiText("Baixar agora")}
        }
        MetadataPlatformBadge(record)
        Row {
            TextButton(onClick={val url=record.cleanString("source_url");if(url.startsWith("https://")) OndaStore.context.startActivity(Intent(Intent.ACTION_VIEW,android.net.Uri.parse(url)).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))}){UiText("Ver no catálogo")}
            if(onCompare!=null)TextButton(onClick=onCompare){UiText("Comparar resultados")}
        }
    }}
}

@Composable fun LinksPage(vm: OndaViewModel) {
    val settings by OndaStore.settings.collectAsStateWithLifecycle()
    val adding by vm.addingToQueue.collectAsStateWithLifecycle()
    val shared by OndaStore.sharedLink.collectAsStateWithLifecycle()
    var link by rememberSaveable {mutableStateOf("")}
    LaunchedEffect(shared) {if(shared.isNotBlank()) {link=shared;OndaStore.sharedLink.value=""}}
    fun add(now:Boolean) {
        val urls=link.lines().map {it.trim()}.filter {it.isNotBlank()}
        vm.enqueueLinks(urls,now)
        link=""
    }
    NavigableList(Modifier.fillMaxSize().padding(horizontal=LayoutSpacing.inset),navigationId="links") {
        item {PageTitle("Do link para sua biblioteca.","Músicas, vídeos e fotos, organizados do seu jeito.")}
        item {OutlinedTextField(link,{link=it},label={UiText("LINKS")},placeholder={UiText("YouTube, Instagram, TikTok, Kwai… um link por linha")},minLines=2,modifier=Modifier.fillMaxWidth().testTag("links-input"),singleLine=false)}
        item {FormatOptions(settings,OndaStore::saveSettings)}
        item {Toggle("Baixar playlist de vídeo",settings.optBoolean("link_playlist")){OndaStore.saveSettings(JSONObject(settings.toString()).put("link_playlist",it))}}
        item {Row(horizontalArrangement=Arrangement.spacedBy(LayoutSpacing.controls)) {
            OutlinedButton(onClick={add(false)},enabled=link.isNotBlank() && !adding,modifier=Modifier.testTag("links-add")){UiText("Adicionar à fila")}
            Button(onClick={add(true)},enabled=link.isNotBlank() && !adding,modifier=Modifier.testTag("links-download")){UiText("Baixar agora")}
        }}
        if(adding)item {LinearProgressIndicator(Modifier.fillMaxWidth())}
        item {TextButton(onClick={vm.queueNavigation.value=true},modifier=Modifier.testTag("view-queue")){UiText("Ver fila")}}
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

@Composable fun ImagesPage(vm: OndaViewModel) {
    val settings by OndaStore.settings.collectAsStateWithLifecycle()
    var link by rememberSaveable {mutableStateOf("")}
    var source by rememberSaveable {mutableStateOf("")}
    var preview by remember {mutableStateOf("")}
    var dimensions by remember {mutableStateOf("")}
    val local=rememberImageSourcePicker(arrayOf("image/*")) {uri->source="";vm.importLocal(uri,"image") {source=it.absolutePath;link="";preview=""}}
    fun imageConfig()=OndaStore.config(JSONObject(settings.toString()).put("mode","photos")).put("url",link).apply {
        if(source.isNotBlank()) put("source",source).put("name",File(source).name.replaceFirst(Regex("^image-[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}-"),""))
    }
    Column(Modifier.verticalScroll(rememberScrollState()).padding(LayoutSpacing.inset),verticalArrangement=Arrangement.spacedBy(LayoutSpacing.controls)) {
        PageTitle("Imagens do seu jeito.","Baixe, converta e ajuste o tamanho sem cortar a imagem.")
        OutlinedTextField(link,{link=it;source=""},label={UiText("Link da imagem ou publicação")},modifier=Modifier.fillMaxWidth(),singleLine=true)
        TextButton(onClick={local()}){UiText(if(source.isBlank()) "Escolher imagem" else File(source).name)}
        ImageOptions(settings,OndaStore::saveSettings)
        OutlinedButton(onClick={vm.operation("image_preview",imageConfig()){preview=it.getString("path");dimensions="${it.optInt("width")} × ${it.optInt("height")}"}},enabled=link.isNotBlank() || source.isNotBlank()){UiText("Ver prévia")}
        if(preview.isNotBlank()) {AsyncImage(File(preview),translateUi("Prévia da imagem",LocalUiLanguage.current),Modifier.fillMaxWidth().heightIn(max=240.dp));UiText(dimensions)}
        Button(onClick={if(source.isNotBlank()) vm.operation("image_convert",imageConfig()) else {val id=OndaStore.enqueue(link,options=JSONObject(settings.toString()).put("mode","photos"),extra=JSONObject().put("_immediate",true));DownloadService.start(OndaStore.context,id);link=""}},enabled=link.isNotBlank() || source.isNotBlank()) {UiText("Baixar agora")}
        OutlinedButton(onClick={OndaStore.enqueue(link,options=JSONObject(settings.toString()).put("mode","photos"));link=""},enabled=link.isNotBlank()){UiText("Adicionar à fila")}
        UiText("SVG incorpora a imagem original; não vetoriza. Animações usam o primeiro quadro.",style=MaterialTheme.typography.bodySmall)
    }
}
@Composable fun ImageOptions(config: JSONObject, change: (JSONObject)->Unit, separated:Boolean=false) {
    val preferences by OndaStore.settings.collectAsStateWithLifecycle()
    if(!separated && preferences.optBoolean("simple_download_ui",false)) return
    fun put(key: String,value: Any) {change(JSONObject(config.toString()).put(key,value))}
    Select("Formato",config.optString("image_format","Original"),listOf("Original","JPG","PNG","WebP","SVG")){put("image_format",it)}
    if(separated)SettingsDivider()
    val sizes=linkedMapOf("Original" to (0 to 0),"Até 1920 × 1080" to (1920 to 1080),"Até 1280 × 720" to (1280 to 720),"Até 1080 × 1080" to (1080 to 1080),"Personalizado" to null)
    val selectedSize=config.optString("image_size").ifBlank {if(config.optInt("image_width")==0 && config.optInt("image_height")==0) "Original" else "Personalizado"}
    Select("Tamanho máximo",selectedSize,sizes.keys.toList()){size->
        val next=JSONObject(config.toString()).put("image_size",size)
        sizes[size]?.let {next.put("image_width",it.first).put("image_height",it.second)}
        change(next)
    }
    if(selectedSize=="Personalizado") {
    UiText("Largura × altura (px)",style=MaterialTheme.typography.labelMedium)
    Row(horizontalArrangement=Arrangement.spacedBy(LayoutSpacing.controls)) {
        OutlinedTextField(config.optInt("image_width").takeIf {it>0}?.toString() ?: "",{put("image_width",it.toIntOrNull()?.coerceIn(0,16384) ?: 0)},label={UiText("Largura")},modifier=Modifier.weight(1f),singleLine=true)
        OutlinedTextField(config.optInt("image_height").takeIf {it>0}?.toString() ?: "",{put("image_height",it.toIntOrNull()?.coerceIn(0,16384) ?: 0)},label={UiText("Altura")},modifier=Modifier.weight(1f),singleLine=true)
    }
    }
    if(separated)SettingsDivider()
    Toggle("Manter proporção (sem ampliar ou distorcer)",config.optBoolean("keep_ratio",true)){put("keep_ratio",it)}
}

@Composable fun CollectionsPage(vm: OndaViewModel) {
    val collection by vm.collection.collectAsStateWithLifecycle()
    val comparison by vm.collectionComparison.collectAsStateWithLifecycle()
    val busy by vm.busy.collectAsStateWithLifecycle()
    var syncReload by remember {mutableStateOf(false)}
    val settings by OndaStore.settings.collectAsStateWithLifecycle()
    val adding by vm.addingToQueue.collectAsStateWithLifecycle()
    val actionsAtTop=settings.optBoolean("queue_actions_at_top",true)
    var url by rememberSaveable {mutableStateOf("")}
    var filter by rememberSaveable {mutableStateOf("")}
    var selected by remember {mutableStateOf(setOf<String>())}
    var options by remember {mutableStateOf(OndaStore.collectionOptions())}
    LaunchedEffect(options) {OndaStore.saveCollectionOptions(options)}
    var listOnly by remember {mutableStateOf(false)}
    val folderPicker=rememberLauncherForActivityResult(ActivityResultContracts.OpenDocumentTree()) {tree->
        if(tree!=null) {
            runCatching {OndaStore.context.contentResolver.takePersistableUriPermission(tree,android.content.Intent.FLAG_GRANT_READ_URI_PERMISSION)}
            vm.compareCollectionLocal(tree,url,options,syncReload)
        }
    }
    val import=rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) {uri->if(uri!=null) vm.importLocal(uri,"playlist") {vm.importCollection(it.absolutePath)}}
    var exported by remember {mutableStateOf("")}
    val export=rememberLauncherForActivityResult(ActivityResultContracts.CreateDocument("text/plain")) {uri->if(uri!=null) OndaStore.context.contentResolver.openOutputStream(uri)?.use {it.write(exported.toByteArray())}}
    val tracks=remember(collection) {collection.optJSONArray("tracks")?.objects() ?: emptyList()}
    val syncItems=remember(comparison) {comparison?.optJSONArray("items")?.objects()?.associateBy {it.optInt("index")} ?: emptyMap()}
    val missingTracks=remember(tracks,comparison) {tracks.filterIndexed {index,_->syncItems[index]?.optString("state")=="missing"}}
    val syncBySource=remember(tracks,comparison) {tracks.mapIndexed {index,record->record.optString("source_url") to syncItems[index]}.toMap()}
    val searchIndex=remember(tracks) {tracks.map {it to (it.optString("title")+" "+it.stringList("artists")).lowercase(java.util.Locale.ROOT)}}
    var settledFilter by remember {mutableStateOf(filter)}
    LaunchedEffect(filter) {delay(150);settledFilter=filter}
    val visible=remember(searchIndex,settledFilter) {
        val term=settledFilter.lowercase(java.util.Locale.ROOT)
        searchIndex.filter {(_,text)->term in text}.map {(record,_)->record}
    }
    LaunchedEffect(visible) {OndaStore.selectAll.collect {selected=selected+visible.map {it.optString("source_url")}}}
    val chosenTracks=remember(visible,selected,filter,settledFilter) {
        if(filter!=settledFilter) emptyList() else visible.filter {it.optString("source_url") in selected}
    }
    fun chosen()=chosenTracks
    fun enqueue(now: Boolean) {
        val rows=chosen()
        vm.queueCollection(rows,options,collection.optString("folder_title",collection.optString("title","Playlist")),now)
    }
    val collectionActions:@Composable ()->Unit = {
        Row(Modifier.horizontalScroll(rememberScrollState())) {
            Button(onClick={enqueue(true)},enabled=chosen().isNotEmpty() && !adding){UiText("Baixar agora")}
            TextButton(onClick={enqueue(false)},enabled=chosen().isNotEmpty() && !adding){UiText("Adicionar à fila")}
        }
    }
    NavigableList(Modifier.fillMaxSize().padding(horizontal=LayoutSpacing.inset),navigationId="collection") {
        item {PageTitle("Seus álbuns e playlists na biblioteca.","Busque por música ou artista. As ações usam somente os itens visíveis selecionados. Formato e qualidade são próprios desta aba.")}
        item {OutlinedTextField(url,{url=it},label={UiText("Link da playlist ou álbum")},modifier=Modifier.fillMaxWidth(),singleLine=true)}
        item {Row(Modifier.horizontalScroll(rememberScrollState())) {
            Button(onClick={vm.loadCollection(url,options)},enabled=url.isNotBlank()){UiText("Carregar álbum ou playlist")}
            TextButton(onClick={import.launch(arrayOf("text/*","application/octet-stream","application/vnd.ms-excel"))}){UiText("Importar arquivo")}
            TextButton(onClick={listOnly=true}){UiText("Ver lista")}
        }}
        item {Row(Modifier.horizontalScroll(rememberScrollState())) {
            TextButton(onClick={syncReload=false;folderPicker.launch(null)},enabled=tracks.isNotEmpty() && !busy && !adding){UiText("Conferir arquivos locais")}
            TextButton(onClick={syncReload=true;folderPicker.launch(null)},enabled=url.isNotBlank() && !busy && !adding){UiText("Atualizar playlist baixada")}
            TextButton(onClick={vm.queueCollection(missingTracks,options,collection.optString("folder_title",collection.optString("title","Playlist")),false);vm.collectionComparison.value=null},enabled=missingTracks.isNotEmpty() && !busy && !adding){UiText("Adicionar ausentes à fila")}
        }}
        comparison?.let {report->item {Text(collectionSyncSummary(report),style=MaterialTheme.typography.bodySmall)}}
        if(busy)item {LinearProgressIndicator(Modifier.fillMaxWidth())}
        item {FormatOptions(options,changed={options=it})}
        if(collection.optString("title").isNotBlank()) item {
            Card(Modifier.fillMaxWidth().testTag("collection-card"),colors=CardDefaults.cardColors(containerColor=MaterialTheme.colorScheme.background)) {
                Row(Modifier.fillMaxWidth().padding(vertical=LayoutSpacing.controls),verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.spacedBy(LayoutSpacing.section)) {
                    if(collection.cleanString("cover_url").isNotBlank()) AsyncImage(model=collection.cleanString("cover_url"),contentDescription=translateUi("Capa de ${collection.optString("title")}",LocalUiLanguage.current),contentScale=androidx.compose.ui.layout.ContentScale.Crop,modifier=Modifier.size(88.dp).clip(RoundedCornerShape(10.dp)))
                    else Surface(Modifier.size(88.dp),shape=RoundedCornerShape(10.dp),color=MaterialTheme.colorScheme.surfaceVariant) {Box(contentAlignment=Alignment.Center){UiText("♫",style=MaterialTheme.typography.headlineLarge)}}
                    Column(Modifier.weight(1f),verticalArrangement=Arrangement.spacedBy(LayoutSpacing.details)) {
                        Text(collection.optString("title"),fontWeight=FontWeight.Bold,style=MaterialTheme.typography.titleMedium)
                        if(collection.cleanString("subtitle").isNotBlank()) Text(collection.cleanString("subtitle"),style=MaterialTheme.typography.bodySmall)
                        UiText("${if(collection.optString("kind")=="album") "Álbum" else "Playlist"} · ${tracks.size} músicas",style=MaterialTheme.typography.bodySmall)
                    }
                }
                if(collection.cleanString("note").isNotBlank()) UiText(collection.cleanString("note"),style=MaterialTheme.typography.bodySmall,modifier=Modifier.padding(bottom=8.dp))
            }
        }
        item {OutlinedTextField(filter,{filter=it},label={UiText("Buscar nesta lista")},modifier=Modifier.fillMaxWidth(),singleLine=true);UiText("${visible.size} de ${tracks.size}",style=MaterialTheme.typography.bodySmall)}
        item {Row(Modifier.horizontalScroll(rememberScrollState())) {
            TextButton(onClick={selected=selected+visible.map {it.optString("source_url")}}){UiText("Selecionar visíveis")}
            TextButton(onClick={selected=emptySet()}){UiText("Limpar seleção")}
            TextButton(onClick={vm.operation("matches",OndaStore.config(options).put("tracks",JSONArray(chosen()))){vm.collection.value=JSONObject(collection.toString()).put("tracks",JSONArray(mergeTrackMatches(tracks,it.getJSONArray("tracks").objects())))}}){UiText("Conferir correspondências")}
        }}
        if(actionsAtTop)item {collectionActions()}
        if(adding)item {LinearProgressIndicator(Modifier.fillMaxWidth())}
        items(visible,contentType={"collection_track"}) {record->Row(Modifier.fillMaxWidth().heightIn(min=48.dp).toggleable(value=record.optString("source_url") in selected,role=Role.Checkbox,onValueChange={checked->val id=record.optString("source_url");selected=if(checked) selected+id else selected-id}).a11yState(if(record.optString("source_url") in selected) "Selecionado" else "Não selecionado"),verticalAlignment=Alignment.CenterVertically) {
            Checkbox(record.optString("source_url") in selected,null,modifier=Modifier.padding(end=LayoutSpacing.checkboxLabel))
            Column(Modifier.weight(1f)) {Text(record.optString("title"));Text(record.stringList("artists"),style=MaterialTheme.typography.bodySmall);record.optJSONObject("youtube_match")?.let {Text(it.optString("title"),color=MaterialTheme.colorScheme.primary,style=MaterialTheme.typography.bodySmall)};syncBySource[record.optString("source_url")]?.let {state->
                UiText(collectionSyncState(state.optString("state")),style=MaterialTheme.typography.bodySmall)
                UiText(state.optString("reason"),style=MaterialTheme.typography.bodySmall)
                state.optJSONArray("paths")?.optString(0)?.takeIf {it.isNotBlank()}?.let {Text(it,style=MaterialTheme.typography.bodySmall)}
            }}
        }}
        if(!actionsAtTop)item {collectionActions()}
        item {Row {for(format in listOf("txt","m3u")) TextButton(onClick={vm.operation("export_list",JSONObject().put("tracks",JSONArray(tracks)).put("format",format)){exported=it.getString("text");export.launch("${collection.optString("title","Playlist")}.$format")}}){UiText("Exportar ${format.uppercase()}")}}}
    }
    if(listOnly) Dialog(onDismissRequest={listOnly=false}) {Surface(shape=RoundedCornerShape(20.dp)) {Column(Modifier.fillMaxWidth().fillMaxHeight(.85f).padding(LayoutSpacing.inset)) {
        UiText(collection.optString("title","Músicas"),style=MaterialTheme.typography.titleLarge)
        NavigableList(Modifier.weight(1f),navigationId="collection-dialog") {items(visible){UiText("${it.stringList("artists")} - ${it.optString("title")}",Modifier.padding(vertical=8.dp))}}
        TextButton(onClick={listOnly=false}){UiText("Fechar")}
    }}}
}

@Composable fun HistoryPage(vm: OndaViewModel,onEditMetadata:(HistoryItem)->Unit) {
    LaunchedEffect(Unit) {invalidateHistoryDetails()}
    val history by OndaStore.history.collectAsStateWithLifecycle()
    val settings by OndaStore.settings.collectAsStateWithLifecycle()
    val complete = settings.optString("history_view","Compacto") == "Completa"
    val cardSize=settings.optString("history_card_size","Grande")

    var selectedHistory by remember {mutableStateOf(setOf<Long>())}
    var batchHistory by remember {mutableStateOf<List<String>?>(null)}
    batchHistory?.let {sources->BatchMetadataEditor(vm,sources){batchHistory=null}}
    val audioModes=setOf("mp3","m4a","flac","wav","ogg","opus")
    var filter by rememberSaveable {mutableStateOf("")}
    val visible=remember(history,filter) {history.filter {it.title.contains(filter,true)}}
    LazyColumn(Modifier.fillMaxSize().padding(horizontal=LayoutSpacing.inset),verticalArrangement=Arrangement.spacedBy(LayoutSpacing.controls)) {
        item {PageTitle("Sua biblioteca de downloads.","Encontre, abra e compartilhe o que já baixou.")}
        item {OutlinedTextField(filter,{filter=it},label={UiText("Pesquisar no histórico")},modifier=Modifier.fillMaxWidth(),singleLine=true)}
        item {HistoryDisplayControls(settings)}
        item {Row(Modifier.horizontalScroll(rememberScrollState())) {
            TextButton(onClick={selectedHistory=visible.filter {it.mode.lowercase() in audioModes}.map {it.id}.toSet()}){UiText("Selecionar áudios visíveis")}
            TextButton(onClick={selectedHistory=emptySet()}){UiText("Limpar seleção")}
            TextButton(onClick={batchHistory=history.filter {it.id in selectedHistory && it.mode.lowercase() in audioModes}.map {it.uri}.distinct()},enabled=selectedHistory.isNotEmpty()){UiText("Editar metadados em lote")}
        }}
        items(visible,key={it.id}) {item->ElevatedCard(Modifier.fillMaxWidth().testTag("history-card-${item.id}").then(
            if(complete) Modifier.toggleable(value=item.id in selectedHistory,role=Role.Checkbox,onValueChange={checked->selectedHistory=if(checked) selectedHistory+item.id else selectedHistory-item.id})
                .border(2.dp,if(item.id in selectedHistory) MaterialTheme.colorScheme.primary else Color.Transparent,MaterialTheme.shapes.medium)
            else Modifier)) {Column(Modifier.padding(if(complete && cardSize=="Pequeno") 6.dp else if(complete && cardSize=="Médio") 9.dp else 12.dp),verticalArrangement=Arrangement.spacedBy(LayoutSpacing.text)) {
            if(complete) {
                Row(verticalAlignment=Alignment.CenterVertically) {
                    Checkbox(checked=item.id in selectedHistory,onCheckedChange={checked->selectedHistory=if(checked) selectedHistory+item.id else selectedHistory-item.id},modifier=Modifier.padding(end=LayoutSpacing.checkboxLabel).a11yLabel("Selecionar música"))
                    UiText(if(item.id in selectedHistory) "Música selecionada" else "Selecionar música")
                }
                CompleteHistoryInformation(item,cardSize)
            }
            Row(Modifier.fillMaxWidth(),verticalAlignment=Alignment.CenterVertically) {
                if(!complete && item.mode.lowercase() in audioModes)Checkbox(checked=item.id in selectedHistory,onCheckedChange={checked->selectedHistory=if(checked) selectedHistory+item.id else selectedHistory-item.id},modifier=Modifier.padding(end=LayoutSpacing.checkboxLabel).a11yLabel("Selecionar música"))
                Text(item.title,Modifier.weight(1f),fontWeight=FontWeight.Bold)
                TextButton(onClick={OndaStore.removeHistory(item.id)},modifier=Modifier.testTag("remove-history-${item.id}")){UiText("Remover")}
            }
            MetadataPlatformBadge(JSONObject().put("platform",item.metadataPlatform))
            UiText("${item.mode.uppercase()} · %.1f MB".format(item.size/1048576.0),style=MaterialTheme.typography.bodySmall)
            TextButton(enabled=historyOrigin(item.source).isNotBlank(),onClick={
                runCatching {OndaStore.context.startActivity(Intent(Intent.ACTION_VIEW,android.net.Uri.parse(historyOrigin(item.source))).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))}
                    .onFailure {vm.showNotice("Abrir origem","Não foi possível abrir a origem.")}
            }){UiText("Abrir origem")}
            Row(Modifier.horizontalScroll(rememberScrollState())) {TextButton(onClick={runCatching {OndaStore.open(item.uri,item.mode)}.onFailure {OndaStore.log("Nenhum aplicativo disponível para abrir este arquivo.")}}){UiText("Abrir arquivo")};TextButton(onClick={vm.openHistoryFolder(item.uri)},modifier=Modifier.testTag("open-history-folder-${item.id}")){UiText("Abrir pasta")};TextButton(onClick={OndaStore.share(item.uri,item.title)}){UiText("Compartilhar")}
                if(item.mode.lowercase() in setOf("mp3","m4a","flac","wav","ogg","opus")) TextButton(onClick={onEditMetadata(item)}) {UiText("Editar metadados")}
                if(historySupportsEffects(item)) TextButton(onClick={vm.useInEffects(item.uri)}) {UiText("Usar nos efeitos")}
            }
        }}}
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
    var lyrics by remember {mutableStateOf<List<Pair<Double,String>>>(emptyList())}
    var lyricLine by remember {mutableStateOf("")}
    val lyricSettings by OndaStore.settings.collectAsStateWithLifecycle()
    val pickLyrics=rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) {uri->if(uri!=null)vm.importLocal(uri,"lyrics") {file->
        vm.operation("lyrics_read",JSONObject().put("source",file.absolutePath)) {result->
            lyrics=result.optJSONArray("lines")?.let {rows->(0 until rows.length()).map {index->rows.getJSONArray(index).let {it.getDouble(0) to it.getString(1)}}} ?: emptyList()
            file.delete()
            if(lyrics.isEmpty())vm.showNotice("Importar letra LRC","Nenhum tempo válido na letra LRC.")
            else OndaStore.saveSettings(JSONObject(OndaStore.settings.value.toString()).put("synced_lyrics",true))
        }
    }}
    LaunchedEffect(lyrics,lyricSettings.optBoolean("synced_lyrics")) {
        if(!lyricSettings.optBoolean("synced_lyrics")) {lyricLine="";return@LaunchedEffect}
        while(true) {lyricLine=lyrics.lastOrNull {it.first<=vm.lyricsPosition()}?.second ?: "";delay(200)}
    }
    var source by rememberSaveable {mutableStateOf("")}
    LaunchedEffect(source) {lyrics=emptyList();lyricLine=""}
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
    Column(Modifier.verticalScroll(rememberScrollState()).padding(LayoutSpacing.inset),verticalArrangement=Arrangement.spacedBy(LayoutSpacing.controls)) {
        if(heading)PageTitle("Slowed · Sped Up · Reverb","Desacelere ou acelere sua música. Adicione reverb se quiser.")
        OutlinedButton(onClick={choose.launch(arrayOf("audio/*"))},modifier=Modifier.fillMaxWidth()){UiText(if(source.isBlank()) "Abrir áudio" else importedAudioName(source),maxLines=2)}
        TextButton(onClick={pickLyrics.launch(arrayOf("text/plain","application/x-lrc","application/octet-stream"))},enabled=source.isNotBlank()){UiText("Importar letra LRC")}
        if(lyricLine.isNotBlank())Text(lyricLine,style=MaterialTheme.typography.titleMedium)
        val presets=remember {linkedMapOf("Original" to (100f to 0f),"Slowed leve" to (90f to 0f),"Slowed intenso" to (75f to 0f),"Sped Up leve" to (115f to 0f),"Sped Up intenso" to (130f to 0f),"Sped Up + Reverb" to (120f to 25f),"Só Reverb" to (100f to 30f),"Clássico" to (85f to 25f),"Atmosférico" to (75f to 50f))}
        val preset=presets.entries.firstOrNull {it.value.first.toInt()==speed.toInt() && it.value.second.toInt()==reverb.toInt()}?.key ?: "Personalizado"
        Select("Preset",preset,presets.keys.toList()) {val value=presets.getValue(it);speed=value.first;reverb=value.second}
        UiText("Velocidade · ${speed.toInt()}% · ${if(speed<100) "Slowed" else if(speed>100) "Sped Up" else "original"}",fontWeight=FontWeight.Bold)
        RoundSlider(speed,{speed=it.toInt().toFloat()},valueRange=50f..150f,modifier=Modifier.testTag("effects-speed").a11yLabel("Velocidade da música","${speed.toInt()}%"))
        UiText("Reverb · ${reverb.toInt()}%${if(reverb==0f) " · desligado" else ""}",fontWeight=FontWeight.Bold)
        RoundSlider(reverb,{reverb=it.toInt().toFloat()},valueRange=0f..100f,modifier=Modifier.testTag("effects-reverb").a11yLabel("Intensidade do reverb","${reverb.toInt()}%"))
        Toggle("Manter tom (pitch) ao alterar a velocidade",pitch){pitch=it}
        UiText("Posição na música · ${mediaClock(start.toLong())} / ${mediaClock(duration.toLong())}")
        RoundSlider(start.coerceIn(0f,duration.coerceAtLeast(1f)),{start=it},valueRange=0f..duration.coerceAtLeast(1f),modifier=Modifier.a11yLabel("Posição inicial da prévia","${mediaClock(start.toLong())} de ${mediaClock(duration.toLong())}"))
        Row(horizontalArrangement=Arrangement.spacedBy(LayoutSpacing.controls)) {
        TextButton(onClick={vm.stopPreview();vm.preview(source,OndaStore.settings.value.optInt("effects_preview",25),start.toInt())},enabled=source.isNotBlank()){UiText("Ouvir original")}
        Button(onClick={vm.previewEffects(source,speed.toInt(),reverb.toInt(),pitch,start.toInt())},enabled=source.isNotBlank()){UiText("Ouvir com efeitos")}
        }
        val previewUrl by vm.previewUrl.collectAsStateWithLifecycle()
        if(previewUrl.isNotBlank()) PlayerControls(vm)
        UiText("Arraste a barra para escolher o trecho. A duração da prévia pode ser alterada em Configurações. Ajuste os efeitos enquanto ouve.",style=MaterialTheme.typography.bodySmall)
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
        },enabled=source.isNotBlank()){UiText("Exportar música inteira")}
    }
}

fun importedAudioName(path: String): String = File(path).name.replaceFirst(Regex("^audio-[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}-"),"")
