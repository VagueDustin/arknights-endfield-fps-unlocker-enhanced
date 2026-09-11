#include <windows.h>
#include <d3dcommon.h>
#include <filesystem>
#include <fstream>
#include <iostream>

using Reader = int (*)();
bool Wait(Reader reader, int expected) {
    const auto deadline = GetTickCount64() + 10000;
    while (reader() != expected && GetTickCount64() < deadline) Sleep(50);
    if (reader() != expected) {
        std::cerr << "Expected " << expected << " got " << reader() << '\n';
        return false;
    }
    return true;
}
void Config(const std::filesystem::path& path, int fps, int vsync, int background = 0) {
    const auto temporary = path.wstring() + L".new";
    {
        std::ofstream stream(temporary);
        stream << "[FPS]\nTarget=" << fps << "\nVSync=" << vsync << "\nBackground=" << background << '\n';
    }
    if (!MoveFileExW(temporary.c_str(), path.c_str(), MOVEFILE_REPLACE_EXISTING)) ExitProcess(10);
}
int wmain() {
    wchar_t modulePath[32768];
    GetModuleFileNameW(nullptr, modulePath, 32768);
    const auto directory = std::filesystem::path(modulePath).parent_path();
    const auto config = directory / L"endfield-enhancer.ini";
    Config(config, 144, 0);
    wchar_t system[32768];
    GetSystemDirectoryW(system, 32768);
    std::filesystem::copy_file(std::filesystem::path(system) / L"d3dcompiler_47.dll",
        directory / L"endfield_original_compiler.dll", std::filesystem::copy_options::overwrite_existing);
    HMODULE fake = LoadLibraryW((directory / L"GameAssembly.dll").c_str());
    if (!fake) return 2;
    auto fps = reinterpret_cast<Reader>(GetProcAddress(fake, "ReadFps"));
    auto vsync = reinterpret_cast<Reader>(GetProcAddress(fake, "ReadVsync"));
    auto badThread = reinterpret_cast<Reader>(GetProcAddress(fake, "BadThread"));
    if (!fps || !vsync || !badThread) return 3;
    HMODULE loader = LoadLibraryW((directory / L"d3dcompiler_47.dll").c_str());
    if (!loader) return 4;
    using CreateBlob = HRESULT (WINAPI*)(SIZE_T, ID3DBlob**);
    auto createBlob = reinterpret_cast<CreateBlob>(GetProcAddress(loader, "D3DCreateBlob"));
    ID3DBlob* blob = nullptr;
    if (!createBlob || FAILED(createBlob(64, &blob)) || !blob || blob->GetBufferSize() != 64) return 5;
    blob->Release();
    if (!Wait(fps, 144) || !Wait(vsync, 0)) return 6;
    Config(config, 240, -1);
    if (!Wait(fps, 240) || !Wait(vsync, 1)) return 7;
    Config(config, -1, 0, 30);
    if (!Wait(fps, 30) || !Wait(vsync, 0)) return 8;
    Config(config, -1, 0);
    if (!Wait(fps, -1) || badThread()) return 9;
    std::cout << "PASS: compiler forwarding, FPS/VSync reload, VSync restore, background cap, thread attachment\n";
    return 0;
}
