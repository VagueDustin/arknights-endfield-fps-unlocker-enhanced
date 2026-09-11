// SPDX-License-Identifier: GPL-3.0-only
#include "StartupTrace.h"
int main() {
    FateStartupTrace::Start(GetModuleHandleW(nullptr));
    int handled = 0;
    for (int i = 0; i < 80; ++i) {
        __try { RaiseException(EXCEPTION_ACCESS_VIOLATION, 0, 0, nullptr); }
        __except(EXCEPTION_EXECUTE_HANDLER) { ++handled; }
    }
    FateStartupTrace::Stop();
    return handled == 80 ? 0 : 1;
}
