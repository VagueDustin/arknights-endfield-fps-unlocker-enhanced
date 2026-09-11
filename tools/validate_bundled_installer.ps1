param(
    [string]$isccPath = 'build/compiler/inno/ISCC.exe',
    [string]$packageDir = '..\build\reshade-preview\package'
)
# Compiles an isolated validation copy of the bundled installer, installs it into a
# scratch folder with a scratch LOCALAPPDATA, verifies every third-party payload hash,
# runs the installed app's smoke test, and uninstalls. No game folder is touched.
$ErrorActionPreference = 'Stop'
$testRoot = Join-Path (Get-Location) 'build/reshade-preview/installer-validation'
New-Item -ItemType Directory -Force -Path $testRoot | Out-Null
$env:LOCALAPPDATA = Join-Path $testRoot 'local-app-data'
New-Item -ItemType Directory -Force -Path $env:LOCALAPPDATA | Out-Null
& $isccPath "/DPackageDir=$packageDir" /DBundledReShade /DValidationBuild installer\EndfieldEnhancer.iss *> build/reshade-preview/validation-compile.log
if ($LASTEXITCODE) { throw 'Validation installer compilation failed; see build/reshade-preview/validation-compile.log' }
$installPath = Join-Path $testRoot 'app'
$installer = (Resolve-Path 'build/installer/Fate-Engine-ReShade-Validation.exe').Path
$process = Start-Process -FilePath $installer -ArgumentList '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/CURRENTUSER', "/DIR=`"$installPath`"", ("/LOG=`"" + (Join-Path $testRoot 'install.log') + "`"") -WindowStyle Hidden -PassThru -Wait
if ($process.ExitCode -ne 0) { throw "Install failed: $($process.ExitCode)" }
$manifest = Get-Content -LiteralPath (Join-Path $installPath 'reshade-payload.json') -Raw | ConvertFrom-Json
foreach ($file in $manifest.files.PSObject.Properties) {
    $actual = (Get-FileHash -LiteralPath (Join-Path $installPath ($file.Name)) -Algorithm SHA256).Hash.ToLower()
    if ($actual -ne $file.Value) { throw "Installed payload mismatch: $($file.Name)" }
}
$package = Get-Content -LiteralPath (Join-Path $installPath 'package.json') -Raw | ConvertFrom-Json
foreach ($file in $package.files.PSObject.Properties) {
    $actual = (Get-FileHash -LiteralPath (Join-Path $installPath ($file.Name)) -Algorithm SHA256).Hash.ToLower()
    if ($actual -ne $file.Value) { throw "Installed runtime mismatch: $($file.Name)" }
}
$app = Start-Process -FilePath (Join-Path $installPath 'FateEngine.exe') -ArgumentList '--smoke-test' -WindowStyle Hidden -PassThru -Wait
if ($app.ExitCode -ne 0) { throw 'Installed app smoke failed' }
$uninstaller = Join-Path $installPath 'unins000.exe'
$process = Start-Process -FilePath $uninstaller -ArgumentList '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', ("/LOG=`"" + (Join-Path $testRoot 'uninstall.log') + "`"") -WindowStyle Hidden -PassThru -Wait
if ($process.ExitCode -ne 0) { throw "Uninstall failed: $($process.ExitCode)" }
if (Test-Path -LiteralPath (Join-Path $installPath 'FateEngine.exe')) { throw 'App remained after uninstall' }
Write-Output "PASS: isolated installer $($package.version), payload and runtime hashes, installed app smoke, and uninstall."
