// SPDX-License-Identifier: GPL-3.0-only
#include "FateNrControl.h"
#include <cstdio>
int main() {
    FateNrControl::Endpoint endpoint;
    FateNrControl::Settings current {0, 0, 0, 1, 1, 1, -1, 1};
    if (!endpoint.Open()) return 2;
    printf("%lu\n", GetCurrentProcessId()); fflush(stdout);
    for (int i = 0; i < 600; ++i) {
        FateNrControl::Settings request;
        if (endpoint.Poll(request)) current = request;
        endpoint.Publish(current); // Transport test only. Never reports a rendered frame.
        Sleep(50);
    }
    return 0;
}
