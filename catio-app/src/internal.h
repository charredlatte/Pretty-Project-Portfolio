// internal.h -- what the public headers keep opaque, given its SDL body. Never installed, never included
// from include/: the public headers name no SDL type, so they compile with nothing installed.

#ifndef CATIO_INTERNAL_H
#define CATIO_INTERNAL_H

#include <SDL3/SDL.h>

#include "catio/art.h"
#include "catio/draw.h"

namespace catio::art {

/// One decoded pack file. The surface is the truth; a texture is made from it the first time a renderer
/// draws it, which keeps the cache free of any renderer and so testable over a directory of files.
struct Texture {
    SDL_Surface* surface = nullptr;   ///< owned
    bool pixel = true;                ///< nearest-neighbour (the pixel packs) or linear (the Pastel pieces)
    SDL_Texture* gpu = nullptr;       ///< owned; made by draw on first use
    SDL_Renderer* owner = nullptr;    ///< the renderer `gpu` belongs to
};

}  // namespace catio::art

namespace catio::draw {

/// The renderer: a window's, on a device, or a software one over a plain surface, headless.
struct Canvas {
    SDL_Renderer* r = nullptr;
};

/// The texture for `t` on this canvas, made on first use with the pack's own smoothing.
SDL_Texture* gpu(Canvas* c, art::Texture* t);

}  // namespace catio::draw

#endif  // CATIO_INTERNAL_H
