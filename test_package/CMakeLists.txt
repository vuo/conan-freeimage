cmake_minimum_required(VERSION 3.0.0)
project(PackageTest CXX)

include(${CMAKE_BINARY_DIR}/conanbuildinfo.cmake)
conan_basic_setup(KEEP_RPATHS)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_COMPILER ${CONAN_BIN_DIRS_LLVM}/clang++)
set(CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS} -stdlib=libc++")
set(CMAKE_OSX_DEPLOYMENT_TARGET 10.12)
set(CMAKE_OSX_SYSROOT ${CONAN_MACOS-SDK_ROOT})

add_executable(test_package test_package.cc)
target_link_libraries(test_package ${CONAN_LIBS})
