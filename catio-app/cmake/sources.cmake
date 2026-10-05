# The translation units, in one list so the desktop build and ios/ share it.

# The core: the floor plan, the house, the art, drawing, the fonts, the view and the interface.
set(CATIO_CORE_SOURCES
    src/manor.cpp
    src/house.cpp
    src/art.cpp
    src/draw.cpp
    src/text.cpp
    src/view.cpp
    src/ui.cpp
)

# The app around it: the window, the loop and the one place a press becomes a write.
set(CATIO_APP_SOURCES
    src/app.cpp
    src/main.cpp
)

# Still to come:
#
#   one net body per platform -- the header names no curl type precisely so this choice is possible:
#     src/net_curl.cpp     desktop
#     src/net_android.cpp  HttpsURLConnection over JNI (no system libcurl on the NDK)
#     src/net_apple.cpp    NSURLSession (no system libcurl on iOS)
#   the queen's voice, behind -DCATIO_TTS=ON (include/catio/voice.h says why it is not in v1):
#     src/voice_android.cpp  src/voice_apple.cpp  src/voice_null.cpp
