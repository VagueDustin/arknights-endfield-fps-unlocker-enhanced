#include "graphics.h"
#include "MinHook.h"
#include <cmath>
#include <iostream>
#include <thread>
#include <cstring>

void Log(const std::string& message) { std::cout << message << '\n'; }
template<typename T> T Function(HMODULE module, const char* name) {
    auto result = reinterpret_cast<T>(GetProcAddress(module, name));
    if (!result) ExitProcess(20);
    return result;
}
int main(int argc, char** argv) {
    HMODULE fake = LoadLibraryW(L"GameAssembly.dll");
    if (!fake) return 1;
    auto fire = Function<void (*)()>(fake, "FireFrame");
    auto read = Function<double (*)(const char*)>(fake, "ReadSetting");
    auto overridden = Function<bool (*)(const char*)>(fake, "IsOverridden");
    auto aniso = Function<int (*)()>(fake, "ReadAniso");
    auto badThread = Function<int (*)()>(fake, "BadThread");
    auto handles = Function<unsigned (*)()>(fake, "HandleCount");
    auto reject = Function<void (*)(const char*)>(fake, "RejectSetting");
    auto wrongType = Function<void (*)(const char*)>(fake, "WrongType");
    Function<void (*)()>(fake, "SetGraphicsThread")();
    if (MH_Initialize() != MH_OK) return 2;
    if (argc > 1 && !std::strcmp(argv[1], "unknown"))
        return Graphics::Initialize(fake, false, Log) ? 3 : 0;
    if (argc > 1 && !std::strcmp(argv[1], "signature")) {
        Function<void (*)()>(fake, "BadCallbackSignature")();
        return Graphics::Initialize(fake, true, Log) ? 4 : 0;
    }
    if (!Graphics::Initialize(fake, true, Log)) return 5;
    Graphics::Config config{2, 20, 125, 2048, 0, 0};
    Graphics::Publish(config);
    if (std::abs(read("renderingScale") - 1.0) > 0.001) return 6; // No callback, no writes.
    auto tick = [&]() { Sleep(1100); fire(); };
    tick();
    if (aniso() != 2 || std::abs(read("sharpenStrength1K") - 0.2) > 0.001 ||
        std::abs(read("renderingScale") - 1.25) > 0.001 || read("csmShadowMapTileResolution") != 2048 ||
        read("gtaoEnable") != 0 || read("taauEnable") != 0 || badThread()) return 7;
    Graphics::Publish({}); tick();
    if (aniso() != 1 || std::abs(read("sharpenStrength1K") - 0.35) > 0.001 ||
        std::abs(read("dlssSharpenStrength") - 0.6) > 0.001 || !overridden("dlssSharpenStrength") ||
        overridden("sharpenStrength1K") || handles()) return 8;
    reject("renderingScale");
    Graphics::Publish({-1, 40, 150}); tick();
    if (read("renderingScale") != 1.0 || std::abs(read("sharpenStrength1K") - 0.4) > 0.001) return 9;
    Graphics::Publish({}); tick();
    wrongType("renderingScale"); reject("");
    Graphics::Publish({-1, -1, 150}); tick();
    if (read("renderingScale") != 1.0 || handles()) return 10;
    Graphics::Publish({}); tick();
    std::thread other([&]() { fire(); }); other.join();
    if (badThread()) return 11;
    std::cout << "PASS: render-only changes, typed validation, original overrides restored, rejection isolation, handles released\n";
    return 0;
}
