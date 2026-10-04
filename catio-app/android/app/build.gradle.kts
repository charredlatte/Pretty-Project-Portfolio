// DRAFT: never configured. See docs/mobile-app.md.
//
// SDL3 comes in as its official Android archive and is found by prefab: gradle reads the prefab
// metadata out of the .aar and generates the CMake package config, so the very same
// `find_package(SDL3 CONFIG REQUIRED)` the desktop build uses resolves here. That is the whole reason
// one CMakeLists serves all three platforms.

plugins { id("com.android.application") }

android {
    namespace = "cafe.kittychat"
    compileSdk = 35

    defaultConfig {
        applicationId = "cafe.kittychat"
        minSdk = 24
        targetSdk = 35
        versionCode = 1
        versionName = "0.1-draft"
        ndk { abiFilters += listOf("arm64-v8a", "armeabi-v7a", "x86_64") }
        externalNativeBuild {
            cmake {
                arguments += listOf(
                    "-DCATIO_HEADERS_ONLY=OFF",
                    "-DANDROID_STL=c++_shared",
                    // her gateway, baked in; empty makes the sign-in screen ask
                    "-DCATIO_GATEWAY_ORIGIN="
                )
            }
        }
    }

    // prefab is what makes find_package(SDL3 CONFIG) work out of the .aar
    buildFeatures { prefab = true }

    externalNativeBuild {
        cmake {
            path = file("../../CMakeLists.txt")
            version = "3.24.0+"
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}

dependencies {
    // tools/fetch-sdl-android.sh puts these in app/libs/. No SDL_image: SDL 3.4's core loads PNG itself,
    // and every pack file is a PNG. SDL_ttf is for the pixel font, when there is text to draw.
    implementation(fileTree("libs") { include("SDL3-*.aar", "SDL3_ttf-*.aar") })
}
