// view.h — the camera, where every cat stands this frame, and what is under her finger.
//
// It computes; it never draws. It includes house.h and manor.h and no renderer, so "does a tap at this
// point hit that cat?" and "where does the queue stand?" are answerable in a test.
//
// This is render()'s body and the camera from catio/index.html, with one difference that matters on a
// phone: the page's camera scale is a float, which is why "zoom that lands on crisp pixel sizes" is
// still an open item in docs/camera-and-minimap.md. Here Cam::u is a whole number of device pixels per
// art pixel, zoom steps are u +/- 1, and panning rounds to whole device pixels. Nothing can blur.
//
// DRAFT: declarations only. Nothing here is implemented yet.

#ifndef CATIO_VIEW_H
#define CATIO_VIEW_H

#include <cstdint>
#include <map>
#include <optional>
#include <string>
#include <string_view>
#include <vector>

#include "catio/draw.h"
#include "catio/house.h"
#include "catio/manor.h"

namespace catio::view {

/// The stage, in device pixels.
struct Stage { int w = 0, h = 0; };

struct Cam {
    int u = 2;                                   ///< always whole: one art pixel in device pixels
    float tx = 0, ty = 0;                        ///< the top-left of the world, in device pixels
    std::string focus;                           ///< the room that fills the view (S.focus)
    manor::Level floor = manor::Level::Ground;
};

/// Fit a box: u snapped DOWN to a whole number, so the fit is crisp rather than exact.
Cam fit(manor::Box what, Stage stage);
/// Never past the meadow's edge.
Cam clamp(Cam c, Stage stage);
Cam zoom_by(Cam c, int du, float at_x, float at_y, Stage stage);
Cam pan_by(Cam c, float dx, float dy, Stage stage);

draw::Pt to_screen(const Cam& c, manor::Point p);
manor::Point to_world(const Cam& c, float sx, float sy);
/// roomInView / settleFocus: the room the camera has settled on.
std::string room_in_view(const Cam& c, Stage stage);

/// Where one cat stands this frame.
struct Spot {
    const Cat* cat = nullptr;
    manor::Point at;
    std::string room;
    int queue_place = -1;   ///< its place in the line at the front door, or -1
    bool on_stairs = false;
};

/// Too many cats for one room's stations: they stack, and the pile opens a list. The page draws no
/// number on a pile.
struct Pile {
    std::vector<const Cat*> cats;
    manor::Point at;
    std::string room;
};

struct Scene {
    std::vector<Spot> cats;
    std::vector<Pile> piles;
    std::optional<Spot> queen;              ///< her seat in the entrance hall; never in `cats`
    std::vector<const Cat*> attic;          ///< napping out of sight, counted nowhere
    std::map<std::string, int> needing;     ///< per room, for the minimap's pips
};

/// One frame's placement: stations, the free floor for wanderers, the piles, and the queue at the door.
Scene build(const House& h, manor::Level floor);

enum class Thing { None, Room, Cat, Queen, Pile, Cabinet, Litter, Stairs, Attic };

struct Hit {
    Thing what = Thing::None;
    std::string key;     ///< a room key, or a cat id
    draw::Rect box;      ///< in device pixels, already grown to the touch minimum where coarse
};

/// Cats before rooms, as the page tests them. On a coarse pointer every box is grown to at least
/// ui::kTouch before testing — her audit measured cats at 6-12px and the smallest rooms at 38x44.
Hit pick(const Scene& s, const Cam& c, Stage stage, float sx, float sy, bool coarse);

/// Cats walk when their place changes: through the doorways to a new room, up the stair to the attic,
/// down when they come back, in by the front door when they are new. A cat that stops waiting walks
/// back to its room. With reduced motion, and for four seconds after the app opens, they are simply
/// in their places.
class Walks {
public:
    Walks();
    ~Walks();

    /// Compare this frame's scene with the last and start any journey that is now due.
    void settle(const Scene& s, double now, bool reduced_motion);
    /// Where to draw a cat: part-way along its journey, or its settled spot.
    manor::Point where(std::string_view cat_id, manor::Point settled) const;
    bool walking(std::string_view cat_id) const;
    /// WAITING: when the app first saw this cat waiting, which orders the queue (longest wait first).
    std::int64_t waiting_since(std::string_view cat_id) const;
    /// A copy of a cat walks its handoff to the queen's seat, and vanishes there.
    void to_queen(std::string_view cat_id);

private:
    struct Impl;
    Impl* impl_;
};

}  // namespace catio::view

#endif  // CATIO_VIEW_H
