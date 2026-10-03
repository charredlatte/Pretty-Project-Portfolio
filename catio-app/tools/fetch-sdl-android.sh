#!/bin/sh
# Fetch SDL's official Android archives into catio-app/android/app/libs/.
#
# DRAFT: never run. VERIFY THE VERSION AND THE FILENAMES against the current SDL release before
# trusting this — the archive coordinates moved between the 3.1 previews and 3.2. The .aar files are
# about 20 MB of binary and are gitignored: they are SDL's to distribute, not ours.
set -eu

VER="${SDL_VERSION:-3.2.24}"
IMG="${SDL_IMAGE_VERSION:-3.2.4}"
TTF="${SDL_TTF_VERSION:-3.2.2}"
OUT="$(dirname "$0")/../android/app/libs"
mkdir -p "$OUT"

get() {
    echo "fetching $2"
    curl -fsSL -o "$OUT/$2" "$1/$2"
}

get "https://github.com/libsdl-org/SDL/releases/download/release-$VER"            "SDL3-$VER.aar"
get "https://github.com/libsdl-org/SDL_image/releases/download/release-$IMG"      "SDL3_image-$IMG.aar"
get "https://github.com/libsdl-org/SDL_ttf/releases/download/release-$TTF"        "SDL3_ttf-$TTF.aar"

echo "done. gradle finds these through settings.gradle.kts's flatDir, and prefab makes"
echo "find_package(SDL3 CONFIG) resolve out of them."
