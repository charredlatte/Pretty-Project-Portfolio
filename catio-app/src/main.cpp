// main.cpp -- the app's entry. SDL_main.h turns this into the platform's own entry where it has one
// (Android's SDLActivity, iOS's UIApplicationMain), so the same main runs everywhere.

#include <SDL3/SDL_main.h>

#include "catio/app.h"

int main(int argc, char** argv) {
    catio::App app;
    if (!app.start(argc, argv)) return 1;
    return app.run();
}
