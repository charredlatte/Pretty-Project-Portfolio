# DRAFT, AND NEVER CONFIGURED. There is no Mac and no Xcode anywhere near the session that wrote this,
# so every line here is read from the documentation rather than tried. See docs/mobile-app.md.
#
#   cmake -S catio-app/ios -B build-ios -G Xcode \
#         -DCMAKE_SYSTEM_NAME=iOS -DCMAKE_OSX_DEPLOYMENT_TARGET=13.0 \
#         -DCATIO_HEADERS_ONLY=OFF -DSDL3_DIR=... -DCATIO_GATEWAY_ORIGIN=https://...
#   cmake --build build-ios --config Debug
#
# CMake has had an iOS generator since 3.14. No .xcodeproj is committed: a generated project nobody
# here can open would be stale before it was first opened.

cmake_minimum_required(VERSION 3.24)
project(catio_app_ios LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

get_filename_component(CATIO_APP_DIR "${CMAKE_CURRENT_LIST_DIR}/.." ABSOLUTE)

find_package(SDL3 CONFIG REQUIRED)
find_package(SDL3_ttf CONFIG REQUIRED)
find_package(nlohmann_json CONFIG REQUIRED)

include("${CATIO_APP_DIR}/cmake/sources.cmake")
list(TRANSFORM CATIO_CORE_SOURCES PREPEND "${CATIO_APP_DIR}/")
list(TRANSFORM CATIO_APP_SOURCES PREPEND "${CATIO_APP_DIR}/")

# The core, the interface and the loop exist; net_apple.cpp does not yet (cmake/sources.cmake lists
# what is to come). The plan rides in the bundle beside the fonts: SDL_GetBasePath() finds both.
add_executable(catio_app MACOSX_BUNDLE ${CATIO_CORE_SOURCES} ${CATIO_APP_SOURCES})
target_compile_definitions(catio_app PRIVATE CATIO_SOURCE_DIR="${CATIO_APP_DIR}")
target_sources(catio_app PRIVATE "${CATIO_APP_DIR}/generated/manor.json")
set_source_files_properties("${CATIO_APP_DIR}/generated/manor.json" PROPERTIES MACOSX_PACKAGE_LOCATION Resources)
target_include_directories(catio_app PRIVATE "${CATIO_APP_DIR}/include")
target_include_directories(catio_app PRIVATE "${CATIO_APP_DIR}/src")
target_link_libraries(catio_app PRIVATE SDL3::SDL3 SDL3_ttf::SDL3_ttf nlohmann_json::nlohmann_json)

# The bundled body font: the one font the app ships, because sprout.ttf is licensed and the page's own
# body font comes off Google Fonts. Without it there is nothing to draw the sign-in screen with.
target_sources(catio_app PRIVATE "${CATIO_APP_DIR}/assets")
set_source_files_properties("${CATIO_APP_DIR}/assets" PROPERTIES MACOSX_PACKAGE_LOCATION Resources)

set_target_properties(catio_app PROPERTIES
    MACOSX_BUNDLE_INFO_PLIST "${CMAKE_CURRENT_LIST_DIR}/Info.plist.in"
    MACOSX_BUNDLE_BUNDLE_NAME "KittyChat Cafe"
    MACOSX_BUNDLE_GUI_IDENTIFIER "cafe.kittychat"
    MACOSX_BUNDLE_SHORT_VERSION_STRING "0.1"
    MACOSX_BUNDLE_BUNDLE_VERSION "1"
    XCODE_ATTRIBUTE_TARGETED_DEVICE_FAMILY "1,2")

# No libcurl on iOS: src/net_apple.cpp is the NSURLSession body (cmake/sources.cmake picks it).
target_link_libraries(catio_app PRIVATE "-framework Foundation")
