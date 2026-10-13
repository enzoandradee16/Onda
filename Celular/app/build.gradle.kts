plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
    id("com.chaquo.python")
}
// Phone builds carry one architecture; emulator builds opt in explicitly.
val targetAbis=providers.gradleProperty("onda.abis").getOrElse("arm64-v8a").split(",").map {it.trim()}.distinct()
require(targetAbis.isNotEmpty() && targetAbis.all {it in setOf("arm64-v8a","x86_64")}) {"onda.abis: use arm64-v8a e/ou x86_64"}
val nativeTools by configurations.creating { isTransitive = false }
val prepareNativeTools by tasks.registering(Sync::class) {
    inputs.property("targetAbis",targetAbis)
    from({ nativeTools.map { zipTree(it) } }) {
        targetAbis.forEach {abi->include("jni/$abi/libffmpeg*", "jni/$abi/libffprobe.so", "jni/$abi/libqjs.so")}
        eachFile { path = path.removePrefix("jni/") }
        includeEmptyDirs = false
    }
    into(layout.buildDirectory.dir("generated/nativeTools"))
    doLast {
        project.exec {
            commandLine(listOf(providers.gradleProperty("onda.buildPython").getOrElse("python"),
                rootProject.file("tools/prepare_native_support.py").absolutePath,
                layout.buildDirectory.dir("generated/nativeTools").get().asFile.absolutePath) + nativeTools.files.map {it.absolutePath})
        }
    }
}
val syncSharedEngine by tasks.registering(Sync::class) {
    from("../../Onda") {
        include("*.py")
        exclude("test_*", "*_ui.py", "app.py", "ui.py", "desktop_entry.py", "ffmpeg_runtime.py",
            "credentials.py", "preferences.py", "first_run.py", "single_instance.py", "window_*.py", "tab_order.py", "settings_scroll.py",
            "appearance.py", "interface_fonts.py", "library.py", "reset_settings.py",
            "flac_browser_ui.py", "catalog_picker.py", "media_picker.py", "version_picker.py", "parallel_queue.py", "lazy_ui.py")
    }
    into("src/main/python/shared")
}
android {
    namespace = "br.com.onda.mobile"
    compileSdk = 36
    buildToolsVersion = "36.0.0"
    defaultConfig {
        applicationId = "br.com.onda.mobile"
        minSdk = 26
        targetSdk = 35
        versionCode = 14
        versionName = "1.0.0-alpha.1"
        ndk { abiFilters += targetAbis }
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }
    buildFeatures { compose = true; buildConfig = true }
    compileOptions { sourceCompatibility = JavaVersion.VERSION_17; targetCompatibility = JavaVersion.VERSION_17 }
    kotlinOptions { jvmTarget = "17" }
    sourceSets["main"].jniLibs.srcDir(layout.buildDirectory.dir("generated/nativeTools"))
    packaging { jniLibs.useLegacyPackaging = true; resources.excludes += listOf("META-INF/DEPENDENCIES", "META-INF/LICENSE*", "META-INF/NOTICE*") }
}
chaquopy {
    defaultConfig {
        version = "3.11"
        providers.gradleProperty("onda.buildPython").orNull?.let { buildPython(it) }
        pip {
            install("yt-dlp==2026.8.19")
            install("yt-dlp-ejs==0.8.0")
            install("requests==2.32.5")
            install("mutagen==1.47.0")
            install("gallery-dl==1.32.16")
            install("Pillow==11.0.0")
        }
    }
    sourceSets["main"].srcDir("src/main/python/shared")
}
tasks.named("preBuild") { dependsOn(prepareNativeTools, syncSharedEngine) }
tasks.matching { it.name.contains("Python") }.configureEach { dependsOn(syncSharedEngine) }
dependencies {
    implementation("androidx.work:work-runtime-ktx:2.10.1")
    nativeTools("io.github.junkfood02.youtubedl-android:ffmpeg:0.18.1@aar")
    nativeTools("io.github.junkfood02.youtubedl-android:library:0.18.1@aar")
    implementation(platform("androidx.compose:compose-bom:2025.05.01"))
    implementation("androidx.browser:browser:1.8.0")
    implementation("androidx.activity:activity-compose:1.10.1")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.foundation:foundation")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.9.0")
    implementation("androidx.lifecycle:lifecycle-runtime-compose:2.9.0")
    implementation("androidx.documentfile:documentfile:1.0.1")
    implementation("androidx.media3:media3-exoplayer:1.7.1")
    implementation("androidx.media3:media3-exoplayer-hls:1.7.1")
    implementation("androidx.media3:media3-exoplayer-dash:1.7.1")
    implementation("androidx.media3:media3-session:1.7.1")
    implementation("io.coil-kt:coil-compose:2.7.0")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.10.2")
    testImplementation("junit:junit:4.13.2")
    androidTestImplementation("androidx.test.ext:junit:1.2.1")
    androidTestImplementation("androidx.test:runner:1.6.2")
    androidTestImplementation(platform("androidx.compose:compose-bom:2025.05.01"))
    androidTestImplementation("androidx.compose.ui:ui-test-junit4")
    debugImplementation("androidx.compose.ui:ui-test-manifest")
}
