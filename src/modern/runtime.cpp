#include <windows.h>
#include "MinHook.h"
#include <atomic>
#include <filesystem>
#include <fstream>
#include <string>

namespace {
std::wstring configPath;
std::filesystem::path logPath;
std::atomic<int> target{120};
std::atomic<int> vsync{-1};
using Setter = void (*)(int, const void*);
Setter originalFps = nullptr;
Setter originalVsync = nullptr;
void FpsHook(int, const void* method) { originalFps(target.load(), method); }
void VsyncHook(int value, const void* method) {
    const int overrideValue = vsync.load();
    originalVsync(overrideValue < 0 ? value : overrideValue, method);
}

void Log(const std::string& message) {
    OutputDebugStringA(("Endfield Enhancer: " + message + "\n").c_str());
    std::ofstream file(logPath, std::ios::app);
    SYSTEMTIME time;
    GetLocalTime(&time);
    file << time.wYear << '-' << time.wMonth << '-' << time.wDay << ' '
         << time.wHour << ':' << time.wMinute << ':' << time.wSecond
         << " " << message << '\n';
}

int Read(const wchar_t* name, int fallback) {
    return static_cast<int>(GetPrivateProfileIntW(L"FPS", name, fallback, configPath.c_str()));
}
bool ValidFps(int value) { return value == -1 || (value >= 30 && value <= 1000); }

struct Api {
    void* (*domainGet)();
    void* (*attach)(void*);
    void (*detach)(void*);
    void** (*assemblies)(void*, size_t*);
    void* (*image)(void*);
    void* (*klass)(void*, const char*, const char*);
    void* (*method)(void*, const char*, int);
    void* (*invoke)(void*, void*, void**, void**);
    void* (*unbox)(void*);
};

bool Resolve(HMODULE module, Api& api) {
#define RESOLVE(field, name) \
    api.field = reinterpret_cast<decltype(api.field)>(GetProcAddress(module, name)); \
    if (!api.field) { Log("Missing runtime export: " name); return false; }
    RESOLVE(domainGet, "il2cpp_domain_get")
    RESOLVE(attach, "il2cpp_thread_attach")
    RESOLVE(detach, "il2cpp_thread_detach")
    RESOLVE(assemblies, "il2cpp_domain_get_assemblies")
    RESOLVE(image, "il2cpp_assembly_get_image")
    RESOLVE(klass, "il2cpp_class_from_name")
    RESOLVE(method, "il2cpp_class_get_method_from_name")
    RESOLVE(invoke, "il2cpp_runtime_invoke")
    RESOLVE(unbox, "il2cpp_object_unbox")
#undef RESOLVE
    return true;
}

bool Invoke(Api& api, void* method, int value) {
    void* arguments[] = {&value};
    void* exception = nullptr;
    api.invoke(method, nullptr, arguments, &exception);
    if (exception) Log("Runtime setter raised an exception; stopping overrides.");
    return !exception;
}

DWORD WINAPI Worker(LPVOID parameter) {
    wchar_t path[32768];
    DWORD processLength = GetModuleFileNameW(nullptr, path, 32768);
    if (!processLength || processLength >= 32768 ||
        _wcsicmp(std::filesystem::path(path).filename().c_str(), L"Endfield.exe") != 0) return 0;
    const DWORD length = GetModuleFileNameW(static_cast<HMODULE>(parameter), path, 32768);
    if (!length || length >= 32768) return 1;
    const auto directory = std::filesystem::path(std::wstring(path, length)).parent_path();
    configPath = (directory / L"endfield-enhancer.ini").wstring();
    // A user-writable log location also works when the game lives in Program Files.
    wchar_t local[32768];
    const DWORD localLength = GetEnvironmentVariableW(L"LOCALAPPDATA", local, 32768);
    if (!localLength || localLength >= 32768) return 1;
    const auto logDirectory = std::filesystem::path(local) / L"EndfieldEnhancer";
    std::error_code error;
    std::filesystem::create_directories(logDirectory, error);
    logPath = logDirectory / (L"runtime-" + std::to_wstring(GetCurrentProcessId()) + L".log");
    Log("Starting FPS-only runtime 0.2.0. Graphics overrides are disabled.");
    if (!std::filesystem::is_regular_file(configPath, error)) {
        Log("Configuration missing; no overrides installed.");
        return 1;
    }

    Api api{};
    HMODULE assembly = nullptr;
    const ULONGLONG deadline = GetTickCount64() + 120000;
    while (!(assembly = GetModuleHandleW(L"GameAssembly.dll")) && GetTickCount64() < deadline)
        Sleep(250);
    if (!assembly) { Log("Timed out waiting for GameAssembly.dll."); return 1; }
    if (!Resolve(assembly, api)) return 1;
    void* domain = nullptr;
    while (!(domain = api.domainGet()) && GetTickCount64() < deadline) Sleep(250);
    if (!domain) { Log("Timed out waiting for IL2CPP domain."); return 1; }
    void* thread = api.attach(domain);
    if (!thread) { Log("IL2CPP thread attach failed."); return 1; }
    void* fpsMethod = nullptr;
    void* vsyncMethod = nullptr;
    void* vsyncGetter = nullptr;
    while ((!fpsMethod || !vsyncMethod) && GetTickCount64() < deadline) {
        size_t count = 0;
        void** assemblies = api.assemblies(domain, &count);
        for (size_t index = 0; assemblies && index < count; ++index) {
            void* image = api.image(assemblies[index]);
            if (!image) continue;
            void* app = api.klass(image, "UnityEngine", "Application");
            void* quality = api.klass(image, "UnityEngine", "QualitySettings");
            if (app) fpsMethod = api.method(app, "set_targetFrameRate", 1);
            if (quality) {
                vsyncMethod = api.method(quality, "set_vSyncCount", 1);
                vsyncGetter = api.method(quality, "get_vSyncCount", 0);
            }
        }
        if (!fpsMethod || !vsyncMethod) Sleep(250);
    }
    if (!fpsMethod || !vsyncMethod || !vsyncGetter) {
        Log("Required Unity setters unavailable; no hooks installed.");
        api.detach(thread);
        return 1;
    }
    // The native method pointer is the first field of IL2CPP MethodInfo.
    void* fpsAddress = *static_cast<void**>(fpsMethod);
    void* vsyncAddress = *static_cast<void**>(vsyncMethod);
    if (!fpsAddress || !vsyncAddress || fpsAddress == vsyncAddress) {
        Log("Invalid setter addresses."); api.detach(thread); return 1;
    }
    int configured = Read(L"Target", 120);
    int configuredVsync = Read(L"VSync", -1);
    int background = Read(L"Background", 0);
    if (!ValidFps(configured) || configuredVsync < -1 || configuredVsync > 4 ||
        (background != 0 && (background < 30 || background > 1000))) {
        Log("Invalid configuration; no hooks installed."); api.detach(thread); return 1;
    }
    target = configured;
    vsync = configuredVsync;
    void* getterException = nullptr;
    void* boxedVsync = api.invoke(vsyncGetter, nullptr, nullptr, &getterException);
    void* unboxedVsync = boxedVsync && !getterException ? api.unbox(boxedVsync) : nullptr;
    if (!unboxedVsync) {
        Log("Could not read original VSync value; no hooks installed.");
        api.detach(thread); return 1;
    }
    const int originalVsyncValue = *static_cast<int*>(unboxedVsync);
    MH_STATUS status = MH_Initialize();
    if (status != MH_OK) {
        Log(std::string("MinHook initialization failed: ") + MH_StatusToString(status));
        api.detach(thread); return 1;
    }
    bool fpsCreated = false;
    bool vsyncCreated = false;
    status = MH_CreateHook(fpsAddress, reinterpret_cast<void*>(&FpsHook),
        reinterpret_cast<void**>(&originalFps));
    fpsCreated = status == MH_OK;
    if (fpsCreated) {
        status = MH_CreateHook(vsyncAddress, reinterpret_cast<void*>(&VsyncHook),
            reinterpret_cast<void**>(&originalVsync));
        vsyncCreated = status == MH_OK;
    }
    if (status == MH_OK) status = MH_EnableHook(fpsAddress);
    if (status == MH_OK) status = MH_EnableHook(vsyncAddress);
    if (status != MH_OK) {
        Log(std::string("Hook setup failed: ") + MH_StatusToString(status));
    } else {
        Log("Unity setters hooked. Verify actual gameplay FPS separately.");
        int previousTarget = 0;
        int previousVsync = -2;
        while (true) {
            configured = Read(L"Target", 120);
            configuredVsync = Read(L"VSync", -1);
            background = Read(L"Background", 0);
            if (!ValidFps(configured) || configuredVsync < -1 || configuredVsync > 4 ||
                (background != 0 && (background < 30 || background > 1000))) {
                Log("Invalid updated configuration; retaining last valid values.");
                Sleep(2000); continue;
            }
            DWORD foregroundPid = 0;
            GetWindowThreadProcessId(GetForegroundWindow(), &foregroundPid);
            const int effective = background && foregroundPid != GetCurrentProcessId()
                ? background : configured;
            target = effective;
            vsync = configuredVsync;
            if (effective != previousTarget || configuredVsync != previousVsync) {
                if (!Invoke(api, fpsMethod, effective)) break;
                if (!Invoke(api, vsyncMethod, configuredVsync < 0 ? originalVsyncValue : configuredVsync)) break;
                Log("Applied target=" + std::to_string(effective) +
                    " vsync=" + std::to_string(configuredVsync));
                previousTarget = effective;
                previousVsync = configuredVsync;
            }
            Sleep(1000);
        }
    }
    // Only remove hooks owned by this component.
    if (fpsCreated) { MH_DisableHook(fpsAddress); MH_RemoveHook(fpsAddress); }
    if (vsyncCreated) { MH_DisableHook(vsyncAddress); MH_RemoveHook(vsyncAddress); }
    MH_Uninitialize();
    api.detach(thread);
    return 1;
}
} // namespace

BOOL WINAPI DllMain(HMODULE module, DWORD reason, LPVOID) {
    if (reason == DLL_PROCESS_ATTACH) {
        DisableThreadLibraryCalls(module);
        // Keep hook code resident for the lifetime of the process.
        HMODULE pinned = nullptr;
        if (GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS |
                GET_MODULE_HANDLE_EX_FLAG_PIN, reinterpret_cast<LPCWSTR>(module), &pinned)) {
            HANDLE thread = CreateThread(nullptr, 0, Worker, module, 0, nullptr);
            if (thread) CloseHandle(thread);
        }
    }
    return TRUE;
}
