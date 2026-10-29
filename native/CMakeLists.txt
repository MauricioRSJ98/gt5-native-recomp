cmake_minimum_required(VERSION 3.20)
project(gt5_native LANGUAGES C CXX)
set(PS3RECOMP_BUILD_TESTS OFF CACHE BOOL "" FORCE)
set(PS3RECOMP_RSX_D3D12 OFF CACHE BOOL "" FORCE)
add_subdirectory(../third_party/ps3recomp-master ps3recomp)
# Preserve compiled SPU dispatch, remove the instruction interpreter entirely.
get_target_property(runtime_sources ps3recomp_runtime SOURCES)
list(FILTER runtime_sources EXCLUDE REGEX "spu_interp\\.c$")
set_property(TARGET ps3recomp_runtime PROPERTY SOURCES "${runtime_sources}")
target_sources(ps3recomp_runtime PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/spu_aot_dispatch.c")
target_include_directories(ps3recomp_runtime PRIVATE ../third_party/ps3recomp-master/runtime/spu)
if(MINGW)
    target_include_directories(ps3recomp_runtime PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}")
    target_compile_options(ps3recomp_runtime PRIVATE -include mingw_time_compat.h)
endif()
set(toolkit "${CMAKE_CURRENT_SOURCE_DIR}/../third_party/ps3recomp-master")
set_source_files_properties(${toolkit}/libs/video/rsx_live_draw.c DIRECTORY "${toolkit}" PROPERTIES COMPILE_DEFINITIONS PS3RECOMP_NO_D3D12)
option(GT5_VULKAN "Use the Windows port of the Vulkan RSX backend" ON)
if(GT5_VULKAN)
    set(sdl "${CMAKE_CURRENT_SOURCE_DIR}/../tools/SDL2-2.32.10/x86_64-w64-mingw32")
    set(vkheaders "${CMAKE_CURRENT_SOURCE_DIR}/../third_party/Vulkan-Headers-vulkan-sdk-1.4.363.0/include")
    target_sources(ps3recomp_runtime PRIVATE
        ${toolkit}/libs/video/rsx_vulkan_backend.c)
    target_include_directories(ps3recomp_runtime PRIVATE ${vkheaders} ${sdl}/include)
    set_source_files_properties(${toolkit}/libs/video/rsx_vulkan_backend.c DIRECTORY "${toolkit}"
        PROPERTIES COMPILE_DEFINITIONS PS3RECOMP_VULKAN_WINDOWS)
    target_link_libraries(ps3recomp_runtime PRIVATE "${sdl}/lib/libSDL2.dll.a")
    set(GLSLANG_TESTS OFF CACHE BOOL "" FORCE)
    set(GLSLANG_ENABLE_INSTALL OFF CACHE BOOL "" FORCE)
    set(ENABLE_GLSLANG_BINARIES OFF CACHE BOOL "" FORCE)
    set(ENABLE_OPT ON CACHE BOOL "" FORCE)
    set(SPIRV_SKIP_TESTS ON CACHE BOOL "" FORCE)
    set(SPIRV_SKIP_EXECUTABLES ON CACHE BOOL "" FORCE)
    add_subdirectory(../third_party/glslang-16.6.0 glslang EXCLUDE_FROM_ALL)
    add_library(gt5_spirv STATIC ${toolkit}/libs/video/rsx_shader_spirv.cpp)
    target_compile_features(gt5_spirv PRIVATE cxx_std_20)
    target_compile_definitions(gt5_spirv PRIVATE PS3RECOMP_HAVE_SPIRV_TRANSLATION=1)
    target_include_directories(gt5_spirv PRIVATE ${toolkit}/include)
    target_link_libraries(gt5_spirv PRIVATE glslang::glslang glslang::SPIRV glslang::glslang-default-resource-limits)
endif()
if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/../private/native-sources.cmake")
    include(../private/native-sources.cmake)
    add_executable(gt5-native main.cpp disc_fs.cpp ${GT5_NATIVE_OBJECTS}
        ../private/native-boot-probe/unlifted_targets.cpp
        ../private/native-batch-registry.cpp
        ../private/ppu_hle_nids.cpp
        ${toolkit}/runtime/ppu/ppu_loader.cpp
        ${toolkit}/runtime/ppu/ppu_hle.cpp
        ${toolkit}/runtime/ppu/ppu_sysprx.cpp
        ${toolkit}/runtime/ppu/ppu_fs.cpp)
    target_include_directories(gt5-native PRIVATE
        ../private
        ../private/ppu-aot-256-r2
        ../third_party/GT5P-main/src
        ${toolkit}/include ${toolkit}/runtime/ppu
        ${toolkit}/runtime/memory ${toolkit}/runtime/syscalls)
    if(GT5_VULKAN)
        target_sources(gt5-native PRIVATE present.cpp)
        target_compile_definitions(gt5-native PRIVATE GT5_VULKAN)
        target_include_directories(gt5-native PRIVATE ${toolkit}/libs/video)
        add_custom_command(TARGET gt5-native POST_BUILD COMMAND ${CMAKE_COMMAND} -E copy_if_different
            "${sdl}/bin/SDL2.dll" "$<TARGET_FILE_DIR:gt5-native>/SDL2.dll")
    endif()
    target_compile_features(gt5-native PRIVATE cxx_std_20)
    target_compile_definitions(gt5-native PRIVATE GT5_AOT_STRICT)
    target_compile_options(gt5-native PRIVATE -msse4.1)
    target_link_libraries(gt5-native PRIVATE ps3recomp_runtime ws2_32 xinput ole32 bcrypt dbghelp)
    if(GT5_VULKAN)
        target_link_libraries(gt5-native PRIVATE gt5_spirv)
    endif()
    target_link_options(gt5-native PRIVATE -static-libgcc -static-libstdc++ -Wl,--stack,268435456)
endif()
