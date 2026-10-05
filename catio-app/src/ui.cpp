// ui.cpp -- what is drawn over the house, and what a press on it does.
//
// The first half is the content: showTip(), roomMenu(), houseMenu(), pileMenu(), queenMenu(), catMenu(),
// summary(), queenLine() and placeMenu() from catio/index.html, line for line, into plain data. The
// second half lays that data out in the page's own CSS lengths (every px times the stage's css, every
// --u the interface's u) and draws it from the packs: the Sprout Lands panel, button, bubble, divider,
// faces and pointer for everything that talks about cats and rooms, and SC_siosio's Pastel pieces,
// smooth, for the map panel that works the camera.

#include "catio/ui.h"

#include <algorithm>
#include <cmath>
#include <map>
#include <memory>
#include <optional>

#include "catio/manor.h"
#include "internal.h"

namespace catio::ui {

using draw::Colour;
using draw::Pt;
using draw::Rect;
using view::Thing;

namespace {

// ---- the words -------------------------------------------------------------------------------------

constexpr std::string_view kCredits =
    "Rooms by Marie Pepo · Cats by ToffeeCraft · Garden by Heosphorus and rowdy41 · Stonework by Cainos · "
    "Interface and flowers by Cup Nooble · Forest and tiles from Little Dreamyland by Starmixu & Utaskuas · "
    "Game UI Pack created by SC_siosio";

constexpr std::string_view kNotYet = "Not in the app yet: the café in a browser has it.";

int face_of(Mood m) { return static_cast<int>(m); }   // faces.png follows MOODS: cry, meow, box, idle, sleep
constexpr int kHeartEyes = 5;

bool needs(const Cat* c) { return info(c->mood).needs; }

// where a cat is now: a cat waiting on her is in the line at the front door, whatever its room
std::string where_is(const Cat* c) { return c->mood == Mood::Meow ? "hall" : c->room; }

// VIEW.cats: every cat that is drawn somewhere, which is all of them but the ones napping in the attic
std::vector<const Cat*> shown(const Frame& f) {
    std::vector<const Cat*> out;
    if (!f.house) return out;
    for (const Cat& c : f.house->cats()) {
        const bool attic = f.scene && std::find(f.scene->attic.begin(), f.scene->attic.end(), &c) != f.scene->attic.end();
        if (!attic) out.push_back(&c);
    }
    return out;
}

std::vector<const Cat*> in_room(const std::vector<const Cat*>& cats, std::string_view k) {
    std::vector<const Cat*> out;
    for (const Cat* c : cats) if (c->room == k) out.push_back(c);
    return out;
}

std::vector<const Cat*> need_on(const std::vector<const Cat*>& cats, manor::Level f) {
    std::vector<const Cat*> out;
    for (const Cat* c : cats) if (needs(c) && manor::level_of(where_is(c)) == f) out.push_back(c);
    return out;
}

manor::Level other(manor::Level f) { return f == manor::Level::Upper ? manor::Level::Ground : manor::Level::Upper; }

std::string plural(int n, std::string_view one, std::string_view many) {
    return std::to_string(n) + " " + std::string(n == 1 ? one : many);
}

std::string join(const std::vector<std::string>& parts, std::string_view sep) {
    std::string out;
    for (const auto& p : parts) {
        if (p.empty()) continue;
        if (!out.empty()) out += sep;
        out += p;
    }
    return out;
}

std::string homework_words(const House& h) {
    const int u = int(h.homework("unblock").size()), l = int(h.homework("litterbox").size()), d = int(h.homework("decision").size());
    return join({u ? plural(u, "quiz", "quizzes") + " to hand in" : "", l ? plural(l, "note to sort", "notes to sort") : "",
                 d ? plural(d, "decision", "decisions") : ""}, ", ");
}

std::vector<const Note*> pinned(const Queen& q) {
    std::vector<const Note*> out;
    for (const Note& n : q.keeps) if (n.pinned) out.push_back(&n);
    return out;
}

std::string_view state_word(QueenState s) { return s == QueenState::Away ? "away" : s == QueenState::Busy ? "answering" : "here"; }

Row cat_row(const Cat* c) {
    Row r;
    r.id = c->id;
    r.name = c->name;
    r.text = !c->ask.empty() ? c->ask : !c->doing.empty() ? c->doing : c->title;
    r.face = face_of(c->mood);
    return r;
}

Block cat_rows(const std::vector<const Cat*>& cats, size_t max) {
    Block b;
    b.kind = Block::Kind::Cats;
    for (size_t i = 0; i < cats.size() && i < max; ++i) b.rows.push_back(cat_row(cats[i]));
    b.more = cats.size() > max ? int(cats.size() - max) : 0;
    return b;
}

Item mi(std::string label, Action a, std::string arg = {}, std::string aside = {}) {
    Item i;
    i.label = std::move(label);
    i.action = a;
    i.arg = std::move(arg);
    i.aside = std::move(aside);
    return i;
}

}  // namespace

// ---- the content -----------------------------------------------------------------------------------

std::string summary(const std::vector<const Cat*>& cats) {
    static const std::pair<Mood, std::string_view> kWords[] = {
        {Mood::Cry, "upset"}, {Mood::Meow, "meowing"}, {Mood::Box, "to review"}, {Mood::Idle, "at work"}, {Mood::Sleep, "asleep"}};
    std::vector<std::string> out;
    for (const auto& [m, w] : kWords) {
        const auto n = std::count_if(cats.begin(), cats.end(), [m = m](const Cat* c) { return c->mood == m; });
        if (n) out.push_back(std::to_string(n) + " " + std::string(w));
    }
    return out.empty() ? "no cats" : join(out, ", ");
}

std::string ago(std::int64_t t, std::int64_t now) {
    if (!t) return "";
    const long m = std::lround(double(now - t) / 60000.0);
    if (m < 1) return "just now";
    if (m < 60) return std::to_string(m) + " min ago";
    const long h = std::lround(m / 60.0);
    if (h < 24) return std::to_string(h) + " h ago";
    const long d = std::lround(h / 24.0);
    return d == 1 ? "yesterday" : std::to_string(d) + " days ago";
}

std::string queen_line(const House& h) {
    const QueenState st = h.queen_state();
    const auto pin = pinned(h.queen());
    if (!pin.empty() && st != QueenState::Busy) return pin[0]->text;
    if (st == QueenState::Away) return "Away: start her runner on your PC to talk to her.";
    if (st == QueenState::Busy) return "Answering…";
    // a cat waiting on her answer comes first, then what the cats brought her, then the notes and decisions
    const bool unblock = !h.homework("unblock").empty();
    const int work = int(h.homework().size()), unread = int(h.handoffs().size());
    if (work && (unblock || !unread)) return "Homework: " + homework_words(h) + ".";
    if (unread) return "Holding " + std::to_string(unread) + (unread == 1 ? " thing" : " things") + " for you.";
    return "Here. Talk to her.";
}

std::vector<const Cat*> urgent_first(const std::vector<const Cat*>& cats) {
    std::vector<const Cat*> out;
    for (const Cat* c : cats) if (needs(c)) out.push_back(c);
    std::stable_sort(out.begin(), out.end(), [](const Cat* a, const Cat* b) { return a->mood < b->mood; });
    return out;
}

Tip tip_for(const Frame& f, const view::Hit& h) {
    Tip t;
    if (!f.house || !f.cam) return t;
    const House& H = *f.house;
    const auto cats = shown(f);
    switch (h.what) {
        case Thing::Room:
        case Thing::Cabinet: {
            t.name = H.room(h.key).name;
            if (!H.open(h.key)) t.small = "closed";
            else {
                t.need = urgent_first(in_room(cats, h.key));
                if (t.need.empty()) t.small = summary(in_room(cats, h.key));
            }
            break;
        }
        case Thing::Stairs: {
            const manor::Level to = other(f.cam->floor);
            t.name = to == manor::Level::Upper ? "Upstairs" : "Downstairs";
            t.need = urgent_first(need_on(cats, to));
            break;
        }
        case Thing::Queen:
            t.name = H.queen().name;
            t.small = "queen";
            t.says = queen_line(H);
            break;
        case Thing::Pile: {
            if (!f.scene) break;
            for (const auto& p : f.scene->piles)
                if (p.room == h.key) t.name = std::to_string(p.cats.size()) + " cats";
            break;
        }
        case Thing::Litter: {
            const int n = int(H.homework("litterbox").size());
            t.name = "The litter box";
            t.says = n ? plural(n, "note", "notes") + " to sort" : "Nothing to sort.";
            break;
        }
        case Thing::Cat: {
            const Cat* c = H.cat(h.key);
            if (!c) break;
            t.name = c->name;
            t.small = std::string(info(c->mood).brief);
            t.says = join({info(c->mood).needs ? c->ask : "", c->waiting ? plural(c->waiting, "file", "files") + " waiting" : ""}, " · ");
            break;
        }
        default: break;
    }
    return t;
}

Menu menu_for(const Frame& f, Thing kind, std::string_view key, bool adding) {
    Menu m;
    m.kind = kind;
    m.key = std::string(key);
    if (!f.house || !f.cam) return m;
    const House& H = *f.house;
    const auto cats = shown(f);
    auto rule = [] { Block b; b.kind = Block::Kind::Rule; return b; };
    auto list = [](std::vector<Item> items) {
        Block b;
        b.kind = Block::Kind::List;
        b.items = std::move(items);
        if (!b.items.empty()) b.items.front().primary = true;
        return b;
    };
    auto sub = [](std::string text) { Block b; b.kind = Block::Kind::Sub; b.text = std::move(text); return b; };
    auto look = [&](const std::string& room) {
        return f.cam->focus == room ? mi("Whole house", Action::WholeHouse) : mi("Look in", Action::LookIn, room);
    };

    if (kind == Thing::Room) {
        const Room& r = H.room(key);
        const auto here = in_room(cats, key);
        const auto needing = urgent_first(here);
        m.title = r.name;
        if (!H.open(key)) {
            m.sub = "Closed";
            m.blocks = {rule(), list({mi("Open this room", Action::OpenRoom, m.key), mi("Edit rooms", Action::OpenEditRooms, m.key)})};
            return m;
        }
        m.sub = !r.blurb.empty() ? r.blurb : !here.empty() ? summary(here) : "No cats in here yet.";
        m.need = needing;
        if (!needing.empty()) m.blocks.push_back(cat_rows(needing, 3));
        // the queen speaks only when she has something to say
        if (const auto pin = pinned(H.queen()); !pin.empty()) {
            Block q;
            q.kind = Block::Kind::Ask;
            q.crown = true;
            q.text = pin[0]->text;
            q.action = Action::OpenQueen;
            q.arg = "talk";
            m.blocks.push_back(q);
        }
        m.blocks.push_back(rule());
        if (adding)   // New session is claude.ai's alone (VIA_GATEWAY): this app adopts a chat
            m.blocks.push_back(list({mi("Adopt a chat", Action::Adopt, m.key), mi("Back", Action::Back, m.key)}));
        else {
            std::vector<Item> items{look(m.key)};
            const manor::Geom* g = manor::of(key);
            if (key == "brain") items.push_back(mi("The brain", Action::OpenBrain));
            if (g && g->cabinet) items.push_back(mi("Files", Action::OpenCabinet, m.key));
            items.push_back(mi(key == "brain" ? "Choose files" : "Add files", Action::AddFiles, key == "brain" ? "" : "room:" + m.key));
            items.push_back(mi("Add a cat", Action::AddACat, m.key));
            items.push_back(mi("Edit room", Action::OpenEditRooms, m.key));
            m.blocks.push_back(list(std::move(items)));
        }
        return m;
    }

    if (kind == Thing::House) {
        // the brand above it is the title and carries the badge, so the menu starts with how the cats reach her
        const int attic = f.scene ? int(f.scene->attic.size()) : 0;
        std::string line = join({f.live, attic ? std::to_string(attic) + " napping in the attic" : ""}, " · ");
        if (!cats.empty()) {
            std::string s = summary(cats);
            if (!s.empty()) s[0] = char(std::toupper(static_cast<unsigned char>(s[0])));
            line += ". " + s + ".";
        }
        m.blocks.push_back(sub(line));
        std::vector<Item> items;
        if (const int hw = int(H.homework().size())) items.push_back(mi("Homework", Action::OpenHomework, "", std::to_string(hw) + " waiting"));
        items.push_back(mi("The brain", Action::OpenBrain));
        items.push_back(mi("House rules", Action::OpenRules));
        items.push_back(mi("Edit rooms", Action::OpenEditRooms, f.cam->focus));
        items.push_back(mi("The look", Action::OpenLook));
        items.push_back(mi("Set up again…", Action::OpenSetup));
        if (attic) items.push_back(mi("Bring them down", Action::BringDown));
        items.push_back(mi("Check now", Action::CheckNow));
        Item sound = mi("Sound off", Action::Sound);   // the meow when a cat starts needing her: not in the app yet
        sound.toggle = 0;
        items.push_back(sound);
        Item still = mi("Still cats", Action::StillCats);
        still.toggle = f.still ? 1 : 0;
        items.push_back(still);
        m.blocks.push_back(list(std::move(items)));
        Block foot;
        foot.kind = Block::Kind::Foot;
        foot.text = std::string(kCredits);
        m.blocks.push_back(foot);
        m.title = H.name();   // never drawn: the brand is its title
        return m;
    }

    if (kind == Thing::Pile) {
        if (!f.scene) return m;
        for (const auto& p : f.scene->piles) {
            if (p.room != key) continue;
            m.title = std::to_string(p.cats.size()) + " cats curled up";
            m.sub = H.room(key).name;
            m.need = urgent_first(p.cats);
            m.blocks = {cat_rows(p.cats, 5), rule(), list({mi("See them all", Action::OpenPile, m.key)})};
        }
        return m;
    }

    if (kind == Thing::Queen) {
        const Queen& q = H.queen();
        const QueenState st = H.queen_state();
        const auto pin = pinned(q);
        m.title = q.name;
        m.crown = true;
        m.sub = "Queen of the house · " + std::string(state_word(st));
        Block line;
        line.text = queen_line(H);
        if (!H.handoffs().empty() || (!pin.empty() && st != QueenState::Busy)) line.kind = Block::Kind::Ask, line.need = true;
        else line.kind = Block::Kind::Sub;
        m.blocks.push_back(line);
        // the headline is already her top pinned note, so the list picks up from the next one
        std::vector<Row> rest;
        for (size_t i = pin.empty() ? 0 : 1; i < q.keeps.size(); ++i) {
            Row r;
            r.text = q.keeps[i].text;
            r.pinned = q.keeps[i].pinned;
            rest.push_back(r);
        }
        if (!rest.empty()) {
            Block k;
            k.kind = Block::Kind::Keeps;
            k.more = rest.size() > 3 ? int(rest.size() - 3) : 0;
            rest.resize(std::min<size_t>(rest.size(), 3));
            k.rows = std::move(rest);
            m.blocks.push_back(k);
        }
        m.blocks.push_back(rule());
        m.blocks.push_back(list({mi("Talk to her", Action::OpenQueen, "talk"), mi("What she keeps", Action::OpenQueen, "keeps"), look(m.key)}));
        return m;
    }

    if (kind == Thing::Cat) {
        const Cat* c = H.cat(key);
        if (!c) return m;
        m.title = c->name;
        m.face = face_of(c->mood);
        m.sub = join({c->project_name, H.room(c->room).name, ago(c->updated, f.clock_ms)}, " · ");
        if (!c->ask.empty()) {
            Block a;
            a.kind = Block::Kind::Ask;
            a.face = face_of(c->mood);
            a.text = c->ask;
            m.blocks.push_back(a);
        } else
            m.blocks.push_back(sub(!c->doing.empty() ? c->doing : c->title));
        if (c->waiting) m.blocks.push_back(sub(plural(c->waiting, "file", "files") + " from the brain"));
        m.blocks.push_back(rule());
        std::vector<Item> items;
        if (!c->link.empty()) items.push_back(mi(c->adopted ? "Open chat" : "Open", Action::OpenLink, c->link));
        items.push_back(mi(c->adopted ? "Details" : "Talk", Action::OpenCat, c->id));
        items.push_back(mi("Add files", Action::AddFiles, "cat:" + c->id));
        if (f.cam->focus != c->room) items.push_back(mi("Look in", Action::LookIn, c->room));
        m.blocks.push_back(list(std::move(items)));
        return m;
    }
    return m;
}

draw::Pt place_menu(const view::Stage& st, Thing kind, Rect a, Pt size, Rect p, float hud_bottom) {
    const float k = float(std::max(1, st.css));
    const float W = float(st.w), H = float(st.h), mw = size.x, mh = size.y, g = 12 * k;
    float left, top;
    if (kind == Thing::House) {
        left = a.x;
        top = hud_bottom + 8 * k;
    } else {
        // beside it on the right, else on the left; on a narrow screen below it, else above it, so the cat
        // itself stays tappable; a room that fills the screen gets the menu in its corner
        left = a.x + a.w + g;
        top = kind == Thing::Room ? a.y : a.y + a.h / 2 - mh / 2;
        if (left + mw > W - g) left = a.x - mw - g;
        if (left < g) {
            left = std::max(g, std::min(W - mw - g, a.x + a.w / 2 - mw / 2));
            if (kind != Thing::Room) top = a.y + a.h + g + mh <= H - g ? a.y + a.h + g : a.y - mh - g;
            else left = W - mw - g;
        }
    }
    left = std::max(g, std::min(std::max(g, W - mw - g), left));
    top = std::max(g, std::min(std::max(g, H - mh - g), top));
    // never under the map panel: to its left, below it or above it, whichever moves it least without covering
    // what it belongs to
    const float P[4] = {p.x - g, p.y - g, p.x + p.w + g, p.y + p.h + g};
    auto under = [&](float l, float t) { return l < P[2] && l + mw > P[0] && t < P[3] && t + mh > P[1]; };
    if (p.w > 0 && under(left, top)) {
        auto fits = [&](Pt c) { return c.x >= g && c.y >= g && c.y + mh <= H - g; };
        auto on_it = [&](Pt c) { return c.x < a.x + a.w && c.x + mw > a.x && c.y < a.y + a.h && c.y + mh > a.y; };
        std::vector<Pt> ok, clear;
        for (Pt c : {Pt{P[0] - mw, top}, Pt{left, P[3]}, Pt{left, P[1] - mh}}) if (fits(c)) ok.push_back(c);
        for (Pt c : ok) if (!on_it(c)) clear.push_back(c);
        auto& from = clear.empty() ? ok : clear;
        if (!from.empty()) {
            const Pt best = *std::min_element(from.begin(), from.end(), [&](Pt x, Pt y) {
                return std::hypot(x.x - left, x.y - top) < std::hypot(y.x - left, y.y - top);
            });
            left = best.x, top = best.y;
        }
    }
    return {left, top};
}

// ---- the interface -------------------------------------------------------------------------------

namespace {

// the page's tokens
constexpr Colour kInk{0x3F, 0x2A, 0x20}, kSoft{0x65, 0x45, 0x35}, kTan{0xDC, 0xB9, 0x8A}, kCream{0xE8, 0xCF, 0xA6},
    kWell{0xDC, 0xE0, 0xD2}, kPressed{0xCD, 0xB7, 0x93}, kMiLit{0xFF, 0xF8, 0xE4, 128}, kGo{0xC0, 0xD4, 0x70},
    kMapFace{0xFB, 0xF3, 0xE4}, kMapBtn{0xF3, 0xD0, 0x8A}, kMapBtnLit{0xF7, 0xDC, 0xAB}, kMapBtnDown{0xE3, 0xBC, 0x6F},
    kPip{0xF0, 0xB5, 0xCA}, kPipFail{0xE7, 0x9A, 0x95}, kMinimap{0xDC, 0xE6, 0xA0}, kMmHere{0xB8, 0xD7, 0x99},
    kCreditsInk{0xFF, 0xF8, 0xEA, 191}, kCreditsEdge{0x2C, 0x4A, 0x18, 191}, kShade{0x12, 0x24, 0x14, 140};
constexpr Colour with(Colour c, std::uint8_t a) { return {c.r, c.g, c.b, a}; }
constexpr Colour kMmEdge45{0x69, 0x55, 0x22, 115}, kMmEdge80{0x69, 0x55, 0x22, 204}, kMmEdge35{0x69, 0x55, 0x22, 89};

// MM.box: the manor and the catio, not the whole grounds, so the rooms read larger
constexpr float kMmBox[4] = {80, 32, 848, 448};
constexpr float kMmW = 250, kMmH = 132;

// the map panel's little drawings, cell by cell (the page's SVG paths, which are rectangles)
struct Cells { float w, h; std::vector<Rect> r; };
const Cells kHouse{9, 8, {{4, 0, 1, 1}, {3, 1, 3, 1}, {2, 2, 5, 1}, {1, 3, 7, 1}, {2, 4, 5, 1}, {2, 5, 2, 3}, {5, 5, 2, 3}}};
const Cells kTuck{8, 8, {{3, 0, 5, 1}, {6, 1, 2, 1}, {5, 2, 3, 1}, {4, 3, 2, 1}, {7, 3, 1, 2}, {3, 4, 2, 1}, {2, 5, 2, 1}, {1, 6, 2, 1}, {0, 7, 2, 1}}};
const Cells kUnfold{10, 8, {{3, 0, 4, 1}, {0, 1, 4, 1}, {6, 1, 4, 1}, {0, 1, 1, 7}, {9, 1, 1, 7}, {3, 0, 1, 7}, {6, 0, 1, 7}, {3, 6, 4, 1}, {0, 7, 4, 1}, {6, 7, 4, 1}}};

bool inside(Rect r, float x, float y) { return x >= r.x && x < r.x + r.w && y >= r.y && y < r.y + r.h; }

struct Region {
    Rect r;
    std::string id;
    Action a = Action::None;
    std::string arg;
    bool enabled = true;
};

// The map panel's boxes this frame, in device pixels.
struct MapBoxes {
    Rect panel, mm;
    Rect row[4];     // zoom out, zoom in, whole house, fold
    Rect floors[2];  // ground, upper
};

// Everything the interface remembers between frames.
struct State {
    // fonts
    std::filesystem::path assets;
    int css = 0;
    draw::Pixel pixel;
    std::map<std::pair<int, int>, std::unique_ptr<draw::Body>> bodies;
    std::unique_ptr<draw::Body> round;   // the pixel font's stand-in until sprout.ttf is here

    // the house's things
    view::Hit tip;
    view::Thing menu = Thing::None;
    std::string menu_key;
    Rect anchor;
    bool adding = false;
    std::optional<Pt> menu_at;

    // cards
    Card card = Card::None;
    std::string card_key;
    bool manage = false;

    // the map panel
    bool map_open = true;
    bool map_decided = false;

    // pointing
    std::string hot, held;
    std::string mm_hot;
    double mm_pressed_at = -1;
    std::string mm_pressed_room;
    std::vector<Region> regions;
    Rect brand, status, menu_box, card_box, tip_box;

    const draw::Body& body(int weight, float size) {
        const int px = int(std::lround(size * css * 100));
        auto& b = bodies[{weight, px}];
        if (!b) {
            b = std::make_unique<draw::Body>();
            const char* name = weight >= 800 ? "Nunito-ExtraBold.ttf" : weight >= 600 ? "Nunito-Bold.ttf" : "Nunito-Medium.ttf";
            b->open(assets / name, px / 100.f);
        }
        return *b;
    }
};

}  // namespace

struct Ui::Impl : State {};

Ui::Ui() : impl_(new Impl) {}
Ui::~Ui() { delete impl_; }

bool Ui::fonts(const std::filesystem::path& assets, const art::Art& art, int css) {
    Impl& I = *impl_;
    if (css != I.css || assets != I.assets) {
        I.bodies.clear();
        I.css = std::max(1, css);
        I.assets = assets;
        I.round = std::make_unique<draw::Body>();
        I.round->open(assets / "Nunito-Bold.ttf", 18.f * I.css);
        I.pixel.fallback(I.round.get());
    }
    I.pixel.open(art.path(art::Id::SproutFont));
    return I.round && I.round->ready();
}

void Ui::tip(const Frame& f, const view::Hit& h, bool moved) {
    Impl& I = *impl_;
    // hover means the pointer really moved onto it: what slides under a still pointer is not named
    const bool same = I.tip.what == h.what && I.tip.key == h.key;
    if (f.coarse || h.what == Thing::None || (!moved && !same) || (h.what == I.menu && h.key == I.menu_key)) {
        I.tip = {};
        return;
    }
    I.tip = h;   // the box follows the camera
}
const view::Hit& Ui::tipped() const { return impl_->tip; }

void Ui::toggle(const Frame& f, const view::Hit& h) {
    Impl& I = *impl_;
    I.tip = {};
    if (I.menu == h.what && I.menu_key == h.key) { close_menu(); return; }
    I.menu = h.what;
    I.menu_key = h.key;
    I.anchor = h.box;
    I.adding = false;
    I.menu_at.reset();
    (void)f;
}

// what a closed menu or card drew is gone at once, not at the next frame: two presses can land in one
void forget(std::vector<Region>& regions, std::string_view prefix) {
    regions.erase(std::remove_if(regions.begin(), regions.end(), [&](const Region& r) { return r.id.rfind(prefix, 0) == 0; }), regions.end());
}

void Ui::close_menu() {
    impl_->menu = Thing::None;
    impl_->menu_key.clear();
    impl_->adding = false;
    impl_->menu_at.reset();
    impl_->menu_box = {};
    forget(impl_->regions, "menu:");
}
view::Thing Ui::menu_kind() const { return impl_->menu; }
const std::string& Ui::menu_key() const { return impl_->menu_key; }

void Ui::open(Card c, std::string key) {
    close_menu();
    impl_->tip = {};
    impl_->card = c;
    impl_->card_key = std::move(key);
    impl_->manage = false;
}
void Ui::close_card() {
    impl_->card = Card::None, impl_->card_key.clear();
    impl_->card_box = {};
    forget(impl_->regions, "card:");
}
Card Ui::card() const { return impl_->card; }
const std::string& Ui::card_key() const { return impl_->card_key; }

bool Ui::map_open() const { return impl_->map_open; }
void Ui::set_map_open(bool open) { impl_->map_open = open, impl_->map_decided = true; }

bool Ui::escape() {
    if (impl_->card != Card::None) { close_card(); return true; }
    if (impl_->menu != Thing::None) { close_menu(); return true; }
    return false;
}

bool Ui::can(Action a) const {
    switch (a) {
        case Action::None: case Action::LookIn: case Action::WholeHouse: case Action::ZoomIn: case Action::ZoomOut:
        case Action::ToFloor: case Action::FoldMap: case Action::MapAt: case Action::StillCats: case Action::AddACat:
        case Action::Back: case Action::OpenHouse: case Action::OpenCat: case Action::OpenLink: case Action::CheckNow:
        case Action::CloseCard: case Action::Manage:
            return true;
        default:
            return false;
    }
}

std::string_view Ui::cannot(Action a) const { return can(a) ? std::string_view{} : kNotYet; }
std::string_view Ui::credits() const { return kCredits; }

// ---- painting --------------------------------------------------------------------------------------

namespace {

// One pass over the interface: it measures, and when `paint` is set it draws and records what can be pressed.
struct Painter {
    const draw::Ctx& c;
    State& I;
    const Frame& f;
    bool paint = true;
    float k;   // one CSS pixel
    float U;   // one art pixel of the interface (--u)

    Painter(const draw::Ctx& ctx, State& impl, const Frame& fr) : c(ctx), I(impl), f(fr), k(float(ctx.css)), U(float(ctx.u)) {}

    void region(Rect r, std::string id, Action a = Action::None, std::string arg = {}, bool enabled = true) {
        if (paint) I.regions.push_back({r, std::move(id), a, std::move(arg), enabled});
    }
    bool lit(const std::string& id) const { return I.hot == id; }
    bool held(const std::string& id) const { return I.held == id && I.hot == id; }

    // the pixel font in a line box `line` CSS pixels tall, its top at y
    float px_w(std::string_view t) const { return I.pixel.measure(t, int(k)).x; }
    void px(std::string_view t, float x, float y, float line, Colour col, int times = 1) {
        if (!paint || t.empty()) return;
        draw::Ctx cc = c;
        cc.css = int(k) * times;
        const float h = I.pixel.measure("A", cc.css).y;
        I.pixel.put(cc, t, std::round(x), std::round(y + (line * k * times - h) / 2), col);
    }
    float px_wide(std::string_view t, int times) const { return I.pixel.measure(t, int(k) * times).x; }

    const draw::Body& body(int weight, float size) { return I.body(weight, size); }
    void text(const draw::Body& b, std::string_view t, float x, float y, float line, Colour col) {
        if (!paint || t.empty()) return;
        const float h = b.measure("Ag").y;
        b.put(c, t, std::round(x), std::round(y + (line * k - h) / 2), col);
    }

    void fill(Rect r, Colour col) { if (paint) draw::fill(c, r, col); }
    void round(Rect r, float rad, Colour col) { if (paint) draw::round(c, r, rad, col); }
    void panel(const draw::Panel& p, Rect r) { if (paint) draw::panel(c, p, r); }
    void nine(art::Id id, draw::Slice cut, draw::Slice w, Rect r, bool fill_mid, std::uint8_t alpha = 255) {
        if (!paint) return;
        draw::Ctx cc = c;
        cc.alpha = alpha;
        draw::nine(cc, id, {}, cut, w, r, fill_mid);
    }
    void cell(art::Id id, Rect src, Rect dst, int coat = 0, std::uint8_t alpha = 255) {
        if (!paint) return;
        draw::Ctx cc = c;
        cc.alpha = alpha;
        draw::cell(cc, id, src, dst, coat);
    }
    void cells(const Cells& s, float x, float y, float scale, Colour col) {
        if (!paint) return;
        for (const Rect& r : s.r)
            draw::fill(c, Rect{std::round(x + r.x * scale), std::round(y + r.y * scale), std::round(r.w * scale), std::round(r.h * scale)}, col);
    }

    // .face-ico: the pack's cat emoji, a 30px window on its 32px cell
    void face(int i, float x, float y) {
        if (i < 0) return;
        cell(art::Id::UiFaces, Rect{float(i * 32 + 1), 1, 30, 30}, Rect{x, y, 30 * k, 30 * k});
    }
    // .divider: the pack's underline, capped at both ends, 4u tall
    void rule(float x, float y, float w) {
        nine(art::Id::UiDivider, {1, 1, 4, 0}, {U, U, 4 * U, 0}, Rect{x, y, w, 4 * U}, false);
    }
    // .badge: the most urgent face and how many, on the pack's white button one pixel thinner than a count's
    Pt badge_size(const std::vector<const Cat*>& need) {
        if (need.empty()) return {};
        const float tw = body(800, 11).measure(std::to_string(need.size())).x;
        return {28 * k + tw + 8 * k, 19 * k};
    }
    void badge(const std::vector<const Cat*>& need, float x, float cy) {
        if (need.empty()) return;
        const std::string n = std::to_string(need.size());
        const float tw = body(800, 11).measure(n).x;
        face(face_of(need[0]->mood), x, cy - 15 * k);
        const Rect box{x + 28 * k, std::round(cy - 9.5f * k), tw + 8 * k, 19 * k};
        fill(Rect{box.x + 3 * k, box.y + 3 * k, box.w - 6 * k, box.h - 8 * k}, {0xFF, 0xF8, 0xE4});
        nine(art::Id::UiButtonHover, {4, 4, 4, 6}, {3 * k, 3 * k, 3 * k, 5 * k}, box, true);
        text(body(800, 11), n, box.x + 4 * k, box.y + 3 * k, 11, kInk);
    }
    // .pip: a round count, red if one is upset
    void pip(const std::vector<const Cat*>& need, float x, float y) {
        if (need.empty()) return;
        const bool fail = std::any_of(need.begin(), need.end(), [](const Cat* c) { return c->mood == Mood::Cry; });
        const std::string n = std::to_string(need.size());
        const float w = std::max(16 * k, body(800, 11).measure(n).x + 6 * k);
        const Rect r{x, y, w, 16 * k};
        round(r, 8 * k, fail ? kPipFail : kPip);
        fill(Rect{r.x + 4 * k, r.y + r.h - 2 * k, r.w - 8 * k, 2 * k}, kMmEdge35);
        text(body(800, 11), n, r.x + (r.w - body(800, 11).measure(n).x) / 2, r.y + 2.5f * k, 11, kInk);
    }
    float pip_w(const std::vector<const Cat*>& need) {
        return need.empty() ? 0 : std::max(16 * k, body(800, 11).measure(std::to_string(need.size())).x + 6 * k);
    }

    // a Sprout Lands button (.btn): cream, white on hover, pressed in when held, green for the main one
    float btn_w(std::string_view label) { return px_w(label) + 4 * U + 8 * U; }
    float btn_h() { return 22 * k + 10 * U; }
    void btn(Rect r, std::string_view label, const std::string& id, Action a, std::string arg, bool green = false) {
        region(r, id, a, arg);
        const bool down = held(id);
        const Rect at = down ? Rect{r.x, r.y + 2 * U, r.w, r.h} : r;
        fill(Rect{at.x + 4 * U, at.y + 4 * U, at.w - 8 * U, at.h - 10 * U}, down ? kPressed : green ? kGo : kCream);
        if (down) panel(draw::kPressed, at);
        else nine(green ? art::Id::UiButtonGreen : lit(id) ? art::Id::UiButtonHover : art::Id::UiButton, {4, 4, 4, 6}, {4 * U, 4 * U, 4 * U, 6 * U}, at, true);
        px(label, at.x + 4 * U + 2 * U, at.y + 4 * U, 22, kInk);
    }
};

// ---- the map panel -------------------------------------------------------------------------------

MapBoxes map_boxes(const Frame& f, bool open, float k, float U) {
    MapBoxes m;
    const bool phone = f.stage.narrow();
    const float bh = (phone ? 44 : 40) * k, edge = 6 * k + 4 * k;   // the panel's border box and padding
    const float inner_w = kMmW * k;
    const float off = 6 * U + 8 * k;   // .mappanel { right: calc(var(--panel-r) * var(--u) + 8px) }
    if (!open) {
        const float w = std::max(bh, 60 * k);   // the fold alone: width auto, padding 0 9px, its 20px drawing
        m.panel = Rect{f.stage.w - off - (w + 2 * edge), phone ? f.stage.h - off - (bh + 2 * edge) : off, w + 2 * edge, bh + 2 * edge};
        m.row[3] = Rect{m.panel.x + edge, m.panel.y + edge, w, bh};
        return m;
    }
    const float h = bh + 6 * k + kMmH * k + 6 * k + bh;
    m.panel = Rect{f.stage.w - off - (inner_w + 2 * edge), phone ? f.stage.h - off - (h + 2 * edge) : off, inner_w + 2 * edge, h + 2 * edge};
    const float x = m.panel.x + edge;
    float y = m.panel.y + edge;
    auto row = [&] {
        const float w = (inner_w - 3 * 4 * k) / 4;   // .mp-row .pbtn { flex: 1 }
        for (int i = 0; i < 4; ++i) m.row[i] = Rect{x + i * (w + 4 * k), y, w, bh};
        y += bh + 6 * k;
    };
    if (!phone) row();   // on a phone the buttons go to the foot, under her thumb
    m.mm = Rect{x, y, inner_w, kMmH * k};
    y += kMmH * k + 6 * k;
    const float fw = (inner_w - 4 * k) / 2;
    m.floors[0] = Rect{x, y, fw, bh};
    m.floors[1] = Rect{x + fw + 4 * k, y, fw, bh};
    y += bh + 6 * k;
    if (phone) row();
    return m;
}

// a Pastel button (.pbtn): smooth art, lit on hover, pressed when held or chosen
void pbtn(Painter& P, Rect r, const std::string& id, Action a, std::string arg, bool on, bool enabled) {
    P.region(r, id, a, std::move(arg), enabled);
    const bool down = on || (enabled && P.held(id));
    const bool hover = enabled && P.lit(id);
    const std::uint8_t alpha = enabled ? 255 : 128;
    P.round(Rect{r.x + 2 * P.k, r.y + 2 * P.k, r.w - 4 * P.k, r.h - 4 * P.k}, 8 * P.k, with(down ? kMapBtnDown : hover ? kMapBtnLit : kMapBtn, alpha));
    P.nine(down ? art::Id::PastelButtonDown : hover ? art::Id::PastelButtonHover : art::Id::PastelButton, {22, 22, 20, 24},
           {11 * P.k, 11 * P.k, 10 * P.k, 12 * P.k}, r, true, alpha);
}

void draw_minimap(Painter& P, const Frame& f, Rect mm) {
    const float k = P.k, s = kMmW / kMmBox[2] * k;   // MM.k, on screen
    auto put = [&](manor::Box b) {
        return Rect{mm.x + (b.x - kMmBox[0]) * s, mm.y + (b.y - kMmBox[1]) * s, b.w * s, b.h * s};
    };
    P.region(mm, "map:mm", Action::MapAt);
    if (!P.paint) return;
    P.round(mm, 6 * k, kMinimap);
    const auto cats = shown(f);
    const manor::Level here = f.cam->floor;
    for (const manor::Level fl : {other(here), here}) {
        const bool faint = fl != here;
        if (fl == manor::Level::Upper) {
            const Rect r = put(manor::landing());
            P.fill(r, faint ? with(kMapBtnLit, 89) : kMapBtnLit);
        }
        for (const auto& g : manor::geom()) {
            if (g.level != fl) continue;
            const Rect r = put(g.box);
            const bool closed = f.house && !f.house->open(g.key);
            const std::uint8_t a = closed ? 102 : 255;
            if (faint) { P.fill(r, with(kMapBtn, closed ? 36 : 89)); continue; }
            const bool hot = P.I.mm_hot == g.key || (P.I.tip.what == Thing::Room && P.I.tip.key == g.key);
            const Colour face = g.key == f.cam->focus ? kMmHere : hot ? kMapBtnLit : kMapBtn;
            P.fill(r, with(face, a));
            const Colour edge = hot ? kMmEdge80 : kMmEdge45;
            P.fill(Rect{r.x, r.y, r.w, k}, edge), P.fill(Rect{r.x, r.y + r.h - k, r.w, k}, edge);
            P.fill(Rect{r.x, r.y + k, k, r.h - 2 * k}, edge), P.fill(Rect{r.x + r.w - k, r.y + k, k, r.h - 2 * k}, edge);
            std::vector<const Cat*> need;
            for (const Cat* c : cats) if (needs(c) && where_is(c) == g.key) need.push_back(c);
            if (!need.empty()) {
                const bool fail = std::any_of(need.begin(), need.end(), [](const Cat* c) { return c->mood == Mood::Cry; });
                P.round(Rect{r.x + r.w - 10 * k, r.y + 2 * k, 8 * k, 8 * k}, 4 * k, fail ? kPipFail : kPip);
            }
        }
    }
    // the stair: a line every three pixels
    const Rect st = put(manor::stairs());
    for (float y = st.y + st.h - k; y >= st.y; y -= 3 * k) P.fill(Rect{st.x, std::round(y), st.w, k}, kMmEdge45);
    // the camera's view, framed (drawView)
    const view::Cam& c = *f.cam;
    const float vx = -c.tx / c.u, vy = -c.ty / c.u, vw = float(f.stage.w) / c.u, vh = float(f.stage.h) / c.u;
    const float x0 = std::max(kMmBox[0], vx) - kMmBox[0], y0 = std::max(kMmBox[1], vy) - kMmBox[1];
    const float x1 = std::min(kMmBox[0] + kMmBox[2], vx + vw) - kMmBox[0], y1 = std::min(kMmBox[1] + kMmBox[3], vy + vh) - kMmBox[1];
    const Rect view{mm.x + x0 * s, mm.y + y0 * s, std::max(6 * k, (x1 - x0) * s), std::max(6 * k, (y1 - y0) * s)};
    P.nine(art::Id::PastelFrame, {28, 28, 28, 28}, {6 * k, 6 * k, 6 * k, 6 * k}, view, false);
}

void draw_map_panel(Painter& P, const Frame& f) {
    const float k = P.k;
    const MapBoxes m = map_boxes(f, P.I.map_open, k, P.U);
    P.region(m.panel, "map:panel");
    P.round(m.panel, 12 * k, kMapFace);
    P.nine(art::Id::PastelPanel, {28, 28, 28, 28}, {14 * k, 14 * k, 14 * k, 14 * k}, m.panel, true);
    const auto cats = shown(f);
    const manor::Level here = f.cam->floor;

    // the fold, with a pip beside its drawing (inline-flex, gap 4px) when cats out of view need her
    {
        const Rect r = m.row[3];
        std::vector<const Cat*> away;
        if (!P.I.map_open) {
            // foldPip(): every cat that needs her and isn't in view -- on the other floor, or off screen on this one
            const view::Cam& c = *f.cam;
            const float vx = -c.tx / c.u, vy = -c.ty / c.u, vw = float(f.stage.w) / c.u, vh = float(f.stage.h) / c.u;
            auto in_view = [&](const Cat* cat) {
                std::optional<manor::Point> at;
                if (f.scene) {
                    for (const auto& s : f.scene->cats) if (s.cat == cat) at = s.at;
                    for (const auto& p : f.scene->piles)
                        if (std::find(p.cats.begin(), p.cats.end(), cat) != p.cats.end()) at = p.at;
                }
                return at && at->x >= vx && at->x <= vx + vw && at->y >= vy && at->y <= vy + vh;
            };
            away = need_on(cats, other(here));
            for (const Cat* cat : need_on(cats, here)) if (!in_view(cat)) away.push_back(cat);
        }
        pbtn(P, r, "map:fold", Action::FoldMap, P.I.map_open ? "fold" : "open", false, true);
        const bool phone = f.stage.narrow();
        const Cells& g = P.I.map_open ? kTuck : kUnfold;
        const float w = g.w * 2 * k, h = g.h * 2 * k, pw = away.empty() ? 0 : 4 * k + P.pip_w(away);
        const float x = r.x + (r.w - w - pw) / 2, y = r.y + (r.h - h) / 2;
        if (P.I.map_open && phone) {   // .pbtn.fold .tuck { transform: scaleY(-1) }, drawn upside down
            Cells flip = g;
            for (Rect& c : flip.r) c.y = g.h - c.y - c.h;
            P.cells(flip, x, y, 2 * k, kInk);
        } else
            P.cells(g, x, y, 2 * k, kInk);
        if (!away.empty()) P.pip(away, x + w + 4 * k, r.y + (r.h - 16 * k) / 2);
    }
    if (!P.I.map_open) return;

    // zoom out, zoom in, whole house
    const int lo_u = [&] { view::Cam lo = view::clamp(view::Cam{1, 0, 0, {}, here}, f.stage); return lo.u; }();
    const int hi_u = [&] { view::Cam hi = view::clamp(view::Cam{1000, 0, 0, {}, here}, f.stage); return hi.u; }();
    const Rect icon{0, 0, 18 * k, 18 * k};
    auto ico = [&](Rect r, int i, bool enabled) {
        P.cell(art::Id::PastelIcons, Rect{float(i * 36), 0, 36, 36}, Rect{r.x + (r.w - icon.w) / 2, r.y + (r.h - icon.h) / 2 - k, icon.w, icon.h}, 0, enabled ? 255 : 128);
    };
    pbtn(P, m.row[0], "map:out", Action::ZoomOut, "", false, f.cam->u > lo_u);
    ico(m.row[0], 1, f.cam->u > lo_u);
    pbtn(P, m.row[1], "map:in", Action::ZoomIn, "", false, f.cam->u < hi_u);
    ico(m.row[1], 0, f.cam->u < hi_u);
    pbtn(P, m.row[2], "map:all", Action::WholeHouse, "", false, true);
    {
        const float sc = 14.f / 9.f * k, w = 9 * sc, h = 8 * sc;
        P.cells(kHouse, m.row[2].x + (m.row[2].w - w) / 2, m.row[2].y + (m.row[2].h - h) / 2 - k, sc, kInk);
    }

    draw_minimap(P, f, m.mm);

    // the floor tabs, a pip on the other floor's when cats there need her
    const char* names[2] = {"Ground", "Upstairs"};
    for (int i = 0; i < 2; ++i) {
        const manor::Level fl = i ? manor::Level::Upper : manor::Level::Ground;
        const Rect r = m.floors[i];
        pbtn(P, r, i ? "floor:upper" : "floor:ground", Action::ToFloor, i ? "upper" : "ground", fl == here, true);
        const auto need = fl != here ? need_on(cats, fl) : std::vector<const Cat*>{};
        const float tw = P.px_w(names[i]), pw = need.empty() ? 0 : P.pip_w(need) + 4 * k;
        const float x = r.x + (r.w - tw - pw) / 2;
        P.px(names[i], x, r.y + (r.h - 18 * k) / 2, 18, kInk);
        if (!need.empty()) P.pip(need, x + tw + 4 * k, r.y + (r.h - 16 * k) / 2);
    }
}

// ---- the brand and the sign ------------------------------------------------------------------------

void draw_hud(Painter& P, const Frame& f) {
    const float k = P.k, U = P.U;
    const bool phone = f.stage.narrow();
    const float x = 6 * U + 8 * k, y = 6 * U + 8 * k;
    const std::string name = f.house ? f.house->name() : "KittyChat Café";
    const auto need = f.house ? urgent_first(shown(f)) : std::vector<const Cat*>{};
    const float logo_w = phone ? 19 * k : 34 * k;   // 21 x 18 art pixels, less its negative margins
    const Pt bs = P.badge_size(need);
    const float w = 4 * U + logo_w + 6 * k + P.px_w(name) + (need.empty() ? 0 : 6 * k + bs.x) + 3 * U + 4 * U;
    const float h = 4 * U + 22 * k + 6 * U;
    const Rect r{x, y, w, h};
    P.I.brand = r;
    P.region(r, "brand", Action::OpenHouse);
    const bool open = P.I.menu == Thing::House;
    const Rect at = open ? Rect{r.x, r.y + 2 * U, r.w, r.h} : r;
    P.fill(Rect{at.x + 4 * U, at.y + 4 * U, at.w - 8 * U, at.h - 10 * U}, open ? kPressed : kCream);
    if (open) P.panel(draw::kPressed, at);
    else P.nine(P.lit("brand") ? art::Id::UiButtonHover : art::Id::UiButton, {4, 4, 4, 6}, {4 * U, 4 * U, 4 * U, 6 * U}, at, true);
    const float cx = at.x + 4 * U, cy = at.y + 4 * U;   // the content box
    if (phone) P.cell(art::Id::UiLogo, Rect{0, 0, 21, 18}, Rect{cx - 2 * k, cy + 2 * k, 21 * U, 18 * U});
    else P.cell(art::Id::UiLogo, Rect{0, 0, 21, 18}, Rect{cx - 8 * k, cy - 6 * k, 21 * U, 18 * U});
    float tx = cx + logo_w + 6 * k;
    P.px(name, tx, cy, 22, kInk);
    tx += P.px_w(name) + 6 * k;
    P.badge(need, tx, cy + 11 * k);

    // the sign shows only when something is wrong
    P.I.status = {};
    if (f.status.empty()) return;
    const float max_w = std::min(460 * k, f.stage.w - 12 * U - 16 * k);
    const draw::Body& b = P.body(700, 12.8f);
    const float inner = max_w - 12 * U - 4 * U - 12 * k - 8 * k;
    const auto lines = b.wrap(f.status, inner);
    float tw = 0;
    for (const auto& l : lines) tw = std::max(tw, b.measure(l).x);
    const float lh = 12.8f * 1.5f;
    const Rect s{x, y + h + 6 * k, 12 * U + 4 * U + 12 * k + 8 * k + tw, 12 * U + std::max(lh * lines.size(), 12.f + 4) * k};
    P.I.status = s;
    P.region(s, "status");
    P.fill(Rect{s.x + 6 * U, s.y + 6 * U, s.w - 12 * U, s.h - 12 * U}, kTan);
    P.panel(draw::kPanel, s);
    const float ix = s.x + 6 * U + 2 * U, iy = s.y + 6 * U;
    P.cell(art::Id::UiStatus, Rect{12, 0, 12, 12}, Rect{ix, iy + 4 * k, 12 * k, 12 * k});   // the pack's cross
    for (size_t i = 0; i < lines.size(); ++i) P.text(b, lines[i], ix + 20 * k, iy + i * lh * k, lh, kInk);
}

// The credits, at the foot of the screen on a desk (a phone has no room: the House menu has them).
void draw_credits(Painter& P, const Frame& f) {
    if (f.stage.narrow() || !P.paint) return;
    const float k = P.k, U = P.U;
    const draw::Body& b = P.body(500, 10.56f);
    const float max_w = f.stage.w - 12 * U - 16 * k, lh = 10.56f * 1.5f * k;
    const auto lines = b.wrap(kCredits, max_w);
    const float x = 6 * U + 8 * k, bottom = f.stage.h - (6 * U + 4 * k);
    for (size_t i = 0; i < lines.size(); ++i) {
        const float y = bottom - (lines.size() - i) * lh;
        for (auto [dx, dy] : {std::pair{0.f, 1.f}, {1.f, 0.f}, {-1.f, 0.f}, {0.f, -1.f}}) P.text(b, lines[i], x + dx * k, y + dy * k, 10.56f * 1.5f, kCreditsEdge);
        P.text(b, lines[i], x, y, 10.56f * 1.5f, kCreditsInk);
    }
}

// ---- the hover line ------------------------------------------------------------------------------

void draw_tip(Painter& P, const Frame& f) {
    P.I.tip_box = {};
    if (P.I.tip.what == Thing::None || f.coarse) return;
    const Tip t = tip_for(f, P.I.tip);
    if (t.name.empty()) return;
    const float k = P.k;
    const draw::Body& small = P.body(700, 11.84f);
    const draw::Body& says = P.body(500, 12.5f);
    auto need = t.need;
    // line one: the name, the small word, the badge, 6px apart
    float w1 = P.px_w(t.name);
    if (!t.small.empty()) w1 += 6 * k + small.measure(t.small).x;
    const Pt bs = P.badge_size(need);
    if (!need.empty()) w1 += 6 * k + bs.x;
    const float max_inner = 228 * k;   // max-width 240px, less the border and the padding
    std::vector<std::string> lines;
    if (!t.says.empty()) lines = says.wrap(t.says, max_inner, 3);
    float inner = std::min(max_inner, w1);
    if (!lines.empty()) {
        float sw = 0;
        for (const auto& l : lines) sw = std::max(sw, says.measure(l).x);
        inner = std::min(max_inner, std::max(inner, sw));
        if (says.measure(t.says).x > max_inner) inner = max_inner;
    }
    const float h1 = (need.empty() ? 18 : 19) * k;
    const float hs = lines.empty() ? 0 : 6 * k + lines.size() * 12.5f * 1.3f * k + 2 * k;
    const float w = inner + 4 * k + 8 * k, h = 4 * k + h1 + hs + 6 * k;
    // above the thing: for a room, a little way down into it
    const Rect a = P.I.tip.box;
    const float x = std::max(w / 2 + 8 * k, std::min(f.stage.w - w / 2 - 8 * k, a.x + a.w / 2));
    const float y = std::max(h + 8 * k, a.y + (P.I.tip.what == Thing::Room || P.I.tip.what == Thing::Cabinet ? std::min(a.h / 2, 60 * k) : -4 * k));
    const Rect r{std::round(x - w / 2), std::round(y - h), w, h};
    P.I.tip_box = r;
    P.fill(Rect{r.x + 4 * k, r.y + 4 * k, r.w - 8 * k, r.h - 10 * k}, kCream);
    P.nine(art::Id::UiButton, {4, 4, 4, 6}, {4 * k, 4 * k, 4 * k, 6 * k}, r, true);
    float cx = r.x + 4 * k + 2 * k;
    const float cy = r.y + 4 * k;
    P.px(t.name, cx, cy, h1 / k, kInk);
    cx += P.px_w(t.name) + 6 * k;
    if (!t.small.empty()) {
        P.text(small, t.small, cx, cy, h1 / k, kSoft);
        cx += small.measure(t.small).x + 6 * k;
    }
    if (!need.empty()) P.badge(need, cx, cy + h1 / 2);
    for (size_t i = 0; i < lines.size(); ++i) P.text(says, lines[i], r.x + 6 * k, cy + h1 + 6 * k + i * 12.5f * 1.3f * k, 12.5f * 1.3f, kInk);
}

// ---- the menu ------------------------------------------------------------------------------------

// One pass over a menu: returns its height; draws it when the painter paints.
float menu_pass(Painter& P, const Menu& m, float x0, float y0, float w) {
    const float k = P.k, U = P.U;
    const float cx = x0 + 6 * U + 2 * U, cw = w - 12 * U - 4 * U;   // the content box: border 6u, padding 2u
    float y = y0 + 6 * U + 2 * k;
    bool first = true;
    auto gap = [&] { if (!first) y += 6 * k; first = false; };
    const draw::Body& sub = P.body(500, 12.8f);
    const float sub_lh = 12.8f * 1.35f;

    // the head: the name, with a face or a crown before it and a badge after it, and one line under it
    if (m.kind != Thing::House) {
        gap();
        float tx = cx;
        if (m.face >= 0) { P.face(m.face, cx - 4 * k, y - 4 * k), tx += 30 * k - 4 * k + 4 * k; }
        if (m.crown) { P.cell(art::Id::UiCrown, Rect{0, 0, 14, 13}, Rect{cx, y + (22 - 13) / 2.f * k, 14 * k, 13 * k}), tx += 14 * k + 4 * k; }
        const Pt bs = P.badge_size(m.need);
        const float room = cx + cw - tx - (m.need.empty() ? 0 : bs.x + 6 * k);
        std::string title = m.title;
        while (title.size() > 1 && P.px_w(title) > room) {   // a long name: cut, as the line has no more room
            title.pop_back();
            while (!title.empty() && (static_cast<unsigned char>(title.back()) & 0xC0) == 0x80) title.pop_back();
        }
        P.px(title, tx, y, 22, kInk);
        if (!m.need.empty()) P.badge(m.need, cx + cw - bs.x, y + 11 * k);
        y += 22 * k;
        if (!m.sub.empty()) {
            const auto lines = sub.wrap(m.sub, cw, 2);
            for (const auto& l : lines) P.text(sub, l, cx, y, sub_lh, kSoft), y += sub_lh * k;
        }
    }

    for (size_t bi = 0; bi < m.blocks.size(); ++bi) {
        const Block& b = m.blocks[bi];
        gap();
        switch (b.kind) {
            case Block::Kind::Sub: {
                for (const auto& l : sub.wrap(b.text, cw)) P.text(sub, l, cx, y, sub_lh, kSoft), y += sub_lh * k;
                break;
            }
            case Block::Kind::Foot: {
                const draw::Body& f = P.body(500, 10.88f);
                for (const auto& l : f.wrap(b.text, cw)) P.text(f, l, cx, y, 10.88f * 1.35f, kSoft), y += 10.88f * 1.35f * k;
                break;
            }
            case Block::Kind::Ask: {
                // the well: the pack's bubble, a face or a crown, and the words beside it
                const draw::Body& t = P.body(700, 15.2f);
                const float lead = b.face >= 0 ? 30 * k + 8 * k : b.crown ? 14 * k + 8 * k : 0;
                const float tw = cw - 10 * U - 8 * k - lead;
                const auto lines = t.wrap(b.text, tw);
                const float lh = 15.2f * 1.5f;
                const float inner_h = std::max(b.face >= 0 ? 30 * k : 0.f, lines.size() * lh * k);
                const Rect r{cx, y, cw, inner_h + 11 * U};
                const std::string id = "menu:ask:" + std::to_string(bi);
                if (b.action != Action::None) P.region(r, id, b.action, b.arg, true);
                P.fill(Rect{r.x + 5 * U, r.y + 5 * U, r.w - 10 * U, r.h - 11 * U}, kWell);
                P.panel(draw::kBubble, r);
                float tx = r.x + 5 * U + 4 * k;
                const float ty = r.y + 5 * U;
                if (b.face >= 0) P.face(b.face, tx, ty + (inner_h - 30 * k) / 2), tx += 38 * k;
                if (b.crown) P.cell(art::Id::UiCrown, Rect{0, 0, 14, 13}, Rect{tx, ty + (inner_h - 13 * k) / 2, 14 * k, 13 * k}), tx += 22 * k;
                const float text_top = ty + (inner_h - lines.size() * lh * k) / 2;
                for (size_t i = 0; i < lines.size(); ++i) P.text(t, lines[i], tx, text_top + i * lh * k, lh, kInk);
                y += r.h;
                break;
            }
            case Block::Kind::Cats: {
                const draw::Body& t = P.body(500, 13.12f);
                for (size_t i = 0; i < b.rows.size(); ++i) {
                    if (i) y += 2 * k;
                    const Row& row = b.rows[i];
                    const Rect r{cx, y, cw, 30 * k};
                    const std::string id = "menu:cat:" + row.id;
                    P.region(r, id, Action::OpenCat, row.id);
                    P.face(row.face, cx, y);
                    float tx = cx + 36 * k;
                    P.px(row.name, tx, y + 4 * k, 22, kInk);
                    tx += P.px_w(row.name);
                    const std::string rest = t.cut(" · " + row.text, cx + cw - tx);
                    P.text(t, rest, tx, y + 4 * k, 22, kInk);
                    if (P.lit(id) && P.paint) P.fill(Rect{tx, y + 4 * k + 17 * k, t.measure(rest).x, k}, kInk);   // underlined on hover
                    y += 30 * k;
                }
                if (b.more) {
                    y += 2 * k;
                    P.text(sub, "and " + std::to_string(b.more) + " more", cx, y, sub_lh, kSoft);
                    y += sub_lh * k;
                }
                break;
            }
            case Block::Kind::Keeps: {
                y += 2 * k;   // ul.keeps { margin: 2px 0 6px }
                for (size_t i = 0; i < b.rows.size(); ++i) {
                    if (i) y += 5 * k;
                    const Row& row = b.rows[i];
                    const draw::Body& t = P.body(row.pinned ? 700 : 500, 14.08f);
                    const auto lines = t.wrap(row.text, cw - 16 * k);
                    const float lh = 14.08f * 1.5f;
                    P.cell(art::Id::UiStars, Rect{row.pinned ? 0.f : 10.f, 0, 10, 8}, Rect{cx, y + (lh - 8) / 2 * k, 10 * k, 8 * k});
                    for (size_t j = 0; j < lines.size(); ++j) P.text(t, lines[j], cx + 16 * k, y + j * lh * k, lh, kInk);
                    y += std::max<size_t>(1, lines.size()) * lh * k;
                }
                if (b.more) {
                    y += 5 * k;
                    P.text(sub, "and " + std::to_string(b.more) + " more", cx, y, sub_lh, kSoft);
                    y += sub_lh * k;
                }
                y += 6 * k;
                break;
            }
            case Block::Kind::Rule:
                P.rule(cx, y, cw);
                y += 4 * U;
                break;
            case Block::Kind::List: {
                // .menu .list { margin: 0 -u }, and the pack's triangle beside the item under the pointer, or the
                // default when none is
                const float lx = cx - U, lw = cw + 2 * U;
                bool any_lit = false;
                for (size_t i = 0; i < b.items.size(); ++i) any_lit |= b.items[i].enabled && P.lit("menu:item:" + std::to_string(bi) + ":" + std::to_string(i));
                // the default is the first item; while it is not built yet, the first one that is
                size_t primary = b.items.size();
                for (size_t i = 0; i < b.items.size() && primary == b.items.size(); ++i) if (b.items[i].enabled && b.items[i].toggle < 0) primary = i;
                for (size_t i = 0; i < b.items.size(); ++i) {
                    const Item& it = b.items[i];
                    const std::string id = "menu:item:" + std::to_string(bi) + ":" + std::to_string(i);
                    const float h = std::max((P.f.coarse ? 44.f : 28.f) * k, 26 * k);
                    const Rect r{lx, y, lw, h};
                    const bool enabled = it.enabled;
                    P.region(r, id, it.action, it.arg, enabled);
                    const bool hot = P.lit(id) && enabled;
                    if (hot) P.fill(r, kMiLit);
                    const Colour ink = enabled ? kInk : with(kInk, 115);
                    float tx = r.x + (it.toggle >= 0 ? 4 * k : 18 * k);
                    if (it.toggle >= 0) {   // .sound .switch: the pack's toggle, off or on
                        P.cell(art::Id::UiToggle, Rect{it.toggle ? 28.f : 0.f, 0, 28, 18}, Rect{tx, r.y + (h - 18 * k) / 2, 28 * k, 18 * k});
                        tx += 28 * k + 6 * k;
                    } else if (enabled && (hot || (i == primary && !any_lit)))
                        P.cell(art::Id::UiPointer, Rect{0, 0, 7, 12}, Rect{r.x + 5 * k, r.y + h / 2 - 6 * k, 7 * k, 12 * k});
                    P.px(it.label, tx, r.y + (h - 22 * k) / 2, 22, ink);
                    const std::string aside = enabled ? it.aside : "not yet";
                    if (!aside.empty()) {
                        const draw::Body& a = P.body(800, 12);
                        P.text(a, aside, r.x + r.w - 6 * k - a.measure(aside).x, r.y + (h - 22 * k) / 2, 22, kSoft);
                    }
                    y += h;
                }
                break;
            }
        }
    }
    return y - y0 + 2 * U + 6 * U;
}

}  // namespace

draw::Rect Ui::panel(const Frame& f) const {
    const float k = float(std::max(1, f.stage.css)), U = k * (f.stage.narrow() ? 1 : 2);
    return map_boxes(f, impl_->map_open, k, U).panel;
}

bool Ui::over(const Frame& f, float x, float y) const {
    const Impl& I = *impl_;
    if (I.card != Card::None) return true;
    for (const Rect r : {panel(f), I.brand, I.status, I.menu_box})
        if (r.w > 0 && inside(r, x, y)) return true;
    return false;
}

std::string_view Ui::under(const Frame&, float x, float y) const {
    for (auto it = impl_->regions.rbegin(); it != impl_->regions.rend(); ++it)
        if (inside(it->r, x, y)) return it->id;
    return {};
}

void Ui::hover(const Frame& f, float x, float y) {
    Impl& I = *impl_;
    I.hot.clear();
    I.mm_hot.clear();
    for (auto it = I.regions.rbegin(); it != I.regions.rend(); ++it) {
        if (!inside(it->r, x, y)) continue;
        I.hot = it->id;
        if (it->id == "map:mm" && f.cam) {
            const float s = kMmW / kMmBox[2] * float(std::max(1, f.stage.css));
            const float ax = kMmBox[0] + (x - it->r.x) / s, ay = kMmBox[1] + (y - it->r.y) / s;
            for (const auto& g : manor::geom())
                if (g.level == f.cam->floor && ax >= g.box.x && ax < g.box.x + g.box.w && ay >= g.box.y && ay < g.box.y + g.box.h) I.mm_hot = g.key;
        }
        break;
    }
}

void Ui::hold(const Frame& f, float x, float y, bool down) {
    if (!down) { impl_->held.clear(); return; }
    hover(f, x, y);
    impl_->held = impl_->hot;
}

bool Ui::map_drag(const Frame& f, float x, float y, std::string* arg) const {
    for (const Region& r : impl_->regions) {
        if (r.id != "map:mm") continue;
        const float s = kMmW / kMmBox[2] * float(std::max(1, f.stage.css));
        const float cx = std::clamp(x, r.r.x, r.r.x + r.r.w), cy = std::clamp(y, r.r.y, r.r.y + r.r.h);
        *arg = std::to_string(int(kMmBox[0] + (cx - r.r.x) / s)) + " " + std::to_string(int(kMmBox[1] + (cy - r.r.y) / s));
        return true;
    }
    return false;
}

bool Ui::press(const Frame& f, float x, float y, Action* what, std::string* arg) {
    Impl& I = *impl_;
    *what = Action::None;
    arg->clear();
    I.held.clear();
    const Region* hit = nullptr;
    for (auto it = I.regions.rbegin(); it != I.regions.rend(); ++it)
        if (inside(it->r, x, y)) { hit = &*it; break; }
    if (I.card != Card::None) {
        if (hit && hit->id.rfind("card:", 0) == 0 && hit->enabled) *what = hit->a, *arg = hit->arg;
        if (*what == Action::CloseCard) close_card();
        if (*what == Action::Manage) I.manage = !I.manage;
        return true;   // the card is modal
    }
    if (!hit) return over(f, x, y);
    if (!hit->enabled) return true;
    *what = hit->a;
    *arg = hit->arg;
    switch (hit->a) {
        case Action::OpenHouse:
            if (I.menu == Thing::House) close_menu();
            else I.menu = Thing::House, I.menu_key = "house", I.anchor = I.brand, I.adding = false, I.menu_at.reset(), I.tip = {};
            break;
        case Action::FoldMap:
            I.map_open = !I.map_open, I.map_decided = true;
            *arg = I.map_open ? "open" : "folded";
            break;
        case Action::AddACat: I.adding = true; break;
        case Action::Back: I.adding = false; break;
        case Action::StillCats: break;   // the menu stays, its switch flipped
        case Action::MapAt: {
            const float s = kMmW / kMmBox[2] * float(std::max(1, f.stage.css));
            const float ax = kMmBox[0] + (x - hit->r.x) / s, ay = kMmBox[1] + (y - hit->r.y) / s;
            *arg = std::to_string(int(ax)) + " " + std::to_string(int(ay));
            // a second press on the same room soon after looks in (the minimap's double-click)
            std::string room;
            for (const auto& g : manor::geom())
                if (f.cam && g.level == f.cam->floor && ax >= g.box.x && ax < g.box.x + g.box.w && ay >= g.box.y && ay < g.box.y + g.box.h) room = g.key;
            if (!room.empty() && room == I.mm_pressed_room && f.now - I.mm_pressed_at < 0.4) *what = Action::LookIn, *arg = room, I.mm_pressed_at = -1;
            else I.mm_pressed_room = room, I.mm_pressed_at = f.now;
            break;
        }
        case Action::None: break;
        default:
            if (hit->id.rfind("menu:", 0) == 0) close_menu();   // an action in a menu closes it (hideMenu)
            break;
    }
    return true;
}

// ---- the card ------------------------------------------------------------------------------------

namespace {

void draw_cat_card(Painter& P, const Frame& f, const Cat& c) {
    const float k = P.k, U = P.U;
    const float W = std::min(500 * k, f.stage.w - 24 * k);
    // .dlg: the content box, after the panel's 6u border, dialog's 2u 4u padding and its own 4px 2px
    const float pad_x = 6 * U + 4 * U + 2 * k, pad_y = 6 * U + 2 * U + 4 * k;
    const float cw = W - 2 * pad_x;
    const MoodInfo& m = info(c.mood);
    const draw::Body& note = P.body(500, 12.8f);
    const draw::Body& mood = P.body(800, 13.6f);
    const draw::Body& ask = P.body(700, 15.2f);
    const draw::Body& blurb = P.body(500, 15.2f);
    const draw::Body& fact = P.body(500, 14.4f), & factk = P.body(700, 14.4f);

    // measure, then draw, in one function: the layout is a column with 12px between its pieces
    auto layout = [&](float x, float y0) {
        float y = y0;
        // the head: the portrait in the pack's frame, the name at twice the pixel font, the mood, where it lives
        const float pw = 112 * k + 14 * U, ph = 96 * k + 14 * U;
        const float ix = x + pw + 14 * k, iw = cw - pw - 14 * k;
        const float name_h = 44 * k, mood_h = 30 * k, note_h = 12.8f * 1.5f * k + 2 * k;
        const float info_h = name_h + mood_h + note_h;
        const float head_h = std::max(ph, info_h);
        if (P.paint) {
            const Rect por{x, y + head_h - ph, pw, ph};
            const Rect inner{por.x + 7 * U, por.y + 7 * U, 112 * k, 96 * k};
            // the meadow, 224 x 64 a tile
            for (float ty = inner.y; ty < inner.y + inner.h; ty += 64 * k)
                for (float tx = inner.x; tx < inner.x + inner.w; tx += 224 * k) {
                    const float w = std::min(224 * k, inner.x + inner.w - tx), h = std::min(64 * k, inner.y + inner.h - ty);
                    P.cell(art::Id::Meadow, Rect{0, 0, w / (2 * k), h / (2 * k)}, Rect{tx, ty, w, h});
                }
            // the sprite, scaled about its middle, its feet 2px up: 2.4 for the 32px sheets, 1.4 for the 64px
            struct S { art::Id id; float row, w, n, secs; };
            const S s = c.mood == Mood::Idle ? S{art::Id::MochiIdle, 0, 32, 10, 1.25f} : c.mood == Mood::Box ? S{art::Id::MochiBox, 0, 32, 4, .8f}
                      : c.mood == Mood::Cry ? S{art::Id::Pochi, 0, 64, 4, .7f} : c.mood == Mood::Meow ? S{art::Id::Pochi, 64, 64, 2, .5f}
                                            : S{art::Id::Pochi, 128, 64, 4, 2.4f};
            const float sc = s.w == 32 ? 2.4f : 1.4f;
            const int frame = f.still ? 0 : int(std::fmod(f.now / s.secs, 1.0) * s.n);
            const float vw = s.w * sc * k, cxm = inner.x + inner.w / 2, cym = inner.y + inner.h - 2 * k - s.w / 2 * k;
            // overflow: hidden, done by hand: the cut of the frame that falls inside the portrait, and where it lands
            Rect dst{cxm - vw / 2, cym - vw / 2, vw, vw}, src{frame * s.w, s.row, s.w, s.w};
            const float per = s.w / vw;   // sheet pixels per screen pixel
            const float x0 = std::max(dst.x, inner.x), y0 = std::max(dst.y, inner.y);
            const float x1 = std::min(dst.x + dst.w, inner.x + inner.w), y1 = std::min(dst.y + dst.h, inner.y + inner.h);
            if (x1 > x0 && y1 > y0) {
                src = Rect{src.x + (x0 - dst.x) * per, src.y + (y0 - dst.y) * per, (x1 - x0) * per, (y1 - y0) * per};
                dst = Rect{x0, y0, x1 - x0, y1 - y0};
                draw::cell(P.c, s.id, src, dst, c.coat);
            }
            P.nine(art::Id::UiFrame, {7, 7, 7, 7}, {7 * U, 7 * U, 7 * U, 7 * U}, por, false);
        }
        float iy = y + head_h - info_h;
        P.px(c.name, ix, iy, 22, kInk, 2);
        iy += name_h;
        P.face(face_of(c.mood), ix, iy);
        P.text(mood, m.label, ix + 34 * k, iy + 4 * k, 22, kInk);
        iy += mood_h + 2 * k;
        P.text(note, note.cut(join({c.project_name, f.house->room(c.room).name}, " · "), iw), ix, iy, 12.8f * 1.5f, kSoft);
        y += head_h + 12 * k;

        // what she came for: its ask, in the well, else what it is doing
        if (!c.ask.empty()) {
            const auto lines = ask.wrap(c.ask, cw - 10 * U - 8 * k - 38 * k);
            const float ih = std::max(30 * k, lines.size() * 15.2f * 1.5f * k);
            const Rect r{x, y, cw, ih + 11 * U};
            P.fill(Rect{r.x + 5 * U, r.y + 5 * U, r.w - 10 * U, r.h - 11 * U}, kWell);
            P.panel(draw::kBubble, r);
            P.face(face_of(c.mood), r.x + 5 * U + 4 * k, r.y + 5 * U + (ih - 30 * k) / 2);
            const float top = r.y + 5 * U + (ih - lines.size() * 15.2f * 1.5f * k) / 2;
            for (size_t i = 0; i < lines.size(); ++i) P.text(ask, lines[i], r.x + 5 * U + 4 * k + 38 * k, top + i * 15.2f * 1.5f * k, 15.2f * 1.5f, kInk);
            y += r.h + 12 * k;
        } else if (!c.adopted) {
            for (const auto& l : blurb.wrap(!c.doing.empty() ? c.doing : c.title, cw)) P.text(blurb, l, x, y, 15.2f * 1.5f, kSoft), y += 15.2f * 1.5f * k;
            y += 12 * k;
        }

        // Manage, folded: the facts. Renaming and moving it are writes, and arrive with the network.
        {
            const Rect r{x, y, P.px_w("Manage") + 15 * k, 22 * k};
            P.region(r, "card:manage", Action::Manage);
            if (P.paint) {
                const Rect tri{x, y + 5 * k, 7 * k, 12 * k};
                if (P.I.manage) {   // turned a quarter, open
                    const SDL_FPoint centre{tri.w / 2, tri.h / 2};
                    SDL_Texture* t = draw::gpu(P.c.canvas, P.c.art->texture(art::Id::UiPointer));
                    const SDL_FRect d{tri.x, tri.y, tri.w, tri.h};
                    if (t) SDL_RenderTextureRotated(P.c.canvas->r, t, nullptr, &d, 90, &centre, SDL_FLIP_NONE);
                } else
                    P.cell(art::Id::UiPointer, Rect{0, 0, 7, 12}, tri);
            }
            P.px("Manage", x + 15 * k, y, 22, kInk);
            y += 22 * k;
            if (P.I.manage) {
                y += 10 * k;
                std::vector<std::pair<std::string, std::string>> facts;
                if (!c.doing.empty() && c.title != c.doing) facts.push_back({"Title", c.title});
                else if (c.doing.empty() && !c.adopted) facts.push_back({"Title", c.title});
                if (!c.repo.empty() && c.repo != c.project_name) facts.push_back({"Repository", c.repo});
                if (!c.model.empty()) facts.push_back({c.adopted ? "Model" : "Agent", c.model});
                if (c.updated) facts.push_back({"Last active", ago(c.updated, f.clock_ms)});
                float kw = 0;
                for (const auto& [key, v] : facts) kw = std::max(kw, factk.measure(key).x);
                const float lh = 14.4f * 1.5f;
                for (const auto& [key, v] : facts) {
                    P.text(factk, key, x, y, lh, kSoft);
                    const auto lines = fact.wrap(v, cw - kw - 12 * k);
                    for (size_t i = 0; i < lines.size(); ++i) P.text(fact, lines[i], x + kw + 12 * k, y + i * lh * k, lh, kInk);
                    y += std::max<size_t>(1, lines.size()) * lh * k + 4 * k;
                }
                P.text(note, "Renaming and moving it arrive with the app's network code.", x, y, 12.8f * 1.5f, kSoft);
                y += 12.8f * 1.5f * k;
            }
            y += 12 * k;
        }

        // the actions: Close on the left, the way out to its session on the right
        const float bh = P.btn_h();
        P.btn(Rect{x, y, P.btn_w("Close"), bh}, "Close", "card:close", Action::CloseCard, "");
        if (!c.link.empty()) {
            const std::string label = c.adopted ? "Open chat" : "Open";
            const float w = P.btn_w(label);
            P.btn(Rect{x + cw - w, y, w, bh}, label, "card:open", Action::OpenLink, c.link, true);
        }
        y += bh;
        return y - y0;
    };

    const bool was = P.paint;
    P.paint = false;
    const float h = layout(0, 0) + 2 * pad_y;
    P.paint = was;
    const Rect box{std::round((f.stage.w - W) / 2), std::round(std::max(20 * k, (f.stage.h - h) / 2)), W, h};
    P.I.card_box = box;
    P.fill(Rect{0, 0, float(f.stage.w), float(f.stage.h)}, kShade);   // dialog::backdrop
    P.fill(Rect{box.x + 6 * U, box.y + 6 * U, box.w - 12 * U, box.h - 12 * U}, kTan);
    P.panel(draw::kPanel, box);
    layout(box.x + pad_x, box.y + pad_y);
}

}  // namespace

void Ui::draw(const draw::Ctx& c, const Frame& f) {
    Impl& I = *impl_;
    I.regions.clear();
    I.menu_box = {};
    I.card_box = {};
    if (!f.house || !f.cam) return;
    if (!I.map_decided) I.map_open = !f.stage.narrow(), I.map_decided = true;   // folded at first on a phone
    Painter P(c, I, f);

    draw_credits(P, f);

    // the menu, beside what it belongs to (z 20, under the screen's frame and the controls)
    if (I.menu != Thing::None) {
        Menu m = menu_for(f, I.menu, I.menu_key, I.adding);
        for (auto& b : m.blocks)   // what this build cannot do yet is drawn, disabled, and says so
            for (auto& it : b.items) it.enabled = it.enabled && can(it.action);
        if (m.title.empty() && m.kind != Thing::House) close_menu();
        else {
            const float w = std::min(248 * P.k, f.stage.w - 24 * P.k);
            P.paint = false;
            const float h = std::min(menu_pass(P, m, 0, 0, w), f.stage.h - 24 * P.k);
            P.paint = true;
            const float hud_bottom = std::max(I.brand.y + I.brand.h, I.status.y + I.status.h);   // the whole #hud, sign and all
            const Pt at = I.menu_at ? *I.menu_at : place_menu(f.stage, I.menu, I.anchor, Pt{w, h}, panel(f), hud_bottom);
            I.menu_at = at;
            const Rect box{std::round(at.x), std::round(at.y), w, h};
            I.menu_box = box;
            P.region(box, "menu:box");
            P.fill(Rect{box.x + 6 * P.U, box.y + 6 * P.U, box.w - 12 * P.U, box.h - 12 * P.U}, kTan);
            P.panel(draw::kPanel, box);
            menu_pass(P, m, box.x, box.y, w);
        }
    }

    draw_tip(P, f);

    // the screen's frame: the panel's border, no fill (z 30)
    P.nine(art::Id::UiPanel, {6, 6, 6, 6}, {6 * P.U, 6 * P.U, 6 * P.U, 6 * P.U}, Rect{0, 0, float(f.stage.w), float(f.stage.h)}, false);

    draw_hud(P, f);
    draw_map_panel(P, f);

    if (I.card == Card::Cat) {
        if (const Cat* cat = f.house->cat(I.card_key)) draw_cat_card(P, f, *cat);
        else close_card();
    }
}

}  // namespace catio::ui
