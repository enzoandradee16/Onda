package br.com.onda.mobile

import android.app.Activity
import android.Manifest
import android.os.Build
import android.content.pm.PackageManager
import androidx.core.content.ContextCompat
import androidx.compose.ui.platform.LocalContext
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

internal fun photoPermissions(sdk:Int):Array<String> = when {
    sdk>=34->arrayOf(Manifest.permission.READ_MEDIA_IMAGES,Manifest.permission.READ_MEDIA_VISUAL_USER_SELECTED)
    sdk>=33->arrayOf(Manifest.permission.READ_MEDIA_IMAGES)
    else->arrayOf(Manifest.permission.READ_EXTERNAL_STORAGE)
}

// Copy the granted content URI immediately; never access a gallery filesystem path.
@Composable fun rememberImageSourcePicker(mimeTypes:Array<String> = arrayOf("image/jpeg","image/png"),onSelected:(Uri)->Unit):()->Unit {
    val context=LocalContext.current
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
    fun openGallery() {
        runCatching {gallery.launch(galleryImageIntent(mimeTypes))}
            .onFailure {error="Não foi possível abrir a galeria. Use Procurar nos arquivos."}
    }
    val permission=rememberLauncherForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) {grants->
        if(grants.values.any {it})openGallery()
        else error="O acesso às fotos não foi permitido. Autorize nas configurações do Android ou use Procurar nos arquivos para escolher somente uma imagem."
    }
    if(show)AlertDialog(containerColor=ondaDialogContainerColor(),onDismissRequest={show=false},title={UiText("Escolher imagem")},text={
        Column(verticalArrangement=Arrangement.spacedBy(LayoutSpacing.controls)) {
            UiText("Escolha de onde abrir a imagem.",style=MaterialTheme.typography.bodySmall)
            Button(onClick={
                show=false;errorTitle="Escolher da galeria"
                val required=photoPermissions(Build.VERSION.SDK_INT)
                if(required.any {ContextCompat.checkSelfPermission(context,it)==PackageManager.PERMISSION_GRANTED})openGallery()
                else permission.launch(required)
            },modifier=Modifier.fillMaxWidth()){UiText("Escolher da galeria")}
            OutlinedButton(onClick={
                show=false;errorTitle="Procurar nos arquivos"
                runCatching {files.launch(mimeTypes)}.onFailure {error="Não foi possível abrir o seletor de arquivos."}
            },modifier=Modifier.fillMaxWidth()){UiText("Procurar nos arquivos")}
        }
    },confirmButton={},dismissButton={TextButton(onClick={show=false}){UiText("Cancelar")}})
    if(error.isNotBlank())AlertDialog(containerColor=ondaDialogContainerColor(),onDismissRequest={error=""},title={UiText(errorTitle)},text={UiText(error)},confirmButton={TextButton(onClick={error="";show=true}){UiText("Voltar")}})
    return {show=true}
}
