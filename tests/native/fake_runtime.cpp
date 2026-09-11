#include <windows.h>
#include <cstring>

#define EXPORT extern "C" __declspec(dllexport)
static volatile LONG fps = 60;
static volatile LONG vsync = 1;
static volatile LONG badThread = 0;
static thread_local bool attached = false;

EXPORT __declspec(noinline) void SetFps(int value, const void*) {
    InterlockedExchange(&fps, value);
}
EXPORT __declspec(noinline) void SetVsync(int value, const void*) {
    InterlockedExchange(&vsync, value);
}
EXPORT int ReadFps() { return static_cast<int>(fps); }
EXPORT int ReadVsync() { return static_cast<int>(vsync); }
EXPORT int BadThread() { return static_cast<int>(badThread); }

struct Method { void* address; int kind; };
static Method fpsMethod{reinterpret_cast<void*>(&SetFps), 1};
static Method vsyncMethod{reinterpret_cast<void*>(&SetVsync), 2};
static Method vsyncGetter{nullptr, 3};
static int token;
EXPORT void* il2cpp_domain_get() { return &token; }
EXPORT void* il2cpp_thread_attach(void*) { attached = true; return &token; }
EXPORT void il2cpp_thread_detach(void*) { attached = false; }
EXPORT void** il2cpp_domain_get_assemblies(void*, size_t* count) {
    static void* assemblies[] = {&token}; *count = 1; return assemblies;
}
EXPORT void* il2cpp_assembly_get_image(void* assembly) { return assembly; }
EXPORT void* il2cpp_class_from_name(void*, const char*, const char*) { return &token; }
EXPORT void* il2cpp_class_get_method_from_name(void*, const char* name, int) {
    if (!std::strcmp(name, "set_targetFrameRate")) return &fpsMethod;
    if (!std::strcmp(name, "set_vSyncCount")) return &vsyncMethod;
    if (!std::strcmp(name, "get_vSyncCount")) return &vsyncGetter;
    return nullptr;
}
EXPORT void* il2cpp_runtime_invoke(void* raw, void*, void** arguments, void** exception) {
    if (!attached) { InterlockedExchange(&badThread, 1); *exception = &token; return nullptr; }
    *exception = nullptr;
    auto* method = static_cast<Method*>(raw);
    if (method->kind == 3) {
        static thread_local int boxed;
        boxed = static_cast<int>(vsync);
        return &boxed;
    }
    auto setter = reinterpret_cast<void (*)(int, const void*)>(method->address);
    setter(*static_cast<int*>(arguments[0]), method);
    return nullptr;
}
EXPORT void* il2cpp_object_unbox(void* object) { return object; }
