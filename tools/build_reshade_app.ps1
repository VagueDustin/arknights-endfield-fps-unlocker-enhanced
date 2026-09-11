param(
    [string]$pythonExe = 'python',
    # Folder holding d3dcompiler_47.dll, endfield_fps.dll and package.json produced by
    # `cmake --install` (or the CI package artifact) for THIS source revision.
    [Parameter(Mandatory = $true)][string]$runtimePackage
)
$ErrorActionPreference = 'Stop'
$product = Get-Content -LiteralPath 'assets/identity/product.json' -Raw | ConvertFrom-Json
$manifestPath = Join-Path $runtimePackage 'package.json'
if (-not (Test-Path -LiteralPath $manifestPath)) {
    throw "No package.json in '$runtimePackage'. Point -runtimePackage at a CMake install prefix or the CI package artifact built from this source."
}
$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
if ($manifest.version -ne $product.version) {
    throw "Runtime package is version $($manifest.version) but the product is $($product.version). Rebuild the native DLLs from this source before packaging; never reuse an older build."
}
foreach ($file in $manifest.files.PSObject.Properties) {
    $actual = (Get-FileHash -LiteralPath (Join-Path $runtimePackage $file.Name) -Algorithm SHA256).Hash.ToLower()
    if ($actual -ne $file.Value) { throw "Runtime package hash mismatch: $($file.Name)" }
    Write-Output "Runtime $($file.Name) $actual"
}
if (Test-Path 'build/build-deps') { $env:PYTHONPATH = (Resolve-Path 'build/build-deps').Path }
$env:PYINSTALLER_CONFIG_DIR = Join-Path (Get-Location) 'build/pyinstaller-cache'
$package = 'build/reshade-preview/package'
New-Item -ItemType Directory -Force -Path $package | Out-Null
& $pythonExe tools/build_product_assets.py
if ($LASTEXITCODE) { throw 'Brand build failed' }
& $pythonExe -m PyInstaller --noconfirm --clean --onefile --windowed --collect-all customtkinter --add-data 'assets;assets' --icon assets/identity/fate-engine.ico --version-file build/brand/FateEngine-version.txt --name FateEngine --distpath $package tools/desktop.py *> build/reshade-preview/gui-build.log
if ($LASTEXITCODE) { throw 'GUI build failed' }
& $pythonExe -m PyInstaller --noconfirm --clean --onefile --icon assets/identity/fate-engine.ico --version-file build/brand/EndfieldManager-version.txt --name EndfieldManager --distpath $package tools/manage.py *> build/reshade-preview/cli-build.log
if ($LASTEXITCODE) { throw 'Manager build failed' }
Copy-Item -LiteralPath (Join-Path $runtimePackage 'd3dcompiler_47.dll'), (Join-Path $runtimePackage 'endfield_fps.dll') -Destination $package
& $pythonExe tools/package_build.py $package
& $pythonExe tools/package_notices.py $package
Copy-Item -LiteralPath (Join-Path $runtimePackage 'licenses/MinHook.txt') -Destination "$package/licenses/MinHook.txt"
$app = Start-Process -FilePath (Join-Path $package 'FateEngine.exe') -ArgumentList '--smoke-test' -WindowStyle Hidden -PassThru -Wait
if ($app.ExitCode -ne 0) { throw 'Packaged desktop app failed its smoke test' }
Write-Output "Desktop and manager packaged successfully for $($product.version)."
