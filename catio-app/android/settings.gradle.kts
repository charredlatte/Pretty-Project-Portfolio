// DRAFT: never configured. There is no Android SDK or NDK in the session that wrote this, so treat
// every version and coordinate below as read-from-the-docs, not tried. See docs/mobile-app.md.

pluginManagement {
    repositories { google(); mavenCentral(); gradlePluginPortal() }
}
dependencyResolutionManagement {
    repositories {
        google(); mavenCentral()
        // SDL ships official Android archives. tools/fetch-sdl-android.sh drops them here; they are
        // ~20 MB of binary and are NOT committed.
        flatDir { dirs("app/libs") }
    }
}

rootProject.name = "KittyChat Cafe"
include(":app")
