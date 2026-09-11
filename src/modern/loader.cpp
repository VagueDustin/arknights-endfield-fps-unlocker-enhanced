#include <windows.h>
#include <string>

static DWORD WINAPI Start(LPVOID parameter) {
    wchar_t path[32768];
    DWORD length = GetModuleFileNameW(static_cast<HMODULE>(parameter), path, 32768);
    if (!length || length >= 32768) return 1;
    std::wstring directory(path, length);
    directory.resize(directory.find_last_of(L"\\/") + 1);
    // Use an absolute sibling path, never the current working directory.
    HMODULE payload = LoadLibraryExW((directory + L"endfield_fps.dll").c_str(),
        nullptr, LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR | LOAD_LIBRARY_SEARCH_SYSTEM32);
    if (!payload) {
        OutputDebugStringW(L"Endfield Enhancer: endfield_fps.dll failed to load\n");
        return 1;
    }
    return 0;
}

BOOL WINAPI DllMain(HMODULE module, DWORD reason, LPVOID) {
    if (reason == DLL_PROCESS_ATTACH) {
        DisableThreadLibraryCalls(module);
        HANDLE thread = CreateThread(nullptr, 0, Start, module, 0, nullptr);
        if (thread) CloseHandle(thread);
    }
    return TRUE;
}
