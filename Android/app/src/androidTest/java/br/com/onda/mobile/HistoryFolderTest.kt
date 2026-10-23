package br.com.onda.mobile

import android.net.Uri
import android.provider.DocumentsContract
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File

@RunWith(AndroidJUnit4::class)
class HistoryFolderTest {
    @Test fun documentParentKeepsTreeAndEncodedNames() {
        val context=InstrumentationRegistry.getInstrumentation().targetContext
        val tree=DocumentsContract.buildTreeDocumentUri("com.android.externalstorage.documents","primary:Music")
        val file=DocumentsContract.buildDocumentUriUsingTree(tree,"primary:Music/Artista - Álbum/Faixa.mp3")
        val folder=historyFolderUri(context,file)
        assertEquals("primary:Music/Artista - Álbum",DocumentsContract.getDocumentId(folder))
        assertEquals("primary:Music",DocumentsContract.getTreeDocumentId(folder))
        val rootFile=DocumentsContract.buildDocumentUri("com.android.externalstorage.documents","primary:Faixa.mp3")
        assertEquals("primary:",DocumentsContract.getDocumentId(historyFolderUri(context,rootFile)))
        assertEquals(folder,historyFolderPicker(folder).getParcelableExtra<Uri>(DocumentsContract.EXTRA_INITIAL_URI))
    }
    @Test fun defaultDownloadOpensItsOriginalPlaylistFolder() {
        val instrumentation=InstrumentationRegistry.getInstrumentation()
        val context=instrumentation.targetContext
        val config=OndaStore.config().put("output_uri","").put("duplicate_policy","keep")
        val group="ONDA folder test ${System.nanoTime()}"
        val file=File(config.getString("folder"),"$group/Fixture folder.mp3")
        file.parentFile!!.mkdirs();file.writeBytes(ByteArray(32))
        val uri=OndaStore.publish(file.absolutePath,config,"mp3")
        try {
            val folder=historyFolderUri(context,uri)
            assertEquals("primary:Download/ONDA/$group",DocumentsContract.getDocumentId(folder))
            openHistoryFolder(context,folder)
            var found=false
            repeat(30) {
                if(!found) {Thread.sleep(200);found=containsText(instrumentation.uiAutomation.rootInActiveWindow,"Fixture folder")}
            }
            assertTrue("O gerenciador deve mostrar o arquivo dentro da pasta de origem",found)
        } finally {
            instrumentation.uiAutomation.performGlobalAction(android.accessibilityservice.AccessibilityService.GLOBAL_ACTION_BACK)
            context.contentResolver.delete(uri,null,null)
            OndaStore.history.value.firstOrNull {it.uri==uri.toString()}?.let {OndaStore.removeHistory(it.id)}
            file.delete();file.parentFile?.delete()
        }
    }
    private fun containsText(node:android.view.accessibility.AccessibilityNodeInfo?,text:String):Boolean {
        if(node==null) return false
        if(node.text?.toString()?.contains(text)==true) return true
        return (0 until node.childCount).any {containsText(node.getChild(it),text)}
    }
}
