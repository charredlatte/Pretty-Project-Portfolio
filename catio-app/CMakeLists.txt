# The KittyChat Café as a native app — a DRAFT. See docs/mobile-app.md.
#
# Nothing is implemented yet: catio-app/src/ is empty and include/catio/*.h are declarations. So the
# DEFAULT target is not the app, it is the one thing a declaration-only branch can honestly verify:
# that every header is self-contained and real C++. It compiles one translation unit per header, each
# including only that header, and needs neither SDL nor libcurl:
#
#     cmake -S catio-app -B build && cmake --build build
#
# The app itself is -DCATIO_HEADERS_ONLY=OFF, and waits for the bodies.

cmake_minimum_required(VERSION 3.24)
project(catio_app LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

option(CATIO_HEADERS_ONLY "Compile each header alone. There is no app yet." ON)
option(CATIO_TTS "The queen's voice: a platform TTS backend. Not in v1." OFF)
set(CATIO_GATEWAY_ORIGIN "" CACHE STRING
    "Her gateway's origin, baked in. Empty means the sign-in screen asks for it.")

add_library(catio_headers INTERFACE)
target_include_directories(catio_headers INTERFACE include)
target_compile_features(catio_headers INTERFACE cxx_std_20)
if(CATIO_GATEWAY_ORIGIN)
  target_compile_definitions(catio_headers INTERFACE CATIO_GATEWAY_ORIGIN="${CATIO_GATEWAY_ORIGIN}")
endif()

# The headers deliberately name no SDL, curl or JSON type: own Rect/Colour, opaque handles, string
# bodies. That is the seam that lets the net layer be libcurl on a desktop and the platform's own HTTPS
# on a phone (docs/mobile-app.md), and it is what makes the check below possible with nothing installed.
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
  message(STATUS "catio-app: header self-containment check only; there is no app yet.")
  message(STATUS "catio-app: pass -DCATIO_HEADERS_ONLY=OFF once src/ has bodies.")
  return()
endif()

# ---- the app proper, once src/ has bodies -------------------------------------------------------
find_package(SDL3 CONFIG REQUIRED)          # SDL3::SDL3 — window, input, 2D renderer, 9-grid panels
find_package(SDL3_image CONFIG REQUIRED)    # the packs' PNGs
find_package(SDL3_ttf CONFIG REQUIRED)      # sprout.ttf at 18px, and the bundled body font

include(cmake/sources.cmake)                # CATIO_SOURCES, shared with ios/

if(ANDROID)
  add_library(catio_app SHARED ${CATIO_SOURCES})   # SDLActivity loads it by name
else()
  add_executable(catio_app ${CATIO_SOURCES})
endif()
target_link_libraries(catio_app PRIVATE catio_headers SDL3::SDL3 SDL3_image::SDL3_image SDL3_ttf::SDL3_ttf)

# HTTPS. There is no system libcurl on the Android NDK or on iOS, so the net layer has a per-platform
# body: net_curl.cpp on a desktop, net_android.cpp over JNI, net_apple.cpp over NSURLSession. See
# docs/mobile-app.md, "HTTPS on a phone" — the first of the hard problems.
if(NOT ANDROID AND NOT IOS)
  find_package(CURL REQUIRED)
  target_link_libraries(catio_app PRIVATE CURL::libcurl)
endif()

if(CATIO_TTS)
  target_compile_definitions(catio_app PRIVATE CATIO_TTS=1)
endif()
