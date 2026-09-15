# CursedColor - installer
# Pulls the plugin files straight from GitHub, downloads
# LibreHardwareMonitorLib + its dependency DLLs, installs pythonnet,
# and sets permissions so Krita can actually read everything.
# Just download this one file and run it - no need to clone the repo first.

$ErrorActionPreference = "Stop"

$libsPath = "C:\KritaPluginLibs"
$pykritaPath = Join-Path $env:APPDATA "krita\pykrita"
$pluginFolder = Join-Path $pykritaPath "cursedcolor"

$repoUser = "LowPolyPhosphorus"
$repoName = "CursedColor"
$branch = "main"
$rawBase = "https://raw.githubusercontent.com/$repoUser/$repoName/$branch"

$pluginFiles = @{
    "__init__.py"           = "$rawBase/cursedcolor/__init__.py"
    "cursedcolor_docker.py" = "$rawBase/cursedcolor/cursedcolor_docker.py"
}
$desktopFileUrl = "$rawBase/cursedcolor.desktop"

Write-Host "Setting up CursedColor plugin files in $pykritaPath ..."

if (-not (Test-Path $pluginFolder)) {
    New-Item -ItemType Directory -Path $pluginFolder -Force | Out-Null
}

foreach ($name in $pluginFiles.Keys) {
    $url = $pluginFiles[$name]
    $dest = Join-Path $pluginFolder $name
    Write-Host "Downloading $name ..."
    Invoke-WebRequest -Uri $url -OutFile $dest
}

Write-Host "Downloading cursedcolor.desktop ..."
Invoke-WebRequest -Uri $desktopFileUrl -OutFile (Join-Path $pykritaPath "cursedcolor.desktop")

Write-Host "Plugin files installed to $pluginFolder"
Write-Host ""
Write-Host "Setting up CursedColor dependencies in $libsPath ..."

if (-not (Test-Path $libsPath)) {
    New-Item -ItemType Directory -Path $libsPath -Force | Out-Null
}

$dlls = @{
    "LibreHardwareMonitorLib.dll"              = "https://cdn.hackclub.com/01a0a2d0-e87d-7535-8650-beae11343cb1/LibreHardwareMonitorLib.dll"
    "System.Memory.dll"                        = "https://cdn.hackclub.com/01a0a2d0-eca2-7635-9715-351e1add57a2/System.Memory.dll"
    "System.Buffers.dll"                       = "https://cdn.hackclub.com/01a0a2d0-eabe-704c-be2d-01138c570874/System.Buffers.dll"
    "System.Numerics.Vectors.dll"              = "https://cdn.hackclub.com/01a0a2d0-ee5d-755f-87b2-f0943a0703e1/System.Numerics.Vectors.dll"
    "System.Runtime.CompilerServices.Unsafe.dll" = "https://cdn.hackclub.com/01a0a2d0-f00d-7672-959a-9de24f71c713/System.Runtime.CompilerServices.Unsafe.dll"
}

foreach ($name in $dlls.Keys) {
    $url = $dlls[$name]
    $dest = Join-Path $libsPath $name
    Write-Host "Downloading $name ..."
    Invoke-WebRequest -Uri $url -OutFile $dest
}

Write-Host "Installing pythonnet ..."
python -m pip install pythonnet --target $libsPath

Write-Host "Unblocking downloaded files ..."
Get-ChildItem $libsPath -Recurse | Unblock-File

$currentUser = "$env:USERDOMAIN\$env:USERNAME"

Write-Host "Granting current user full access to $libsPath ..."
icacls $libsPath /grant "$($currentUser):(F)" /T | Out-Null

Write-Host "Unblocking and granting access to plugin files ..."
Get-ChildItem $pluginFolder -Recurse | Unblock-File
icacls $pluginFolder /grant "$($currentUser):(F)" /T | Out-Null

Write-Host ""
Write-Host "Done."
Write-Host "Plugin installed to: $pluginFolder"
Write-Host "Dependencies installed to: $libsPath"
Write-Host ""
Write-Host "Next steps:"
Write-Host "1. Restart Krita"
Write-Host "2. Enable CursedColor in Settings > Configure Krita > Python Plugin Manager"
Write-Host "3. Restart Krita (with ADMINISTRATOR for temp reading ability) and then open a document"
Write-Host "4. Enable the docker by opening Settings > Dockers > CursedColor"