param([string]$pythonExe='python', [string]$runtimePackage='build/package')
$ErrorActionPreference='Stop'
if (Test-Path 'build/build-deps') { $env:PYTHONPATH=(Resolve-Path 'build/build-deps').Path }
$env:PYINSTALLER_CONFIG_DIR=Join-Path (Get-Location) 'build/pyinstaller-cache'
$package='build/reshade-preview/package'
New-Item -ItemType Directory -Force -Path $package | Out-Null
& $pythonExe tools/build_product_assets.py
if ($LASTEXITCODE) { throw 'Brand build failed' }
& $pythonExe -m PyInstaller --noconfirm --clean --onefile --windowed --collect-all customtkinter --add-data 'assets;assets' --icon assets/identity/fate-engine.ico --version-file build/brand/FateEngine-version.txt --name FateEngine --distpath $package tools/desktop.py *> build/reshade-preview/gui-build.log
if ($LASTEXITCODE) { throw 'GUI build failed' }
& $pythonExe -m PyInstaller --noconfirm --clean --onefile --icon assets/identity/fate-engine.ico --version-file build/brand/EndfieldManager-version.txt --name EndfieldManager --distpath $package tools/manage.py *> build/reshade-preview/cli-build.log
if ($LASTEXITCODE) { throw 'Manager build failed' }
Copy-Item -LiteralPath (Join-Path $runtimePackage 'd3dcompiler_47.dll'),(Join-Path $runtimePackage 'endfield_fps.dll') -Destination $package
& $pythonExe tools/package_build.py $package
& $pythonExe tools/package_notices.py $package
Copy-Item -LiteralPath (Join-Path $runtimePackage 'licenses/MinHook.txt') -Destination "$package/licenses/MinHook.txt"
Write-Output 'Desktop and manager packaged successfully.'
