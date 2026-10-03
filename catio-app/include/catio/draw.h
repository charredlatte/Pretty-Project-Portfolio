// draw.h — putting the packs on screen the way the page does.
//
// It draws; it does not know what a cat is. No house.h, no view.h, no transport.
//
// The page builds its whole interface out of the packs, as CSS `border-image` 9-slices. SDL3 has that
// call outright — SDL_RenderTexture9Grid, since 3.2.0 — which is why this stack suits the job: a panel
// is one call, not nine.
//
// Two rules this module exists to keep.
//
// 1. ONE ART PIXEL IS A WHOLE NUMBER OF SCREEN PIXELS. The page's `--u` is 2px on a laptop and 1px on a
//    phone; here it is an integer chosen from the device (see scale_for). The pixel font is rasterised
//    ONCE at 18px into a nearest-filtered atlas and blitted at x u — never reopened at 18*u, which
//    re-hints the outlines and breaks the page's "one font pixel is one screen pixel" promise. Its one
//    "good" in her UI audit was "Pixel font kept at 18px".
//
// 2. EACH PANEL IS DRAWN FROM ONE PACK, AND AT THAT PACK'S OWN SMOOTHING. Sprout Lands is pixel art,
//    nearest-neighbour; Game UI Pastel is smooth, and scaling it with nearest is the one way to make it
//    look wrong. CLAUDE.md: "scale it down with ordinary smoothing, never pixelated."
//
// The slice numbers below are read off catio/index.html's border-image rules, and the two packs differ
// in a way worth knowing: Sprout Lands panels give their border a width of N x --u, so their corners
// grow with the zoom; the Pastel panels and the selection brackets give theirs a FIXED pixel width, so
// they stay one size on screen at any zoom. That is deliberate — CLAUDE.md says the brackets "stay one
// size on screen at any zoom" — and it is what `scales_with_u` carries.
//
// DRAFT: declarations only. Nothing here is implemented yet.

#ifndef CATIO_DRAW_H
#define CATIO_DRAW_H

#include <cstdint>
#include <filesystem>
#include <string_view>

#include "catio/art.h"

namespace catio::draw {

struct Rect { float x = 0, y = 0, w = 0, h = 0; };
struct Pt { float x = 0, y = 0; };
struct Colour { std::uint8_t r = 0, g = 0, b = 0, a = 255; };

/// The renderer, behind one name so this header stays free of graphics types.
struct Canvas;

/// A 9-slice panel: the four slice widths in SOURCE pixels, and how the corner is scaled on screen.
///
/// It maps straight onto SDL_RenderTexture9Grid(renderer, tex, nullptr, l, r, t, b, scale, dst). The
/// single `scale` works only because each of the page's panels has one slice-to-width ratio; a panel
/// that ever needed two different ratios could not use this call, and would want nine draws.
struct Panel {
    art::Id tex;
    float l, r, t, b;      ///< border-image-slice, in the source PNG's pixels
    float ratio;           ///< border width / slice: 1 for Sprout Lands, 0.5 for the Pastel panels
    bool scales_with_u;    ///< true: corner = slice * ratio * u. false: corner = slice * ratio, fixed
};

// Sprout Lands — menus, dialogs, buttons, fields, the sign, the screen's frame. Corners grow with u.
inline constexpr Panel kPanel  { art::Id::UiPanel,      6, 6, 6, 6, 1.0f, true };  // panel.png 6 fill / 6u
inline constexpr Panel kButton { art::Id::UiButton,     4, 4, 4, 6, 1.0f, true };  // 4 4 6 4 fill / 4u 4u 6u
inline constexpr Panel kPressed{ art::Id::UiButtonDown, 4, 4, 4, 4, 1.0f, true };  // 4 fill / 4u
inline constexpr Panel kField  { art::Id::UiField,      4, 4, 4, 5, 1.0f, true };  // 4 4 5 4 fill / 4u 4u 5u
inline constexpr Panel kBubble { art::Id::UiBubble,     6, 6, 6, 6, 1.0f, true };
/// The white selection brackets on a room, a cabinet or a focused cat. Fixed: one size at any zoom.
inline constexpr Panel kBrackets { art::Id::UiCorners,  8, 8, 9, 9, 1.0f, false }; // 9 8 / 9px 8px

// Game UI Pastel — the map panel, the minimap frame and the camera's buttons. Smooth, and fixed size.
inline constexpr Panel kMapPanel  { art::Id::PastelPanel,  28, 28, 28, 28, 0.5f,  false }; // 28 fill / 14px
inline constexpr Panel kMapButton { art::Id::PastelButton, 22, 22, 20, 24, 0.5f,  false }; // 20 22 24 / 10 11 12
inline constexpr Panel kMapFrame  { art::Id::PastelFrame,  28, 28, 28, 28, 0.214f, false }; // 28 / 6px

/// The integer art pixel for this device, from its size and content scale. 1 is one art pixel per
/// device pixel — correct, and far too small to read on a phone; see docs/mobile-app.md.
int scale_for(int pixel_width, int pixel_height, float content_scale);

struct Ctx {
    Canvas* canvas;
    const art::Art* art;
    int u;          ///< one art pixel, in device pixels
};

/// A missing texture draws nothing and is not an error: the house fills in as the fetches land.
void panel(const Ctx& c, const Panel& p, Rect dst);
void cell(const Ctx& c, art::Id id, Rect src, Rect dst);
/// One frame of a sprite strip, chosen from the clock. Cats animate; with reduced motion they do not.
void strip(const Ctx& c, art::Id id, Rect frame0, int frames, double now, double seconds, Rect dst);
void fill(const Ctx& c, Rect dst, Colour col);

/// The pack's pixel font (sprout.ttf) at 18px, blitted at x u. Capitals only — small letters draw as
/// capitals — so prose belongs in Body. build-art.py adds the accents French names need.
class Pixel {
public:
    Pixel();
    ~Pixel();
    bool open(const art::Art& a, int px = 18);
    bool ready() const;
    Pt measure(std::string_view text, int u) const;
    void put(const Ctx& c, std::string_view text, float x, float y, Colour col);

private:
    struct Impl;
    Impl* impl_;
};

/// The body font, for prose and for every screen that comes before the art: the sign-in form and the
/// "fetching the art" line. It is the ONE font the app commits, because sprout.ttf is licensed and the
/// page's own body font comes off Google Fonts — so without a bundled OFL font the app cannot draw a
/// single letter before it has signed in and fetched. See catio-app/assets/.
class Body {
public:
    Body();
    ~Body();
    bool open(const std::filesystem::path& ttf, int px);
    bool ready() const;
    Pt measure(std::string_view text) const;
    void put(const Ctx& c, std::string_view text, float x, float y, Colour col);

private:
    struct Impl;
    Impl* impl_;
};

}  // namespace catio::draw

#endif  // CATIO_DRAW_H
