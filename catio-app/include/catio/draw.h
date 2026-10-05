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
//    phone; here it is an integer chosen from the device (see css_for). The pixel font is rasterised
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
// Implemented in src/draw.cpp, and the two fonts in src/text.cpp over SDL_ttf. The coats match Chromium's
// own rendering of COATS byte for byte.

#ifndef CATIO_DRAW_H
#define CATIO_DRAW_H

#include <cstdint>
#include <filesystem>
#include <string>
#include <string_view>
#include <vector>

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
inline constexpr Panel kBubble { art::Id::UiBubble,     5, 5, 5, 6, 1.0f, true };  // 5 5 6 5 fill / 5u 5u 6u
/// The white selection brackets on a room. They grow with the interface's u, as everything Sprout
/// does, but not with the camera: `--bw` is u x slice divided by the camera's scale, so a room's
/// brackets are one size on screen at any zoom.
inline constexpr Panel kBrackets { art::Id::UiCorners,  8, 8, 9, 9, 1.0f, true };  // 9 8 / 9u 8u

// Game UI Pastel — the map panel, the minimap frame and the camera's buttons. Smooth, and fixed size.
inline constexpr Panel kMapPanel  { art::Id::PastelPanel,  28, 28, 28, 28, 0.5f,  false }; // 28 fill / 14px
inline constexpr Panel kMapButton { art::Id::PastelButton, 22, 22, 20, 24, 0.5f,  false }; // 20 22 24 / 10 11 12
inline constexpr Panel kMapFrame  { art::Id::PastelFrame,  28, 28, 28, 28, 0.214f, false }; // 28 / 6px

/// Whole device pixels to one CSS pixel, from the display's content scale: floored, so the interface
/// is never larger than the page's, and never below one. A 2.625 phone draws at 2. The art pixel is
/// then this times the page's --u: 2, or 1 on a phone (Stage::narrow()).
int css_for(float content_scale);

struct Ctx {
    Canvas* canvas;
    const art::Art* art;
    int u;          ///< one art pixel of the interface, in device pixels: --u, 2 CSS px (1 on a phone)
    int css = 1;    ///< one CSS pixel, in device pixels: every px in the page's stylesheet is this many
    std::uint8_t alpha = 255;   ///< opacity for the art drawn through this context (.pbtn:disabled is .5)
};

/// A 9-slice with each side its own width on screen, and the middle filled or not: CSS border-image in
/// full, for the pieces whose sides do not share one ratio (a count's thinner button, 3 3 5 3 from
/// 4 4 6 4) and the ones with no `fill` (the screen's frame, a divider). `src` empty means the whole
/// sheet. Nine draws rather than SDL's one, so it costs more: panel() is still the one to reach for.
struct Slice { float l = 0, r = 0, t = 0, b = 0; };
void nine(const Ctx& c, art::Id id, Rect src, Slice cut, Slice width, Rect dst, bool fill);

/// A missing texture draws nothing and is not an error: the house fills in as the fetches land.
void panel(const Ctx& c, const Panel& p, Rect dst);
/// A cut of one sheet. A coat above 0 draws the sheet in that coat: COATS' CSS filters, ported as the
/// colour matrices the Filter Effects spec defines, applied once into a cached copy. kOutline draws
/// its shape alone in the pack's white: four of those a world pixel or two apart are the page's
/// drop-shadow outline around a cat under the pointer ("it outlines the object boundaries").
inline constexpr int kOutline = -1;
void cell(const Ctx& c, art::Id id, Rect src, Rect dst, int coat = 0);
/// One frame of a sprite strip, chosen from the clock. Cats animate; with reduced motion they do not.
void strip(const Ctx& c, art::Id id, Rect frame0, int frames, double now, double seconds, Rect dst);
void fill(const Ctx& c, Rect dst, Colour col);
/// A rounded box, for what the page draws with border-radius and no art: the minimap's ground, a pip.
void round(const Ctx& c, Rect dst, float radius, Colour col);

class Body;

/// The pack's pixel font (sprout.ttf), rasterised once at 18px and blitted at x css: one font pixel a
/// CSS pixel, as `--px-size: 18px` keeps it. Capitals only -- small letters draw as capitals -- so
/// prose belongs in Body. build-art.py adds the accents French names need.
///
/// Until the art is fetched there is no sprout.ttf, and the page's own fallback (`--pixel: "Sprout",
/// var(--display)`) is a round font: so is this one's, the Body it is given.
class Pixel {
public:
    Pixel();
    ~Pixel();
    bool open(const std::filesystem::path& ttf);
    /// Draw with this round font instead while sprout.ttf is missing. It must outlive the Pixel.
    void fallback(const Body* round);
    bool ready() const;
    /// In device pixels, at `css` device pixels a CSS pixel.
    Pt measure(std::string_view text, int css) const;
    void put(const Ctx& c, std::string_view text, float x, float y, Colour col) const;

private:
    struct Impl;
    Impl* impl_;
};

/// The body font, for prose and for every screen that comes before the art: the sign-in form and the
/// "fetching the art" line. It is the ONE font the app commits (catio-app/assets/: Nunito, OFL),
/// because sprout.ttf is licensed and the page's own body font comes off Google Fonts -- so without it
/// the app could not draw a single letter before it has signed in and fetched.
///
/// One Body is one face at one size, opened in DEVICE pixels: the page's 12.8px at css 3 is 38.
class Body {
public:
    Body();
    ~Body();
    bool open(const std::filesystem::path& ttf, float px);
    bool ready() const;
    float px() const;
    Pt measure(std::string_view text) const;
    /// Break into lines no wider than `width`, at spaces where it can and anywhere where it must
    /// (overflow-wrap: anywhere). More than `max_lines` and the last one ends in an ellipsis, as
    /// -webkit-line-clamp does. 0 means no limit.
    std::vector<std::string> wrap(std::string_view text, float width, int max_lines = 0) const;
    /// One line, cut with an ellipsis to fit (text-overflow: ellipsis).
    std::string cut(std::string_view text, float width) const;
    void put(const Ctx& c, std::string_view text, float x, float y, Colour col) const;

private:
    struct Impl;
    Impl* impl_;
};

}  // namespace catio::draw

#endif  // CATIO_DRAW_H
