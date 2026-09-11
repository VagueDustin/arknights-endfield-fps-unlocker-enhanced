#include <windows.h>
#include <cstring>
#include <map>
#include <memory>
#include <string>
#include <vector>

#define EXPORT extern "C" __declspec(dllexport)
static volatile LONG fps = 60, vsync = 1, aniso = 1, badThread = 0, frames = 0;
static thread_local bool attached = false;
static DWORD graphicsThread = 0;
static std::string rejected, wrongType;
static bool badCallback = false;
EXPORT __declspec(noinline) void SetFps(int value, const void*) { InterlockedExchange(&fps, value); }
EXPORT __declspec(noinline) void SetVsync(int value, const void*) { InterlockedExchange(&vsync, value); }
EXPORT __declspec(noinline) void BeforeRender(void*, void*, void*, const void*) { InterlockedIncrement(&frames); }
EXPORT void FireFrame() { BeforeRender(nullptr, nullptr, nullptr, nullptr); }
EXPORT int ReadFps() { return static_cast<int>(fps); }
EXPORT int ReadVsync() { return static_cast<int>(vsync); }
EXPORT int ReadAniso() { return static_cast<int>(aniso); }
EXPORT int BadThread() { return static_cast<int>(badThread); }
EXPORT void SetGraphicsThread() { graphicsThread = GetCurrentThreadId(); attached = true; }
EXPORT void RejectSetting(const char* name) { rejected = name; }
EXPORT void WrongType(const char* name) { wrongType = name; }
EXPORT void BadCallbackSignature() { badCallback = true; }

struct Class { const char* name; const char* space; };
static Class app{"Application", "UnityEngine"}, quality{"QualitySettings", "UnityEngine"},
    manager{"RenderPipelineManager", "UnityEngine.Rendering"}, pipeline{"HGRenderPipeline", "HG.Rendering.Runtime"},
    settings{"HGSettingParameters", "HG.Rendering.Runtime"}, floatParam{"SettingParameter`1", "HG.Rendering.Runtime"},
    intParam{"SettingParameter`1", "HG.Rendering.Runtime"}, boolParam{"SettingParameter`1", "HG.Rendering.Runtime"};
struct Parameter { Class* klass; double value; double original; bool overridden; std::string name; };
static std::map<std::string, Parameter> parameters;
static std::vector<std::unique_ptr<std::wstring>> strings;
static std::map<unsigned, void*> handles;
static unsigned nextHandle = 1;

static Parameter& ParameterFor(const std::string& name) {
    auto found = parameters.find(name);
    if (found != parameters.end()) return found->second;
    Class* klass = &floatParam;
    double value = 0.35;
    if (name == "renderingScale") value = 1.0;
    if (name.find("Resolution") != std::string::npos || name == "punctualLightTileMaxSize") { klass = &intParam; value = 1024; }
    if (name == "sharpenEnabled" || name == "gtaoEnable" || name == "taauEnable") { klass = &boolParam; value = 1; }
    if (name == "dlssSharpenStrength") value = 0.6;
    return parameters.emplace(name, Parameter{klass, value, value, name == "dlssSharpenStrength", name}).first->second;
}
EXPORT double ReadSetting(const char* name) { return ParameterFor(name).value; }
EXPORT bool IsOverridden(const char* name) { return ParameterFor(name).overridden; }
EXPORT unsigned HandleCount() { return static_cast<unsigned>(handles.size()); }
struct Method { void* address; int kind; int returnType; int parameterType; bool isStatic; std::string name; };
static Method fpsMethod{reinterpret_cast<void*>(&SetFps), 1, 1, 8, true, ""},
    vsyncMethod{reinterpret_cast<void*>(&SetVsync), 2, 1, 8, true, ""},
    vsyncGetter{nullptr, 3, 8, -1, true, ""},
    frame{reinterpret_cast<void*>(&BeforeRender), 4, 1, -1, true, ""},
    anisoGetter{nullptr, 5, 0x11, -1, true, ""}, anisoSetter{nullptr, 6, 1, 0x11, true, ""},
    pipelineGetter{nullptr, 7, 0x12, -1, true, ""}, settingsGetter{nullptr, 8, 0x12, -1, false, ""},
    typedFloat{nullptr, 10, 0x0c, -1, false, ""}, typedInt{nullptr, 10, 8, -1, false, ""}, typedBool{nullptr, 10, 2, -1, false, ""},
    valueGetter{nullptr, 11, 0x0e, -1, false, ""}, overriddenGetter{nullptr, 12, 2, -1, false, ""},
    overrideMethod{nullptr, 13, 2, 0x0e, false, ""}, resetMethod{nullptr, 14, 1, -1, false, ""},
    dirtyMethod{nullptr, 15, 1, -1, false, ""};
static std::map<std::string, Method> getters;
static int token;
EXPORT void* il2cpp_domain_get() { return &token; }
EXPORT void* il2cpp_thread_attach(void*) { attached = true; return &token; }
EXPORT void il2cpp_thread_detach(void*) { attached = false; }
EXPORT void** il2cpp_domain_get_assemblies(void*, size_t* count) {
    static void* assemblies[] = {&token}; *count = 1; return assemblies;
}
EXPORT void* il2cpp_assembly_get_image(void* assembly) { return assembly; }
EXPORT void* il2cpp_class_from_name(void*, const char* space, const char* name) {
    for (Class* klass : {&app, &quality, &manager})
        if (!std::strcmp(klass->name, name) && !std::strcmp(klass->space, space)) return klass;
    return nullptr;
}
EXPORT void* il2cpp_class_get_method_from_name(void* raw, const char* name, int) {
    auto* klass = static_cast<Class*>(raw);
    if (klass == &app) {
        if (!std::strcmp(name, "set_targetFrameRate")) return &fpsMethod;
        if (!std::strcmp(name, "InvokeOnBeforeRender")) { frame.returnType = badCallback ? 2 : 1; return &frame; }
    }
    if (klass == &quality) {
        if (!std::strcmp(name, "set_vSyncCount")) return &vsyncMethod;
        if (!std::strcmp(name, "get_vSyncCount")) return &vsyncGetter;
        if (!std::strcmp(name, "get_anisotropicFiltering")) return &anisoGetter;
        if (!std::strcmp(name, "set_anisotropicFiltering")) return &anisoSetter;
    }
    if (klass == &manager && !std::strcmp(name, "DoRenderLoop_Internal")) { frame.returnType = badCallback ? 2 : 1; return &frame; }
    if (klass == &manager && !std::strcmp(name, "get_currentPipeline")) return &pipelineGetter;
    if (klass == &pipeline && !std::strcmp(name, "get_settingParameters")) return &settingsGetter;
    if (klass == &settings && !std::strncmp(name, "get_", 4)) {
        const std::string key(name + 4);
        return &getters.emplace(key, Method{nullptr, 9, 0x15, -1, false, key}).first->second;
    }
    if (klass == &floatParam || klass == &intParam || klass == &boolParam) {
        if (!std::strcmp(name, "get_paramValue")) return klass == &floatParam ? &typedFloat : klass == &intParam ? &typedInt : &typedBool;
        if (!std::strcmp(name, "get_valueString")) return &valueGetter;
        if (!std::strcmp(name, "get_overrided")) return &overriddenGetter;
        if (!std::strcmp(name, "OverrideWithString")) return &overrideMethod;
        if (!std::strcmp(name, "Reset")) return &resetMethod;
        if (!std::strcmp(name, "MarkFeatureDirty")) return &dirtyMethod;
    }
    return nullptr;
}
EXPORT void* il2cpp_string_new_utf16(const wchar_t* value, int length) {
    strings.push_back(std::make_unique<std::wstring>(value, length)); return strings.back().get();
}
EXPORT void* il2cpp_runtime_invoke(void* raw, void* object, void** arguments, void** exception) {
    auto* method = static_cast<Method*>(raw);
    if (!attached || (method->kind >= 5 && GetCurrentThreadId() != graphicsThread)) {
        InterlockedExchange(&badThread, 1); *exception = &token; return nullptr;
    }
    *exception = nullptr;
    static thread_local int boxedInt;
    static thread_local bool boxedBool;
    static thread_local float boxedFloat;
    if (method->kind == 3 || method->kind == 5) { boxedInt = method->kind == 3 ? vsync : aniso; return &boxedInt; }
    if (method->kind == 6) { aniso = *static_cast<int*>(arguments[0]); return nullptr; }
    if (method->kind == 7) return &pipeline;
    if (method->kind == 8) return &settings;
    if (method->kind == 9) return &ParameterFor(method->name);
    if (method->kind >= 10) {
        auto* parameter = static_cast<Parameter*>(object);
        if (method->kind == 10) {
            if (parameter->klass == &boolParam) { boxedBool = parameter->value != 0; return &boxedBool; }
            if (parameter->klass == &intParam) { boxedInt = static_cast<int>(parameter->value); return &boxedInt; }
            boxedFloat = static_cast<float>(parameter->value); return &boxedFloat;
        }
        if (method->kind == 11) {
            std::wstring text = parameter->klass == &boolParam ? (parameter->value ? L"True" : L"False") : std::to_wstring(parameter->value);
            return il2cpp_string_new_utf16(text.c_str(), static_cast<int>(text.size()));
        }
        if (method->kind == 12) { boxedBool = parameter->overridden; return &boxedBool; }
        if (method->kind == 13) {
            boxedBool = parameter->name != rejected;
            if (boxedBool) {
                const auto& text = *static_cast<std::wstring*>(arguments[0]);
                parameter->value = text == L"True" ? 1 : text == L"False" ? 0 : std::stod(text);
                parameter->overridden = true;
            }
            return &boxedBool;
        }
        if (method->kind == 14) { parameter->value = parameter->original; parameter->overridden = false; }
        return nullptr;
    }
    auto setter = reinterpret_cast<void (*)(int, const void*)>(method->address);
    setter(*static_cast<int*>(arguments[0]), method); return nullptr;
}
EXPORT void* il2cpp_object_unbox(void* object) { return object; }
EXPORT void* il2cpp_object_get_class(void* object) {
    if (object == &pipeline || object == &settings) return object;
    auto* parameter = static_cast<Parameter*>(object);
    return parameter->name == wrongType ? &boolParam : parameter->klass;
}
EXPORT void* il2cpp_class_get_parent(void*) { return nullptr; }
EXPORT const char* il2cpp_class_get_name(void* klass) { return static_cast<Class*>(klass)->name; }
EXPORT const char* il2cpp_class_get_namespace(void* klass) { return static_cast<Class*>(klass)->space; }
EXPORT const void* il2cpp_method_get_return_type(void* method) { return &static_cast<Method*>(method)->returnType; }
EXPORT const void* il2cpp_method_get_param(void* method, unsigned index) { static int types[] = {0x12, 0x18, 0x1c}; if (method == &frame) return &types[index]; return &static_cast<Method*>(method)->parameterType; }
EXPORT unsigned il2cpp_method_get_param_count(void* method) { if (method == &frame) return 3; return static_cast<Method*>(method)->parameterType < 0 ? 0 : 1; }
EXPORT unsigned il2cpp_method_get_flags(void* method, unsigned* ignored) { *ignored = 0; return static_cast<Method*>(method)->isStatic ? 0x10 : 0; }
EXPORT int il2cpp_type_get_type(const void* type) { return *static_cast<const int*>(type); }
EXPORT const wchar_t* il2cpp_string_chars(void* text) { return static_cast<std::wstring*>(text)->c_str(); }
EXPORT int il2cpp_string_length(void* text) { return static_cast<int>(static_cast<std::wstring*>(text)->size()); }
EXPORT unsigned il2cpp_gchandle_new(void* object, bool) { const auto handle = nextHandle++; handles[handle] = object; return handle; }
EXPORT void* il2cpp_gchandle_get_target(unsigned handle) { return handles.at(handle); }
EXPORT void il2cpp_gchandle_free(unsigned handle) { handles.erase(handle); }
