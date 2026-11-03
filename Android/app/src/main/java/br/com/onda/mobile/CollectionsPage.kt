package br.com.onda.mobile

import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.*
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.*
import androidx.compose.foundation.selection.toggleable
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import coil.compose.AsyncImage
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import org.json.JSONArray
import org.json.JSONObject

@Composable fun CollectionsPage(vm: OndaViewModel,onConnectSpotify:()->Unit={}) {
    val collection by vm.collection.collectAsStateWithLifecycle()
    var referenceResult by remember {mutableStateOf("")}
    val compareFile=rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) {uri->if(uri!=null)vm.importLocal(uri,"collection-reference") {file->
        vm.operation("compare_collection_file",JSONObject().put("source",file.absolutePath).put("tracks",vm.collection.value.optJSONArray("tracks") ?: JSONArray())) {referenceResult=it.optString("message");file.delete()}
    }}
    LaunchedEffect(collection){referenceResult=""}
    val comparison by vm.collectionComparison.collectAsStateWithLifecycle()
    val busy by vm.busy.collectAsStateWithLifecycle()
    val spotifyConnected by vm.spotifyConnected.collectAsStateWithLifecycle()
    val spotifyPlaylists by vm.spotifyPlaylists.collectAsStateWithLifecycle()
    val spotifyNext by vm.spotifyPlaylistsNext.collectAsStateWithLifecycle()
    val spotifyLoaded by vm.spotifyPlaylistsLoaded.collectAsStateWithLifecycle()
    var libraryTab by rememberSaveable {mutableIntStateOf(if(collection.optString("title").isNotBlank())1 else if(vm.spotifyConnected.value)2 else 0)}
    var advanced by rememberSaveable {mutableStateOf(false)}
    var moreActions by remember {mutableStateOf(false)}
    var saved by remember {mutableStateOf<List<JSONObject>>(emptyList())}
    val libraryScope=rememberCoroutineScope()
    val listState=rememberLazyListState()
    LaunchedEffect(libraryTab){listState.scrollToItem(0)}
    LaunchedEffect(libraryTab,spotifyConnected){if(libraryTab==2 && spotifyConnected && !spotifyLoaded)vm.loadSpotifyPlaylists()}
    LaunchedEffect(Unit){saved=CollectionsLibrary.read()}
    var syncReload by remember {mutableStateOf(false)}
    val settings by OndaStore.settings.collectAsStateWithLifecycle()
    val adding by vm.addingToQueue.collectAsStateWithLifecycle()
    var url by rememberSaveable {mutableStateOf("")}
    var filter by rememberSaveable {mutableStateOf("")}
    var artistFilter by rememberSaveable {mutableStateOf("")}
    var albumFilter by rememberSaveable {mutableStateOf("")}
    var releaseFilter by rememberSaveable {mutableStateOf("")}
    var libraryQuery by rememberSaveable {mutableStateOf("")}
    var libraryKind by rememberSaveable {mutableStateOf("")}
    var releaseDate by rememberSaveable {mutableStateOf("")}
    var creationDate by rememberSaveable {mutableStateOf("")}
    var librarySort by rememberSaveable {mutableStateOf("")}
    var libraryDescending by rememberSaveable {mutableStateOf(false)}
    var trackSort by rememberSaveable {mutableStateOf("")}
    var trackDescending by rememberSaveable {mutableStateOf(false)}
    val savedIndex=remember(saved){collectionFilterIndex(saved,true)}
    val spotifyIndex=remember(spotifyPlaylists){collectionFilterIndex(spotifyPlaylists,true)}
    val savedVisible=remember(savedIndex,libraryQuery,libraryKind,releaseDate,creationDate,librarySort,libraryDescending){
        orderCollectionRows(filterCollectionEntries(savedIndex,libraryQuery,kind=libraryKind,collections=true).filter {row->collectionDateMatches(collectionDate(row),if(row.optString("kind")=="album")releaseDate else creationDate)},librarySort,libraryDescending)
    }
    val spotifyVisible=remember(spotifyIndex,libraryQuery,creationDate,librarySort,libraryDescending){orderCollectionRows(filterCollectionEntries(spotifyIndex,libraryQuery,date=creationDate,collections=true),librarySort,libraryDescending)}
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
    LaunchedEffect(collection.optString("_collection_url"),collection.optString("title")){selected=emptySet();filter="";artistFilter="";albumFilter="";releaseFilter=""}
    val import=rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) {uri->if(uri!=null) vm.importLocal(uri,"playlist") {vm.importCollection(it.absolutePath)}}
    var exported by remember {mutableStateOf("")}
    val export=rememberLauncherForActivityResult(ActivityResultContracts.CreateDocument("text/plain")) {uri->if(uri!=null) OndaStore.context.contentResolver.openOutputStream(uri)?.use {it.write(exported.toByteArray())}}
    val tracks=remember(collection) {collection.optJSONArray("tracks")?.objects() ?: emptyList()}
    val trackKeys=remember(tracks){
        val keys=stableTrackKeys(tracks)
        java.util.IdentityHashMap<JSONObject,String>().apply {tracks.forEachIndexed {index,row->put(row,keys[index])}}
    }
    val syncItems=remember(comparison) {comparison?.optJSONArray("items")?.objects()?.associateBy {it.optInt("index")} ?: emptyMap()}
    val missingTracks=remember(tracks,comparison) {tracks.filterIndexed {index,_->syncItems[index]?.optString("state")=="missing"}}
    val syncBySource=remember(tracks,comparison) {tracks.mapIndexed {index,record->record.optString("source_url") to syncItems[index]}.toMap()}
    val searchIndex=remember(tracks) {collectionFilterIndex(tracks)}
    var settledFilters by remember {mutableStateOf(listOf(filter,artistFilter,albumFilter,releaseFilter))}
    val requestedFilters=listOf(filter,artistFilter,albumFilter,releaseFilter)
    LaunchedEffect(requestedFilters) {delay(150);settledFilters=requestedFilters}
    val visible=remember(searchIndex,settledFilters,trackSort,trackDescending) {
        orderCollectionRows(filterCollectionEntries(searchIndex,settledFilters[0],settledFilters[1],settledFilters[2],date=settledFilters[3]),trackSort,trackDescending)
    }
    LaunchedEffect(visible) {OndaStore.selectAll.collect {selected=selected+visible.map {it.optString("source_url")}}}
    val chosenTracks=remember(visible,selected,requestedFilters,settledFilters) {
        if(requestedFilters!=settledFilters) emptyList() else visible.filter {it.optString("source_url") in selected}
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
            TextButton(onClick={vm.collectionToPlayback(if(selected.isEmpty())visible else chosen())},enabled=visible.isNotEmpty()&&requestedFilters==settledFilters&&!busy){UiText("Usar em reprodução")}
        }

    }
    NavigableList(Modifier.fillMaxSize().imePadding().padding(horizontal=20.dp),navigationId="collection",state=listState) {
        item {ToolHeading("Coleção")}
        item {
            OutlinedTextField(url,{url=it},label={UiText("Link da playlist ou álbum")},singleLine=true,modifier=Modifier.fillMaxWidth(),keyboardOptions=androidx.compose.foundation.text.KeyboardOptions(imeAction=androidx.compose.ui.text.input.ImeAction.Go),keyboardActions=androidx.compose.foundation.text.KeyboardActions(onGo={if(!busy&&url.isNotBlank()){libraryTab=1;vm.loadCollection(url,options)}}))
            Button(onClick={if(busy)vm.cancel() else {libraryTab=1;vm.loadCollection(url,options)}},enabled=busy||url.isNotBlank()) {UiText(if(busy)"Cancelar" else if(tracks.isNotEmpty()&&collection.optString("_collection_url")==url)"Atualizar" else "Carregar")}
        }
        item {ToolTabs(listOf("Salvos","Importar","Spotify"),libraryTab){libraryTab=it}}
        if(libraryTab!=1)item {
            OutlinedTextField(libraryQuery,{libraryQuery=it},label={UiText("Buscar coleções")},singleLine=true,modifier=Modifier.fillMaxWidth().testTag("collection-library-query"))
            if(libraryTab==0)Row(Modifier.horizontalScroll(rememberScrollState()),horizontalArrangement=Arrangement.spacedBy(8.dp)) {
                listOf("" to "Todos","album" to "Álbuns","playlist" to "Playlists").forEach {(kind,label)->FilterChip(selected=libraryKind==kind,onClick={libraryKind=kind},label={UiText(label)})}
            }
            if(libraryTab==0 && libraryKind!="playlist")OutlinedTextField(releaseDate,{releaseDate=it},label={UiText("Data de lançamento")},placeholder={UiText("AAAA ou AAAA-MM-DD")},singleLine=true,modifier=Modifier.fillMaxWidth())
            if(libraryTab==2 || libraryKind!="album")OutlinedTextField(creationDate,{creationDate=it},label={UiText("Data de criação")},placeholder={UiText("AAAA ou AAAA-MM-DD")},singleLine=true,modifier=Modifier.fillMaxWidth())
            if(creationDate.isNotBlank())UiText("Somente coleções com data informada pelo serviço.",style=MaterialTheme.typography.bodySmall)
            CollectionOrdering(librarySort,libraryDescending,listOf("" to "Ordem original","title" to "Nome","date" to "Data de criação / lançamento"),{librarySort=it},{libraryDescending=it})
            TextButton(onClick={libraryQuery="";libraryKind="";releaseDate="";creationDate=""}){UiText("Limpar filtros")}
        }
        if(libraryTab==2) {
            item {
                Row(Modifier.fillMaxWidth(),verticalAlignment=Alignment.CenterVertically) {
                    UiText("Playlists do Spotify",Modifier.weight(1f),style=MaterialTheme.typography.titleMedium)
                    TextButton(enabled=!busy,onClick={if(spotifyConnected)vm.loadSpotifyPlaylists() else onConnectSpotify()}) {UiText(if(spotifyConnected)"Atualizar" else "Conectar")}
                }
                if(!spotifyConnected)UiText("Conecte sua conta Spotify para ver suas playlists.")
            }
            if(spotifyPlaylists.isEmpty() && spotifyConnected && !busy)item {ToolEmpty("album","Nenhuma playlist encontrada","As playlists da conta conectada aparecerão aqui.")}
            if(spotifyPlaylists.isNotEmpty() && spotifyVisible.isEmpty())item {ToolEmpty("search","Nenhuma coleção encontrada","Tente outros filtros.")}
            items(spotifyVisible,key={it.optString("id")},contentType={"spotify_playlist"}) {row->
                ToolCard(Modifier.testTag("spotify-playlist-"+row.optString("id"))) {
                    Row(verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.spacedBy(12.dp)) {
                        Surface(Modifier.size(72.dp),shape=RoundedCornerShape(10.dp),color=MaterialTheme.colorScheme.surfaceVariant) {
                            if(row.optString("cover_url").isNotBlank())AsyncImage(row.optString("cover_url"),translateUi("Capa do álbum"),Modifier.fillMaxSize())
                            else Box(contentAlignment=Alignment.Center){OndaIcon("album")}
                        }
                        Column(Modifier.weight(1f)) {
                            Text(row.optString("title"),style=MaterialTheme.typography.titleMedium,maxLines=2)
                            Text(row.optString("owner"),style=MaterialTheme.typography.bodySmall)
                            if(!row.isNull("count"))UiText("${row.optInt("count")} faixas",style=MaterialTheme.typography.bodySmall)
                        }
                        var menu by remember {mutableStateOf(false)}
                        Box {
                            IconButton(onClick={menu=true},enabled=!busy){OndaIcon("more-vertical","Mais ações")}
                            DropdownMenu(menu,{menu=false}) {
                                DropdownMenuItem(text={UiText("Baixar agora")},onClick={menu=false;vm.openSpotifyPlaylist(row.optString("id"),options,"download");libraryTab=1;url=row.optString("source_url")})
                                DropdownMenuItem(text={UiText("Adicionar à fila")},onClick={menu=false;vm.openSpotifyPlaylist(row.optString("id"),options,"add");libraryTab=1;url=row.optString("source_url")})
                            }
                        }
                    }
                    Row(Modifier.horizontalScroll(rememberScrollState())) {
                        TextButton(enabled=!busy,onClick={vm.openSpotifyPlaylist(row.optString("id"),options);libraryTab=1;url=row.optString("source_url")}){UiText("Abrir coleção")}
                        TextButton(enabled=!busy,onClick={vm.openSpotifyPlaylist(row.optString("id"),options,"playback")}){UiText("Usar em reprodução")}
                    }
                }
            }
            if(spotifyNext>=0)item {OutlinedButton(enabled=!busy,onClick={vm.loadSpotifyPlaylists(true)},modifier=Modifier.fillMaxWidth()){UiText("Carregar mais")}}
        } else         if(libraryTab==0) {
            if(saved.isNotEmpty() && savedVisible.isEmpty())item {ToolEmpty("search","Nenhuma coleção encontrada","Tente outros filtros.")}
            if(saved.isEmpty())item {ToolEmpty("album","Suas coleções ficam aqui","Importe um álbum ou playlist e salve para acessar depois.")}
            items(savedVisible,key={CollectionsLibrary.identity(it)},contentType={"saved_collection"}) {row->
                ToolCard(Modifier.clickable {vm.collection.value=JSONObject(row.toString());vm.collectionComparison.value=null;url=row.optString("_collection_url");selected=emptySet();filter="";libraryTab=1}) {
                    Row(verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.spacedBy(12.dp)) {
                        Surface(Modifier.size(80.dp),shape=RoundedCornerShape(12.dp),color=MaterialTheme.colorScheme.surfaceVariant){
                            if(row.cleanString("cover_url").isNotBlank())AsyncImage(row.cleanString("cover_url"),translateUi("Capa do álbum"),Modifier.fillMaxSize(),contentScale=androidx.compose.ui.layout.ContentScale.Crop)
                            else Box(contentAlignment=Alignment.Center){OndaIcon("album",modifier=Modifier.size(32.dp))}
                        }
                        Column(Modifier.weight(1f),verticalArrangement=Arrangement.spacedBy(4.dp)) {
                            Text(row.optString("title"),style=MaterialTheme.typography.titleMedium,maxLines=2)
                            Text(row.optString("subtitle"),style=MaterialTheme.typography.bodySmall)
                            if(collectionDate(row).isNotBlank())Text(collectionDate(row),style=MaterialTheme.typography.bodySmall)
                            UiText("${row.optJSONArray("tracks")?.length() ?: 0} músicas",style=MaterialTheme.typography.bodySmall)
                        }
                        var menu by remember {mutableStateOf(false)}
                        Box {IconButton(onClick={menu=true}){OndaIcon("more-vertical","Mais ações",Modifier.size(22.dp))}
                            DropdownMenu(menu,{menu=false}) {
                                DropdownMenuItem(text={UiText("Abrir coleção")},onClick={menu=false;vm.collection.value=JSONObject(row.toString());vm.collectionComparison.value=null;url=row.optString("_collection_url");selected=emptySet();filter="";libraryTab=1})
                                DropdownMenuItem(text={UiText("Remover dos salvos")},onClick={menu=false;libraryScope.launch {runCatching {CollectionsLibrary.remove(row)}.onSuccess {saved=it}.onFailure {vm.showNotice("Salvar coleção","Não foi possível salvar a coleção.")}}})
                            }
                        }
                    }
                }
            }
            item {OutlinedButton(onClick={libraryTab=1;import.launch(arrayOf("text/*","application/octet-stream","application/vnd.ms-excel"))},modifier=Modifier.fillMaxWidth()){OndaIcon("add",modifier=Modifier.size(20.dp));Spacer(Modifier.width(8.dp));UiText("Importar lista")}}
        } else {
        item {Box {
            TextButton(onClick={moreActions=true}){UiText("Mais ações")}
            DropdownMenu(moreActions,{moreActions=false}) {
                DropdownMenuItem(text={UiText("Importar arquivo")},onClick={moreActions=false;import.launch(arrayOf("text/*","application/octet-stream","application/vnd.ms-excel"))})
                DropdownMenuItem(text={UiText("Selecionar visíveis")},onClick={moreActions=false;selected=selected+visible.map {it.optString("source_url")}})
                DropdownMenuItem(text={UiText("Limpar seleção")},onClick={moreActions=false;selected=emptySet()})
                DropdownMenuItem(text={UiText("Conferir correspondências")},enabled=chosen().isNotEmpty()&&!busy,onClick={moreActions=false;vm.operation("matches",OndaStore.config(options).put("tracks",JSONArray(chosen()))){vm.collection.value=JSONObject(collection.toString()).put("tracks",JSONArray(mergeTrackMatches(tracks,it.getJSONArray("tracks").objects())))}})
                DropdownMenuItem(text={UiText("Conferir arquivos locais")},enabled=tracks.isNotEmpty()&&!busy,onClick={moreActions=false;syncReload=false;folderPicker.launch(null)})
                DropdownMenuItem(text={UiText("Adicionar ausentes à fila")},enabled=missingTracks.isNotEmpty()&&!busy,onClick={moreActions=false;vm.queueCollection(missingTracks,options,collection.optString("title","Playlist"),false)})
                for(format in listOf("txt","m3u"))DropdownMenuItem(text={UiText("Exportar ${format.uppercase()}")},enabled=tracks.isNotEmpty()&&!busy,onClick={moreActions=false;vm.operation("export_list",JSONObject().put("tracks",JSONArray(tracks)).put("format",format)){exported=it.getString("text");export.launch("${collection.optString("title","Playlist")}.$format")}})
                DropdownMenuItem(text={UiText("Ver lista")},enabled=tracks.isNotEmpty(),onClick={moreActions=false;listOnly=true})
                DropdownMenuItem(text={UiText("Opções de download")},onClick={moreActions=false;advanced=!advanced})
            }
        }}
        if(advanced) {
        comparison?.let {report->item {Text(collectionSyncSummary(report),style=MaterialTheme.typography.bodySmall)}}
        item {ToolCard {FormatOptions(options,changed={options=it},separated=true)}}
        }
        if(collection.optString("title").isNotBlank()) item {
            ToolCard(Modifier.testTag("collection-card")) {
                Row(Modifier.fillMaxWidth().padding(vertical=LayoutSpacing.controls),verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.spacedBy(LayoutSpacing.section)) {
                    if(collection.cleanString("cover_url").isNotBlank()) AsyncImage(model=collection.cleanString("cover_url"),contentDescription=translateUi("Capa de ${collection.optString("title")}",LocalUiLanguage.current),contentScale=androidx.compose.ui.layout.ContentScale.Crop,modifier=Modifier.size(88.dp).clip(RoundedCornerShape(10.dp)))
                    else Surface(Modifier.size(88.dp),shape=RoundedCornerShape(10.dp),color=MaterialTheme.colorScheme.surfaceVariant) {Box(contentAlignment=Alignment.Center){UiText("♫",style=MaterialTheme.typography.headlineLarge)}}
                    Column(Modifier.weight(1f),verticalArrangement=Arrangement.spacedBy(LayoutSpacing.details)) {
                        Text(collection.optString("title"),fontWeight=FontWeight.Bold,style=MaterialTheme.typography.titleMedium)
                        if(collection.cleanString("subtitle").isNotBlank()) Text(collection.cleanString("subtitle"),style=MaterialTheme.typography.bodySmall)
                        UiText("${if(collection.optString("kind")=="album") "Álbum" else "Playlist"} · ${tracks.size} músicas",style=MaterialTheme.typography.bodySmall)
                    }
                }
                OutlinedButton(onClick={libraryScope.launch {val snapshot=JSONObject(collection.toString());val next=(listOf(snapshot)+saved.filter {CollectionsLibrary.identity(it)!=CollectionsLibrary.identity(snapshot)}).take(30);runCatching {CollectionsLibrary.write(next)}.onSuccess {saved=next;vm.status.value="Coleção salva."}.onFailure {vm.showNotice("Salvar coleção","Não foi possível salvar a coleção.")}}},modifier=Modifier.fillMaxWidth()){UiText("Salvar coleção")}
                if(collection.cleanString("coverage_summary").isNotBlank())UiText(collection.cleanString("coverage_summary"),style=MaterialTheme.typography.bodyMedium)
                TextButton(enabled=!busy,onClick={compareFile.launch(arrayOf("text/*","application/octet-stream","application/vnd.ms-excel"))}){UiText("Conferir lista importada")}
                if(referenceResult.isNotBlank())UiText(referenceResult,style=MaterialTheme.typography.bodySmall)
                if(collection.cleanString("note").isNotBlank()) UiText(collection.cleanString("note"),style=MaterialTheme.typography.bodySmall,modifier=Modifier.padding(bottom=8.dp))
            }
        }
        item {
            OutlinedTextField(filter,{filter=it},label={UiText("Título")},modifier=Modifier.fillMaxWidth().testTag("collection-title-filter"),singleLine=true)
            Row(horizontalArrangement=Arrangement.spacedBy(8.dp)) {
                OutlinedTextField(artistFilter,{artistFilter=it},label={UiText("Artista")},modifier=Modifier.weight(1f),singleLine=true)
                OutlinedTextField(albumFilter,{albumFilter=it},label={UiText("Álbum")},modifier=Modifier.weight(1f),singleLine=true)
            }
            OutlinedTextField(releaseFilter,{releaseFilter=it},label={UiText("Data de lançamento")},placeholder={UiText("AAAA ou AAAA-MM-DD")},modifier=Modifier.fillMaxWidth(),singleLine=true)
            CollectionOrdering(trackSort,trackDescending,listOf("" to "Ordem original","title" to "Título","artist" to "Artista","album" to "Álbum","release_date" to "Data de lançamento"),{trackSort=it},{trackDescending=it})
            Row(Modifier.fillMaxWidth(),verticalAlignment=Alignment.CenterVertically) {
                UiText("${visible.size} de ${tracks.size}",Modifier.weight(1f),style=MaterialTheme.typography.bodySmall)
                TextButton(onClick={filter="";artistFilter="";albumFilter="";releaseFilter=""}){UiText("Limpar filtros")}
            }
        }
        item {collectionActions()}
        if(adding)item {LinearProgressIndicator(Modifier.fillMaxWidth())}
        items(visible,key={row->requireNotNull(trackKeys[row])},contentType={"collection_track"}) {original->
            val record=rememberCardMetadata(original,vm)
            var actions by remember {mutableStateOf(false)}
            Surface(modifier=Modifier.onSecondaryClick(record.optString("source_url")){actions=true},shape=RoundedCornerShape(16.dp),color=MaterialTheme.colorScheme.surfaceVariant.copy(alpha=.45f)){Row(Modifier.fillMaxWidth().heightIn(min=64.dp).toggleable(value=record.optString("source_url") in selected,role=Role.Checkbox,onValueChange={checked->val id=record.optString("source_url");selected=if(checked) selected+id else selected-id}).a11yState(if(record.optString("source_url") in selected) "Selecionado" else "Não selecionado"),verticalAlignment=Alignment.CenterVertically) {
            Checkbox(record.optString("source_url") in selected,null,modifier=Modifier.padding(end=LayoutSpacing.checkboxLabel))
            EffectsArtwork(JSONObject().put("record",record),Modifier.size(56.dp).padding(end=8.dp))
            Column(Modifier.weight(1f)) {Text(record.optString("title"));Text(record.stringList("artists"),style=MaterialTheme.typography.bodySmall);AlbumDateLabel(record);record.optJSONObject("youtube_match")?.let {Text(it.optString("title"),color=MaterialTheme.colorScheme.primary,style=MaterialTheme.typography.bodySmall)};syncBySource[record.optString("source_url")]?.let {state->
                UiText(collectionSyncState(state.optString("state")),style=MaterialTheme.typography.bodySmall)
                UiText(state.optString("reason"),style=MaterialTheme.typography.bodySmall)
                state.optJSONArray("paths")?.optString(0)?.takeIf {it.isNotBlank()}?.let {Text(it,style=MaterialTheme.typography.bodySmall)}
            }}
            Box {
                IconButton(onClick={actions=true}){OndaIcon("more-vertical","Mais ações",Modifier.size(22.dp))}
                DropdownMenu(actions,{actions=false}) {
                    DropdownMenuItem(text={UiText("Baixar agora")},onClick={actions=false;vm.queueCollection(listOf(record),options,collection.optString("title","Playlist"),true)})
                    DropdownMenuItem(text={UiText("Adicionar à fila")},onClick={actions=false;vm.queueCollection(listOf(record),options,collection.optString("title","Playlist"),false)})
                    DropdownMenuItem(text={UiText("Usar em reprodução")},onClick={actions=false;vm.collectionToPlayback(listOf(record))})
                    DropdownMenuItem(text={UiText("Ver no catálogo")},onClick={actions=false;openRecordLink(record)})
                    DropdownMenuItem(text={UiText("Copiar link")},onClick={actions=false;copyRecordLink(record)})
                }
            }
        }}}

        }
        item {Spacer(Modifier.height(16.dp))}
    }
    if(listOnly) Dialog(onDismissRequest={listOnly=false}) {Surface(shape=RoundedCornerShape(20.dp)) {Column(Modifier.fillMaxWidth().fillMaxHeight(.85f).padding(LayoutSpacing.inset)) {
        UiText(collection.optString("title","Músicas"),style=MaterialTheme.typography.titleLarge)
        NavigableList(Modifier.weight(1f),navigationId="collection-dialog") {items(visible){UiText("${it.stringList("artists")} - ${it.optString("title")}",Modifier.padding(vertical=8.dp))}}
        TextButton(onClick={listOnly=false}){UiText("Fechar")}
    }}}
}

@Composable private fun CollectionOrdering(field:String,descending:Boolean,options:List<Pair<String,String>>,onField:(String)->Unit,onDirection:(Boolean)->Unit) {
    var open by remember {mutableStateOf(false)}
    Row(Modifier.fillMaxWidth(),verticalAlignment=Alignment.CenterVertically) {
        Box(Modifier.weight(1f)) {
            TextButton(onClick={open=true}) {UiText("Ordenar por");Text(": ");UiText(options.first {it.first==field}.second)}
            DropdownMenu(open,{open=false}) {options.forEach {(key,label)->DropdownMenuItem(text={UiText(label)},onClick={onField(key);open=false})}}
        }
        TextButton(enabled=field.isNotBlank(),onClick={onDirection(!descending)}) {UiText(if(descending)"Decrescente" else "Crescente")}
    }
}
