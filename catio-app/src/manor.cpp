// manor.cpp -- the generated floor plan, and what the page derives from it.
//
// Each derivation here is a port of the page's own, line for line, and names the original: GEOM,
// stationsOf, freeFloor, LINE and NEXT in catio/index.html. Where the page's arithmetic is odd, so is this.

#include "catio/manor.h"

#include <algorithm>
#include <array>
#include <cmath>
#include <fstream>
#include <limits>
#include <map>

#include <nlohmann/json.hpp>

namespace catio::manor {
namespace {

using json = nlohmann::json;

// ORDER and ROOM_NAMES, as in catio/index.html. Not in manor.json: they are the page's, not the plan's.
// The names are only defaults -- rooms/<key>.name is hers -- and catio_tests checks that ORDER and the
// plan's rooms are the same set, so a room added to one and not the other fails the build's tests.
constexpr std::array<std::pair<std::string_view, std::string_view>, 10> kOrder{{
    {"dining", "Café"}, {"kitchen", "Kitchen"}, {"living", "Cat lounge"}, {"study", "Craft room"},
    {"hall", "Entrance hall"}, {"sunroom", "Terrace"}, {"garden", "Catio"}, {"brain", "Library"},
    {"bath", "Ensuite"}, {"bedroom", "Bedroom"},
}};

struct Plan {
    bool ok = false;
    Box world, landing, stairs;
    int face = 0;
    std::map<std::string, Piece, std::less<>> pieces;
    std::map<std::string, std::vector<Placed>, std::less<>> layout;
    std::map<std::string, Box, std::less<>> rooms;                 // [x, y, w, h]
    std::map<std::string, std::array<int, 4>, std::less<>> floors; // [x0, y0, x1, y1] -- corners, not w/h
    std::map<std::string, Level, std::less<>> level;
    std::map<std::string, Box, std::less<>> atlases;
    std::vector<Door> doors;
    std::vector<Geom> geom;
    std::map<std::string, std::vector<Point>, std::less<>> free;   // freeFloor, cached
    std::vector<Point> line, flight;
    std::map<std::string, std::array<std::string, 4>, std::less<>> next;
};
Plan P;

const std::vector<Placed> kNone;
const std::vector<Point> kNoPoints;

Box box4(const json& a) { return Box{a.at(0).get<int>(), a.at(1).get<int>(), a.at(2).get<int>(), a.at(3).get<int>()}; }

State state_of(std::string_view s) {
    if (s == "needs") return State::Needs;
    if (s == "review") return State::Review;
    if (s == "work") return State::Work;
    if (s == "fail") return State::Fail;
    if (s == "sleep") return State::Sleep;
    if (s == "queen") return State::Queen;
    return State::Upstairs;
}

Layer layer_of(std::string_view s) {
    return s == "rug" ? Layer::Rug : s == "wall" ? Layer::Wall : s == "top" ? Layer::Top : Layer::Floor;
}

Kind kind_of(std::string_view s) {
    return s == "essential" ? Kind::Essential : s == "connected" ? Kind::Connected : Kind::Decor;
}

// GEOM, as the page builds it: the first filing cabinet (or the catio's chest), the first queen station
// in layout order, and the brain's chest, which is the litter box.
void derive_geom() {
    P.geom.clear();
    for (auto [key, name] : kOrder) {
        Geom g;
        g.key = std::string(key);
        g.name = std::string(name);
        if (auto r = P.rooms.find(key); r != P.rooms.end()) g.box = r->second;
        if (auto f = P.floors.find(key); f != P.floors.end())
            g.floor = Box{f->second[0], f->second[1], f->second[2] - f->second[0], f->second[3] - f->second[1]};
        g.level = level_of(key);
        for (const auto& q : layout(key)) {
            const Piece* p = piece(q.piece);
            if (!p) continue;
            if (!g.cabinet && (q.piece == "filing_cabinet" || q.piece == "catio_chest"))
                g.cabinet = Box{q.x, q.y, p->cell.w, p->cell.h};
            if (!g.litter && q.piece == "brain_chest") g.litter = Box{q.x, q.y, p->cell.w, p->cell.h};
            if (!g.queen)
                for (const auto& s : p->stations)
                    if (s.state == State::Queen) { g.queen = Point{q.x + s.dx, q.y + s.dy}; break; }
        }
        P.geom.push_back(std::move(g));
    }
}

// LINE: the queue's places, in front of the hall's door, beside the queen's seat. Two rows, 20 apart.
void derive_line() {
    P.line.clear();
    Point door{394, 378};
    for (const auto& d : P.doors)
        if (d.a == "hall" && d.b.empty()) { door = d.at_a; break; }
    auto f = P.floors.find("hall");
    if (f == P.floors.end()) return;
    const int x1 = f->second[2], y1 = f->second[3];
    const Geom* hall = of("hall");
    const Point seat = hall && hall->queen ? *hall->queen : Point{door.x - 46, door.y};
    const int row = std::min(door.y, y1 - 6);
    for (int y : {row, row - 18})
        for (int x = seat.x + 22; x <= x1 - 12; x += 20) P.line.push_back(Point{x, y});
}

// The stair's steps, foot to top: the stair piece's `upstairs` stations, in the order furniture.py wrote them.
void derive_flight() {
    P.flight.clear();
    for (const auto& q : layout("hall")) {
        const Piece* p = piece(q.piece);
        if (!p) continue;
        for (const auto& s : p->stations)
            if (s.state == State::Upstairs) P.flight.push_back(Point{q.x + s.dx, q.y + s.dy});
    }
}

// NEXT: for each arrow, the nearest same-floor room whose centre lies within 45 degrees of that way,
// scored by the distance along it plus twice the sideways offset.
void derive_next() {
    P.next.clear();
    auto mid = [](const Geom& g) { return std::pair<double, double>{g.box.x + g.box.w / 2.0, g.box.y + g.box.h / 2.0}; };
    constexpr std::array<std::array<int, 2>, 4> kWays{{{-1, 0}, {1, 0}, {0, -1}, {0, 1}}};   // Dir order
    for (const auto& a : P.geom) {
        auto [ax, ay] = mid(a);
        std::array<std::string, 4> best{};
        for (size_t d = 0; d < kWays.size(); ++d) {
            const int dx = kWays[d][0], dy = kWays[d][1];
            double score = std::numeric_limits<double>::infinity();
            for (const auto& b : P.geom) {
                if (b.level != a.level) continue;
                auto [bx, by] = mid(b);
                const double along = (bx - ax) * dx + (by - ay) * dy;
                const double side = std::abs((bx - ax) * dy + (by - ay) * dx);
                if (along > 0 && side <= along && along + 2 * side < score) { score = along + 2 * side; best[d] = b.key; }
            }
        }
        P.next[a.key] = best;
    }
}

}  // namespace

bool load(const std::filesystem::path& manor_json) {
    P = Plan{};
    std::ifstream in(manor_json);
    if (!in) return false;
    json j = json::parse(in, nullptr, /*allow_exceptions=*/false);
    if (j.is_discarded() || !j.is_object()) return false;
    try {
        P.world = Box{0, 0, j.at("world").at(0).get<int>(), j.at("world").at(1).get<int>()};
        P.face = j.at("face").get<int>();
        P.landing = box4(j.at("landing"));
        P.stairs = box4(j.at("stairs"));
        for (auto& [k, v] : j.at("rooms").items()) P.rooms[k] = box4(v);
        for (auto& [k, v] : j.at("floors").items())
            P.floors[k] = {v.at(0).get<int>(), v.at(1).get<int>(), v.at(2).get<int>(), v.at(3).get<int>()};
        for (auto& [k, v] : j.at("level").items()) P.level[k] = v.get<std::string>() == "upper" ? Level::Upper : Level::Ground;
        for (auto& [k, v] : j.at("atlases").items()) P.atlases[k] = Box{0, 0, v.at(0).get<int>(), v.at(1).get<int>()};
        for (auto& [k, v] : j.at("pieces").items()) {
            Piece p;
            p.key = k;
            p.atlas = v.at("atlas").get<std::string>();
            p.cell = Box{v.at("at").at(0).get<int>(), v.at("at").at(1).get<int>(),
                         v.at("size").at(0).get<int>(), v.at("size").at(1).get<int>()};
            if (v.at("foot").is_array()) p.foot = box4(v.at("foot"));   // null: no footprint (w stays 0)
            p.kind = kind_of(v.at("kind").get<std::string>());
            p.layer = layer_of(v.at("layer").get<std::string>());
            for (auto& s : v.at("stations"))
                p.stations.push_back(Station{state_of(s.at(0).get<std::string>()), s.at(1).get<int>(), s.at(2).get<int>()});
            P.pieces[k] = std::move(p);
        }
        for (auto& [k, v] : j.at("layout").items())
            for (auto& q : v) P.layout[k].push_back(Placed{q.at(0).get<std::string>(), q.at(1).get<int>(), q.at(2).get<int>()});
        for (auto& d : j.at("doors")) {
            Door door;
            door.a = d.at(0).get<std::string>();
            if (!d.at(1).is_null()) door.b = d.at(1).get<std::string>();   // empty: the front door
            door.at_a = Point{d.at(2).at(0).get<int>(), d.at(2).at(1).get<int>()};
            door.at_b = Point{d.at(3).at(0).get<int>(), d.at(3).at(1).get<int>()};
            P.doors.push_back(std::move(door));
        }
    } catch (const json::exception&) {
        P = Plan{};
        return false;
    }
    P.ok = true;
    derive_geom();
    derive_line();
    derive_flight();
    derive_next();
    return true;
}

bool loaded() { return P.ok; }
Box world() { return P.world; }
int facade() { return P.face; }
Box landing() { return P.landing; }
Box stairs() { return P.stairs; }
const std::vector<Geom>& geom() { return P.geom; }
const std::vector<Door>& doors() { return P.doors; }

const Geom* of(std::string_view key) {
    for (const auto& g : P.geom)
        if (g.key == key) return &g;
    return nullptr;
}

// levelOf: the landing isn't a room, but it is upstairs.
Level level_of(std::string_view key) {
    if (key == "landing") return Level::Upper;
    auto l = P.level.find(key);
    return l == P.level.end() ? Level::Ground : l->second;
}

const Piece* piece(std::string_view key) {
    auto p = P.pieces.find(key);
    return p == P.pieces.end() ? nullptr : &p->second;
}

const std::vector<Placed>& layout(std::string_view room) {
    auto l = P.layout.find(room);
    return l == P.layout.end() ? kNone : l->second;
}

Box atlas(std::string_view name) {
    auto a = P.atlases.find(name);
    return a == P.atlases.end() ? Box{} : a->second;
}

// stationsOf: every piece's stations, in absolute art pixels.
std::vector<std::pair<State, Point>> stations_of(std::string_view room) {
    std::vector<std::pair<State, Point>> out;
    for (const auto& q : layout(room))
        if (const Piece* p = piece(q.piece))
            for (const auto& s : p->stations) out.emplace_back(s.state, Point{q.x + s.dx, q.y + s.dy});
    return out;
}

// freeFloor: a grid over the room's floor, rows bottom-up every 12, columns every 14, off every
// footprint grown by 3.
const std::vector<Point>& free_floor(std::string_view room) {
    if (auto c = P.free.find(room); c != P.free.end()) return c->second;
    auto f = P.floors.find(room);
    if (f == P.floors.end()) return kNoPoints;
    const auto [x0, y0, x1, y1] = f->second;
    std::vector<Box> foots;
    for (const auto& q : layout(room))
        if (const Piece* p = piece(q.piece); p && p->foot.w)
            foots.push_back(Box{q.x + p->foot.x, q.y + p->foot.y, p->foot.w, p->foot.h});
    std::vector<Point> pts;
    for (int y = y1 - 6; y >= y0 + 10; y -= 12)
        for (int x = x0 + 8; x < x1 - 8; x += 14) {
            const bool blocked = std::any_of(foots.begin(), foots.end(), [&](const Box& b) {
                return x >= b.x - 3 && x < b.x + b.w + 3 && y >= b.y - 3 && y < b.y + b.h + 3;
            });
            if (!blocked) pts.push_back(Point{x, y});
        }
    return P.free.emplace(std::string(room), std::move(pts)).first->second;
}

const std::vector<Point>& line_spots() { return P.line; }
const std::vector<Point>& flight() { return P.flight; }

std::string_view next_room(std::string_view from, Dir d) {
    auto n = P.next.find(from);
    return n == P.next.end() ? std::string_view{} : std::string_view{n->second[static_cast<size_t>(d)]};
}

// way_to -- the cats' route through the doorways -- arrives with walking. A static frame has nobody
// walking, and a route that has never been checked against the page's wayTo would only look finished.

}  // namespace catio::manor
