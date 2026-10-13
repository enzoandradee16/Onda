package br.com.onda.mobile

import android.content.Context
import android.net.Uri
import android.os.ParcelFileDescriptor
import java.io.File
import java.io.IOException
import java.io.InputStream
import java.security.MessageDigest

private fun audioDigest(input: InputStream): ByteArray = input.use { stream ->
    val digest=MessageDigest.getInstance("SHA-256")
    val buffer=ByteArray(65536)
    while(true) {val count=stream.read(buffer);if(count<0)break;if(count>0)digest.update(buffer,0,count)}
    digest.digest()
}

/** Prepare first; never truncate the provider's file before checking write/seek access. */
internal fun replaceAudioOriginal(context: Context, uri: Uri, original: File, edited: File) {
    require(original.isFile && edited.isFile && edited.length()>0) {"Arquivo de edição indisponível."}
    val expected=audioDigest(original.inputStream())
    val current=audioDigest(requireNotNull(context.contentResolver.openInputStream(uri)) {"Não foi possível ler o arquivo original."})
    require(expected.contentEquals(current)) {"O arquivo original mudou durante a edição. Abra-o novamente antes de salvar."}
    val directory=File(context.filesDir,"audio-backups").apply {mkdirs()}
    val backup=File.createTempFile("original-", "."+original.extension, directory)
    var preserveBackup=false
    try {
        original.copyTo(backup,overwrite=true)
        val descriptor=context.contentResolver.openFileDescriptor(uri,"rw")
            ?: throw IOException("Não foi possível abrir o arquivo original para escrita.")
        ParcelFileDescriptor.AutoCloseOutputStream(descriptor).use { output ->
            val channel=output.channel
            channel.position(0) // Reject non-seekable providers before modifying their data.
            try {
                edited.inputStream().use {it.copyTo(output)}
                channel.truncate(edited.length())
                output.fd.sync()
            } catch(error: Exception) {
                try {
                    channel.position(0)
                    backup.inputStream().use {it.copyTo(output)}
                    channel.truncate(backup.length())
                    output.fd.sync()
                } catch(restore: Exception) {
                    preserveBackup=true
                    error.addSuppressed(restore)
                    throw IOException("Não foi possível concluir nem restaurar a gravação. A cópia de segurança foi preservada nos dados do ONDA: "+backup.name,error)
                }
                throw IOException("Não foi possível salvar no original. O arquivo anterior foi restaurado.",error)
            }
        }
    } finally {
        if(!preserveBackup)backup.delete()
    }
}
