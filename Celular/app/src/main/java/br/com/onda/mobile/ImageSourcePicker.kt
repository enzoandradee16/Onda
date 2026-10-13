package br.com.onda.mobile

import android.app.Activity
import android.content.Intent
import android.net.Uri
import android.provider.MediaStore
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

internal fun galleryImageIntent(mimeTypes:Array<String>):Intent {
    val gallery=Intent(Intent.ACTION_PICK).apply {
        setDataAndType(MediaStore.Images.Media.EXTERNAL_CONTENT_URI,"image/*")
        putExtra(Intent.EXTRA_MIME_TYPES,mimeTypes)
        addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
    }
    val content=Intent(Intent.ACTION_GET_CONTENT).apply {
        type="image/*"
        addCategory(Intent.CATEGORY_OPENABLE)
        putExtra(Intent.EXTRA_MIME_TYPES,mimeTypes)
        addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
    }
    return Intent.createChooser(gallery,"Escolher da galeria").apply {
        putExtra(Intent.EXTRA_ALTERNATE_INTENTS,arrayOf(content))
    }
}

// Gallery permissions are temporary: callers copy the chosen image immediately.
@Composable fun rememberImageSourcePicker(mimeTypes:Array<String> = arrayOf("image/jpeg","image/png"),onSelected:(Uri)->Unit):()->Unit {
    var show by rememberSaveable {mutableStateOf(false)}
    var errorTitle by remember {mutableStateOf("Escolher imagem")}
    var error by remember {mutableStateOf("")}
    val files=rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) {uri->if(uri!=null)onSelected(uri)}
    val gallery=rememberLauncherForActivityResult(ActivityResultContracts.StartActivityForResult()) {result->
        if(result.resultCode==Activity.RESULT_OK) {
            val uri=result.data?.data ?: result.data?.clipData?.takeIf {it.itemCount>0}?.getItemAt(0)?.uri
            if(uri!=null)onSelected(uri)
        }
    }
    if(show)AlertDialog(onDismissRequest={show=false},title={Text("Escolher imagem")},text={
        Column(verticalArrangement=Arrangement.spacedBy(10.dp)) {
            Text("Escolha de onde abrir a imagem.",style=MaterialTheme.typography.bodySmall)
            Button(onClick={
                show=false;errorTitle="Escolher da galeria"
                runCatching {gallery.launch(galleryImageIntent(mimeTypes))}
                    .onFailure {error="Não foi possível abrir a galeria. Use Procurar nos arquivos."}
            },modifier=Modifier.fillMaxWidth()){Text("Escolher da galeria")}
            OutlinedButton(onClick={
                show=false;errorTitle="Procurar nos arquivos"
                runCatching {files.launch(mimeTypes)}.onFailure {error="Não foi possível abrir o seletor de arquivos."}
            },modifier=Modifier.fillMaxWidth()){Text("Procurar nos arquivos")}
        }
    },confirmButton={},dismissButton={TextButton(onClick={show=false}){Text("Cancelar")}})
    if(error.isNotBlank())AlertDialog(onDismissRequest={error=""},title={Text(errorTitle)},text={Text(error)},confirmButton={TextButton(onClick={error="";show=true}){Text("Voltar")}})
    return {show=true}
}
