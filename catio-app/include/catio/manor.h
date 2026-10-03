// manor.h — the floor plan, and the geometry the page derives from it.
//
// The plan is generated, never written by hand. catio/tools/furniture.py emits the same page_data()
// twice from one call: into the MANOR block of catio/index.html, and into
// catio-app/generated/manor.json. Change the plan in manor.py and furniture.py together, re-run
// furniture.py (or build-art.py, which calls it), and both move at once. A hand-copy of these numbers
// in C++ would be the third copy of one truth, and the one that goes stale.
//
// manor.json is committed: it is generated from committed code and holds no art. The app reads it at
// start — on a phone from the application bundle, on a desktop from beside the binary.
//
// What manor.json holds (verified against the generated file):
//   world    [960, 576]            the grounds, in art pixels
//   face     32                    the south facade's band
//   rooms    key -> [x, y, w, h]   the room's box
//   floors   key -> [x0,y0,x1,y1]  the floor a cat may stand on
//   level    key -> "ground"|"upper"
//   landing  [x, y, w, h]          over the kitchen and hall
//   stairs   [x, y, w, h]          the same place on both floors, so changing floor never moves the camera
//   atlases  name -> [w, h]        "cc" is art/furniture.png, "lic" is art/licensed/furniture.png
//   pieces   key -> {atlas, at, size, kind, layer, foot, stations}
//   layout   room -> [[piece, x, y], …]
//   doors    [[a, b, [ax,ay], [bx,by]], …]   b null is the front door
//
// This module owns the *derivation* (GEOM, NEXT, LINE, freeFloor, wayTo), not the generator. Python
// already has twins of those rules for furniture.check(); emitting them as data too would make a third
// copy. One guard instead, in catio/test/: assert the committed manor.json still matches the page's
// MANOR block.
//
// DRAFT: declarations only. Nothing here is implemented yet.

#ifndef CATIO_MANOR_H
#define CATIO_MANOR_H

#include <cstdint>
#include <filesystem>
#include <optional>
#include <string>
#include <string_view>
#include <vector>

namespace catio::manor {

struct Point { int x = 0, y = 0; };
/// Art pixels, always. The camera turns these into device pixels; see view.h.
struct Box { int x = 0, y = 0, w = 0, h = 0; };

enum class Level { Ground, Upper };
/// Essential never moves (the front door mat, the stair, the cabinets, the brain's desk); connected
/// carries a station, so it may move but not go; decor may come and go.
enum class Kind { Essential, Connected, Decor };
/// Draw order: a rug under everything, wall pieces on the back wall band, floor pieces sorted by their
/// bottom edge (interleaved with the cats), top pieces set into a floor piece.
enum class Layer { Rug, Wall, Floor, Top };
/// Where a cat stands to show its state. `Queen` is the room's seat; `Upstairs` are the stair's steps,
/// foot to top, which cats climb on their way to the attic.
enum class State { Needs, Review, Work, Fail, Sleep, Queen, Upstairs };

struct Station { State state; int dx = 0, dy = 0; };

struct Piece {
    std::string key;
    std::string atlas;          ///< "cc" or "lic"
    Box cell;                   ///< where it sits on the sheet: at + size
    Box foot;                   ///< the part standing on the floor; no cat stands there. w==0 means none
    Kind kind = Kind::Decor;
    Layer layer = Layer::Floor;
    std::vector<Station> stations;
};

struct Placed { std::string piece; int x = 0, y = 0; };

/// A doorway as the cats use it. `b` empty is the front door; the stair is one link from the hall's
/// foot to the landing's top.
struct Door { std::string a, b; Point at_a, at_b; };

/// What GEOM is in the page: the room, where its cabinet and litter box stand, and the queen's seat.
struct Geom {
    std::string key, name;
    Box box, floor;
    Level level = Level::Ground;
    std::optional<Box> cabinet;   ///< filing_cabinet, or the catio's chest
    std::optional<Box> litter;    ///< brain_chest — the library's litter box, no sign on it
    std::optional<Point> queen;   ///< the seat, from a piece's `queen` station
};

/// Which way an arrow key or a phone swipe goes.
enum class Dir { Left, Right, Up, Down };

/// Load the generated plan. False if the file is missing or does not parse — the app then says so
/// rather than drawing an empty meadow.
bool load(const std::filesystem::path& manor_json);
bool loaded();

Box world();
int facade();
Box landing();
Box stairs();

const std::vector<Geom>& geom();                 ///< in the page's ORDER
const Geom* of(std::string_view key);
Level level_of(std::string_view key);            ///< the landing counts as upper
const std::vector<Door>& doors();
const Piece* piece(std::string_view key);
const std::vector<Placed>& layout(std::string_view room);
Box atlas(std::string_view name);

/// Every station in a room: where a cat of each state goes.
std::vector<std::pair<State, Point>> stations_of(std::string_view room);
/// The open floor a wandering cat may stand on: a grid over the room's floor, off every footprint.
const std::vector<Point>& free_floor(std::string_view room);
/// LINE: the queue spots in front of the entrance hall's door, beside the queen.
const std::vector<Point>& line_spots();
/// The stair's steps, foot to top — the stair piece's `upstairs` stations.
const std::vector<Point>& flight();

/// NEXT: the room next door on the same floor, by the page's 45-degree rule. Empty if there is none.
std::string_view next_room(std::string_view from, Dir d);

/// One leg of a journey: walk to this point, and be in this room when you get there.
struct Leg { Point to; std::string room; };
/// The cats' route through the doorways, breadth first. A journey that changes floor starts at the
/// stair on the floor it is going to.
std::vector<Leg> way_to(Point from, std::string_view from_room, Point to, std::string_view to_room);

}  // namespace catio::manor

#endif  // CATIO_MANOR_H
