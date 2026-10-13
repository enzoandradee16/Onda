package br.com.onda.mobile

import android.Manifest
import android.content.Intent
import android.net.Uri
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
import androidx.compose.ui.res.painterResource
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
    var statusVisible by rememberStatusNotice(status,busy,settings.optString("notice_duration","Fechar manualmente"))
    val effectsSource by vm.effectsSource.collectAsStateWithLifecycle()
    val shared by OndaStore.sharedLink.collectAsStateWithLifecycle()
    val pureBlack=settings.optString("theme")=="Preto puro"
    val dark=when(settings.optString("theme")) { "Claro"->false; "Escuro","Preto puro"->true; else->isSystemInDarkTheme() }
    val palette=if(dark) accents else lightAccents
    val accent=Color(palette[settings.optString("accent")] ?: palette.getValue("Verde-Água"))
    val baseScheme=if(dark) darkColorScheme(primary=accent,background=Color(0xFF0E131B),surface=Color(0xFF161E29),onPrimary=Color(0xFF10171F)) else lightColorScheme(primary=accent)
    val tabs=settings.optJSONArray("tab_order") ?: OndaStore.defaults().getJSONArray("tab_order")
    val scheme=if(pureBlack) baseScheme.copy(
        background=Color.Black,surface=Color.Black,surfaceTint=Color.Transparent,
        surfaceDim=Color.Black,surfaceBright=Color(0xFF181818),
        surfaceContainerLowest=Color.Black,surfaceContainerLow=Color.Black,surfaceContainer=Color.Black,
        surfaceContainerHigh=Color(0xFF101010),surfaceContainerHighest=Color(0xFF181818),
        surfaceVariant=Color(0xFF181818),outlineVariant=Color(0xFF303030)
    ) else baseScheme
    val homeTab=tabs.optString(0,"Pesquisar")
    var tab by rememberSaveable { mutableStateOf(homeTab) }
    var metadataUri by rememberSaveable {mutableStateOf<String?>(null)}
    var showSettings by rememberSaveable { mutableStateOf(false) }
    var settingsCategory by rememberSaveable { mutableStateOf("Aparência") }
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
    LaunchedEffect(tab) { if(!settings.optBoolean("keep_preview")) vm.stopPreview() }
    val typography=remember(settings.optString("interface_font"),settings.optString("interface_font_size")) {interfaceTypography(settings.optString("interface_font",DEFAULT_INTERFACE_FONT),settings.optString("interface_font_size","100%"))}
    MaterialTheme(colorScheme=scheme,typography=typography) {
        ModalNavigationDrawer(drawerState=drawer,drawerContent={ModalDrawerSheet(Modifier.width(300.dp)) {
            Row(Modifier.fillMaxWidth().padding(20.dp),horizontalArrangement=Arrangement.Center,verticalAlignment=Alignment.CenterVertically) {Image(painterResource(R.drawable.ic_onda),null,Modifier.size(36.dp).clip(RoundedCornerShape(25)));Text("ONDA",style=MaterialTheme.typography.titleLarge,fontWeight=FontWeight.Bold,modifier=Modifier.padding(start=8.dp))}
            Column(Modifier.weight(1f).verticalScroll(rememberScrollState())) {
                for(index in 0 until tabs.length()) {val name=tabs.getString(index)
                    NavigationDrawerItem(label={Text(tabLabel(name))},selected=tab==name,onClick={navigateFromDrawer {tab=name}},modifier=Modifier.padding(horizontal=10.dp).testTag("tab-$name"))
                }
                HorizontalDivider(Modifier.padding(12.dp))
                NavigationDrawerItem(label={Text("Configurações")},selected=false,onClick={navigateFromDrawer {settingsCategory="Aparência";showSettings=true}})
                NavigationDrawerItem(label={Text("Sessão do YouTube")},selected=false,onClick={navigateFromDrawer {youtubeSession=true}})
                NavigationDrawerItem(label={Text("Licenças e fontes")},selected=false,onClick={navigateFromDrawer {showLicenses=true}})
                Text("Seus downloads",style=MaterialTheme.typography.labelLarge,modifier=Modifier.padding(16.dp))
                val queue by OndaStore.items.collectAsStateWithLifecycle()
                Text("${queue.count {it.state=="Pendente"}} pendentes · ${queue.count {it.state=="Concluído"}} concluídos",modifier=Modifier.padding(horizontal=16.dp),style=MaterialTheme.typography.bodySmall)
                if(statusVisible) Text(status,modifier=Modifier.padding(16.dp),style=MaterialTheme.typography.bodySmall)
            }
            Text("ONDA Android ${BuildConfig.VERSION_NAME}",Modifier.padding(16.dp),style=MaterialTheme.typography.labelSmall)
        }}) {
        Scaffold(topBar={ TopAppBar(navigationIcon={IconButton(onClick={scope.launch {drawer.open()}},modifier=Modifier.testTag("open-menu")){Text("☰",style=MaterialTheme.typography.titleLarge)}},title={Row(verticalAlignment=Alignment.CenterVertically) {Image(painterResource(R.drawable.ic_onda),"Ícone ONDA",Modifier.size(28.dp).clip(RoundedCornerShape(25)));Column(Modifier.padding(start=8.dp)){Text("ONDA",color=MaterialTheme.colorScheme.primary,fontWeight=FontWeight.Bold,style=MaterialTheme.typography.titleMedium);Text(tabLabel(tab),style=MaterialTheme.typography.labelSmall)}}}) }) { padding ->
            Column(Modifier.fillMaxSize().padding(padding)) {
                if(busy) LinearProgressIndicator(Modifier.fillMaxWidth())
                if(statusVisible) Row(Modifier.fillMaxWidth().padding(horizontal=16.dp),verticalAlignment=Alignment.CenterVertically) {
                    Text(status,Modifier.weight(1f).testTag("app-status"),style=MaterialTheme.typography.bodySmall,maxLines=2)
                    if(busy) TextButton(onClick={vm.cancel()}) {Text("Cancelar")}
                    else TextButton(onClick={statusVisible=false}) {Text("×")}
                }
                Box(Modifier.weight(1f)) {
                    pages.SaveableStateProvider(tab) {when(tab) {
                        "Pesquisar"->SearchPage(vm,onConnectSpotify={settingsCategory="Contas";showSettings=true})
                        "Links e fila"->LinksPage(vm)
                        "Imagens"->ImagesPage(vm)
                        "Playlists / Álbuns"->CollectionsPage(vm)
                        "Histórico"->HistoryPage(vm,onEditMetadata={metadataUri=it.uri;tab="Metadados"})
                        "Efeitos"->EffectsPage(vm)
                        "Metadados"->MetadataPage(vm,metadataUri){metadataUri=null}
                    }}
                }
            }
        }
        }
        question?.let { ChoiceWindow(it,vm) }
        if(showSettings) SettingsWindow(vm,initialCategory=settingsCategory) {showSettings=false}
        if(youtubeSession) YouTubeSessionWindow {youtubeSession=false}
        if(showLicenses) LicensesWindow {showLicenses=false}
        if(welcome) AlertDialog(onDismissRequest={preferences.edit().putBoolean("welcome_seen",true).apply();welcome=false},title={Text("Bem-vindo ao Onda")},
            text={Text("Ajuste o básico para começar. Você pode fechar esta janela e configurar tudo depois.")},
            confirmButton={TextButton(onClick={preferences.edit().putBoolean("welcome_seen",true).apply();welcome=false;settingsCategory="Aparência";showSettings=true}){Text("Configurações")}},
            dismissButton={TextButton(onClick={preferences.edit().putBoolean("welcome_seen",true).apply();welcome=false}){Text("Agora não")}})
        notice?.let {current->AlertDialog(onDismissRequest=vm::dismissNotice,title={Text(current.title)},text={Column(Modifier.heightIn(max=320.dp).verticalScroll(rememberScrollState())){Text(current.message)}},confirmButton={TextButton(onClick=vm::dismissNotice){Text("OK")}})}
    }
}
fun tabLabel(tab: String)=when(tab) {"Metadados"->"Editar metadados";"Pesquisar"->"Pesquisar músicas";"Efeitos"->"Slowed / Sped Up";"Playlists / Álbuns"->"Álbuns e playlists";else->tab}

@Composable fun PageTitle(title: String, description: String) {
    Column(Modifier.fillMaxWidth().padding(vertical=8.dp),horizontalAlignment=Alignment.CenterHorizontally) {
        Text(title,style=MaterialTheme.typography.titleLarge,fontWeight=FontWeight.Bold,textAlign=TextAlign.Center)
        Text(description,style=MaterialTheme.typography.bodySmall,textAlign=TextAlign.Center,modifier=Modifier.padding(top=6.dp))
    }
}
@Composable fun Select(label: String, value: String, choices: List<String>, modifier: Modifier=Modifier, changed: (String)->Unit) {
    var open by remember { mutableStateOf(false) }
    Column(modifier) {
        if(label.isNotBlank()) Text(label,style=MaterialTheme.typography.labelMedium)
        Box { OutlinedButton(onClick={open=true},modifier=Modifier.fillMaxWidth().heightIn(min=40.dp),shape=RoundedCornerShape(10.dp),contentPadding=PaddingValues(horizontal=12.dp,vertical=6.dp)) {Text(value,Modifier.weight(1f),maxLines=1,style=MaterialTheme.typography.bodyMedium);Text("▾",Modifier.padding(start=6.dp))}
            DropdownMenu(expanded=open,onDismissRequest={open=false}) { choices.forEach { choice-> DropdownMenuItem(text={Text(choice)},onClick={changed(choice);open=false}) } }
        }
    }
}
@Composable fun Toggle(text: String, checked: Boolean, changed: (Boolean)->Unit) {
    Row(Modifier.fillMaxWidth().clickable {changed(!checked)},verticalAlignment=Alignment.CenterVertically) {
        Checkbox(checked=checked,onCheckedChange=changed); Text(text,Modifier.weight(1f),style=MaterialTheme.typography.bodyMedium)
    }
}
val modes=linkedMapOf("Vídeo · melhor qualidade (MKV)" to "video","Vídeo · MP4" to "mp4",
    "Áudio · original, sem recodificar" to "original","Áudio · MP3 (320 kbps)" to "mp3",
    "Áudio · M4A (AAC)" to "m4a","Áudio · FLAC" to "flac","Fotos · todas do carrossel" to "photos",
    "Publicação · fotos e vídeos originais" to "social")
@Composable fun FormatOptions(config: JSONObject, changed: (JSONObject)->Unit, separated:Boolean=false) {
    fun put(key: String, value: Any) {changed(JSONObject(config.toString()).put(key,value))}
    val mode=config.optString("mode","mp3")
    Row(horizontalArrangement=Arrangement.spacedBy(8.dp)) {
        Select("Formato",modes.entries.firstOrNull {it.value==mode}?.key ?: "Áudio · MP3 (320 kbps)",modes.keys.toList(),Modifier.weight(1f)) {put("mode",modes.getValue(it))}
        if(mode in listOf("mp3","m4a")) {
            val qualities=if(mode=="mp3") listOf("320 kbps","256 kbps","192 kbps","128 kbps","96 kbps") else listOf("256 kbps","192 kbps","128 kbps","96 kbps")
            Select("Qualidade de áudio",config.optString("audio_quality").takeIf {it in qualities} ?: qualities.first(),qualities,Modifier.weight(1f)) {put("audio_quality",it)}
        }
    }
    if(separated && mode in listOf("mp4","video","social")) SettingsDivider()
    if(mode in listOf("mp4","video","social")) Row(horizontalArrangement=Arrangement.spacedBy(8.dp)) {
        val heights=listOf("Melhor disponível","2160p / 4K","1440p","1080p","720p","480p")
        Select("Resolução máxima",if(config.isNull("height")) "Melhor disponível" else if(config.optInt("height")==2160) "2160p / 4K" else "${config.optInt("height",1080)}p",heights,Modifier.weight(1f)) {put("height",it.substringBefore(" / ").removeSuffix("p").toIntOrNull() ?: JSONObject.NULL)}
        Select("FPS máximo",if(config.isNull("fps")) "Original" else "${config.optInt("fps")} fps",listOf("Original","24 fps","30 fps","60 fps","120 fps"),Modifier.weight(1f)) {put("fps",it.substringBefore(' ').toIntOrNull() ?: JSONObject.NULL)}
    }
    if(mode=="flac") Text("Links de catálogo em FLAC baixam diretamente do Monochrome, quando disponíveis. Outros links são convertidos; isso não melhora fontes com perdas.",style=MaterialTheme.typography.bodySmall)
}

@Composable fun SearchPage(vm: OndaViewModel, onConnectSpotify: ()->Unit) {
    val queue by OndaStore.items.collectAsStateWithLifecycle()
    val searchQueue=remember(queue) {queue.filter {it.config.optString("_origin")=="search"}}
    val active by OndaStore.active.collectAsStateWithLifecycle()
    val running by OndaStore.running.collectAsStateWithLifecycle()
    val results by vm.searchResults.collectAsStateWithLifecycle()
    var query by rememberSaveable { mutableStateOf("") }
    var provider by rememberSaveable { mutableStateOf("Deezer") }
    var downloadTrack by rememberSaveable {mutableStateOf<String?>(null)}
    val busy by vm.busy.collectAsStateWithLifecycle()
    val keyboard=LocalSoftwareKeyboardController.current
    fun submitSearch() {
        val text=query.lineSequence().joinToString(" ").trim()
        if(text.isNotBlank() && !vm.busy.value) {keyboard?.hide();vm.search(text,provider)}
    }
    downloadTrack?.let {raw->key(raw) {
        val track=remember(raw) {JSONObject(raw)}
        TrackDownloadDialog(track,OndaStore.settings.value,onDismiss={downloadTrack=null},onSubmit={options,now->
            try {
                val id=vm.queueTrack(track,options=options,origin="search",immediate=now)
                if(now)DownloadService.start(OndaStore.context,id)
                downloadTrack=null
            } catch(error:Exception) {vm.showNotice(if(now) "Baixar agora" else "Adicionar à fila",error.message ?: "Não foi possível adicionar a música.")}
        })
    }}
    LazyColumn(Modifier.fillMaxSize().padding(horizontal=16.dp),verticalArrangement=Arrangement.spacedBy(6.dp)) {
        item {PageTitle("Encontre sua próxima música.","Pesquise artista ou música, ou cole um link de faixa.")}
        item {OutlinedTextField(query,{query=it},label={Text("Música, artista ou link")},singleLine=true,
            keyboardOptions=KeyboardOptions(imeAction=ImeAction.Search),keyboardActions=KeyboardActions(onSearch={submitSearch()}),
            modifier=Modifier.fillMaxWidth().testTag("music-query").onPreviewKeyEvent {event->
                if(event.key==Key.Enter || event.key==Key.NumPadEnter) {
                    if(event.type==KeyEventType.KeyDown && event.nativeKeyEvent.repeatCount==0) submitSearch()
                    true
                } else false
            })}
        item {Column {
            Text("Catálogo",style=MaterialTheme.typography.labelMedium)
            Row(horizontalArrangement=Arrangement.spacedBy(8.dp),verticalAlignment=Alignment.CenterVertically) {
                Select("",provider,listOf("Deezer","Apple / iTunes","Spotify"),Modifier.weight(1f)){provider=it}
                Button(onClick={submitSearch()},enabled=query.isNotBlank() && !busy) {Text("Pesquisar")}
            }
        }}
        if(provider=="Spotify") item {
            Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(8.dp),verticalAlignment=Alignment.CenterVertically) {
                OutlinedButton(onClick=onConnectSpotify,modifier=Modifier.testTag("search-connect-spotify")) {Text("Conectar Spotify")}
                Text("Client ID em Configurações → Contas.",Modifier.weight(1f),style=MaterialTheme.typography.bodySmall)
            }
        }
        if(searchQueue.isNotEmpty()) item {
            ElevatedCard(Modifier.fillMaxWidth().testTag("search-queue")) {Column(Modifier.padding(10.dp),verticalArrangement=Arrangement.spacedBy(4.dp)) {
                Text("Fila da pesquisa · ${searchQueue.count {it.state=="Concluído"}} de ${searchQueue.size} concluídas",style=MaterialTheme.typography.titleSmall)
                LazyColumn(Modifier.fillMaxWidth().heightIn(max=180.dp)) {items(searchQueue,key={it.id}) {item->Column(Modifier.padding(vertical=6.dp)) {
                    Row(Modifier.fillMaxWidth(),verticalAlignment=Alignment.CenterVertically) {
                        Text(item.title,Modifier.weight(1f),maxLines=2,style=MaterialTheme.typography.bodyMedium)
                        TextButton(onClick={OndaStore.remove(setOf(item.id))},enabled=item.id!=active && item.state !in listOf("Baixando","Aguardando escolha"),modifier=Modifier.testTag("remove-search-${item.id}")){Text("Remover")}
                    }
                    Text(item.state,style=MaterialTheme.typography.labelMedium)
                    if(item.state in listOf("Baixando","Aguardando escolha")) LinearProgressIndicator(progress={item.progress/100},modifier=Modifier.fillMaxWidth())
                    if(item.message.isNotBlank()) Text(item.message,style=MaterialTheme.typography.bodySmall,maxLines=2)
                }}}
                Row(Modifier.horizontalScroll(rememberScrollState())) {
                    TextButton(onClick={DownloadService.batch(OndaStore.context,searchQueue.filter {it.state=="Pendente"}.map {it.id})},enabled=searchQueue.any {it.state=="Pendente"}){Text("Baixar fila da pesquisa")}
                    TextButton(onClick={OndaStore.retry(searchQueue.filter {it.state=="Erro"}.map {it.id}.toSet())},enabled=searchQueue.any {it.state=="Erro"}){Text("Tentar novamente")}
                    TextButton(onClick={OndaStore.remove(searchQueue.filter {it.id!=OndaStore.active.value}.map {it.id}.toSet())}){Text("Limpar fila da pesquisa")}
                }
            }}
        }
        if(results.isEmpty()) item {Text("Sua biblioteca começa com uma busca",fontWeight=FontWeight.Bold);Text("Encontre a música e escolha a versão que você quer.",style=MaterialTheme.typography.bodySmall)}
        items(results,contentType={"search_track"}) {record-> TrackCard(record,vm,onDownload={downloadTrack=record.toString()}) }
        item {Text("Catálogo e capa: plataforma selecionada  •  Áudio: YouTube / FLAC: Monochrome",style=MaterialTheme.typography.bodySmall)}
        item {Spacer(Modifier.height(12.dp))}
    }
}
@Composable fun TrackCard(record: JSONObject, vm: OndaViewModel, onDownload:()->Unit) {
    val playing by vm.previewActive.collectAsStateWithLifecycle()
    val playingUrl by vm.previewUrl.collectAsStateWithLifecycle()
    val url=record.cleanString("preview_url")
    val thisPlaying=playing && playingUrl==url
    Card(Modifier.fillMaxWidth(),colors=CardDefaults.cardColors(containerColor=MaterialTheme.colorScheme.background,contentColor=MaterialTheme.colorScheme.onBackground),elevation=CardDefaults.cardElevation(defaultElevation=0.dp)) { Column(Modifier.padding(12.dp)) {
        Row(verticalAlignment=Alignment.CenterVertically) {
            AsyncImage(model=record.cleanString("cover_url"),contentDescription="Capa do álbum",modifier=Modifier.size(60.dp))
            Column(Modifier.padding(start=12.dp).weight(1f)) {Text(record.cleanString("title"),fontWeight=FontWeight.Bold);Text(record.stringList("artists"),style=MaterialTheme.typography.bodySmall);Text(record.cleanString("album"),style=MaterialTheme.typography.bodySmall);if(record.optLong("duration_ms")>0) Text(mediaClock(record.optLong("duration_ms")/1000),style=MaterialTheme.typography.labelSmall)}
        }
        Row(Modifier.horizontalScroll(rememberScrollState())) {
            TextButton(onClick={if(thisPlaying) vm.stopPreview() else if(url.isNotBlank()) vm.preview(url,OndaStore.settings.value.optInt("search_preview",25)) else vm.status.value="Esta faixa não oferece prévia no catálogo."}) {Text(if(thisPlaying) "Parar prévia" else "Ouvir prévia")}
            TextButton(onClick={vm.queueTrack(record,origin="search")}) {Text("Adicionar à fila")}
            Button(onClick=onDownload) {Text("Baixar agora")}
        }
    }}
}

@Composable fun LinksPage(vm: OndaViewModel) {
    val active by OndaStore.active.collectAsStateWithLifecycle()
    val settings by OndaStore.settings.collectAsStateWithLifecycle()
    val queue by OndaStore.items.collectAsStateWithLifecycle()
    val running by OndaStore.running.collectAsStateWithLifecycle()
    val shared by OndaStore.sharedLink.collectAsStateWithLifecycle()
    val logs by OndaStore.messages.collectAsStateWithLifecycle()
    var link by rememberSaveable {mutableStateOf("")}
    var selected by remember {mutableStateOf(setOf<String>())}
    var showLogs by remember {mutableStateOf(false)}
    var clear by remember {mutableStateOf(false)}
    LaunchedEffect(queue) {OndaStore.selectAll.collect {selected=queue.filterNot {it.config.optBoolean("_immediate")}.map {it.id}.toSet()}}
    LaunchedEffect(shared) {if(shared.isNotBlank()) {link=shared;OndaStore.sharedLink.value=""}}
    fun add(now: Boolean) {
        val urls=link.lines().map {it.trim()}.filter {it.isNotBlank()}
        val ids=urls.map {vm.enqueueLink(it,immediate=now)}
        link=""
        if(now && ids.isNotEmpty()) DownloadService.batch(OndaStore.context,ids)
    }
    LazyColumn(Modifier.fillMaxSize().padding(horizontal=16.dp),verticalArrangement=Arrangement.spacedBy(8.dp)) {
        item {PageTitle("Do link para sua biblioteca.","Músicas, vídeos e fotos, organizados do seu jeito.")}
        item {OutlinedTextField(link,{link=it},label={Text("LINKS")},placeholder={Text("YouTube, Instagram, TikTok, Kwai… um link por linha")},minLines=2,modifier=Modifier.fillMaxWidth().testTag("links-input"),singleLine=false)}
        item {FormatOptions(settings,OndaStore::saveSettings)}
        item {Toggle("Baixar playlist de vídeo",settings.optBoolean("link_playlist")){OndaStore.saveSettings(JSONObject(settings.toString()).put("link_playlist",it))}}
        item {Row(horizontalArrangement=Arrangement.spacedBy(8.dp)) {OutlinedButton(onClick={add(false)},enabled=link.isNotBlank()) {Text("Adicionar à fila")};Button(onClick={add(true)},enabled=link.isNotBlank()) {Text("Baixar agora")}}}
        item {Row(Modifier.horizontalScroll(rememberScrollState())) {
            TextButton(onClick={selected=queue.filterNot {it.config.optBoolean("_immediate")}.map {it.id}.toSet()}) {Text("Selecionar tudo")}
            TextButton(onClick={OndaStore.remove(selected);selected=emptySet()}) {Text("Remover selecionados")}
            TextButton(onClick={clear=true}) {Text("Limpar fila")}
            TextButton(onClick={OndaStore.retry(selected)}) {Text("Tentar novamente")}
        }}
        items(queue,key={it.id}) {item->
            val immediate=item.config.optBoolean("_immediate")
            val cardModifier=Modifier.fillMaxWidth().let {base->if(immediate) base else base.clickable {selected=if(item.id in selected) selected-item.id else selected+item.id}}
            ElevatedCard(cardModifier) {
            Column(Modifier.padding(10.dp)) {
                Row(verticalAlignment=Alignment.CenterVertically) {
                    if(!immediate) Checkbox(item.id in selected,{selected=if(it) selected+item.id else selected-item.id})
                    Text(item.title,Modifier.weight(1f),maxLines=2)
                }
                if(item.state !in listOf("Baixando","Aguardando escolha")) Row {
                    TextButton(onClick={OndaStore.move(item.id,-1)}){Text("↑")}
                    TextButton(onClick={OndaStore.move(item.id,1)}){Text("↓")}
                    TextButton(onClick={OndaStore.move(item.id,0)}){Text("Próximo")}
                    if(immediate) TextButton(onClick={OndaStore.remove(setOf(item.id))},enabled=item.id!=active && item.state !in listOf("Baixando","Aguardando escolha")){Text("Remover")}
                }
                if(immediate && item.state=="Erro") TextButton(onClick={OndaStore.retry(setOf(item.id))}) {Text("Tentar novamente")}
                Text("${item.config.optString("mode").uppercase()} · ${item.state}",style=MaterialTheme.typography.labelMedium)
                if(item.state in listOf("Baixando","Aguardando escolha")) LinearProgressIndicator(progress={item.progress/100},modifier=Modifier.fillMaxWidth().padding(vertical=6.dp))
                if(item.message.isNotBlank()) Text(item.message,style=MaterialTheme.typography.bodySmall,maxLines=3)
            }
        }}
        item {Row(horizontalArrangement=Arrangement.spacedBy(8.dp)) {
            Button(onClick={DownloadService.start(OndaStore.context)},enabled=queue.any {it.state=="Pendente"}){Text("Baixar fila")}
            OutlinedButton(onClick={DownloadService.stop(OndaStore.context)},enabled=running){Text("Parar")}
            TextButton(onClick={showLogs=!showLogs}){Text("Ver detalhes")}
        }}
        if(showLogs) item {Text(logs.takeLast(35).joinToString("\n"),style=MaterialTheme.typography.bodySmall)}
    }
    if(clear) AlertDialog(onDismissRequest={clear=false},title={Text("Limpar fila?")},text={Text("Remove todos os itens, exceto o download em andamento. Seus arquivos são preservados.")},confirmButton={TextButton(onClick={OndaStore.remove(queue.map {it.id}.toSet());clear=false}){Text("Limpar")}},dismissButton={TextButton(onClick={clear=false}){Text("Cancelar")}})
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
    Column(Modifier.verticalScroll(rememberScrollState()).padding(16.dp),verticalArrangement=Arrangement.spacedBy(6.dp)) {
        PageTitle("Imagens do seu jeito.","Baixe, converta e ajuste o tamanho sem cortar a imagem.")
        OutlinedTextField(link,{link=it;source=""},label={Text("Link da imagem ou publicação")},modifier=Modifier.fillMaxWidth(),singleLine=true)
        TextButton(onClick={local()}){Text(if(source.isBlank()) "Escolher imagem" else File(source).name)}
        ImageOptions(settings,OndaStore::saveSettings)
        OutlinedButton(onClick={vm.operation("image_preview",imageConfig()){preview=it.getString("path");dimensions="${it.optInt("width")} × ${it.optInt("height")}"}},enabled=link.isNotBlank() || source.isNotBlank()){Text("Ver prévia")}
        if(preview.isNotBlank()) {AsyncImage(File(preview),"Prévia da imagem",Modifier.fillMaxWidth().heightIn(max=240.dp));Text(dimensions)}
        Button(onClick={if(source.isNotBlank()) vm.operation("image_convert",imageConfig()) else {val id=OndaStore.enqueue(link,options=JSONObject(settings.toString()).put("mode","photos"),extra=JSONObject().put("_immediate",true));DownloadService.start(OndaStore.context,id);link=""}},enabled=link.isNotBlank() || source.isNotBlank()) {Text("Baixar agora")}
        OutlinedButton(onClick={OndaStore.enqueue(link,options=JSONObject(settings.toString()).put("mode","photos"));link=""},enabled=link.isNotBlank()){Text("Adicionar à fila")}
        Text("SVG incorpora a imagem original; não vetoriza. Animações usam o primeiro quadro.",style=MaterialTheme.typography.bodySmall)
    }
}
@Composable fun ImageOptions(config: JSONObject, change: (JSONObject)->Unit, separated:Boolean=false) {
    fun put(key: String,value: Any) {change(JSONObject(config.toString()).put(key,value))}
    Select("Formato",config.optString("image_format","Original"),listOf("Original","JPG","PNG","WebP","SVG")){put("image_format",it)}
    if(separated)SettingsDivider()
    Text("Largura × altura (px)",style=MaterialTheme.typography.labelMedium)
    Row(horizontalArrangement=Arrangement.spacedBy(8.dp)) {
        OutlinedTextField(config.optInt("image_width").takeIf {it>0}?.toString() ?: "",{put("image_width",it.toIntOrNull()?.coerceIn(0,16384) ?: 0)},label={Text("Largura")},modifier=Modifier.weight(1f),singleLine=true)
        OutlinedTextField(config.optInt("image_height").takeIf {it>0}?.toString() ?: "",{put("image_height",it.toIntOrNull()?.coerceIn(0,16384) ?: 0)},label={Text("Altura")},modifier=Modifier.weight(1f),singleLine=true)
    }
    if(separated)SettingsDivider()
    Toggle("Manter proporção (sem ampliar ou distorcer)",config.optBoolean("keep_ratio",true)){put("keep_ratio",it)}
}

@Composable fun CollectionsPage(vm: OndaViewModel) {
    val collection by vm.collection.collectAsStateWithLifecycle()
    var url by rememberSaveable {mutableStateOf("")}
    var filter by rememberSaveable {mutableStateOf("")}
    var selected by remember {mutableStateOf(setOf<String>())}
    var options by remember {mutableStateOf(OndaStore.collectionOptions())}
    LaunchedEffect(options) {OndaStore.saveCollectionOptions(options)}
    var listOnly by remember {mutableStateOf(false)}
    val import=rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) {uri->if(uri!=null) vm.importLocal(uri,"playlist") {vm.importCollection(it.absolutePath)}}
    var exported by remember {mutableStateOf("")}
    val export=rememberLauncherForActivityResult(ActivityResultContracts.CreateDocument("text/plain")) {uri->if(uri!=null) OndaStore.context.contentResolver.openOutputStream(uri)?.use {it.write(exported.toByteArray())}}
    val tracks=remember(collection) {collection.optJSONArray("tracks")?.objects() ?: emptyList()}
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
    LazyColumn(Modifier.fillMaxSize().padding(horizontal=16.dp),verticalArrangement=Arrangement.spacedBy(8.dp)) {
        item {PageTitle("Seus álbuns e playlists na biblioteca.","Busque por música ou artista. As ações usam somente os itens visíveis selecionados. Formato e qualidade são próprios desta aba.")}
        item {OutlinedTextField(url,{url=it},label={Text("Link da playlist ou álbum")},modifier=Modifier.fillMaxWidth(),singleLine=true)}
        item {Row(Modifier.horizontalScroll(rememberScrollState())) {
            Button(onClick={vm.loadCollection(url,options)},enabled=url.isNotBlank()){Text("Carregar álbum ou playlist")}
            TextButton(onClick={import.launch(arrayOf("text/*","application/octet-stream","application/vnd.ms-excel"))}){Text("Importar arquivo")}
            TextButton(onClick={listOnly=true}){Text("Ver lista")}
        }}
        item {FormatOptions(options,changed={options=it})}
        if(collection.optString("title").isNotBlank()) item {
            Card(Modifier.fillMaxWidth().testTag("collection-card"),colors=CardDefaults.cardColors(containerColor=MaterialTheme.colorScheme.background)) {
                Row(Modifier.fillMaxWidth().padding(vertical=12.dp),verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.spacedBy(12.dp)) {
                    if(collection.cleanString("cover_url").isNotBlank()) AsyncImage(model=collection.cleanString("cover_url"),contentDescription="Capa de ${collection.optString("title")}",contentScale=androidx.compose.ui.layout.ContentScale.Crop,modifier=Modifier.size(88.dp).clip(RoundedCornerShape(10.dp)))
                    else Surface(Modifier.size(88.dp),shape=RoundedCornerShape(10.dp),color=MaterialTheme.colorScheme.surfaceVariant) {Box(contentAlignment=Alignment.Center){Text("♫",style=MaterialTheme.typography.headlineLarge)}}
                    Column(Modifier.weight(1f),verticalArrangement=Arrangement.spacedBy(4.dp)) {
                        Text(collection.optString("title"),fontWeight=FontWeight.Bold,style=MaterialTheme.typography.titleMedium)
                        if(collection.cleanString("subtitle").isNotBlank()) Text(collection.cleanString("subtitle"),style=MaterialTheme.typography.bodySmall)
                        Text("${if(collection.optString("kind")=="album") "Álbum" else "Playlist"} · ${tracks.size} músicas",style=MaterialTheme.typography.bodySmall)
                    }
                }
                if(collection.cleanString("note").isNotBlank()) Text(collection.cleanString("note"),style=MaterialTheme.typography.bodySmall,modifier=Modifier.padding(bottom=8.dp))
            }
        }
        item {OutlinedTextField(filter,{filter=it},label={Text("Buscar nesta lista")},modifier=Modifier.fillMaxWidth(),singleLine=true);Text("${visible.size} de ${tracks.size}",style=MaterialTheme.typography.bodySmall)}
        item {Row(Modifier.horizontalScroll(rememberScrollState())) {
            TextButton(onClick={selected=selected+visible.map {it.optString("source_url")}}){Text("Selecionar visíveis")}
            TextButton(onClick={selected=emptySet()}){Text("Limpar seleção")}
            TextButton(onClick={vm.operation("matches",OndaStore.config(options).put("tracks",JSONArray(chosen()))){vm.collection.value=JSONObject(collection.toString()).put("tracks",JSONArray(mergeTrackMatches(tracks,it.getJSONArray("tracks").objects())))}}){Text("Conferir correspondências")}
        }}
        items(visible,contentType={"collection_track"}) {record->Row(Modifier.fillMaxWidth().clickable {val id=record.optString("source_url");selected=if(id in selected) selected-id else selected+id},verticalAlignment=Alignment.CenterVertically) {
            Checkbox(record.optString("source_url") in selected,{val id=record.optString("source_url");selected=if(it) selected+id else selected-id})
            Column(Modifier.weight(1f)) {Text(record.optString("title"));Text(record.stringList("artists"),style=MaterialTheme.typography.bodySmall);record.optJSONObject("youtube_match")?.let {Text(it.optString("title"),color=MaterialTheme.colorScheme.primary,style=MaterialTheme.typography.bodySmall)}}
        }}
        item {Row(Modifier.horizontalScroll(rememberScrollState())) {Button(onClick={enqueue(true)},enabled=chosen().isNotEmpty()){Text("Baixar agora")};TextButton(onClick={enqueue(false)},enabled=chosen().isNotEmpty()){Text("Adicionar à fila")}}}
        item {Row {for(format in listOf("txt","m3u")) TextButton(onClick={vm.operation("export_list",JSONObject().put("tracks",JSONArray(tracks)).put("format",format)){exported=it.getString("text");export.launch("${collection.optString("title","Playlist")}.$format")}}){Text("Exportar ${format.uppercase()}")}}}
    }
    if(listOnly) Dialog(onDismissRequest={listOnly=false}) {Surface(shape=RoundedCornerShape(20.dp)) {Column(Modifier.fillMaxWidth().fillMaxHeight(.85f).padding(16.dp)) {
        Text(collection.optString("title","Músicas"),style=MaterialTheme.typography.titleLarge)
        LazyColumn(Modifier.weight(1f)) {items(visible){Text("${it.stringList("artists")} - ${it.optString("title")}",Modifier.padding(vertical=8.dp))}}
        TextButton(onClick={listOnly=false}){Text("Fechar")}
    }}}
}

@Composable fun HistoryPage(vm: OndaViewModel,onEditMetadata:(HistoryItem)->Unit) {
    val history by OndaStore.history.collectAsStateWithLifecycle()
    var filter by rememberSaveable {mutableStateOf("")}
    val visible=remember(history,filter) {history.filter {it.title.contains(filter,true)}}
    LazyColumn(Modifier.fillMaxSize().padding(horizontal=16.dp),verticalArrangement=Arrangement.spacedBy(8.dp)) {
        item {PageTitle("Sua biblioteca de downloads.","Encontre, abra e compartilhe o que já baixou.")}
        item {OutlinedTextField(filter,{filter=it},label={Text("Pesquisar no histórico")},modifier=Modifier.fillMaxWidth(),singleLine=true)}
        items(visible,key={it.id}) {item->ElevatedCard(Modifier.fillMaxWidth()) {Column(Modifier.padding(12.dp)) {
            Row(Modifier.fillMaxWidth(),verticalAlignment=Alignment.CenterVertically) {
                Text(item.title,Modifier.weight(1f),fontWeight=FontWeight.Bold)
                TextButton(onClick={OndaStore.removeHistory(item.id)},modifier=Modifier.testTag("remove-history-${item.id}")){Text("Remover")}
            }
            Text("${item.mode.uppercase()} · %.1f MB".format(item.size/1048576.0),style=MaterialTheme.typography.bodySmall)
            Row(Modifier.horizontalScroll(rememberScrollState())) {TextButton(onClick={runCatching {OndaStore.open(item.uri,item.mode)}.onFailure {OndaStore.log("Nenhum aplicativo disponível para abrir este arquivo.")}}){Text("Abrir arquivo")};TextButton(onClick={vm.openHistoryFolder(item.uri)},modifier=Modifier.testTag("open-history-folder-${item.id}")){Text("Abrir pasta")};TextButton(onClick={OndaStore.share(item.uri,item.title)}){Text("Compartilhar")}
                if(item.mode.lowercase() in setOf("mp3","m4a","flac","wav","ogg","opus")) TextButton(onClick={onEditMetadata(item)}) {Text("Editar metadados")}
                if(historySupportsEffects(item)) TextButton(onClick={vm.useInEffects(item.uri)}) {Text("Usar nos efeitos")}
            }
        }}}
        item {TextButton(onClick={OndaStore.clearHistory()}){Text("Limpar histórico")}}
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
    LaunchedEffect(vm) {while(true) {position=vm.player.currentPosition/1000f;duration=(vm.player.duration/1000f).coerceAtLeast(1f);playing=vm.player.isPlaying;delay(200)}}
    Slider(value=position.coerceIn(0f,duration),onValueChange={vm.player.seekTo((it*1000).toLong())},valueRange=0f..duration)
    Row(verticalAlignment=Alignment.CenterVertically) {TextButton(onClick={if(playing) vm.player.pause() else vm.player.play()}){Text(if(playing) "Pausar" else "Reproduzir")};Text("${mediaClock(position.toLong())} / ${mediaClock(duration.toLong())}",style=MaterialTheme.typography.bodySmall);TextButton(onClick={vm.stopPreview()}){Text("Parar")}}
}

@Composable fun EffectsPage(vm: OndaViewModel) {
    var source by rememberSaveable {mutableStateOf("")}
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
    Column(Modifier.verticalScroll(rememberScrollState()).padding(16.dp),verticalArrangement=Arrangement.spacedBy(6.dp)) {
        PageTitle("Slowed · Sped Up · Reverb","Desacelere ou acelere sua música. Adicione reverb se quiser.")
        OutlinedButton(onClick={choose.launch(arrayOf("audio/*"))},modifier=Modifier.fillMaxWidth()){Text(if(source.isBlank()) "Abrir áudio" else importedAudioName(source),maxLines=2)}
        val presets=remember {linkedMapOf("Original" to (100f to 0f),"Slowed leve" to (90f to 0f),"Slowed intenso" to (75f to 0f),"Sped Up leve" to (115f to 0f),"Sped Up intenso" to (130f to 0f),"Sped Up + Reverb" to (120f to 25f),"Só Reverb" to (100f to 30f),"Clássico" to (85f to 25f),"Atmosférico" to (75f to 50f))}
        val preset=presets.entries.firstOrNull {it.value.first.toInt()==speed.toInt() && it.value.second.toInt()==reverb.toInt()}?.key ?: "Personalizado"
        Select("Preset",preset,presets.keys.toList()) {val value=presets.getValue(it);speed=value.first;reverb=value.second}
        Text("Velocidade · ${speed.toInt()}% · ${if(speed<100) "Slowed" else if(speed>100) "Sped Up" else "original"}",fontWeight=FontWeight.Bold)
        Slider(speed,{speed=it.toInt().toFloat()},valueRange=50f..150f,modifier=Modifier.testTag("effects-speed"))
        Text("Reverb · ${reverb.toInt()}%${if(reverb==0f) " · desligado" else ""}",fontWeight=FontWeight.Bold)
        Slider(reverb,{reverb=it.toInt().toFloat()},valueRange=0f..100f,modifier=Modifier.testTag("effects-reverb"))
        Toggle("Manter tom (pitch) ao alterar a velocidade",pitch){pitch=it}
        Text("Posição na música · ${mediaClock(start.toLong())} / ${mediaClock(duration.toLong())}")
        Slider(start.coerceIn(0f,duration.coerceAtLeast(1f)),{start=it},valueRange=0f..duration.coerceAtLeast(1f))
        Row(horizontalArrangement=Arrangement.spacedBy(8.dp)) {
        TextButton(onClick={vm.stopPreview();vm.preview(source,OndaStore.settings.value.optInt("effects_preview",25),start.toInt())},enabled=source.isNotBlank()){Text("Ouvir original")}
        Button(onClick={vm.previewEffects(source,speed.toInt(),reverb.toInt(),pitch,start.toInt())},enabled=source.isNotBlank()){Text("Ouvir com efeitos")}
        }
        val previewUrl by vm.previewUrl.collectAsStateWithLifecycle()
        if(previewUrl.isNotBlank()) PlayerControls(vm)
        Text("Arraste a barra para escolher o trecho. A duração da prévia pode ser alterada em Configurações. Ajuste os efeitos enquanto ouve.",style=MaterialTheme.typography.bodySmall)
        Select("Salvar como",format.uppercase(),listOf("MP3","M4A","FLAC","WAV")){format=it.lowercase()}
        Button(onClick={
            val name=importedAudioName(source).substringBeforeLast('.')
            val suffix=effectName().let {if(it.isBlank()) "" else " - $it"}
            val output=File(OndaStore.config().getString("folder"),"$name$suffix.$format")
            val config=OndaStore.config().put("source",source).put("output",output.absolutePath).put("speed",speed.toInt()).put("reverb",reverb.toInt()).put("keep_pitch",pitch)
            config.put("_operation","effects")
            val id=OndaStore.enqueue(source,output.name,extra=config)
            DownloadService.start(OndaStore.context,id)
            vm.status.value="Exportação adicionada à fila. Acompanhe em Links e fila."
        },enabled=source.isNotBlank()){Text("Exportar música inteira")}
    }
}

fun importedAudioName(path: String): String = File(path).name.replaceFirst(Regex("^audio-[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}-"),"")
