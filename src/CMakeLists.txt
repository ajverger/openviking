cmake_minimum_required(VERSION 3.12)

project(openviking_cpp)

include(CheckCXXCompilerFlag)

set(OV_ENGINE_VARIANTS "native" CACHE STRING "Engine variants to build: native;sse3;avx2;avx512")
set(OV_ENGINE_OUTPUT_DIR "" CACHE PATH "Directory for generated Python engine modules")
set(OV_PY_OUTPUT_SUFFIX ".so" CACHE STRING "Python extension suffix")

set(OV_PLATFORM_X86 OFF)
if(CMAKE_SYSTEM_PROCESSOR MATCHES "x86_64|amd64|AMD64|i[3-6]86")
    set(OV_PLATFORM_X86 ON)
endif()

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

if(APPLE)
    set(CMAKE_OSX_DEPLOYMENT_TARGET "10.15" CACHE STRING "Minimum macOS deployment version")
endif()

set(THREADS_PREFER_PTHREAD_FLAG ON)
set(CMAKE_STRIP FALSE)

add_compile_definitions(HAVE_CXX17_HAS_INCLUDE=1)
if(WIN32)
    add_compile_definitions(NOMINMAX)
endif()

set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wno-error -Wno-deprecated-declarations -Wno-format -Wno-inconsistent-missing-override")
set(CMAKE_CXX_LINK_EXECUTABLE "${CMAKE_CXX_LINK_EXECUTABLE} -lpthread")

set(Python3_ARCH_INCLUDE_DIR "/usr/include/${CMAKE_SYSTEM_PROCESSOR}-linux-gnu/")

find_package(Python3 COMPONENTS Interpreter Development REQUIRED)

if(UNIX AND NOT APPLE)
    set(Python3_LIBRARIES "")
endif()

find_package(pybind11 REQUIRED)
find_package(Threads REQUIRED)

set(BUILD_SHARED_LIBS OFF CACHE BOOL "" FORCE)
set(SPDLOG_BUILD_SHARED OFF CACHE BOOL "" FORCE)
set(LEVELDB_BUILD_TESTS OFF CACHE BOOL "" FORCE)
set(LEVELDB_BUILD_BENCHMARKS OFF CACHE BOOL "" FORCE)
set(LEVELDB_INSTALL OFF CACHE BOOL "" FORCE)
set(SPDLOG_BUILD_TESTS OFF CACHE BOOL "" FORCE)
set(SPDLOG_BUILD_EXAMPLE OFF CACHE BOOL "" FORCE)

add_subdirectory(../third_party/leveldb-1.23 ${CMAKE_BINARY_DIR}/leveldb_build)
if(TARGET leveldb)
    target_compile_options(leveldb PRIVATE -fPIC)
endif()

add_subdirectory(../third_party/spdlog-1.14.1 ${CMAKE_BINARY_DIR}/spdlog_build)

set(OV_PLATFORM_ARM OFF)
if(CMAKE_SYSTEM_PROCESSOR MATCHES "aarch64|ARM64|arm64")
    set(OV_PLATFORM_ARM ON)
    message(STATUS "Building for ARM platform with KRL support")
    add_subdirectory(../third_party/krl ${CMAKE_BINARY_DIR}/krl_build)
endif()

include_directories(.)
include_directories(../third_party/)
include_directories(../third_party/leveldb-1.23/include/)
include_directories(../third_party/spdlog-1.14.1/include/)

if(OV_PLATFORM_ARM)
    include_directories(../third_party/krl/include/)
endif()

if(NOT DEFINED Python3_INCLUDE_DIRS)
    set(Python3_INCLUDE_DIRS
        ${Python3_ARCH_INCLUDE_DIR}
        "/usr/include/../include/"
    )
endif()

file(GLOB_RECURSE ENGINE_INDEX_SOURCES
    "index/*.cpp"
)
file(GLOB_RECURSE ENGINE_X86_ONLY_SOURCES
    "index/detail/vector/common/x86/*.cpp"
)
if(NOT OV_PLATFORM_X86)
    list(REMOVE_ITEM ENGINE_INDEX_SOURCES ${ENGINE_X86_ONLY_SOURCES})
endif()

file(GLOB_RECURSE ENGINE_BASE_SOURCES
    "store/*.cpp"
    "common/*.cpp"
)

add_library(engine_base STATIC ${ENGINE_BASE_SOURCES})
target_link_libraries(engine_base PRIVATE Threads::Threads leveldb)
target_compile_options(engine_base PRIVATE -fPIC)

if(OV_PLATFORM_ARM)
    target_link_libraries(engine_base PRIVATE krl)
endif()

function(ov_link_filesystem_lib target_name)
    if(CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
        if(CMAKE_CXX_COMPILER_VERSION VERSION_LESS "9.0")
            target_link_libraries(${target_name} PRIVATE stdc++fs)
        endif()
    elseif(CMAKE_CXX_COMPILER_ID STREQUAL "Clang")
        if(CMAKE_CXX_COMPILER_VERSION VERSION_LESS "10.0")
            target_link_libraries(${target_name} PRIVATE c++fs)
        endif()
    elseif(CMAKE_CXX_COMPILER_ID STREQUAL "AppleClang")
        if(CMAKE_CXX_COMPILER_VERSION VERSION_LESS "11.0")
            target_link_libraries(${target_name} PRIVATE c++fs)
        endif()
    endif()
endfunction()

ov_link_filesystem_lib(engine_base)

function(ov_get_output_name target_name default_name out_var)
    string(TOUPPER "${target_name}" target_name_upper)
    set(var_name "OV_OUTPUT_NAME_${target_name_upper}")
    if(DEFINED ${var_name} AND NOT "${${var_name}}" STREQUAL "")
        set(${out_var} "${${var_name}}" PARENT_SCOPE)
    else()
        set(${out_var} "${default_name}" PARENT_SCOPE)
    endif()
endfunction()

function(ov_collect_variant_flags variant_name out_supported out_flags out_defs)
    set(supported ON)
    set(flags "")
    set(defs "")

    if(OV_PLATFORM_X86)
        if("${variant_name}" STREQUAL "sse3")
            check_cxx_compiler_flag("-msse3" HAVE_OV_SSE3)
            if(HAVE_OV_SSE3)
                list(APPEND flags -msse3)
                list(APPEND defs OV_DISABLE_AVX512=1 CROARING_COMPILER_SUPPORTS_AVX512=0)
            else()
                set(supported OFF)
            endif()
        elseif("${variant_name}" STREQUAL "avx2")
            check_cxx_compiler_flag("-mavx2" HAVE_OV_AVX2)
            if(HAVE_OV_AVX2)
                list(APPEND flags -mavx2)
                list(APPEND defs OV_DISABLE_AVX512=1 CROARING_COMPILER_SUPPORTS_AVX512=0)
                foreach(flag -mno-avx512f -mno-avx512bw -mno-avx512dq -mno-avx512vl)
                    string(REPLACE "-" "_" flag_var_suffix "${flag}")
                    set(flag_var "HAVE_OV${flag_var_suffix}")
                    check_cxx_compiler_flag("${flag}" ${flag_var})
                    if(${flag_var})
                        list(APPEND flags ${flag})
                    endif()
                endforeach()
            else()
                set(supported OFF)
            endif()
        elseif("${variant_name}" STREQUAL "avx512")
            foreach(flag -mavx512f -mavx512bw -mavx512dq -mavx512vl)
                string(REPLACE "-" "_" flag_var_suffix "${flag}")
                set(flag_var "HAVE_OV${flag_var_suffix}")
                check_cxx_compiler_flag("${flag}" ${flag_var})
                if(${flag_var})
                    list(APPEND flags ${flag})
                else()
                    set(supported OFF)
                endif()
            endforeach()
        elseif("${variant_name}" STREQUAL "native")
            check_cxx_compiler_flag("-march=native" HAVE_OV_MARCH_NATIVE)
            if(HAVE_OV_MARCH_NATIVE)
                list(APPEND flags -march=native)
            endif()
        endif()
    endif()

    set(${out_supported} "${supported}" PARENT_SCOPE)
    set(${out_flags} "${flags}" PARENT_SCOPE)
    set(${out_defs} "${defs}" PARENT_SCOPE)
endfunction()

function(ov_add_engine_variant variant_name)
    set(target_name "engine_${variant_name}")
    set(module_symbol "_engine_${variant_name}")
    set(default_output_name "${module_symbol}")

    ov_collect_variant_flags("${variant_name}" variant_supported variant_flags variant_defs)
    if(NOT variant_supported)
        message(WARNING "Skipping engine variant ${variant_name}: compiler does not support its required flags")
        return()
    endif()

    add_library(engine_index_${variant_name} STATIC ${ENGINE_INDEX_SOURCES})
    target_compile_options(engine_index_${variant_name} PRIVATE -fPIC ${variant_flags})
    if(variant_defs)
        target_compile_definitions(engine_index_${variant_name} PRIVATE ${variant_defs})
    endif()
    ov_link_filesystem_lib(engine_index_${variant_name})

    pybind11_add_module(${target_name} MODULE pybind11_interface.cpp)
    target_include_directories(${target_name} PRIVATE ${Python3_INCLUDE_DIRS})
    target_compile_definitions(${target_name} PRIVATE OV_PY_MODULE_NAME=${module_symbol})
    target_link_libraries(${target_name} PRIVATE
        engine_base
        engine_index_${variant_name}
        Threads::Threads
    )

    if(MINGW)
        target_link_libraries(${target_name} PRIVATE
            -static-libgcc
            -static-libstdc++
            -Wl,-Bstatic
            -lstdc++
            -lpthread
            -Wl,-Bdynamic
        )
    endif()

    ov_get_output_name("${target_name}" "${default_output_name}" output_name)
    set_target_properties(
        ${target_name}
        PROPERTIES
        LIBRARY_OUTPUT_DIRECTORY "${OV_ENGINE_OUTPUT_DIR}"
        RUNTIME_OUTPUT_DIRECTORY "${OV_ENGINE_OUTPUT_DIR}"
        SUFFIX "${OV_PY_OUTPUT_SUFFIX}"
        PYBIND11_MODULE_NAME "${module_symbol}"
        OUTPUT_NAME "${output_name}"
    )
    set_property(GLOBAL APPEND PROPERTY OV_BUILT_ENGINE_TARGETS ${target_name})
endfunction()

foreach(variant_name IN LISTS OV_ENGINE_VARIANTS)
    ov_add_engine_variant("${variant_name}")
endforeach()

get_property(ov_built_engine_targets GLOBAL PROPERTY OV_BUILT_ENGINE_TARGETS)
if(NOT ov_built_engine_targets)
    set(ov_built_engine_targets "")
endif()
list(JOIN ov_built_engine_targets "\n" ov_built_engine_targets_text)
file(WRITE "${CMAKE_BINARY_DIR}/engine_targets.txt" "${ov_built_engine_targets_text}\n")
