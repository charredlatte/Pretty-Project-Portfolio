#!/bin/sh
# Fetch SDL's official Android archives into catio-app/android/app/libs/.
#
# DRAFT: never run. The versions are SDL's current releases (checked 3 October 2026: SDL 3.4.18,
# SDL_ttf 3.2.2). The .aar FILENAMES are not checked -- GitHub's release listing was out of reach -- so
# confirm them on the release pages before trusting this. The .aar files are about 20 MB of binary and
# are gitignored: they are SDL's to distribute, not ours. No SDL_image: SDL 3.4's core loads PNG.
set -eu

VER="${SDL_VERSION:-3.4.18}"
TTF="${SDL_TTF_VERSION:-3.2.2}"
OUT="$(dirname "$0")/../android/app/libs"
mkdir -p "$OUT"

get() {
    echo "fetching $2"
    curl -fsSL -o "$OUT/$2" "$1/$2"
}

get "https://github.com/libsdl-org/SDL/releases/download/release-$VER"            "SDL3-$VER.aar"
get "https://github.com/libsdl-org/SDL_ttf/releases/download/release-$TTF"        "SDL3_ttf-$TTF.aar"

echo "done. gradle finds these through settings.gradle.kts's flatDir, and prefab makes"
echo "find_package(SDL3 CONFIG) resolve out of them."
