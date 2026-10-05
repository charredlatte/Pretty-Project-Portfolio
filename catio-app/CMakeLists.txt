# The KittyChat Café as a native app. See docs/mobile-app.md.
#
# Two builds:
#
#   cmake -S catio-app -B build && cmake --build build
#       The DEFAULT, and it needs nothing installed: one translation unit per public header, each
#       including only that header, which proves every header is self-contained C++20. The public
#       headers name no SDL, curl or JSON type, which is what makes this possible.
#
#   cmake -S catio-app -B build -DCATIO_HEADERS_ONLY=OFF && cmake --build build
#       The app: catio_app (a window, the loop, the interface), catio_look, which renders a floor to a
#       PNG with no window and no GPU, and catio_tests. SDL3, SDL3_ttf and nlohmann/json are fetched
#       and built from source (about a minute). Add -DCATIO_HEADLESS=ON where there is no windowing
#       system at all (CI, a cloud session): catio_app then only draws frames to PNGs (--shot).
#
# The network layer is still to come (cmake/sources.cmake lists it). This builds what exists.

cmake_minimum_required(VERSION 3.24)
project(catio_app LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

option(CATIO_HEADERS_ONLY "Compile each header alone, needing nothing installed." ON)
option(CATIO_FETCH_DEPS "Fetch and build SDL3 and nlohmann/json rather than find them installed." ON)
option(CATIO_HEADLESS "Build SDL with no windowing system: the software renderer only, for CI and cloud sessions." OFF)
option(CATIO_TTS "The queen's voice: a platform TTS backend. Not in v1." OFF)
set(CATIO_GATEWAY_ORIGIN "" CACHE STRING
    "Her gateway's origin, baked in. Empty means the sign-in screen asks for it.")

add_library(catio_headers INTERFACE)
target_include_directories(catio_headers INTERFACE include)
target_compile_features(catio_headers INTERFACE cxx_std_20)
if(CATIO_GATEWAY_ORIGIN)
  target_compile_definitions(catio_headers INTERFACE CATIO_GATEWAY_ORIGIN="${CATIO_GATEWAY_ORIGIN}")
endif()

set(CATIO_PUBLIC_HEADERS net house manor art draw view ui voice app)

if(CATIO_HEADERS_ONLY)
  set(CATIO_SELFTEST_SOURCES "")
  foreach(h IN LISTS CATIO_PUBLIC_HEADERS)
    set(gen "${CMAKE_CURRENT_BINARY_DIR}/selftest/${h}.cpp")
    file(GENERATE OUTPUT "${gen}" CONTENT "#include \"catio/${h}.h\"\n")
    list(APPEND CATIO_SELFTEST_SOURCES "${gen}")
  endforeach()
  add_library(catio_selftest OBJECT ${CATIO_SELFTEST_SOURCES})
  target_link_libraries(catio_selftest PRIVATE catio_headers)
  message(STATUS "catio-app: header self-containment check. -DCATIO_HEADERS_ONLY=OFF builds the core.")
  return()
endif()

# ---- dependencies --------------------------------------------------------------------------------
# SDL3: since 3.4 its core loads and saves PNG (SDL_LoadPNG, SDL_SavePNG), and every pack file is a PNG,
# so SDL_image is not needed. SDL3_ttf draws the two fonts, with its own FreeType and nothing else:
# no HarfBuzz (the words are Latin, left to right) and no plutosvg (no colour emoji).
if(CATIO_FETCH_DEPS)
  include(FetchContent)
  FetchContent_Declare(nlohmann_json
      URL https://github.com/nlohmann/json/releases/download/v3.12.0/json.tar.xz)
  set(CATIO_FETCHED nlohmann_json)
  if(NOT ANDROID)   # on Android, SDL3 comes from its .aar, found by prefab
    set(SDL_SHARED OFF CACHE BOOL "" FORCE)
    set(SDL_STATIC ON CACHE BOOL "" FORCE)
    set(SDL_TEST_LIBRARY OFF CACHE BOOL "" FORCE)
    if(CATIO_HEADLESS)
      # No X11, no Wayland, no GL: only the software renderer, which draws into a plain surface. SDL
      # refuses a Unix build with no windowing system unless told it is meant.
      foreach(o X11 WAYLAND KMSDRM OPENGL OPENGLES VULKAN GPU AUDIO JOYSTICK HAPTIC HIDAPI SENSOR CAMERA DIALOG TRAY)
        set(SDL_${o} OFF CACHE BOOL "" FORCE)
      endforeach()
      set(SDL_UNIX_CONSOLE_BUILD ON CACHE BOOL "" FORCE)
    endif()
    FetchContent_Declare(SDL3
        GIT_REPOSITORY https://github.com/libsdl-org/SDL.git
        GIT_TAG release-3.4.18
        GIT_SHALLOW TRUE)
    list(APPEND CATIO_FETCHED SDL3)
    set(SDLTTF_VENDORED ON CACHE BOOL "" FORCE)
    set(SDLTTF_HARFBUZZ OFF CACHE BOOL "" FORCE)
    set(SDLTTF_PLUTOSVG OFF CACHE BOOL "" FORCE)
    set(SDLTTF_SAMPLES OFF CACHE BOOL "" FORCE)
    set(SDLTTF_INSTALL OFF CACHE BOOL "" FORCE)
    set(BUILD_SHARED_LIBS OFF CACHE BOOL "" FORCE)
    FetchContent_Declare(SDL3_ttf
        GIT_REPOSITORY https://github.com/libsdl-org/SDL_ttf.git
        GIT_TAG release-3.2.2
        GIT_SHALLOW TRUE
        GIT_SUBMODULES external/freetype)
    list(APPEND CATIO_FETCHED SDL3_ttf)
  endif()
  FetchContent_MakeAvailable(${CATIO_FETCHED})
endif()
if(NOT TARGET SDL3::SDL3)
  find_package(SDL3 CONFIG REQUIRED)
endif()
if(NOT TARGET SDL3_ttf::SDL3_ttf)
  find_package(SDL3_ttf CONFIG REQUIRED)
endif()
if(NOT TARGET nlohmann_json::nlohmann_json)
  find_package(nlohmann_json CONFIG REQUIRED)
endif()

# ---- the core ------------------------------------------------------------------------------------
include(cmake/sources.cmake)   # CATIO_CORE_SOURCES, shared with ios/

add_library(catio_core STATIC ${CATIO_CORE_SOURCES})
target_include_directories(catio_core PRIVATE src)
target_link_libraries(catio_core PUBLIC catio_headers SDL3::SDL3 SDL3_ttf::SDL3_ttf nlohmann_json::nlohmann_json)
# where a desktop build finds the plan and the fonts when it is run from the build tree
target_compile_definitions(catio_core PUBLIC
    CATIO_SOURCE_DIR="${CMAKE_CURRENT_SOURCE_DIR}")

# catio_app: the window, the loop and the interface. With no windowing system it draws frames to PNGs:
#   catio_app --shot out.png [--size 1280x800] [--css 1] [--do "<steps>"]
add_executable(catio_app ${CATIO_APP_SOURCES})
target_include_directories(catio_app PRIVATE src)
target_link_libraries(catio_app PRIVATE catio_core)

# catio_look: render a floor to a PNG, with no window and no GPU. What CLAUDE.md's "look first" is for:
#   catio_look <catio dir> <manor.json> <fixtures dir> <out.png> [ground|upper|<room>]
add_executable(catio_look src/look.cpp)
target_include_directories(catio_look PRIVATE src)
target_link_libraries(catio_look PRIVATE catio_core)

# catio_tests: the floor plan, the house, the view and the interface's content, driven from JSON.
enable_testing()
add_executable(catio_tests test/tests.cpp)
target_include_directories(catio_tests PRIVATE src)
target_link_libraries(catio_tests PRIVATE catio_core)
add_test(NAME catio_tests
         COMMAND catio_tests "${CMAKE_CURRENT_SOURCE_DIR}/generated/manor.json" "${CMAKE_CURRENT_SOURCE_DIR}/test/fixtures")
