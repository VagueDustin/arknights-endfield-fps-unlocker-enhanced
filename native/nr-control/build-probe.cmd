@echo off
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /EHsc /W4 /Fe:build\native-nr-audit\control_probe.exe /Fo:build\native-nr-audit\control_probe.obj native\nr-control\control_probe.cpp
