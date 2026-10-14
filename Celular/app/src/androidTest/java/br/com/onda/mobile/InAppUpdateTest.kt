package br.com.onda.mobile

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File

@RunWith(AndroidJUnit4::class)
class InAppUpdateTest {
    private val context=InstrumentationRegistry.getInstrumentation().targetContext
    @Test fun onlyOfficialApkLinksAreAccepted() {
        val updater=InAppUpdate(context)
        assertTrue(updater.officialUrl("https://github.com/enzoandradee16/Onda/releases/download/v1.2.0/ONDA.apk"))
        for(url in listOf("http://github.com/enzoandradee16/Onda/releases/download/v1/a.apk","https://github.com.evil.example/enzoandradee16/Onda/releases/download/v1/a.apk","https://github.com/other/Onda/releases/download/v1/a.apk","https://github.com/enzoandradee16/Onda/releases/download/v1/a.exe","https://user@github.com/enzoandradee16/Onda/releases/download/v1/a.apk"))assertFalse(url,updater.officialUrl(url))
    }
    @Test fun invalidAndSameVersionArchivesAreRejected() {
        val updater=InAppUpdate(context)
        val invalid=File(context.cacheDir,"invalid-update.apk")
        try {
            invalid.writeText("not an APK")
            assertThrows(IllegalStateException::class.java) {updater.validate(invalid)}
            assertThrows(IllegalArgumentException::class.java) {updater.validate(File(context.applicationInfo.sourceDir))}
        } finally {invalid.delete()}
    }
    @Test fun cancelledDownloadIsClearedAcrossInstancesAndInstallRequiresCompletion() {
        val updater=InAppUpdate(context)
        updater.cancel()
        assertEquals(0,InAppUpdate(context).state().status)
        assertThrows(IllegalStateException::class.java) {updater.install()}
        assertThrows(IllegalArgumentException::class.java) {updater.start("https://example.com/update.apk","en")}
        assertEquals(0,InAppUpdate(context).state().status)
    }
    @Test fun newerVersionRequiresTheInstalledPackageAndSigner() {
        val flags=if(android.os.Build.VERSION.SDK_INT>=28)android.content.pm.PackageManager.GET_SIGNING_CERTIFICATES else android.content.pm.PackageManager.GET_SIGNATURES
        @Suppress("DEPRECATION")
        val installed=context.packageManager.getPackageInfo(context.packageName,flags)
        val parcel=android.os.Parcel.obtain()
        val newer=try {
            installed.writeToParcel(parcel,0);parcel.setDataPosition(0)
            android.content.pm.PackageInfo.CREATOR.createFromParcel(parcel)
        } finally {parcel.recycle()}
        @Suppress("DEPRECATION")
        if(android.os.Build.VERSION.SDK_INT>=28)newer.setLongVersionCode(installed.longVersionCode+1) else newer.versionCode=installed.versionCode+1
        val updater=InAppUpdate(context)
        updater.validateMetadata(newer,installed)
        newer.packageName="other.application"
        assertThrows(IllegalArgumentException::class.java) {updater.validateMetadata(newer,installed)}
        newer.packageName=context.packageName
        if(android.os.Build.VERSION.SDK_INT>=28)newer.signingInfo=null else newer.signatures=null
        assertThrows(IllegalArgumentException::class.java) {updater.validateMetadata(newer,installed)}
    }
    @Test fun downloadRegistrationSurvivesRecreationAndCanBeCancelled() {
        val updater=InAppUpdate(context)
        try {
            updater.start("https://github.com/enzoandradee16/Onda/releases/download/update-test-fixture/ONDA.apk","en")
            val preferences=context.getSharedPreferences("app-update",android.content.Context.MODE_PRIVATE)
            assertTrue(preferences.getLong("id",-1)>0)
            assertNotEquals(0,InAppUpdate(context).state().status)
            InAppUpdate(context).cancel()
            assertEquals(0,updater.state().status)
            assertFalse(java.io.File(context.getExternalFilesDir(null),"updates/ONDA-update.apk").exists())
        } finally {updater.cancel()}
    }

    @Test fun pollingStopsAfterCompletionAndSkipsWaitingForTerminalStates() = kotlinx.coroutines.runBlocking {
        for(status in listOf(0,android.app.DownloadManager.STATUS_SUCCESSFUL,android.app.DownloadManager.STATUS_FAILED)) {
            var reads=0
            pollUpdateDownload({reads++;UpdateDownload(status)},{assertEquals(status,it.status)},{error("Terminal state must not keep polling")})
            assertEquals(1,reads)
        }
        val states=java.util.ArrayDeque(listOf(UpdateDownload(android.app.DownloadManager.STATUS_PENDING),UpdateDownload(android.app.DownloadManager.STATUS_RUNNING),UpdateDownload(android.app.DownloadManager.STATUS_SUCCESSFUL)))
        var published=0;var waits=0
        pollUpdateDownload({states.removeFirst()},{published++},{waits++})
        assertEquals(3,published);assertEquals(2,waits)
    }
    @Test fun pollingRetainsCancellationAndStopsAfterReadFailure() = kotlinx.coroutines.runBlocking {
        var published:UpdateDownload?=null
        pollUpdateDownload({throw IllegalStateException("Download service unavailable")},{published=it},{error("No retry loop on failure")})
        assertEquals(android.app.DownloadManager.STATUS_FAILED,published!!.status)
        var cancelled=false
        try {
            pollUpdateDownload({UpdateDownload(android.app.DownloadManager.STATUS_RUNNING)},{},{throw kotlinx.coroutines.CancellationException("Activity stopped")})
        } catch(_:kotlinx.coroutines.CancellationException) {cancelled=true}
        assertTrue(cancelled)
    }

}
