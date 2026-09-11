// SPDX-License-Identifier: GPL-3.0-only
#pragma once
#include <windows.h>
#include <cstdio>

// Opt-in, first-chance observation only. A recorded exception may be handled
// successfully by the application. Never changes exception disposition.
namespace FateStartupTrace {
inline HANDLE output = INVALID_HANDLE_VALUE;
inline PVOID observer = nullptr;
inline PVOID volatile sites[64]{};
inline void Mark(const char* text) {
    if (output == INVALID_HANDLE_VALUE) return;
    DWORD written = 0;
    WriteFile(output, text, static_cast<DWORD>(lstrlenA(text)), &written, nullptr);
}
inline LONG CALLBACK Observe(EXCEPTION_POINTERS* info) {
    DWORD code = info->ExceptionRecord->ExceptionCode;
    if (code != EXCEPTION_ACCESS_VIOLATION && code != EXCEPTION_ILLEGAL_INSTRUCTION &&
        code != EXCEPTION_IN_PAGE_ERROR && code != EXCEPTION_INT_DIVIDE_BY_ZERO)
        return EXCEPTION_CONTINUE_SEARCH;
    bool fresh = false;
    for (auto& site : sites) {
        PVOID existing = InterlockedCompareExchangePointer(&site, info->ExceptionRecord->ExceptionAddress, nullptr);
        if (existing == info->ExceptionRecord->ExceptionAddress) return EXCEPTION_CONTINUE_SEARCH;
        if (!existing) { fresh = true; break; }
    }
    if (!fresh) return EXCEPTION_CONTINUE_SEARCH;
    MEMORY_BASIC_INFORMATION region{};
    VirtualQuery(info->ExceptionRecord->ExceptionAddress, &region, sizeof(region));
    char modulePath[MAX_PATH]{};
    if (region.Type == MEM_IMAGE && region.AllocationBase)
        GetModuleFileNameA(static_cast<HMODULE>(region.AllocationBase), modulePath, MAX_PATH);
    char line[640];
    int length = sprintf_s(line, "first_chance code=%08lX thread=%lu address=%p module_base=%p offset=%llX module=%s\r\n",
        code, GetCurrentThreadId(), info->ExceptionRecord->ExceptionAddress, region.AllocationBase,
        static_cast<unsigned long long>(reinterpret_cast<ULONG_PTR>(info->ExceptionRecord->ExceptionAddress) -
                                        reinterpret_cast<ULONG_PTR>(region.AllocationBase)), modulePath);
    DWORD written = 0;
    if (length > 0) WriteFile(output, line, static_cast<DWORD>(length), &written, nullptr);
    return EXCEPTION_CONTINUE_SEARCH;
}
inline void Start(HMODULE module) {
    wchar_t path[MAX_PATH]{};
    DWORD length = GetModuleFileNameW(module, path, MAX_PATH);
    if (!length || length >= MAX_PATH) return;
    wchar_t* name = wcsrchr(path, L'\\');
    if (!name) return;
    ++name;
    size_t available = MAX_PATH - (name - path);
    if (wcscpy_s(name, available, L"OptiScaler.ini")) return;
    if (GetPrivateProfileIntW(L"FateDiagnostics", L"StartupTrace", 0, path) != 1) return;
    if (swprintf_s(name, available, L"FateEngine-startup-trace-%lu.log", GetCurrentProcessId()) < 0) return;
    output = CreateFileW(path, FILE_APPEND_DATA, FILE_SHARE_READ | FILE_SHARE_WRITE, nullptr,
                         CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL | FILE_FLAG_WRITE_THROUGH, nullptr);
    if (output == INVALID_HANDLE_VALUE) return;
    Mark("startup_trace version=2; first-chance records are not proof of an unhandled crash\r\n");
    char executable[MAX_PATH]{};
    GetModuleFileNameA(nullptr, executable, MAX_PATH);
    Mark("process="); Mark(executable); Mark("\r\n");
    observer = AddVectoredExceptionHandler(0, Observe);
    Mark(observer ? "observer_registered\r\n" : "observer_registration_failed\r\n");
}
inline void Stop() {
    if (observer) { RemoveVectoredExceptionHandler(observer); observer = nullptr; }
    Mark("process_detach\r\n");
    if (output != INVALID_HANDLE_VALUE) { CloseHandle(output); output = INVALID_HANDLE_VALUE; }
}
}
