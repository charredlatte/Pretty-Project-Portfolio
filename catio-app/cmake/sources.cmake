# The app's translation units, in one list so the desktop build, android/ and ios/ share it.
#
# EVERY FILE BELOW IS STILL TO BE WRITTEN: this branch is declarations only (docs/mobile-app.md). The
# list is here so the three builds cannot drift apart the moment the first body lands.

set(CATIO_SOURCES
    src/main.cpp
    src/house.cpp
    src/manor.cpp
    src/art.cpp
    src/draw.cpp
    src/view.cpp
    src/ui.cpp
    src/app.cpp
)

# One net body per platform: the header names no curl type precisely so this choice is possible.
if(ANDROID)
  list(APPEND CATIO_SOURCES src/net_android.cpp)
elseif(IOS OR APPLE)
  list(APPEND CATIO_SOURCES src/net_apple.cpp)
else()
  list(APPEND CATIO_SOURCES src/net_curl.cpp)
endif()

# The queen's voice, off in v1 (include/catio/voice.h says why).
if(CATIO_TTS)
  if(ANDROID)
    list(APPEND CATIO_SOURCES src/voice_android.cpp)
  elseif(APPLE)
    list(APPEND CATIO_SOURCES src/voice_apple.cpp)
  else()
    list(APPEND CATIO_SOURCES src/voice_null.cpp)
  endif()
endif()
