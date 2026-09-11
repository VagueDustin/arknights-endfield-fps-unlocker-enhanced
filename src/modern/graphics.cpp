#include "graphics.h"
#include "MinHook.h"
#include <bcrypt.h>
#include <array>
#include <atomic>
#include <cmath>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <limits>
#include <mutex>
#include <sstream>
#include <vector>

namespace Graphics {
namespace {
struct Api {
    void* (*domain)();
    void** (*assemblies)(void*, size_t*);
    void* (*image)(void*);
    void* (*klass)(void*, const char*, const char*);
    void* (*method)(void*, const char*, int);
    void* (*invoke)(void*, void*, void**, void**);
    void* (*unbox)(void*);
    void* (*objectClass)(void*);
    void* (*parent)(void*);
    const char* (*className)(void*);
    const char* (*classNamespace)(void*);
    const void* (*returnType)(void*);
    const void* (*paramType)(void*, unsigned);
    unsigned (*paramCount)(void*);
    unsigned (*flags)(void*, unsigned*);
    int (*type)(const void*);
    void* (*newString)(const wchar_t*, int);
    unsigned (*newHandle)(void*, bool);
    void* (*handleTarget)(unsigned);
    void (*freeHandle)(unsigned);
} api{};
Logger logMessage = nullptr;
void Log(const std::string& text) { if (logMessage) logMessage("Graphics: " + text); }
Config requested;
std::mutex configMutex;
std::atomic<bool> ready{false};
std::atomic<unsigned> callbackCount{0};
std::atomic<DWORD> callbackThread{0};
using BeforeRender = void (*)(void*, void*, void*, const void*);
BeforeRender originalBeforeRender = nullptr;
void* pipelineGetter = nullptr;
void* anisoGetter = nullptr;
void* anisoSetter = nullptr;
int originalAniso = -1;
int appliedAniso = -1;
ULONGLONG lastPoll = 0;
ULONGLONG started = 0;

enum Kind { Sharpen, SharpenEnabled, Scale, Shadow, AO, TAA };
struct Feature {
    const char* name;
    Kind kind;
    int expectedType;
    unsigned handle = 0;
    std::wstring original;
    bool originallyOverridden = false;
    std::wstring applied;
    std::string lastStatus;
    std::wstring rejected;
};
std::array<Feature, 14> features{{
    {"sharpenStrength1K", Sharpen, 0x0c}, {"sharpenStrength2K", Sharpen, 0x0c},
    {"sharpenStrength4K", Sharpen, 0x0c}, {"dlssSharpenStrength", Sharpen, 0x0c},
    {"fsr3SharpenStrength", Sharpen, 0x0c}, {"pssrSharpness", Sharpen, 0x0c},
    {"sharpenEnabled", SharpenEnabled, 0x02}, {"renderingScale", Scale, 0x0c},
    {"csmShadowMapTileResolution", Shadow, 0x08}, {"characterShadowMapResolution", Shadow, 0x08},
    {"punctualLightTileMaxSize", Shadow, 0x08}, {"asmShadowMapTileResolution", Shadow, 0x08},
    {"gtaoEnable", AO, 0x02}, {"taauEnable", TAA, 0x02}
}};

void Status(Feature& feature, const std::string& value) {
    if (feature.lastStatus != value) {
        Log(std::string(feature.name) + ": " + value);
        feature.lastStatus = value;
    }
}

void* Class(const char* space, const char* name) {
    size_t count = 0;
    void** assemblies = api.assemblies(api.domain(), &count);
    for (size_t i = 0; assemblies && i < count; ++i) {
        void* image = api.image(assemblies[i]);
        if (image) if (void* klass = api.klass(image, space, name)) return klass;
    }
    return nullptr;
}
void* Method(void* klass, const char* name, int count) {
    for (int depth = 0; klass && depth < 32; ++depth, klass = api.parent(klass))
        if (void* method = api.method(klass, name, count)) return method;
    return nullptr;
}
bool Signature(void* method, int result, bool isStatic, int parameter = -1) {
    if (!method || api.paramCount(method) != (parameter < 0 ? 0u : 1u)) return false;
    unsigned ignored = 0;
    if (((api.flags(method, &ignored) & 0x10) != 0) != isStatic) return false;
    return api.type(api.returnType(method)) == result &&
        (parameter < 0 || api.type(api.paramType(method, 0)) == parameter);
}
bool Invoke(void* method, void* object, void** parameters, void*& result) {
    if (!method) return false;
    void* exception = nullptr;
    result = api.invoke(method, object, parameters, &exception);
    return !exception;
}
bool ReadValue(void* method, void* object, int type, std::wstring& text) {
    void* result = nullptr;
    if (!Invoke(method, object, nullptr, result) || !result) return false;
    void* value = api.unbox(result);
    if (!value) return false;
    if (type == 0x02) text = *static_cast<bool*>(value) ? L"True" : L"False";
    else if (type == 0x08) text = std::to_wstring(*static_cast<int*>(value));
    else if (type == 0x0c) {
        const float number = *static_cast<float*>(value);
        if (!std::isfinite(number)) return false;
        std::wostringstream stream;
        stream.imbue(std::locale::classic());
        stream << std::setprecision(std::numeric_limits<float>::max_digits10) << number;
        text = stream.str();
    } else return false;
    return true;
}
bool ReadBool(void* method, void* object, bool& value) {
    void* result = nullptr;
    if (!Invoke(method, object, nullptr, result) || !result) return false;
    void* unboxed = api.unbox(result);
    if (!unboxed) return false;
    value = *static_cast<bool*>(unboxed);
    return true;
}
bool Override(void* object, void* method, const std::wstring& value) {
    void* text = api.newString(value.c_str(), static_cast<int>(value.size()));
    if (!text) return false;
    void* args[] = {text};
    void* result = nullptr;
    if (!Invoke(method, object, args, result) || !result) return false;
    void* unboxed = api.unbox(result);
    return unboxed && *static_cast<bool*>(unboxed);
}
struct Methods { void* value; void* overridden; void* overrideValue; void* reset; void* dirty; };
bool ResolveParameter(void* object, int expectedType, Methods& methods) {
    void* klass = api.objectClass(object);
    if (!klass) return false;
    const char* name = api.className(klass);
    const char* space = api.classNamespace(klass);
    if (!name || !space || std::strncmp(name, "SettingParameter", 16) || std::strcmp(space, "HG.Rendering.Runtime")) return false;
    void* typedValue = Method(klass, "get_paramValue", 0);
    methods = {typedValue, Method(klass, "get_overrided", 0),
        Method(klass, "OverrideWithString", 1), Method(klass, "Reset", 0), Method(klass, "MarkFeatureDirty", 0)};
    return Signature(typedValue, expectedType, false) &&
        Signature(methods.overridden, 0x02, false) && Signature(methods.overrideValue, 0x02, false, 0x0e) &&
        Signature(methods.reset, 0x01, false) && Signature(methods.dirty, 0x01, false);
}
bool Restore(Feature& feature) {
    if (!feature.handle) return true;
    void* object = api.handleTarget(feature.handle);
    Methods methods{};
    void* ignored = nullptr;
    if (!object || !ResolveParameter(object, feature.expectedType, methods)) {
        Status(feature, "reset unavailable; original object retained"); return false;
    }
    const bool restored = feature.originallyOverridden
        ? Override(object, methods.overrideValue, feature.original)
        : Invoke(methods.reset, object, nullptr, ignored);
    if (!restored || !Invoke(methods.dirty, object, nullptr, ignored)) {
        Status(feature, "reset failed; restart restores game state"); return false;
    }
    api.freeHandle(feature.handle);
    feature.handle = 0;
    feature.applied.clear();
    Status(feature, "reset to game control");
    return true;
}
std::wstring Desired(const Feature& feature, const Config& config) {
    int value = -1;
    switch (feature.kind) {
    case Sharpen: case SharpenEnabled: value = config.sharpening; break;
    case Scale: value = config.renderScale; break;
    case Shadow: value = config.shadows; break;
    case AO: value = config.ambientOcclusion; break;
    case TAA: value = config.temporalAA; break;
    }
    if (value < 0) return L"";
    if (feature.kind == SharpenEnabled) return L"True";
    if (feature.kind == AO || feature.kind == TAA) return value ? L"True" : L"False";
    if (feature.kind == Scale || feature.kind == Sharpen) {
        std::wostringstream stream;
        stream.imbue(std::locale::classic());
        stream << std::fixed << std::setprecision(2) << value / 100.0;
        return stream.str();
    }
    return std::to_wstring(value);
}
void Apply(Feature& feature, void* settings, const std::wstring& desired) {
    if (desired.empty()) { Restore(feature); feature.rejected.clear(); return; }
    if (feature.rejected == desired) return;
    if (!settings) { Status(feature, "waiting for render pipeline"); return; }
    void* getter = Method(api.objectClass(settings), (std::string("get_") + feature.name).c_str(), 0);
    // A setting parameter is a managed reference (CLASS or GENERICINST), never a raw struct.
    if (!Signature(getter, 0x12, false) && !Signature(getter, 0x15, false)) {
        Status(feature, "unavailable: parameter getter signature"); return;
    }
    void* object = nullptr;
    if (!Invoke(getter, settings, nullptr, object) || !object) {
        Status(feature, "unavailable: parameter instance"); return;
    }
    if (feature.handle && api.handleTarget(feature.handle) != object && !Restore(feature)) return;
    Methods methods{};
    if (!ResolveParameter(object, feature.expectedType, methods)) {
        Status(feature, "unavailable: typed update/reset API"); return;
    }
    if (!feature.handle) {
        if (!ReadValue(methods.value, object, feature.expectedType, feature.original) ||
            !ReadBool(methods.overridden, object, feature.originallyOverridden)) {
            Status(feature, "unavailable: original value"); return;
        }
        feature.handle = api.newHandle(object, false);
        if (!feature.handle) { Status(feature, "could not retain parameter instance"); return; }
    }
    if (feature.applied == desired) return;
    void* ignored = nullptr;
    if (!Override(object, methods.overrideValue, desired) || !Invoke(methods.dirty, object, nullptr, ignored)) {
        Restore(feature); feature.rejected = desired;
        Status(feature, "update rejected; original restored when possible"); return;
    }
    std::wstring actual;
    if (!ReadValue(methods.value, object, feature.expectedType, actual)) {
        Restore(feature); feature.rejected = desired;
        Status(feature, "readback failed; original restored when possible"); return;
    }
    bool matches = false;
    if (feature.expectedType == 0x02) {
        matches = _wcsicmp(actual.c_str(), desired.c_str()) == 0 ||
            (desired == L"True" && actual == L"1") || (desired == L"False" && actual == L"0");
    } else {
        std::wistringstream readActual(actual), readDesired(desired);
        readActual.imbue(std::locale::classic()); readDesired.imbue(std::locale::classic());
        double actualNumber = 0, desiredNumber = 0;
        matches = (readActual >> actualNumber) && (readDesired >> desiredNumber) &&
            std::isfinite(actualNumber) && std::abs(actualNumber - desiredNumber) < 0.0001;
    }
    if (!matches) {
        Restore(feature); feature.rejected = desired;
        Status(feature, "readback mismatch; original restored when possible"); return;
    }
    feature.applied = desired;
    std::string printable;
    for (wchar_t character : actual)
        printable.push_back(character >= 32 && character <= 126 ? static_cast<char>(character) : '?');
    Status(feature, "applied; readback=" + printable);
}
void Anisotropic(int desired) {
    if (!anisoGetter || !anisoSetter || (desired == -1 && originalAniso == -1)) return;
    void* result = nullptr;
    if (originalAniso < 0) {
        if (!Invoke(anisoGetter, nullptr, nullptr, result) || !result || !api.unbox(result)) return;
        originalAniso = *static_cast<int*>(api.unbox(result));
        if (originalAniso < 0 || originalAniso > 2) { originalAniso = -1; return; }
    }
    const int value = desired < 0 ? originalAniso : desired;
    if (appliedAniso != value || desired == -1) {
        int argument = value;
        void* args[] = {&argument};
        if (!Invoke(anisoSetter, nullptr, args, result)) { Log("anisotropic update failed"); return; }
        if (!Invoke(anisoGetter, nullptr, nullptr, result) || !result || !api.unbox(result) ||
            *static_cast<int*>(api.unbox(result)) != value) { Log("anisotropic readback mismatch"); return; }
        appliedAniso = value;
        Log("anisotropic mode=" + std::to_string(value) + (desired < 0 ? " (restored)" : ""));
    }
    if (desired == -1) { originalAniso = -1; appliedAniso = -1; }
}
void OnFrame() {
    if (!ready.load(std::memory_order_acquire)) return;
    DWORD expectedThread = 0;
    callbackThread.compare_exchange_strong(expectedThread, GetCurrentThreadId());
    if (callbackThread.load() != GetCurrentThreadId()) return;
    if (callbackCount.fetch_add(1) == 0) Log("render-loop callback active on thread " + std::to_string(GetCurrentThreadId()));
    const auto now = GetTickCount64();
    if (now - lastPoll < 1000) return;
    Config config;
    {
        std::unique_lock<std::mutex> lock(configMutex, std::try_to_lock);
        if (!lock.owns_lock()) return;
        config = requested;
    }
    lastPoll = now;
    Anisotropic(config.anisotropic);
    void* pipeline = nullptr;
    void* settings = nullptr;
    const bool needsSettings = config.sharpening >= 0 || config.renderScale >= 0 ||
        config.shadows >= 0 || config.ambientOcclusion >= 0 || config.temporalAA >= 0;
    if (needsSettings && pipelineGetter && Invoke(pipelineGetter, nullptr, nullptr, pipeline) && pipeline) {
        void* klass = api.objectClass(pipeline);
        const char* name = klass ? api.className(klass) : nullptr;
        const char* space = klass ? api.classNamespace(klass) : nullptr;
        if (name && space && !std::strcmp(name, "HGRenderPipeline") && !std::strcmp(space, "HG.Rendering.Runtime")) {
            void* getter = Method(klass, "get_settingParameters", 0);
            if (Signature(getter, 0x12, false)) Invoke(getter, pipeline, nullptr, settings);
        }
    }
    for (auto& feature : features) Apply(feature, settings, Desired(feature, config));
}
void BeforeRenderHook(void* asset, void* context, void* request, const void* method) {
    originalBeforeRender(asset, context, request, method);
    // The engine calls this entry point as part of rendering; workers only publish settings.
    OnFrame();
}
} // namespace

bool Valid(const Config& c) {
    return c.anisotropic >= -1 && c.anisotropic <= 2 && c.sharpening >= -1 && c.sharpening <= 100 &&
        (c.renderScale == -1 || (c.renderScale >= 50 && c.renderScale <= 200)) &&
        (c.shadows == -1 || c.shadows == 512 || c.shadows == 1024 || c.shadows == 2048 || c.shadows == 4096) &&
        c.ambientOcclusion >= -1 && c.ambientOcclusion <= 1 && c.temporalAA >= -1 && c.temporalAA <= 1;
}
void Publish(const Config& config) {
    if (!Valid(config)) return;
    std::lock_guard<std::mutex> lock(configMutex);
    requested = config;
}
void CheckCallback() {
    static bool reported = false;
    if (ready.load() && !reported && !callbackCount.load() && GetTickCount64() - started > 30000) {
        Log("waiting for render-loop callback; no graphics changes applied"); reported = true;
    }
}
bool KnownRuntime(const std::wstring& path) {
    std::ifstream file(std::filesystem::path(path), std::ios::binary);
    if (!file) return false;
    BCRYPT_ALG_HANDLE algorithm = nullptr;
    BCRYPT_HASH_HANDLE hash = nullptr;
    if (BCryptOpenAlgorithmProvider(&algorithm, BCRYPT_SHA256_ALGORITHM, nullptr, 0) < 0) return false;
    bool ok = BCryptCreateHash(algorithm, &hash, nullptr, 0, nullptr, 0, 0) >= 0;
    std::array<char, 65536> buffer{};
    while (ok && file) {
        file.read(buffer.data(), buffer.size());
        if (file.gcount()) ok = BCryptHashData(hash, reinterpret_cast<PUCHAR>(buffer.data()), static_cast<ULONG>(file.gcount()), 0) >= 0;
    }
    std::array<unsigned char, 32> bytes{};
    ok = ok && file.eof() && BCryptFinishHash(hash, bytes.data(), static_cast<ULONG>(bytes.size()), 0) >= 0;
    if (hash) BCryptDestroyHash(hash);
    BCryptCloseAlgorithmProvider(algorithm, 0);
    std::ostringstream hex;
    for (unsigned char value : bytes) hex << std::hex << std::setw(2) << std::setfill('0') << static_cast<int>(value);
    return ok && hex.str() == "db7e920698e3c4a375d85fd42c3ffcc03fa551f611b8ba9a3528b296079d9947";
}
bool Initialize(HMODULE module, bool knownRuntime, Logger logger) {
    logMessage = logger;
    if (!knownRuntime) { Log("unknown game build; graphics disabled, FPS remains independent"); return false; }
#define RESOLVE(field, name) \
    api.field = reinterpret_cast<decltype(api.field)>(GetProcAddress(module, name)); \
    if (!api.field) { Log("missing " name "; graphics disabled"); return false; }
    RESOLVE(domain, "il2cpp_domain_get") RESOLVE(assemblies, "il2cpp_domain_get_assemblies")
    RESOLVE(image, "il2cpp_assembly_get_image") RESOLVE(klass, "il2cpp_class_from_name")
    RESOLVE(method, "il2cpp_class_get_method_from_name") RESOLVE(invoke, "il2cpp_runtime_invoke")
    RESOLVE(unbox, "il2cpp_object_unbox") RESOLVE(objectClass, "il2cpp_object_get_class")
    RESOLVE(parent, "il2cpp_class_get_parent") RESOLVE(className, "il2cpp_class_get_name")
    RESOLVE(classNamespace, "il2cpp_class_get_namespace") RESOLVE(returnType, "il2cpp_method_get_return_type")
    RESOLVE(paramType, "il2cpp_method_get_param") RESOLVE(paramCount, "il2cpp_method_get_param_count")
    RESOLVE(flags, "il2cpp_method_get_flags") RESOLVE(type, "il2cpp_type_get_type")
    RESOLVE(newString, "il2cpp_string_new_utf16") RESOLVE(newHandle, "il2cpp_gchandle_new")
    RESOLVE(handleTarget, "il2cpp_gchandle_get_target") RESOLVE(freeHandle, "il2cpp_gchandle_free")
#undef RESOLVE
    void* frame = Method(Class("UnityEngine.Rendering", "RenderPipelineManager"), "DoRenderLoop_Internal", 3);
    unsigned ignoredFlags = 0;
    // Shipping Unity signature: static void(RenderPipelineAsset, IntPtr, Object).
    // Do not guess the ABI when the game changes this entry point.
    if (!frame || api.paramCount(frame) != 3 || api.type(api.returnType(frame)) != 0x01 ||
        !(api.flags(frame, &ignoredFlags) & 0x10) || api.type(api.paramType(frame, 0)) != 0x12 ||
        api.type(api.paramType(frame, 1)) != 0x18 || api.type(api.paramType(frame, 2)) != 0x12 ||
        !*static_cast<void**>(frame)) {
        if (frame) {
            std::string types;
            for (unsigned index = 0; index < api.paramCount(frame); ++index)
                types += " " + std::to_string(api.type(api.paramType(frame, index)));
            Log("render-loop signature types:" + types);
        }
        Log("render-loop entry point unavailable; graphics disabled"); return false;
    }
    pipelineGetter = Method(Class("UnityEngine.Rendering", "RenderPipelineManager"), "get_currentPipeline", 0);
    if (!Signature(pipelineGetter, 0x12, true)) pipelineGetter = nullptr;
    void* quality = Class("UnityEngine", "QualitySettings");
    anisoGetter = Method(quality, "get_anisotropicFiltering", 0);
    anisoSetter = Method(quality, "set_anisotropicFiltering", 1);
    if (!Signature(anisoGetter, 0x11, true) || !Signature(anisoSetter, 0x01, true, 0x11)) {
        anisoGetter = nullptr; anisoSetter = nullptr; Log("anisotropic API unavailable");
    }
    void* address = *static_cast<void**>(frame);
    MH_STATUS status = MH_CreateHook(address, reinterpret_cast<void*>(&BeforeRenderHook), reinterpret_cast<void**>(&originalBeforeRender));
    if (status != MH_OK) { Log(std::string("callback hook rejected: ") + MH_StatusToString(status)); return false; }
    started = GetTickCount64();
    ready.store(true, std::memory_order_release);
    status = MH_EnableHook(address);
    if (status != MH_OK) {
        ready = false; MH_RemoveHook(address);
        Log(std::string("callback hook enable failed: ") + MH_StatusToString(status)); return false;
    }
    Log("callback installed; controls default to game settings");
    return true;
}
} // namespace Graphics
