package br.com.onda.mobile

import android.app.Application
import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform
import java.io.File
import java.security.KeyStore
import java.util.zip.ZipInputStream
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

class OndaApplication : Application() {
    override fun onCreate() {
        super.onCreate()
        SecureVault.initialize(this)
        OndaStore.initialize(this)
    }
}

object SecureVault {
    private lateinit var context: Context
    fun initialize(value: Context) { context = value.applicationContext }
    private fun key(): SecretKey {
        val store = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        (store.getKey("onda-secrets", null) as? SecretKey)?.let { return it }
        return KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore").apply {
            init(KeyGenParameterSpec.Builder("onda-secrets", KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM).setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE).build())
        }.generateKey()
    }
    @JvmStatic @Synchronized fun put(name: String, value: String) {
        val cipher = Cipher.getInstance("AES/GCM/NoPadding").apply { init(Cipher.ENCRYPT_MODE, key()) }
        val encrypted = cipher.iv + cipher.doFinal(value.toByteArray(Charsets.UTF_8))
        context.getSharedPreferences("vault", 0).edit().putString(name, Base64.encodeToString(encrypted, Base64.NO_WRAP)).commit()
    }
    @JvmStatic @Synchronized fun get(name: String): String? {
        val stored = context.getSharedPreferences("vault", 0).getString(name, null) ?: return null
        val data = Base64.decode(stored, Base64.NO_WRAP)
        return Cipher.getInstance("AES/GCM/NoPadding").run {
            init(Cipher.DECRYPT_MODE, key(), GCMParameterSpec(128, data.copyOfRange(0,12)))
            String(doFinal(data.copyOfRange(12,data.size)), Charsets.UTF_8)
        }
    }
    @JvmStatic fun remove(name: String) { context.getSharedPreferences("vault", 0).edit().remove(name).commit() }
    fun clear() { context.getSharedPreferences("vault", 0).edit().clear().commit() }
}

object MobileEngine {
    private var ready = false
    @Synchronized fun initialize(context: Context) {
        if (ready) return
        val directory = File(context.noBackupFilesDir,"media-tools-v2")
        val support = File(context.noBackupFilesDir,"media-support-v1")
        val native = File(context.applicationInfo.nativeLibraryDir)
        val marker = File(directory,"version")
        if (!marker.exists() || marker.readText() != "0.18.1") {
            directory.mkdirs()
            if (!Python.isStarted()) Python.start(AndroidPlatform(context.applicationContext))
            Python.getInstance().getModule("mobile_backend").callAttr("prepare_native_archive",File(native,"libffmpeg.zip.so").absolutePath,directory.absolutePath)
            marker.writeText("0.18.1")
        }
        if (!Python.isStarted()) Python.start(AndroidPlatform(context.applicationContext))
        if(!File(support,"version").exists()) {
            Python.getInstance().getModule("mobile_backend").callAttr("prepare_native_archive",File(native,"libonda-support.zip.so").absolutePath,support.absolutePath)
            File(support,"version").writeText("0.18.1")
        }
        Python.getInstance().getModule("mobile_backend").callAttr("configure", context.filesDir.absolutePath,
            native.absolutePath, File(directory,"usr/lib").absolutePath + ":" + File(support,"usr/lib").absolutePath)
        ready = true
    }
    fun call(context: Context, identity: String, action: String, config: org.json.JSONObject, callback: EventCallback): org.json.JSONObject {
        initialize(context)
        return org.json.JSONObject(Python.getInstance().getModule("mobile_backend").callAttr("run",identity,action,config.toString(),callback).toString())
    }
    fun reply(identity: String, value: org.json.JSONObject) {
        if (ready) Python.getInstance().getModule("mobile_backend").callAttr("reply",identity,value.toString())
    }
    fun cancel(identity: String) {
        if (ready) Python.getInstance().getModule("mobile_backend").callAttr("cancel",identity)
    }
}

fun interface EventCallback { fun onEvent(value: String) }
