// SPDX-License-Identifier: GPL-3.0-only
// Copyright (c) 2026 VagueDustin Enterprises
// Native OptiScaler integration. This component is separate from the MIT desktop app.
#pragma once
#include <windows.h>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <cwchar>

namespace FateNrControl {
struct Settings {
    uint32_t enabled, style, preset;
    float intensity, structure, tone, skin;
    uint32_t autoMask;
};
struct Shared {
    uint32_t magic, version, pid, size;
    uint64_t session;
    volatile LONG request;
    Settings requested;
    volatile LONG statusSequence;
    uint32_t accepted, evaluated, rejected;
    Settings current;
    uint32_t failed;
    uint64_t heartbeat, frames;
};
static_assert(sizeof(Settings) == 32);
static_assert(sizeof(Shared) == 128);
inline bool Valid(const Settings& s) {
    return s.enabled <= 1 && s.style <= 2 && s.preset <= 3 && s.autoMask <= 1 &&
        std::isfinite(s.intensity) && s.intensity >= 0 && s.intensity <= 2 &&
        std::isfinite(s.structure) && s.structure >= 0 && s.structure <= 2 &&
        std::isfinite(s.tone) && s.tone >= 0 && s.tone <= 2 &&
        std::isfinite(s.skin) && s.skin >= -1 && s.skin <= 2;
}
class Endpoint {
    HANDLE mapping = nullptr;
    Shared* shared = nullptr;
    uint32_t seen = 0, accepted = 0, evaluated = 0, rejected = 0;
    uint64_t frames = 0;
public:
    ~Endpoint() { if (shared) UnmapViewOfFile(shared); if (mapping) CloseHandle(mapping); }
    bool Open() {
        if (shared) return true;
        wchar_t name[96];
        swprintf_s(name, L"Local\\FateEngine.NR.%lu", GetCurrentProcessId());
        mapping = CreateFileMappingW(INVALID_HANDLE_VALUE, nullptr, PAGE_READWRITE, 0, sizeof(Shared), name);
        if (!mapping) return false;
        if (GetLastError() == ERROR_ALREADY_EXISTS) { CloseHandle(mapping); mapping = nullptr; return false; }
        shared = static_cast<Shared*>(MapViewOfFile(mapping, FILE_MAP_ALL_ACCESS, 0, 0, sizeof(Shared)));
        if (!shared) { CloseHandle(mapping); mapping = nullptr; return false; }
        std::memset(shared, 0, sizeof(Shared));
        shared->version = 1; shared->pid = GetCurrentProcessId(); shared->size = sizeof(Shared);
        shared->session = GetTickCount64();
        MemoryBarrier(); shared->magic = 0x524E4546;
        return true;
    }
    bool Poll(Settings& result) {
        if (!Open()) return false;
        LONG revision = InterlockedCompareExchange(&shared->request, 0, 0);
        if (!revision || (revision & 1) || static_cast<uint32_t>(revision) == seen) return false;
        Settings copy; std::memcpy(&copy, &shared->requested, sizeof(copy)); MemoryBarrier();
        if (revision != InterlockedCompareExchange(&shared->request, 0, 0)) return false;
        seen = static_cast<uint32_t>(revision);
        if (!Valid(copy)) { rejected = seen; return false; }
        result = copy; accepted = seen; return true;
    }
    void Publish(const Settings& current, bool rendered = false, bool failed = false) {
        if (!Open()) return;
        if (rendered) { evaluated = accepted; ++frames; }
        InterlockedIncrement(&shared->statusSequence);
        shared->accepted = accepted; shared->evaluated = evaluated; shared->rejected = rejected;
        shared->current = current; shared->heartbeat = GetTickCount64(); shared->frames = frames;
        shared->failed = failed;
        InterlockedIncrement(&shared->statusSequence);
    }
};
}
