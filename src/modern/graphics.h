#pragma once
#include <windows.h>
#include <string>

namespace Graphics {
struct Config {
    int anisotropic = -1;
    int sharpening = -1;
    int renderScale = -1;
    int shadows = -1;
    int ambientOcclusion = -1;
    int temporalAA = -1;
};
using Logger = void (*)(const std::string&);
bool KnownRuntime(const std::wstring& path);
bool Initialize(HMODULE assembly, bool knownRuntime, Logger logger);
void Publish(const Config& config);
bool Valid(const Config& config);
void CheckCallback();
}
