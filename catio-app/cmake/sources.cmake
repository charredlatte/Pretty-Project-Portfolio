# The translation units, in one list so the desktop build and ios/ share it.

# What exists: the floor plan, the house, the art, drawing and the view.
set(CATIO_CORE_SOURCES
    src/manor.cpp
    src/house.cpp
    src/art.cpp
    src/draw.cpp
    src/view.cpp
)

# Still to come: the app proper. It is not a target yet because its sources do not exist, and a target
# naming files that are not there would only fail the build.
#
#   src/main.cpp  src/app.cpp  src/ui.cpp
#   one net body per platform -- the header names no curl type precisely so this choice is possible:
#     src/net_curl.cpp     desktop
#     src/net_android.cpp  HttpsURLConnection over JNI (no system libcurl on the NDK)
#     src/net_apple.cpp    NSURLSession (no system libcurl on iOS)
#   the queen's voice, behind -DCATIO_TTS=ON (include/catio/voice.h says why it is not in v1):
#     src/voice_android.cpp  src/voice_apple.cpp  src/voice_null.cpp
