package br.com.onda.mobile

import android.app.DownloadManager
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.provider.Settings
import androidx.core.content.FileProvider
import java.io.File

internal data class UpdateDownload(val status:Int=0,val bytes:Long=0,val total:Long=0)

internal class InAppUpdate(private val context:Context) {
    private val manager=context.getSystemService(DownloadManager::class.java)
    private val prefs=context.getSharedPreferences("app-update",Context.MODE_PRIVATE)
    private val file:File get()=File(requireNotNull(context.getExternalFilesDir(null)),"updates/ONDA-update.apk")
    internal fun officialUrl(value:String):Boolean {
        val uri=Uri.parse(value)
        return uri.scheme=="https" && uri.host=="github.com" && uri.userInfo==null && uri.port==-1 &&
            uri.path.orEmpty().startsWith("/enzoandradee16/Onda/releases/download/") && uri.path.orEmpty().endsWith(".apk")
    }
    fun start(url:String,language:String) {
        require(officialUrl(url)) {"Link de atualização inválido."}
        cancel()
        file.parentFile?.mkdirs()
        val request=DownloadManager.Request(Uri.parse(url))
            .setTitle("ONDA")
            .setDescription(translateUi("Baixando atualização do ONDA",language))
            .setMimeType("application/vnd.android.package-archive")
            .setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE)
            .setDestinationInExternalFilesDir(context,null,"updates/ONDA-update.apk")
        val id=manager.enqueue(request)
        prefs.edit().putLong("id",id).apply()
    }
    fun cancel() {
        val id=prefs.getLong("id",-1)
        if(id!=-1L)manager.remove(id)
        prefs.edit().clear().apply()
        file.delete()
    }
    fun state():UpdateDownload {
        val id=prefs.getLong("id",-1)
        if(id==-1L)return UpdateDownload()
        manager.query(DownloadManager.Query().setFilterById(id)).use {c->
            if(c==null || !c.moveToFirst())return UpdateDownload(DownloadManager.STATUS_FAILED)
            return UpdateDownload(c.getInt(c.getColumnIndexOrThrow(DownloadManager.COLUMN_STATUS)),c.getLong(c.getColumnIndexOrThrow(DownloadManager.COLUMN_BYTES_DOWNLOADED_SO_FAR)),c.getLong(c.getColumnIndexOrThrow(DownloadManager.COLUMN_TOTAL_SIZE_BYTES)))
        }
    }
    @Suppress("DEPRECATION")
    internal fun validate(candidate:File=file) {
        val pm=context.packageManager
        val flags=if(Build.VERSION.SDK_INT>=28)PackageManager.GET_SIGNING_CERTIFICATES else PackageManager.GET_SIGNATURES
        val archive=pm.getPackageArchiveInfo(candidate.absolutePath,flags) ?: error("APK de atualização inválido.")
        val installed=pm.getPackageInfo(context.packageName,flags)
        validateMetadata(archive,installed)
    }
    @Suppress("DEPRECATION")
    internal fun validateMetadata(archive:android.content.pm.PackageInfo,installed:android.content.pm.PackageInfo) {
        require(archive.packageName==context.packageName) {"APK de atualização inválido."}
        val newer=if(Build.VERSION.SDK_INT>=28) archive.longVersionCode>installed.longVersionCode else archive.versionCode>installed.versionCode
        require(newer) {"A atualização não é mais recente que a versão instalada."}
        fun signatures(info:android.content.pm.PackageInfo)=if(Build.VERSION.SDK_INT>=28)info.signingInfo?.apkContentsSigners else info.signatures
        val current=signatures(installed)?.map {it.toCharsString()}?.toSet().orEmpty()
        val next=signatures(archive)?.map {it.toCharsString()}?.toSet().orEmpty()
        require(current.isNotEmpty() && current==next) {"A assinatura da atualização não corresponde ao ONDA instalado."}
    }
    fun install():Boolean {
        check(state().status==DownloadManager.STATUS_SUCCESSFUL) {"A atualização ainda não terminou de baixar."}
        validate()
        if(!context.packageManager.canRequestPackageInstalls()) {
            context.startActivity(Intent(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES,Uri.parse("package:${context.packageName}")).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
            return false
        }
        val uri=FileProvider.getUriForFile(context,"${context.packageName}.files",file)
        context.startActivity(Intent(Intent.ACTION_VIEW).setDataAndType(uri,"application/vnd.android.package-archive")
            .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_ACTIVITY_NEW_TASK))
        return true
    }
}
