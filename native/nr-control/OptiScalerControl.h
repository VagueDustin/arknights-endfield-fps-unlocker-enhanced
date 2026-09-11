// SPDX-License-Identifier: GPL-3.0-only
#pragma once
#include "FateNrControl.h"
#include <Config.h>
namespace FateNrControl {
inline Endpoint endpoint;
inline Settings Current() {
    auto& c = *Config::Instance();
    return {c.DlssNrEnabled.value_or_default(), c.DlssNrStyle.value_or_default(),
        c.DlssNrPreset.value_or_default(), c.DlssNrIntensity.value_or_default(),
        c.DlssNrLocalStructure.value_or_default(), c.DlssNrLocalTone.value_or_default(),
        c.DlssNrSkinStructure.value_or_default(), c.DlssNrAutoMask.value_or_default()};
}
inline void Tick(bool failed = false) {
    // Handle the approved Insert bind without requiring an overlay or ReShade.
    static bool keyWasDown = false;
    DWORD foregroundPid = 0;
    GetWindowThreadProcessId(GetForegroundWindow(), &foregroundPid);
    const bool keyDown = (GetAsyncKeyState(VK_INSERT) & 0x8000) != 0;
    if (foregroundPid == GetCurrentProcessId() && keyDown && !keyWasDown) {
        auto& enabled = Config::Instance()->DlssNrEnabled;
        enabled = !enabled.value_or_default();
    }
    keyWasDown = keyDown;
    Settings s;
    if (endpoint.Poll(s)) {
        auto& c = *Config::Instance();
        c.DlssNrEnabled = s.enabled != 0; c.DlssNrStyle = s.style; c.DlssNrPreset = s.preset;
        c.DlssNrIntensity = s.intensity; c.DlssNrLocalStructure = s.structure;
        c.DlssNrLocalTone = s.tone; c.DlssNrSkinStructure = s.skin; c.DlssNrAutoMask = s.autoMask != 0;
    }
    endpoint.Publish(Current(), false, failed);
}
inline void Rendered() { endpoint.Publish(Current(), true); }
}
