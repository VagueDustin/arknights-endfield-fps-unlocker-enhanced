// SPDX-License-Identifier: GPL-3.0-only
// Isolated diagnostic process. Never injects into or starts Endfield.
#include <windows.h>
#include <cstdio>
#include <vulkan/vulkan.h>
int CheckVulkan() {
    HMODULE loader=LoadLibraryW(L"vulkan-1.dll");
    if (!loader) return 10;
    auto get=reinterpret_cast<PFN_vkGetInstanceProcAddr>(GetProcAddress(loader,"vkGetInstanceProcAddr"));
    if (!get) return 11;
    auto create=reinterpret_cast<PFN_vkCreateInstance>(get(nullptr,"vkCreateInstance"));
    VkApplicationInfo app{VK_STRUCTURE_TYPE_APPLICATION_INFO};app.pApplicationName="Fate loader diagnostic";app.apiVersion=VK_API_VERSION_1_2;
    VkInstanceCreateInfo info{VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO};info.pApplicationInfo=&app;
    VkInstance instance=nullptr;VkResult result=create(&info,nullptr,&instance);
    printf("vkCreateInstance=%d\n",result);fflush(stdout);
    if(result!=VK_SUCCESS)return 12;
    auto enumerate=reinterpret_cast<PFN_vkEnumeratePhysicalDevices>(get(instance,"vkEnumeratePhysicalDevices"));
    auto queues=reinterpret_cast<PFN_vkGetPhysicalDeviceQueueFamilyProperties>(get(instance,"vkGetPhysicalDeviceQueueFamilyProperties"));
    auto deviceCreate=reinterpret_cast<PFN_vkCreateDevice>(get(instance,"vkCreateDevice"));
    auto destroyInstance=reinterpret_cast<PFN_vkDestroyInstance>(get(instance,"vkDestroyInstance"));
    uint32_t count=8;VkPhysicalDevice devices[8]{};result=enumerate(instance,&count,devices);
    if(result!=VK_SUCCESS || !count)return 13;
    uint32_t queueCount=32;VkQueueFamilyProperties families[32]{};queues(devices[0],&queueCount,families);
    uint32_t index=0;while(index<queueCount && !(families[index].queueFlags&VK_QUEUE_GRAPHICS_BIT))++index;
    if(index==queueCount)return 14;
    float priority=1;VkDeviceQueueCreateInfo qi{VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO};qi.queueFamilyIndex=index;qi.queueCount=1;qi.pQueuePriorities=&priority;
    VkDeviceCreateInfo di{VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO};di.queueCreateInfoCount=1;di.pQueueCreateInfos=&qi;
    VkDevice device=nullptr;result=deviceCreate(devices[0],&di,nullptr,&device);
    printf("vkCreateDevice=%d\n",result);fflush(stdout);
    if(result==VK_SUCCESS){
        auto destroy=reinterpret_cast<PFN_vkDestroyDevice>(get(instance,"vkDestroyDevice"));destroy(device,nullptr);
    }
    destroyInstance(instance,nullptr);
    return result==VK_SUCCESS?0:15;
}
int main(int argc, char**) {
    SetErrorMode(SEM_FAILCRITICALERRORS | SEM_NOGPFAULTERRORBOX | SEM_NOOPENFILEERRORBOX);
    printf("probe pid=%lu: loading local winmm.dll\n", GetCurrentProcessId()); fflush(stdout);
    HMODULE module = LoadLibraryExW(L".\\winmm.dll", nullptr, LOAD_WITH_ALTERED_SEARCH_PATH);
    if (!module) { printf("LoadLibrary failed: %lu\n", GetLastError()); return 2; }
    printf("LoadLibrary succeeded\n"); fflush(stdout);
    using Timer = DWORD(WINAPI*)();
    auto timer = reinterpret_cast<Timer>(GetProcAddress(module, "timeGetTime"));
    if (!timer) { printf("timeGetTime missing: %lu\n", GetLastError()); return 3; }
    DWORD first=timer(); Sleep(100); DWORD second=timer();
    printf("Forwarded timer delta=%lu ms\n", second-first); fflush(stdout);
    if (second-first < 50 || second-first > 5000) return 4;
    if(argc>1){int result=CheckVulkan();if(result)return result;}
    Sleep(3000);
    printf("Initialization and forwarding passed; exiting process\n"); fflush(stdout);
    return 0;
}
