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

@Composable fun CollectionsPage(vm: OndaViewModel) {
    val collection by vm.collection.collectAsStateWithLifecycle()
    var referenceResult by remember {mutableStateOf("")}
    val compareFile=rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) {uri->if(uri!=null)vm.importLocal(uri,"collection-reference") {file->
        vm.operation("compare_collection_file",JSONObject().put("source",file.absolutePath).put("tracks",vm.collection.value.optJSONArray("tracks") ?: JSONArray())) {referenceResult=it.optString("message");file.delete()}
    }}
    LaunchedEffect(collection){referenceResult=""}
    val comparison by vm.collectionComparison.collectAsStateWithLifecycle()
    val busy by vm.busy.collectAsStateWithLifecycle()
    var libraryTab by rememberSaveable {mutableIntStateOf(if(collection.optString("title").isNotBlank())1 else 0)}
    var advanced by rememberSaveable {mutableStateOf(false)}
    var moreActions by remember {mutableStateOf(false)}
    var saved by remember {mutableStateOf<List<JSONObject>>(emptyList())}
    val libraryScope=rememberCoroutineScope()
    val listState=rememberLazyListState()
    LaunchedEffect(libraryTab){listState.scrollToItem(0)}
    LaunchedEffect(Unit){saved=CollectionsLibrary.read()}
    var syncReload by remember {mutableStateOf(false)}
    val settings by OndaStore.settings.collectAsStateWithLifecycle()
    val adding by vm.addingToQueue.collectAsStateWithLifecycle()
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
    LaunchedEffect(collection.optString("_collection_url"),collection.optString("title")){selected=emptySet();filter=""}
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
    NavigableList(Modifier.fillMaxSize().imePadding().padding(horizontal=20.dp),navigationId="collection",state=listState) {
        item {ToolHeading("Álbuns e playlists")}
        item {
            OutlinedTextField(url,{url=it},label={UiText("Link da playlist ou álbum")},singleLine=true,modifier=Modifier.fillMaxWidth(),keyboardOptions=androidx.compose.foundation.text.KeyboardOptions(imeAction=androidx.compose.ui.text.input.ImeAction.Go),keyboardActions=androidx.compose.foundation.text.KeyboardActions(onGo={if(!busy&&url.isNotBlank()){libraryTab=1;vm.loadCollection(url,options)}}))
            Button(onClick={if(busy)vm.cancel() else {libraryTab=1;vm.loadCollection(url,options)}},enabled=busy||url.isNotBlank()) {UiText(if(busy)"Cancelar" else if(tracks.isNotEmpty()&&collection.optString("_collection_url")==url)"Atualizar" else "Carregar")}
        }
        item {ToolTabs(listOf("Salvos","Importar"),libraryTab){libraryTab=it}}
        if(libraryTab==0) {
            if(saved.isEmpty())item {ToolEmpty("album","Suas coleções ficam aqui","Importe um álbum ou playlist e salve para acessar depois.")}
            items(saved,key={CollectionsLibrary.identity(it)},contentType={"saved_collection"}) {row->
                ToolCard(Modifier.clickable {vm.collection.value=JSONObject(row.toString());vm.collectionComparison.value=null;url=row.optString("_collection_url");selected=emptySet();filter="";libraryTab=1}) {
                    Row(verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.spacedBy(12.dp)) {
                        Surface(Modifier.size(80.dp),shape=RoundedCornerShape(12.dp),color=MaterialTheme.colorScheme.surfaceVariant){
                            if(row.cleanString("cover_url").isNotBlank())AsyncImage(row.cleanString("cover_url"),translateUi("Capa do álbum"),Modifier.fillMaxSize(),contentScale=androidx.compose.ui.layout.ContentScale.Crop)
                            else Box(contentAlignment=Alignment.Center){OndaIcon("album",modifier=Modifier.size(32.dp))}
                        }
                        Column(Modifier.weight(1f),verticalArrangement=Arrangement.spacedBy(4.dp)) {
                            Text(row.optString("title"),style=MaterialTheme.typography.titleMedium,maxLines=2)
                            Text(row.optString("subtitle"),style=MaterialTheme.typography.bodySmall)
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
        item {OutlinedTextField(filter,{filter=it},label={UiText("Buscar nesta lista")},modifier=Modifier.fillMaxWidth(),singleLine=true);UiText("${visible.size} de ${tracks.size}",style=MaterialTheme.typography.bodySmall)}
        item {collectionActions()}
        if(adding)item {LinearProgressIndicator(Modifier.fillMaxWidth())}
        items(visible,contentType={"collection_track"}) {original->
            val record=rememberCardMetadata(original,vm)
            var actions by remember {mutableStateOf(false)}
            Surface(modifier=Modifier.onSecondaryClick(record.optString("source_url")){actions=true},shape=RoundedCornerShape(16.dp),color=MaterialTheme.colorScheme.surfaceVariant.copy(alpha=.45f)){Row(Modifier.fillMaxWidth().heightIn(min=64.dp).toggleable(value=record.optString("source_url") in selected,role=Role.Checkbox,onValueChange={checked->val id=record.optString("source_url");selected=if(checked) selected+id else selected-id}).a11yState(if(record.optString("source_url") in selected) "Selecionado" else "Não selecionado"),verticalAlignment=Alignment.CenterVertically) {
            Checkbox(record.optString("source_url") in selected,null,modifier=Modifier.padding(end=LayoutSpacing.checkboxLabel))
            EffectsArtwork(JSONObject().put("record",record),Modifier.size(56.dp).padding(end=8.dp))
            Column(Modifier.weight(1f)) {Text(record.optString("title"));Text(record.stringList("artists"),style=MaterialTheme.typography.bodySmall);Text(record.cleanString("album"),style=MaterialTheme.typography.bodySmall);ReleaseDateLabel(record);record.optJSONObject("youtube_match")?.let {Text(it.optString("title"),color=MaterialTheme.colorScheme.primary,style=MaterialTheme.typography.bodySmall)};syncBySource[record.optString("source_url")]?.let {state->
                UiText(collectionSyncState(state.optString("state")),style=MaterialTheme.typography.bodySmall)
                UiText(state.optString("reason"),style=MaterialTheme.typography.bodySmall)
                state.optJSONArray("paths")?.optString(0)?.takeIf {it.isNotBlank()}?.let {Text(it,style=MaterialTheme.typography.bodySmall)}
            }}
            Box {
                IconButton(onClick={actions=true}){OndaIcon("more-vertical","Mais ações",Modifier.size(22.dp))}
                DropdownMenu(actions,{actions=false}) {
                    DropdownMenuItem(text={UiText("Baixar agora")},onClick={actions=false;vm.queueCollection(listOf(record),options,collection.optString("title","Playlist"),true)})
                    DropdownMenuItem(text={UiText("Adicionar à fila")},onClick={actions=false;vm.queueCollection(listOf(record),options,collection.optString("title","Playlist"),false)})
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
