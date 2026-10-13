param([string]$Sdk = $env:ANDROID_HOME, [string]$Jdk = $env:JAVA_HOME, [switch]$Testar, [ValidateSet("arm64-v8a","x86_64","universal")][string]$Arquitetura="arm64-v8a")
$ErrorActionPreference='Stop'
if(-not $Sdk) {
    foreach($candidate in @("$env:LOCALAPPDATA\Android\Sdk", 'C:\Program Files (x86)\Android\android-sdk')) {
        if(Test-Path -LiteralPath "$candidate\platform-tools\adb.exe") { $Sdk=$candidate; break }
    }
}
if(-not $Jdk) {
    foreach($candidate in @('C:\Program Files\Android\openjdk\jdk-21.0.8', 'C:\Program Files\Android\Android Studio\jbr')) {
        if(Test-Path -LiteralPath "$candidate\bin\java.exe") { $Jdk=$candidate; break }
    }
}
if(-not (Test-Path -LiteralPath "$Sdk\platform-tools\adb.exe")) { throw 'Informe o Android SDK com -Sdk.' }
if(-not (Test-Path -LiteralPath "$Jdk\bin\java.exe")) { throw 'Informe o JDK 17 ou 21 com -Jdk.' }
$env:JAVA_HOME=$Jdk
$env:ANDROID_HOME=$Sdk
$temporaryDirectory=Join-Path $env:LOCALAPPDATA 'OndaAndroidBuild\tmp'
New-Item -ItemType Directory -Path $temporaryDirectory -Force | Out-Null
$env:JAVA_TOOL_OPTIONS='"-Djdk.net.unixdomain.tmpdir='+$temporaryDirectory.Replace('\','/')+'"'
$sdkLine='sdk.dir='+$Sdk.Replace('\','/').Replace(':','\:')
[IO.File]::WriteAllText((Join-Path $PSScriptRoot 'local.properties'),$sdkLine+[Environment]::NewLine)
$python=Join-Path (Split-Path $PSScriptRoot) 'Portatil\_runtime\python\python.exe'
$arguments=@('-p',$PSScriptRoot,'--console=plain')
if(Test-Path -LiteralPath $python) { $arguments+='-Ponda.buildPython='+$python.Replace('\','/') }
$abis=if($Arquitetura -eq 'universal') {'arm64-v8a,x86_64'} else {$Arquitetura}
$arguments+='-Ponda.abis='+$abis
$arguments+=':app:assembleDebug'
if($Testar) { $arguments+=':app:connectedDebugAndroidTest' }
& "$PSScriptRoot\gradlew.bat" @arguments
if($LASTEXITCODE -ne 0) { throw 'Falha ao compilar/testar. Confira a mensagem acima.' }
$destination=Join-Path $PSScriptRoot 'APK'
New-Item -ItemType Directory -Path $destination -Force | Out-Null
$versionMatch=[regex]::Match([IO.File]::ReadAllText((Join-Path $PSScriptRoot 'app\build.gradle.kts')), 'versionName\s*=\s*"([^"]+)"')
if(-not $versionMatch.Success) { throw 'Não foi possível identificar a versão Android.' }
$apk=Join-Path $destination ("ONDA-Android-"+$versionMatch.Groups[1].Value+"-"+$Arquitetura+"-debug.apk")
Copy-Item -LiteralPath "$PSScriptRoot\app\build\outputs\apk\debug\app-debug.apk" -Destination $apk -Force
Get-FileHash -LiteralPath $apk -Algorithm SHA256
Write-Output "APK criado: $apk"
