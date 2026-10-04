// draw.cpp -- putting the packs on screen the way the page does.

#include "catio/draw.h"

#include <array>
#include <cmath>
#include <map>
#include <utility>
#include <vector>

#include "internal.h"

namespace catio::draw {

SDL_Texture* gpu(Canvas* c, art::Texture* t) {
    if (!c || !c->r || !t || !t->surface) return nullptr;
    if (t->gpu && t->owner == c->r) return t->gpu;
    if (t->gpu) SDL_DestroyTexture(t->gpu);
    t->gpu = SDL_CreateTextureFromSurface(c->r, t->surface);
    t->owner = c->r;
    // the pixel packs nearest-neighbour; the Pastel pieces smooth, never pixelated
    if (t->gpu) SDL_SetTextureScaleMode(t->gpu, t->pixel ? SDL_SCALEMODE_NEAREST : SDL_SCALEMODE_LINEAR);
    return t->gpu;
}

namespace {

SDL_FRect fr(Rect r) { return SDL_FRect{r.x, r.y, r.w, r.h}; }

// ---- the eight coats ---------------------------------------------------------------------------
//
// COATS in catio/index.html: each is a CSS filter list on the cat's sprite. Each function below is the
// colour matrix the Filter Effects spec defines for it, applied to the unpremultiplied sRGB values the
// way browsers apply CSS filter functions, one after another, each clamped before the next -- as each
// filter primitive's output is.

using M3 = std::array<float, 9>;

M3 hue_rotate(float deg) {
    const float a = std::cos(deg * 3.14159265358979f / 180.f), b = std::sin(deg * 3.14159265358979f / 180.f);
    return {0.213f + a * 0.787f - b * 0.213f, 0.715f - a * 0.715f - b * 0.715f, 0.072f - a * 0.072f + b * 0.928f,
            0.213f - a * 0.213f + b * 0.143f, 0.715f + a * 0.285f + b * 0.140f, 0.072f - a * 0.072f - b * 0.283f,
            0.213f - a * 0.213f - b * 0.787f, 0.715f - a * 0.715f + b * 0.715f, 0.072f + a * 0.928f + b * 0.072f};
}
M3 saturate(float s) {
    return {0.213f + 0.787f * s, 0.715f - 0.715f * s, 0.072f - 0.072f * s,
            0.213f - 0.213f * s, 0.715f + 0.285f * s, 0.072f - 0.072f * s,
            0.213f - 0.213f * s, 0.715f - 0.715f * s, 0.072f + 0.928f * s};
}
M3 grayscale(float g) {
    const float s = 1.f - std::min(1.f, g);
    return {0.2126f + 0.7874f * s, 0.7152f - 0.7152f * s, 0.0722f - 0.0722f * s,
            0.2126f - 0.2126f * s, 0.7152f + 0.2848f * s, 0.0722f - 0.0722f * s,
            0.2126f - 0.2126f * s, 0.7152f - 0.7152f * s, 0.0722f + 0.9278f * s};
}
M3 sepia(float a) {
    const float s = 1.f - std::min(1.f, a);
    return {0.393f + 0.607f * s, 0.769f - 0.769f * s, 0.189f - 0.189f * s,
            0.349f - 0.349f * s, 0.686f + 0.314f * s, 0.168f - 0.168f * s,
            0.272f - 0.272f * s, 0.534f - 0.534f * s, 0.131f + 0.869f * s};
}
M3 brightness(float b) { return {b, 0, 0, 0, b, 0, 0, 0, b}; }

// COATS, in the page's order. 0 is Cream: no filter at all.
const std::array<std::vector<M3>, 8>& coats() {
    static const std::array<std::vector<M3>, 8> k{{
        {},                                                         // Cream     none
        {hue_rotate(-18), saturate(1.3f)},                          // Ginger
        {grayscale(1), brightness(1.05f)},                          // Silver
        {sepia(0.5f), saturate(1.4f)},                              // Honey
        {hue_rotate(180), saturate(0.45f), brightness(1.02f)},      // Blue-grey
        {brightness(0.62f), saturate(0.5f)},                        // Shadow
        {hue_rotate(20), saturate(1.7f)},                           // Marmalade
        {grayscale(0.6f), brightness(0.8f)},                        // Smoke
    }};
    return k;
}

float clamp01(float v) { return v < 0 ? 0 : v > 1 ? 1 : v; }

// One tinted copy of a sheet per coat, made once.
std::map<std::pair<art::Texture*, int>, art::Texture>& tints() {
    static std::map<std::pair<art::Texture*, int>, art::Texture> k;
    return k;
}

art::Texture* tinted(art::Texture* sheet, int coat) {
    if (!sheet || coat <= 0 || coat >= 8) return sheet;
    auto& cache = tints();
    if (auto it = cache.find({sheet, coat}); it != cache.end()) return &it->second;
    SDL_Surface* s = SDL_ConvertSurface(sheet->surface, SDL_PIXELFORMAT_RGBA32);
    if (!s) return sheet;
    const auto& chain = coats()[static_cast<size_t>(coat)];
    for (int y = 0; y < s->h; ++y) {
        auto* row = static_cast<Uint8*>(s->pixels) + y * s->pitch;
        for (int x = 0; x < s->w; ++x) {
            Uint8* p = row + x * 4;
            if (!p[3]) continue;   // nothing to colour where there is nothing
            float r = p[0] / 255.f, g = p[1] / 255.f, b = p[2] / 255.f;
            for (const M3& m : chain) {
                const float nr = m[0] * r + m[1] * g + m[2] * b;
                const float ng = m[3] * r + m[4] * g + m[5] * b;
                const float nb = m[6] * r + m[7] * g + m[8] * b;
                r = clamp01(nr), g = clamp01(ng), b = clamp01(nb);
            }
            p[0] = static_cast<Uint8>(std::lround(r * 255.f));
            p[1] = static_cast<Uint8>(std::lround(g * 255.f));
            p[2] = static_cast<Uint8>(std::lround(b * 255.f));
        }
    }
    art::Texture t;
    t.surface = s;
    t.pixel = sheet->pixel;
    return &cache.emplace(std::make_pair(sheet, coat), t).first->second;
}

}  // namespace

// The integer art pixel for this device: the page's --u (2px, or 1px on a narrow screen, in CSS pixels)
// times the device's content scale, rounded down and never below one.
int scale_for(int pixel_width, int /*pixel_height*/, float content_scale) {
    const float cs = content_scale > 0 ? content_scale : 1.f;
    const float css_width = static_cast<float>(pixel_width) / cs;
    const float css_u = css_width <= 560.f ? 1.f : 2.f;
    const int u = static_cast<int>(std::floor(css_u * cs + 1e-4f));
    return u < 1 ? 1 : u;
}

void panel(const Ctx& c, const Panel& p, Rect dst) {
    SDL_Texture* t = gpu(c.canvas, c.art ? c.art->texture(p.tex) : nullptr);
    if (!t) return;   // not fetched yet: nothing, and not an error
    const float scale = p.ratio * (p.scales_with_u ? static_cast<float>(c.u) : 1.f);
    const SDL_FRect d = fr(dst);
    SDL_RenderTexture9Grid(c.canvas->r, t, nullptr, p.l, p.r, p.t, p.b, scale, &d);
}

void cell(const Ctx& c, art::Id id, Rect src, Rect dst, int coat) {
    art::Texture* t = c.art ? c.art->texture(id) : nullptr;
    SDL_Texture* g = gpu(c.canvas, tinted(t, coat));
    if (!g) return;
    const SDL_FRect s = fr(src), d = fr(dst);
    SDL_RenderTexture(c.canvas->r, g, &s, &d);
}

// steps(n) in the page's CSS: jump-end, so the frame is floor(fraction of the period * n).
void strip(const Ctx& c, art::Id id, Rect frame0, int frames, double now, double seconds, Rect dst) {
    int f = 0;
    if (frames > 1 && seconds > 0) {
        const double t = now / seconds;
        f = static_cast<int>((t - std::floor(t)) * frames);
        if (f >= frames) f = frames - 1;
    }
    cell(c, id, Rect{frame0.x + f * frame0.w, frame0.y, frame0.w, frame0.h}, dst);
}

void fill(const Ctx& c, Rect dst, Colour col) {
    if (!c.canvas || !c.canvas->r) return;
    SDL_SetRenderDrawBlendMode(c.canvas->r, SDL_BLENDMODE_BLEND);
    SDL_SetRenderDrawColor(c.canvas->r, col.r, col.g, col.b, col.a);
    const SDL_FRect d = fr(dst);
    SDL_RenderFillRect(c.canvas->r, &d);
}

// Pixel and Body -- the pack's pixel font and the bundled body font -- arrive with SDL_ttf, when there
// is text to draw. The first frame has none: nothing is ever written on the map.

}  // namespace catio::draw
