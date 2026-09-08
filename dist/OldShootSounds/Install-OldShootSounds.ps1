param(
    [string]$GameRoot
)

$ErrorActionPreference = "Stop"
$interactiveSelection = $false

if ([string]::IsNullOrWhiteSpace($GameRoot)) {
    Add-Type -AssemblyName System.Windows.Forms
    $dialog = New-Object System.Windows.Forms.FolderBrowserDialog
    $dialog.Description = "Select the World of Tanks root folder"
    $dialog.ShowNewFolderButton = $false
    $result = $dialog.ShowDialog()
    if ($result -ne [System.Windows.Forms.DialogResult]::OK) {
        exit 0
    }
    $GameRoot = $dialog.SelectedPath
    $interactiveSelection = $true
}

$resolvedGameRoot = (Resolve-Path -LiteralPath $GameRoot).Path
$pathsPath = Join-Path $resolvedGameRoot "paths.xml"
if (-not (Test-Path -LiteralPath $pathsPath)) {
    throw "paths.xml not found in $resolvedGameRoot"
}

[xml]$pathsDocument = Get-Content -LiteralPath $pathsPath -Raw
$resModsPathNode = $pathsDocument.SelectSingleNode("/root/Paths/Path[@cacheSubdirs='true']")
if ($null -eq $resModsPathNode) {
    throw "The current res_mods path was not found in paths.xml"
}

$relativeResModsPath = $resModsPathNode.InnerText.Trim().Replace("/", "\")
while ($relativeResModsPath.StartsWith(".\")) {
    $relativeResModsPath = $relativeResModsPath.Substring(2)
}
$targetRoot = Join-Path $resolvedGameRoot $relativeResModsPath
$audioTarget = Join-Path $targetRoot "audioww"
$scriptsTarget = Join-Path $targetRoot "scripts\client\gui\mods"
$payloadRoot = Join-Path $PSScriptRoot "payload"

New-Item -ItemType Directory -Path $audioTarget -Force | Out-Null
New-Item -ItemType Directory -Path $scriptsTarget -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $payloadRoot "audioww\oldshoot.bnk") -Destination $audioTarget -Force
Copy-Item -LiteralPath (Join-Path $payloadRoot "scripts\client\gui\mods\mod_oldshoot.pyc") -Destination $scriptsTarget -Force
Copy-Item -LiteralPath (Join-Path $payloadRoot "scripts\client\gui\mods\oldshoot_data.pyc") -Destination $scriptsTarget -Force

$audioModsPath = Join-Path $audioTarget "audio_mods.xml"
if (Test-Path -LiteralPath $audioModsPath) {
    $backupPath = $audioModsPath + ".oldshoot.bak"
    if (-not (Test-Path -LiteralPath $backupPath)) {
        Copy-Item -LiteralPath $audioModsPath -Destination $backupPath
    }
    [xml]$audioDocument = Get-Content -LiteralPath $audioModsPath -Raw
} else {
    $audioDocument = New-Object System.Xml.XmlDocument
    $root = $audioDocument.CreateElement("audio_mods.xml")
    $audioDocument.AppendChild($root) | Out-Null
}

$audioRoot = $audioDocument.DocumentElement
$loadBanks = $audioRoot.SelectSingleNode("loadBanks")
if ($null -eq $loadBanks) {
    $loadBanks = $audioDocument.CreateElement("loadBanks")
    $audioRoot.AppendChild($loadBanks) | Out-Null
}

$existingBank = $loadBanks.SelectSingleNode("bank[name='oldshoot.bnk']")
if ($null -eq $existingBank) {
    $bank = $audioDocument.CreateElement("bank")
    $name = $audioDocument.CreateElement("name")
    $name.InnerText = "oldshoot.bnk"
    $bank.AppendChild($name) | Out-Null
    $loadBanks.AppendChild($bank) | Out-Null
}

$settings = New-Object System.Xml.XmlWriterSettings
$settings.Indent = $true
$settings.Encoding = New-Object System.Text.UTF8Encoding($false)
$writer = [System.Xml.XmlWriter]::Create($audioModsPath, $settings)
try {
    $audioDocument.Save($writer)
} finally {
    $writer.Dispose()
}

Write-Host "OldShootSounds installed to $targetRoot"
Write-Host "Existing voiceover.bnk and other audio_mods.xml entries were preserved"

if ($interactiveSelection) {
    $message = "OldShootSounds was installed successfully." + [Environment]::NewLine + [Environment]::NewLine + $targetRoot
    [System.Windows.Forms.MessageBox]::Show($message, "OldShootSounds", "OK", "Information") | Out-Null
}
