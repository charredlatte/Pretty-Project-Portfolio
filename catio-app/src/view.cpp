// view.cpp -- the camera, where every cat stands this frame, and the draw list.
//
// build() is render()'s placement in catio/index.html, ported line for line; world() is the page's
// layering -- #world's meadow, the plates, drawFurniture's z formula, dress()'s sprite arithmetic -- as
// one sorted list. Neither draws: they compute, so both can be tested without a window.

#include "catio/view.h"

#include <algorithm>
#include <cmath>
#include <limits>
#include <set>

namespace catio::view {
namespace {

constexpr int kZup = 4000;        // ZUP: the whole upper floor sits above the ground's dim
constexpr float kTouch = 44.f;    // ui::kTouch, the audit's minimum; view cannot include ui.h (ui includes view)

int z_of(manor::Level l) { return l == manor::Level::Upper ? kZup : 0; }

// SPR, and the CSS that animates each sheet: which sheet, which row, the frame's size, the feet inside it
// (always the bottom row; off-centre for idle and meow), and steps(n) over a period.
struct Spr {
    art::Id sheet;
    int row, w, h, ax, ay, frames;
    double secs;
};
Spr spr(Mood m) {
    switch (m) {
        case Mood::Idle: return {art::Id::MochiIdle, 0, 32, 32, 12, 32, 10, 1.25};
        case Mood::Box: return {art::Id::MochiBox, 0, 32, 32, 16, 32, 4, 0.8};
        case Mood::Cry: return {art::Id::Pochi, 0, 64, 64, 32, 64, 4, 0.7};
        case Mood::Meow: return {art::Id::Pochi, 64, 64, 64, 25, 64, 2, 0.5};
        case Mood::Sleep: break;
    }
    return {art::Id::Pochi, 128, 64, 64, 32, 64, 4, 2.4};
}

// STATE: which station a mood goes to.
manor::State station_for(Mood m) {
    switch (m) {
        case Mood::Meow: return manor::State::Needs;
        case Mood::Cry: return manor::State::Fail;
        case Mood::Box: return manor::State::Review;
        case Mood::Idle: return manor::State::Work;
        case Mood::Sleep: break;
    }
    return manor::State::Sleep;
}

// margin(): keep the house clear of the screen's frame -- the frame's 6 art pixels at --u (2 CSS px, 1 on a
// phone), and 8 CSS px more.
int margin(Stage s) { return (6 * (s.narrow() ? 1 : 2) + 8) * std::max(1, s.css); }

int lowest(Stage s) {
    const manor::Box w = manor::world();
    const int m = margin(s);
    if (!w.w || !w.h) return 1;
    return std::max(1, static_cast<int>(std::floor(std::min(double(s.w - 2 * m) / w.w, double(s.h - 2 * m) / w.h))));
}

Blit cat_blit(const Spot& at, double now) {
    const Spr s = spr(at.mood);
    int f = 0;
    if (s.frames > 1 && now > 0) {
        const double t = now / s.secs;
        f = std::min(s.frames - 1, static_cast<int>((t - std::floor(t)) * s.frames));
    }
    Blit b;
    b.sheet = s.sheet;
    b.coat = at.coat;
    // dress(): the feet at the spot, the frame 1:1 in world pixels
    b.src = draw::Rect{float(f * s.w), float(s.row), float(s.w), float(s.h)};
    b.dst = draw::Rect{float(at.at.x * 2 - s.ax), float(at.at.y * 2 - s.ay), float(s.w), float(s.h)};
    b.z = z_of(manor::level_of(at.room)) + 1000 + at.at.y * 2;
    if (at.queue_place >= 0) {
        // .cat[data-line] { clip-path: inset(0 14px 0 6px) } -- written for the hit area, but it clips
        // the queued cat's picture too, so the line looks as it does in the page
        b.src.x += 6, b.src.w -= 20;
        b.dst.x += 6, b.dst.w -= 20;
    }
    return b;
}

}  // namespace

Blit blit_of(const Spot& s, double now) { return cat_blit(s, now); }

// ---- the camera ----------------------------------------------------------------------------------

Cam fit(manor::Box what, Stage stage) {
    Cam c;
    const int m = margin(stage);
    if (what.w <= 0 || what.h <= 0) return c;
    c.u = std::max(1, static_cast<int>(std::floor(std::min(double(stage.w - 2 * m) / what.w, double(stage.h - 2 * m) / what.h))));
    c.tx = std::round((stage.w - what.w * c.u) / 2.f - what.x * c.u);
    c.ty = std::round((stage.h - what.h * c.u) / 2.f - what.y * c.u);
    return c;
}

// clampCam: the zoom between the whole grounds and twice that (at least 8), and never past the meadow.
Cam clamp(Cam c, Stage stage) {
    const int lo = lowest(stage), hi = std::max(lo * 2, 8);
    c.u = std::clamp(c.u, lo, hi);
    const manor::Box w = manor::world();
    const float m = float(margin(stage));
    auto axis = [&](float t, int view, int world) {
        return world <= view ? std::round((view - world) / 2.f) : std::min(m, std::max(float(view - world) - m, t));
    };
    c.tx = axis(c.tx, stage.w, w.w * c.u);
    c.ty = axis(c.ty, stage.h, w.h * c.u);
    return c;
}

// zoomAt: whole steps, and the point under her finger stays under it.
Cam zoom_by(Cam c, int du, float at_x, float at_y, Stage stage) {
    const int lo = lowest(stage), hi = std::max(lo * 2, 8);
    const int u = std::clamp(c.u + du, lo, hi);
    const float k = float(u) / float(c.u);
    c.tx = std::round(at_x - (at_x - c.tx) * k);
    c.ty = std::round(at_y - (at_y - c.ty) * k);
    c.u = u;
    return clamp(c, stage);
}

Cam pan_by(Cam c, float dx, float dy, Stage stage) {
    c.tx = std::round(c.tx + dx);
    c.ty = std::round(c.ty + dy);
    return clamp(c, stage);
}

draw::Pt to_screen(const Cam& c, manor::Point p) { return {p.x * float(c.u) + c.tx, p.y * float(c.u) + c.ty}; }

manor::Point to_world(const Cam& c, float sx, float sy) {
    return {static_cast<int>(std::floor((sx - c.tx) / c.u)), static_cast<int>(std::floor((sy - c.ty) / c.u))};
}

// roomInView: the room on this floor that fills the view -- one covering most of it, or one shown nearly whole
// that fills it across or down -- scored as the page scores it, so both settle on the same room.
std::string room_in_view(const Cam& c, Stage stage) {
    const double vx = -c.tx / c.u, vy = -c.ty / c.u, vw = double(stage.w) / c.u, vh = double(stage.h) / c.u;
    std::string best;
    double score = 0;
    for (const auto& g : manor::geom()) {
        if (g.level != c.floor) continue;
        const auto& b = g.box;
        const double iw = std::max(0.0, std::min(b.x + b.w + 0.0, vx + vw) - std::max(b.x + 0.0, vx));
        const double ih = std::max(0.0, std::min(b.y + b.h + 0.0, vy + vh) - std::max(b.y + 0.0, vy));
        const double cover = iw * ih / (vw * vh), shown = iw * ih / (double(b.w) * b.h), fills = std::max(iw / vw, ih / vh);
        const double sc = cover >= 0.6 ? 1 + cover : shown >= 0.8 && fills >= 0.6 ? cover + 0.5 : 0;
        if (sc > score) score = sc, best = g.key;
    }
    return best;
}

manor::Box padded(std::string_view room) {
    const manor::Geom* g = manor::of(room);
    if (!g) return manor::world();
    constexpr int p = 6;
    return {g->box.x - p, g->box.y - p, g->box.w + 2 * p, g->box.h + 2 * p};
}

// ---- where everyone stands -----------------------------------------------------------------------

Scene build(const House& h, manor::Level floor) {
    Scene s;
    const auto line = h.queue();
    std::set<std::string> queued;
    for (const Cat* c : line) queued.insert(c->id);
    const auto& places = manor::line_spots();
    const std::string qroom = h.queen_room();

    for (const auto& g : manor::geom()) {
        if (g.level != floor) continue;
        const auto st = manor::stations_of(g.key);
        const auto& open = manor::free_floor(g.key);
        std::vector<manor::Point> taken;
        if (g.queen && g.key == qroom) taken.push_back(*g.queen);   // her seat is hers
        if (g.key == "hall")                                         // the line's places are the line's
            for (size_t i = 0; i < std::min(line.size(), places.size()); ++i) taken.push_back(places[i]);
        auto clear = [&](manor::Point p) {
            return std::none_of(taken.begin(), taken.end(), [&](manor::Point t) {
                return std::abs(t.x - p.x) < 22 && std::abs(t.y - p.y) < 14;   // a cat's width apart
            });
        };
        const double mx = g.box.x + g.box.w / 2.0, my = g.box.y + g.box.h / 2.0;
        std::vector<const Cat*> pile;
        for (const auto& c : h.cats()) {
            if (c.room != g.key || queued.count(c.id)) continue;
            // its state's station, if one is free; else the free floor nearest one (or the room's middle)
            const manor::State want = station_for(c.mood);
            std::vector<manor::Point> mine;
            for (const auto& [state, p] : st) if (state == want) mine.push_back(p);
            std::optional<manor::Point> spot;
            for (const auto& p : mine) if (clear(p)) { spot = p; break; }
            if (!spot) {
                // a cat that needs her with no mat to wait on waits at the front of the room
                const double ax = mine.empty() ? mx : mine[0].x;
                const double ay = mine.empty() ? (want == manor::State::Needs ? g.box.y + g.box.h - 16 : my) : mine[0].y;
                double best = std::numeric_limits<double>::infinity();
                for (const auto& p : open) {
                    if (!clear(p)) continue;
                    const double d = std::hypot(p.x - ax, p.y - ay);
                    if (d < best) best = d, spot = p;   // the first of the nearest, as a stable sort finds it
                }
            }
            if (!spot) { pile.push_back(&c); continue; }
            taken.push_back(*spot);
            s.cats.push_back(Spot{&c, c.mood, c.coat, *spot, g.key});
        }
        if (!pile.empty()) {
            // curled up together on the last spot taken, or the room's middle (a half pixel rounds down)
            const manor::Point at = taken.empty() ? manor::Point{int(std::floor(mx)), int(std::floor(my))} : taken.back();
            s.piles.push_back(Pile{pile, at, g.key});
        }
    }

    // the line at the front door: upstairs cats included, so it is the ground floor's
    if (floor == manor::Level::Ground && !places.empty()) {
        for (size_t i = 0; i < line.size() && i < places.size(); ++i) {
            Spot sp{line[i], line[i]->mood, line[i]->coat, places[i], "hall"};
            sp.queue_place = static_cast<int>(i);
            s.cats.push_back(sp);
        }
        if (line.size() > places.size())
            s.piles.push_back(Pile{std::vector<const Cat*>(line.begin() + places.size(), line.end()), places.back(), "hall"});
    }

    // the queen, on her seat
    if (const manor::Geom* qg = manor::of(qroom); qg && qg->queen && qg->level == floor) {
        s.queen = Spot{nullptr, h.queen_mood(), h.queen().coat, *qg->queen, qroom};
    }

    // the minimap's pips: a cat that needs her counts where it stands
    for (const Cat* c : h.needing()) s.needing[c->mood == Mood::Meow ? std::string("hall") : c->room]++;
    return s;
}

// ---- what to draw --------------------------------------------------------------------------------

draw::Rect world_rect() {
    const manor::Box w = manor::world();
    return draw::Rect{0, 0, float(w.w * 2), float(w.h * 2)};
}

std::vector<Blit> world(const Scene& s, manor::Level floor, double now) {
    std::vector<Blit> out;
    const draw::Rect all = world_rect();
    const manor::Box w = manor::world();

    // #world's own background: the meadow, tiled at twice its 112 x 32
    for (float y = 0; y < all.h; y += 64)
        for (float x = 0; x < all.w; x += 224) {
            Blit b;
            b.sheet = art::Id::Meadow;
            b.src = draw::Rect{0, 0, 112, 32};
            b.dst = draw::Rect{x, y, 224, 64};
            b.z = -100;
            out.push_back(b);
        }
    // the plates: the grounds, then the ground floor, each the whole scene doubled
    for (art::Id plate : {art::Id::Decor, art::Id::House}) {
        Blit b;
        b.sheet = plate;
        b.src = draw::Rect{0, 0, float(w.w), float(w.h)};
        b.dst = all;
        b.z = -50;
        out.push_back(b);
    }

    // drawFurniture: every room, and the landing. From the ground floor nothing upstairs shows; from the
    // upper floor the ground's furniture stays, under the dim, which is what makes it read as below.
    std::vector<std::string> rooms;
    for (const auto& g : manor::geom()) rooms.push_back(g.key);
    rooms.push_back("landing");
    for (const auto& k : rooms) {
        const manor::Level lv = manor::level_of(k);
        if (floor == manor::Level::Ground && lv == manor::Level::Upper) continue;
        const int zk = z_of(lv);
        for (const auto& q : manor::layout(k)) {
            const manor::Piece* p = manor::piece(q.piece);
            if (!p) continue;
            const int bottom = (q.y + p->cell.h) * 2;
            Blit b;
            b.sheet = p->atlas == "cc" ? art::Id::Furniture : art::Id::FurnitureLicensed;
            b.src = draw::Rect{float(p->cell.x), float(p->cell.y), float(p->cell.w), float(p->cell.h)};
            b.dst = draw::Rect{float(q.x * 2), float(q.y * 2), float(p->cell.w * 2), float(p->cell.h * 2)};
            b.z = zk + (p->layer == manor::Layer::Rug    ? 900
                        : p->layer == manor::Layer::Wall ? 950
                        : p->layer == manor::Layer::Top  ? 1001 + bottom
                                                         : 1000 + bottom);
            out.push_back(b);
        }
    }

    // the upper floor: the ground below dimmed, then its own plate, then everything of its own lifted
    if (floor == manor::Level::Upper) {
        Blit dim;
        dim.fill = true;
        dim.dst = all;
        dim.colour = draw::Colour{22, 34, 20, 128};   // .dim: rgba(22, 34, 20, .5)
        dim.z = 3850;
        out.push_back(dim);
        Blit plate;
        plate.sheet = art::Id::HouseUpper;
        plate.src = draw::Rect{0, 0, float(w.w), float(w.h)};
        plate.dst = all;
        plate.z = 3900;
        out.push_back(plate);
    }

    // the cats, after the furniture: on an exact tie the page paints #cats after #props, so a cat wins
    for (const auto& c : s.cats) out.push_back(cat_blit(c, now));
    for (const auto& p : s.piles) out.push_back(cat_blit(Spot{p.cats[0], p.cats[0]->mood, p.cats[0]->coat, p.at, p.room}, now));
    if (s.queen) out.push_back(cat_blit(*s.queen, now));

    std::stable_sort(out.begin(), out.end(), [](const Blit& a, const Blit& b) { return a.z < b.z; });
    return out;
}

// ---- what is under her finger --------------------------------------------------------------------

Hit pick(const Scene& s, const Cam& c, Stage stage, float sx, float sy, bool coarse) {
    const float k = c.u / 2.f;   // world pixels to screen pixels
    const float touch = kTouch * std::max(1, stage.css);
    auto screen = [&](draw::Rect r) {
        draw::Rect o{r.x * k + c.tx, r.y * k + c.ty, r.w * k, r.h * k};
        if (coarse) {
            if (o.w < touch) o.x -= (touch - o.w) / 2, o.w = touch;
            if (o.h < touch) o.y -= (touch - o.h) / 2, o.h = touch;
        }
        return o;
    };
    auto art_box = [&](manor::Box b) { return draw::Rect{float(b.x * 2), float(b.y * 2), float(b.w * 2), float(b.h * 2)}; };
    auto inside = [&](draw::Rect r) { return sx >= r.x && sx < r.x + r.w && sy >= r.y && sy < r.y + r.h; };

    // #cats, over #hits: the topmost first
    struct Cand { Thing what; std::string key; draw::Rect box; int z; };
    std::vector<Cand> cands;
    for (const auto& sp : s.cats) { const Blit b = cat_blit(sp, 0); cands.push_back({Thing::Cat, sp.cat->id, screen(b.dst), b.z}); }
    for (const auto& p : s.piles) {
        const Blit b = cat_blit(Spot{p.cats[0], p.cats[0]->mood, p.cats[0]->coat, p.at, p.room}, 0);
        cands.push_back({Thing::Pile, p.room, screen(b.dst), b.z});
    }
    if (s.queen) { const Blit b = cat_blit(*s.queen, 0); cands.push_back({Thing::Queen, s.queen->room, screen(b.dst), b.z}); }
    std::stable_sort(cands.begin(), cands.end(), [](const Cand& a, const Cand& b) { return a.z > b.z; });
    for (const auto& cd : cands) if (inside(cd.box)) return Hit{cd.what, cd.key, cd.box};

    // #hits: the stair (z 4990, over every room), then the cabinets and the litter box, then the rooms
    if (const draw::Rect r = screen(art_box(manor::stairs())); inside(r)) return Hit{Thing::Stairs, "stairs", r};
    for (const auto& g : manor::geom()) {
        if (g.level != c.floor) continue;
        if (g.litter) if (const draw::Rect r = screen(art_box(*g.litter)); inside(r)) return Hit{Thing::Litter, g.key, r};
        if (g.cabinet) if (const draw::Rect r = screen(art_box(*g.cabinet)); inside(r)) return Hit{Thing::Cabinet, g.key, r};
    }
    for (const auto& g : manor::geom()) {
        if (g.level != c.floor) continue;
        const draw::Rect r{g.box.x * 2 * k + c.tx, g.box.y * 2 * k + c.ty, g.box.w * 2 * k, g.box.h * 2 * k};
        if (inside(r)) return Hit{Thing::Room, g.key, r};
    }
    return Hit{};
}

// Walks -- cats walking through the doorways and up the stair -- arrive with the loop. A single frame has
// nobody walking.

}  // namespace catio::view
