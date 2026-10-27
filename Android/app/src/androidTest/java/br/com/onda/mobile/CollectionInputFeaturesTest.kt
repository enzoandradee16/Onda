package br.com.onda.mobile

import androidx.compose.foundation.layout.Column
import androidx.compose.material3.MaterialTheme
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.graphics.asAndroidBitmap
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.ViewModelStore
import androidx.test.core.app.ApplicationProvider
import androidx.test.platform.app.InstrumentationRegistry
import kotlinx.coroutines.*
import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test

class CollectionInputFeaturesTest {
    @get:Rule val compose=createComposeRule()
    private val context get()=InstrumentationRegistry.getInstrumentation().targetContext
    private fun viewModel(store:ViewModelStore):OndaViewModel {
        OndaStore.initialize(context)
        return ViewModelProvider(store,ViewModelProvider.AndroidViewModelFactory.getInstance(ApplicationProvider.getApplicationContext()))[OndaViewModel::class.java]
    }
    @Test fun collectionHasOneLoadCancelRefreshButtonAndSecondaryActionsInMenu() {
        val store=ViewModelStore();lateinit var vm:OndaViewModel
        compose.runOnIdle {
            vm=viewModel(store)
            vm.collection.value=JSONObject().put("title","Album fixture").put("_collection_url","https://example.com/list").put("tracks",JSONArray().put(JSONObject().put("title","Song fixture").put("artists",JSONArray(listOf("Artist"))).put("album","Album").put("release_date","1998-07-20").put("cover_url","https://example.com/cover.jpg").put("source_url","https://example.com/song")))
        }
        try {
            compose.setContent {MaterialTheme {CollectionsPage(vm)}}
            compose.onAllNodesWithText("Carregar").assertCountEquals(1)
            compose.onNodeWithText("Link da playlist ou álbum").performTextInput("https://example.com/list")
            compose.onAllNodesWithText("Atualizar").assertCountEquals(1)
            compose.runOnIdle {vm.busy.value=true}
            compose.onAllNodesWithText("Cancelar").assertCountEquals(1)
            compose.onAllNodesWithText("Adicionar aos Efeitos").assertCountEquals(0)
            compose.onAllNodesWithText("Adicionar ao Jukebox").assertCountEquals(0)
            compose.runOnIdle {vm.busy.value=false}
            compose.onNodeWithText("Mais ações").performClick()
            compose.onNodeWithText("Selecionar visíveis").assertExists()
            compose.onNodeWithText("Exportar TXT").assertExists()
        } finally {compose.runOnIdle {store.clear()}}
    }
    @Test fun bothQueueSearchFieldsAcceptTheSameInputAndStayVisibleOutsideEditMode() {
        val store=ViewModelStore();lateinit var vm:OndaViewModel
        compose.runOnIdle {vm=viewModel(store)}
        try {
            compose.setContent {MaterialTheme {Column {PlaybackQueueSearch(vm,false);PlaybackQueueSearch(vm,true)}}}
            compose.onAllNodesWithTag("playback-queue-search").assertCountEquals(2)
            compose.onAllNodesWithText(PLAYBACK_INPUT_HINT).assertCountEquals(2)
            compose.onAllNodesWithText("Pesquisar").assertCountEquals(2)
            assertFalse(vm.effectsQueueOpen.value)
        } finally {compose.runOnIdle {store.clear()}}
    }
    @Test fun appShellDoesNotDuplicateTheCollectionCancelButton() {
        OndaStore.initialize(context)
        val preferences=context.getSharedPreferences("preferences",0)
        val welcome=preferences.getBoolean("welcome_seen",false)
        preferences.edit().putBoolean("welcome_seen",true).commit()
        val store=ViewModelStore();lateinit var vm:OndaViewModel
        compose.runOnIdle {
            vm=viewModel(store)
            vm.collection.value=JSONObject().put("title","Album fixture").put("tracks",JSONArray().put(JSONObject().put("title","Song fixture").put("artists",JSONArray(listOf("Artist"))).put("album","Album").put("release_date","1998-07-20").put("cover_url","https://example.com/cover.jpg").put("source_url","https://example.com/song")))
        }
        try {
            compose.setContent {OndaApp(vm)}
            compose.onNodeWithText("Mais").performClick()
            compose.onNodeWithTag("more-Álbuns e playlists").performScrollTo().performClick()
            compose.runOnIdle {vm.busy.value=true;vm.status.value="Carregando álbum ou playlist…"}
            compose.onAllNodesWithText("Cancelar").assertCountEquals(1)
            compose.runOnIdle {vm.busy.value=false}
            val image=compose.onRoot().captureToImage().asAndroidBitmap()
            java.io.File(context.getExternalFilesDir(null),"collections-new.png").outputStream().use {image.compress(android.graphics.Bitmap.CompressFormat.PNG,100,it)}
        } finally {
            compose.runOnIdle {vm.busy.value=false;store.clear()}
            preferences.edit().putBoolean("welcome_seen",welcome).commit()
        }
    }
    @Test fun searchResultShowsReleaseDateAndAddingDoesNotOpenQueue() {
        val store=ViewModelStore();lateinit var vm:OndaViewModel
        compose.runOnIdle {vm=viewModel(store);vm.effectsQueueOpen.value=false;vm.queueNavigation.value=false}
        val record=JSONObject().put("title","Chosen song").put("artists",JSONArray(listOf("Artist"))).put("album","Album").put("release_date","1998-07-20").put("cover_url","https://example.com/cover.jpg").put("source_url","https://example.com/song")
        var added=0
        try {
            compose.setContent {MaterialTheme {PlaybackSearchResult(record,vm,true,{}, {added++})}}
            compose.onNodeWithText("Data de lançamento: 20/07/1998").assertExists()
            compose.onNodeWithText("Adicionar à fila").performClick()
            assertEquals(1,added);assertFalse(vm.effectsQueueOpen.value);assertFalse(vm.queueNavigation.value)
            compose.onNodeWithContentDescription("Mais ações").performClick()
            compose.onNodeWithText("Copiar link").assertExists()
        } finally {compose.runOnIdle {store.clear()}}
    }
    @Test fun jukeboxCollectionSearchUsesSharedResolverAndKeepsPlaybackStopped()=runBlocking {
        OndaStore.initialize(context)
        val scope=CoroutineScope(SupervisorJob()+Dispatchers.Main.immediate)
        val actions=java.util.Collections.synchronizedList(mutableListOf<String>())
        lateinit var controller:JukeboxController
        try {
            withContext(Dispatchers.Main) {
                controller=JukeboxController(context,scope,{}, {action,_,_->
                    actions.add(action)
                    if(action=="playback_input")JSONObject().put("is_collection",true).put("tracks",JSONArray().put(JSONObject().put("title","A").put("source_url","https://example.com/a")).put(JSONObject().put("title","B").put("source_url","https://example.com/b")))
                    else JSONObject().put("error","Fixture has no audio")
                })
                controller.clearPlaybackQueue();controller.search("https://example.com/collection")
            }
            withTimeout(10000){while(controller.playbackQueue.value.size<2)delay(30)}
            assertTrue(actions.contains("playback_input"));assertFalse(controller.state.value.playing)
        } finally {withContext(Dispatchers.Main){runCatching {controller.close()}};scope.cancel()}
    }
}
