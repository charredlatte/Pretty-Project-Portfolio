// catio_tests -- the floor plan, the house, the view and the interface, driven from JSON with no window
// and no network.
//
//   catio_tests <generated/manor.json> <test/fixtures>
//
// Expected values come from outside this code: the GEOM numbers the page itself computes, the page's
// own hash run in node (names and coats), and the invented fixtures' construction. A test that only
// asked the C++ what it thinks would prove nothing.

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <filesystem>
#include <vector>
#include <fstream>
#include <set>
#include <sstream>
#include <string>

#include "catio/art.h"
#include "catio/draw.h"
#include "catio/house.h"
#include "catio/manor.h"
#include "catio/ui.h"
#include "catio/view.h"
#include "internal.h"

namespace {

int pass = 0, fail = 0;

void check(bool ok, const char* what) {
    std::printf("%s %s\n", ok ? "PASS" : "FAIL", what);
    (ok ? pass : fail)++;
}

std::string slurp(const std::string& path) {
    std::ifstream in(path);
    std::stringstream s;
    s << in.rdbuf();
    return s.str();
}

using catio::manor::Box;
using catio::manor::Point;
bool same(const Box& a, int x, int y, int w, int h) { return a.x == x && a.y == y && a.w == w && a.h == h; }
bool same(const Point& p, int x, int y) { return p.x == x && p.y == y; }

void the_plan(const std::string& manor_json) {
    namespace m = catio::manor;
    check(!m::load("/no/such/manor.json") && !m::loaded(), "a missing plan says so rather than drawing an empty meadow");
    check(m::load(manor_json) && m::loaded(), "the generated plan loads");

    check(m::world().w == 960 && m::world().h == 576, "the grounds are 960 x 576 art pixels");

    // ORDER, as the page has it, and the plan's rooms: the same set, or a room was added to one only
    const char* order[] = {"dining", "kitchen", "living", "study", "hall", "sunroom", "garden", "brain", "bath", "bedroom"};
    bool in_order = m::geom().size() == 10;
    for (size_t i = 0; in_order && i < 10; ++i) in_order = m::geom()[i].key == order[i];
    check(in_order, "GEOM runs in the page's ORDER, ten rooms");

    // the numbers the page computes for GEOM
    const m::Geom* hall = m::of("hall");
    check(hall && hall->queen && same(*hall->queen, 348, 370), "the queen's seat is the hall's pink armchair, at (348, 370)");
    const m::Geom* dining = m::of("dining");
    check(dining && dining->cabinet && same(*dining->cabinet, 106, 72, 16, 27), "the café's filing cabinet is where the page puts it");
    const m::Geom* garden = m::of("garden");
    check(garden && garden->cabinet && same(*garden->cabinet, 704, 200, 22, 21), "the catio's cabinet is its chest");
    const m::Geom* brain = m::of("brain");
    check(brain && brain->litter && same(*brain->litter, 224, 150, 22, 21), "the library's chest is the litter box");
    check(dining && !dining->litter, "only the library has a litter box");
    const m::Geom* living = m::of("living");
    check(living && same(living->box, 512, 48, 181, 165), "the lounge's box is the plan's");

    check(m::level_of("brain") == m::Level::Upper && m::level_of("hall") == m::Level::Ground, "the library is upstairs, the hall down");
    check(m::level_of("landing") == m::Level::Upper, "the landing is upstairs, though it is not a room");

    // LINE: two rows of seven, from beside her seat to the hall's far wall
    const auto& line = m::line_spots();
    check(line.size() == 14, "the queue at the front door has fourteen places");
    check(line.size() == 14 && same(line[0], 370, 378) && same(line[6], 490, 378) && same(line[7], 370, 360),
          "the queue starts beside her and curls back a row");

    // the stair's steps, foot to top
    const auto& steps = m::flight();
    bool climbing = steps.size() == 4;
    for (size_t i = 1; climbing && i < steps.size(); ++i) climbing = steps[i].y < steps[i - 1].y;
    check(climbing && same(steps[0], 394, 291) && same(steps[3], 394, 219), "the stair has four steps, foot to top");

    // the free floor: inside the room's floor, and off every footprint (grown by 3)
    const auto& open = m::free_floor("hall");
    bool inside = !open.empty();
    for (const auto& p : open) inside = inside && p.x >= 277 && p.x < 512 && p.y >= 245 && p.y < 384;
    bool off = true;
    for (const auto& q : m::layout("hall"))
        if (const m::Piece* pc = m::piece(q.piece); pc && pc->foot.w)
            for (const auto& p : open)
                if (p.x >= q.x + pc->foot.x - 3 && p.x < q.x + pc->foot.x + pc->foot.w + 3 &&
                    p.y >= q.y + pc->foot.y - 3 && p.y < q.y + pc->foot.y + pc->foot.h + 3) off = false;
    check(inside, "the hall's free floor is on the hall's floor");
    check(off, "no free-floor point stands on furniture");

    // NEXT: whatever it answers is on the same floor, and that way, within 45 degrees
    bool sane = true;
    int answers = 0;
    const int ways[4][2] = {{-1, 0}, {1, 0}, {0, -1}, {0, 1}};
    for (const auto& a : m::geom())
        for (int d = 0; d < 4; ++d) {
            auto b = m::next_room(a.key, static_cast<m::Dir>(d));
            if (b.empty()) continue;
            ++answers;
            const m::Geom* g = m::of(b);
            const double ax = a.box.x + a.box.w / 2.0, ay = a.box.y + a.box.h / 2.0;
            const double bx = g->box.x + g->box.w / 2.0, by = g->box.y + g->box.h / 2.0;
            const double along = (bx - ax) * ways[d][0] + (by - ay) * ways[d][1];
            const double side = std::abs((bx - ax) * ways[d][1] + (by - ay) * ways[d][0]);
            sane = sane && g->level == a.level && along > 0 && side <= along;
        }
    check(answers > 0 && sane, "an arrow or a swipe goes to a room that way, on the same floor");
}

void the_house(const std::string& dir) {
    catio::House h;
    check(!h.ready(), "a house is not ready before its first read");
    h.docs(slurp(dir + "/db.json"));
    h.agents(slurp(dir + "/agents.json"));
    check(h.ready() && !h.never_set_up(), "a café with rooms is set up");
    check(h.name() == "The Test Café", "the café's own name");

    const auto& cats = h.cats();
    check(cats.size() == 7, "seven cats: six agents and one adopted chat; the archived one and the queen are not among them");
    check(h.cats(true).size() == 8, "everything includes the archived one, and still not the queen");
    bool queenless = true;
    for (const auto& c : h.cats(true)) queenless = queenless && c.id != "agent:queen";
    check(queenless, "the queen is never a cat: she would make the badge a liar");

    // MOODS rank, then the most recently heard from
    const char* want[] = {"agent:a4", "agent:a1", "adopted:café", "agent:a3", "agent:a2", "agent:a6", "agent:a5"};
    bool ordered = cats.size() == 7;
    for (size_t i = 0; ordered && i < 7; ++i) ordered = cats[i].id == want[i];
    check(ordered, "cats sort by mood rank, then the newest first");

    const catio::Cat* a1 = h.cat("agent:a1");
    check(a1 && a1->mood == catio::Mood::Meow && a1->ask == "Approve the copy?", "needs is a meowing cat, with its ask");
    check(a1 && a1->room == "study", "a repo the craft room lists lives in the craft room");
    check(a1 && a1->link == "https://claude.ai/code/session_abc123", "a Claude Code cat links its session, cse_ becoming session_");
    const catio::Cat* a2 = h.cat("agent:a2");
    check(a2 && a2->room == "living", "a repo no room lists goes to the catch-all, the first open room");
    check(a2 && a2->name == "Pistache", "an unnamed cat is named by the page's own hash");
    check(a2 && a2->coat == 1, "projects/<key>.coat is the look she chose for a project");
    const catio::Cat* a4 = h.cat("agent:a4");
    check(a4 && a4->mood == catio::Mood::Cry && a4->name == "Noisette", "failed is upset");
    const catio::Cat* a6 = h.cat("agent:a6");
    check(a6 && a6->room == "living", "a cat whose room is closed goes to the catch-all");
    check(!h.open("bath") && h.room("bath").closed, "the ensuite is closed");

    const catio::Cat* chat = h.cat("adopted:café");
    check(chat && chat->adopted && chat->mood == catio::Mood::Meow && chat->ask == "Which oven?", "an adopted chat that needs her");
    check(chat && chat->name == "Réglisse", "the hash walks code points, as the page's does, not bytes");
    check(chat && chat->project == "bakery-business-plan" && chat->coat == 2, "a chat's project is its title, and its coat the hash");

    check(h.needing().size() == 4, "four need her: upset, two meowing, one to review");
    const auto q = h.queue();
    check(q.size() == 2 && q[0]->id == "adopted:café" && q[1]->id == "agent:a1",
          "only the meowing cats queue, the longest wait first");
    check(h.needing_on("ground") == 4 && h.needing_on("upper") == 0, "the floor badges count a cat where it stands");

    check(h.queen().name == "Duchesse", "her name is hers");
    check(h.queen().keeps.size() == 2 && h.queen().keeps[0].pinned, "what she says aloud comes first");
    check(h.queen_state() == catio::QueenState::Away, "no word from her runner for two minutes: she is asleep");
    check(h.queen_room() == "hall", "she sits in the hall");
    const auto gifts = h.handoffs();
    check(gifts.size() == 1 && gifts[0]->id == "agent:a4", "a word newer than her card was opened is a handoff");

    catio::House empty;
    empty.docs(R"({"docs": {}})");
    check(empty.never_set_up(), "a café with no rooms at all is one nobody has opened: the wizard");
    check(empty.queen().name == "Simone", "a queen with no name of her own is named by the page's hash");
}

// The draw list: the page's layering rules, checked without a window.
void the_draw_list(const std::string& dir) {
    namespace m = catio::manor;
    namespace v = catio::view;
    catio::House h;
    h.docs(slurp(dir + "/db.json"));
    h.agents(slurp(dir + "/agents.json"));

    const v::Scene ground = v::build(h, m::Level::Ground);
    check(ground.queen.has_value() && ground.queen->room == "hall", "the queen sits in the hall on the ground floor");
    check(ground.cats.size() == 6, "six cats on the ground floor; the seventh is upstairs in the library");
    const auto gl = v::world(ground, m::Level::Ground, 0);
    check(!gl.empty() && gl.front().sheet == catio::art::Id::Meadow && gl.front().z == -100, "the meadow is under everything");
    bool upstairs = false;
    for (const auto& b : gl) upstairs = upstairs || b.z >= 3850 || b.sheet == catio::art::Id::HouseUpper;
    check(!upstairs, "nothing from upstairs shows on the ground floor");

    // .cat[data-line]'s clip-path: the queued cats show their middle 44 pixels
    int clipped = 0;
    for (const auto& c : ground.cats)
        if (c.queue_place >= 0) {
            v::Scene one;
            one.cats.push_back(c);
            for (const auto& b : v::world(one, m::Level::Ground, 0))
                if (b.sheet == catio::art::Id::Pochi && b.dst.w == 44 && b.src.w == 44) ++clipped;
        }
    check(clipped == 2, "both queued cats are clipped to their middle 44 pixels, as the page's clip-path does");

    // an exact tie: a cat whose feet are on a floor piece's bottom edge draws after it, as #cats after #props
    const m::Placed* desk = nullptr;
    for (const auto& q : m::layout("hall"))
        if (const m::Piece* pc = m::piece(q.piece); pc && pc->layer == m::Layer::Floor) { desk = &q; break; }
    bool tie = false;
    if (desk) {
        const m::Piece* pc = m::piece(desk->piece);
        v::Scene one;
        v::Spot sp;
        sp.mood = catio::Mood::Idle;
        sp.at = m::Point{desk->x + 4, desk->y + pc->cell.h};
        sp.room = "hall";
        one.cats.push_back(sp);
        const auto list = v::world(one, m::Level::Ground, 0);
        int at_piece = -1, at_cat = -1;
        for (int i = 0; i < int(list.size()); ++i) {
            if (list[i].dst.x == desk->x * 2 && list[i].dst.y == desk->y * 2 && list[i].sheet != catio::art::Id::MochiIdle) at_piece = i;
            if (list[i].sheet == catio::art::Id::MochiIdle) at_cat = i;
        }
        tie = at_piece >= 0 && at_cat > at_piece && list[at_piece].z == list[at_cat].z;
    }
    check(tie, "on an exact tie with furniture, the cat wins");

    // "top" pieces sit one above the floor piece they are set into
    bool tops = true;
    int seen = 0;
    for (const auto& b : gl)
        if (b.sheet == catio::art::Id::Furniture || b.sheet == catio::art::Id::FurnitureLicensed)
            for (const auto& g : m::geom())
                for (const auto& q : m::layout(g.key))
                    if (const m::Piece* pc = m::piece(q.piece); pc && pc->layer == m::Layer::Top &&
                        b.dst.x == q.x * 2 && b.dst.y == q.y * 2 && g.level == m::Level::Ground) {
                        ++seen;
                        tops = tops && b.z == 1001 + (q.y + pc->cell.h) * 2;
                    }
    check(seen > 0 && tops, "a piece set into a counter draws one above it");

    // the upper floor: the ground below, dimmed, under its own plate; everything upstairs lifted by 4000
    const v::Scene upper = v::build(h, m::Level::Upper);
    check(upper.cats.size() == 1 && !upper.queen, "upstairs: the one cat in the library, and no queen");
    const auto ul = v::world(upper, m::Level::Upper, 0);
    bool dim = false, plate = false, below = false, lifted = true;
    for (const auto& b : ul) {
        if (b.fill && b.z == 3850 && b.colour.a == 128) dim = true;
        if (b.sheet == catio::art::Id::HouseUpper && b.z == 3900) plate = true;
        if ((b.sheet == catio::art::Id::Furniture || b.sheet == catio::art::Id::FurnitureLicensed) && b.z < 3850) below = true;
    }
    for (const auto& c : upper.cats) {
        v::Scene one;
        one.cats.push_back(c);
        for (const auto& b : v::world(one, m::Level::Upper, 0))
            if (b.sheet == catio::art::Id::Pochi || b.sheet == catio::art::Id::MochiIdle || b.sheet == catio::art::Id::MochiBox)
                lifted = lifted && b.z >= 4000;
    }
    check(dim && plate, "the upper floor dims the ground at 3850 and lays its own plate at 3900");
    check(below, "from upstairs the ground's furniture still shows, under the dim");
    check(lifted, "an upstairs cat is lifted above it all");
}

}  // namespace

// The interface's words and shapes, from the page's own rules: showTip(), the menu builders, list() and
// placeMenu(). What each should say is read off catio/index.html and the invented fixtures, not off ui.cpp.
void the_interface(const std::string& dir) {
    namespace v = catio::view;
    namespace ui = catio::ui;
    using catio::Mood;
    using ui::Action;
    using ui::Block;
    catio::House h;
    h.docs(slurp(dir + "/db.json"));
    h.agents(slurp(dir + "/agents.json"));
    v::Stage stage{1280, 800, 1};
    v::Cam cam = v::fit(catio::manor::world(), stage);
    const v::Scene scene = v::build(h, catio::manor::Level::Ground);
    ui::Frame f;
    f.house = &h, f.scene = &scene, f.cam = &cam, f.stage = stage;
    f.clock_ms = 1791000400000 + 5 * 60000;
    f.live = "On this computer";

    // summary() and ago(), word for word
    catio::Cat cry, meow1, meow2;
    cry.mood = Mood::Cry, meow1.mood = meow2.mood = Mood::Meow;
    check(ui::summary({&cry, &meow1, &meow2}) == "1 upset, 2 meowing", "a room's cats in words, the most urgent first");
    check(ui::summary({}) == "no cats", "an empty room says no cats");
    const std::int64_t now = 1791000000000;
    check(ui::ago(now - 20000, now) == "just now" && ui::ago(now - 5 * 60000, now) == "5 min ago" && ui::ago(now - 3 * 3600000, now) == "3 h ago" &&
          ui::ago(now - 24 * 3600000LL, now) == "yesterday" && ui::ago(now - 4 * 24 * 3600000LL, now) == "4 days ago" && ui::ago(0, now).empty(),
          "ago() says just now, minutes, hours, yesterday and days as the page does");

    // the queen's line: her pinned note is what she is saying, while she is not answering
    check(ui::queen_line(h) == "Said aloud", "the queen's line is the note she is saying");

    // every list has one default, its first item
    auto one_primary = [](const ui::Menu& m) {
        for (const Block& b : m.blocks)
            if (b.kind == Block::Kind::List) {
                int n = 0;
                for (const auto& it : b.items) n += it.primary;
                if (n != 1 || !b.items.front().primary) return false;
            }
        return true;
    };
    auto items = [](const ui::Menu& m) {
        std::vector<std::string> out;
        for (const Block& b : m.blocks) for (const auto& it : b.items) out.push_back(it.label);
        return out;
    };
    auto has = [&](const ui::Menu& m, const std::string& label) {
        const auto l = items(m);
        return std::find(l.begin(), l.end(), label) != l.end();
    };

    // the kitchen: its upset cat, then the queen's said note, then the actions
    const ui::Menu kitchen = ui::menu_for(f, v::Thing::Room, "kitchen");
    check(kitchen.title == "Kitchen" && kitchen.need.size() == 1 && kitchen.need[0]->mood == Mood::Cry, "a room's menu: its name, and a badge for the cat that needs her");
    check(!kitchen.blocks.empty() && kitchen.blocks[0].kind == Block::Kind::Cats && kitchen.blocks[0].rows.size() == 1 &&
          kitchen.blocks[0].rows[0].text == "Waiting for you.", "then the cats that need her, each with its ask");
    check(kitchen.blocks.size() > 1 && kitchen.blocks[1].kind == Block::Kind::Ask && kitchen.blocks[1].crown && kitchen.blocks[1].text == "Said aloud",
          "then the queen's note, when she is saying one, with her crown");
    check(one_primary(kitchen) && items(kitchen).front() == "Look in", "its default is Look in");
    check(has(kitchen, "Files") && !has(ui::menu_for(f, v::Thing::Room, "sunroom"), "Files"), "Files only where the room has a filing cabinet");
    check(has(ui::menu_for(f, v::Thing::Room, "brain"), "The brain") && has(ui::menu_for(f, v::Thing::Room, "brain"), "Choose files"),
          "the library's menu has the brain, and chooses files for it");
    const ui::Menu adding = ui::menu_for(f, v::Thing::Room, "kitchen", true);
    check(items(adding) == std::vector<std::string>{"Adopt a chat", "Back"}, "Add a cat adopts a chat: New session is claude.ai's alone");
    const ui::Menu closed = ui::menu_for(f, v::Thing::Room, "bath");
    check(closed.sub == "Closed" && items(closed) == std::vector<std::string>{"Open this room", "Edit rooms"}, "a closed room's menu is its name, Closed, and two ways to open it");
    v::Cam in_kitchen = cam;
    in_kitchen.focus = "kitchen";
    f.cam = &in_kitchen;
    check(items(ui::menu_for(f, v::Thing::Room, "kitchen")).front() == "Whole house", "in the room already, its default is Whole house");
    f.cam = &cam;

    // the House menu: how the cats reach her, the actions, the credits at its foot word for word
    const ui::Menu house = ui::menu_for(f, v::Thing::House, "house");
    check(!house.blocks.empty() && house.blocks[0].kind == Block::Kind::Sub && house.blocks[0].text.rfind("On this computer. ", 0) == 0,
          "the House menu starts with how the cats are reaching her");
    check(house.blocks.back().kind == Block::Kind::Foot &&
          house.blocks.back().text.find("Game UI Pack created by SC_siosio") != std::string::npos, "SC_siosio's credit, word for word, at its foot");
    bool switch_last = false;
    for (const Block& b : house.blocks)
        if (b.kind == Block::Kind::List) switch_last = b.items.back().label == "Still cats" && b.items.back().toggle == 0;
    check(switch_last && one_primary(house), "Still cats is a switch, off");

    // the queen: crowned, away (no runner), her line in the well, the rest of what she keeps
    const ui::Menu queen = ui::menu_for(f, v::Thing::Queen, "hall");
    check(queen.title == "Duchesse" && queen.crown && queen.sub == "Queen of the house · away", "the queen's menu: her name, crowned, and that she is away");
    check(queen.blocks.size() > 1 && queen.blocks[0].kind == Block::Kind::Ask && queen.blocks[0].need && queen.blocks[1].kind == Block::Kind::Keeps &&
          queen.blocks[1].rows.size() == 1 && queen.blocks[1].rows[0].text == "Kept, not said", "her line first, then what else she keeps");
    check(items(queen) == std::vector<std::string>{"Talk to her", "What she keeps", "Look in"}, "Talk to her is the default");
    check(queen.need.empty(), "the queen is never counted among the cats that need her");

    // a cat: its link first when it has one, its ask in the well
    const ui::Menu a1 = ui::menu_for(f, v::Thing::Cat, "agent:a1");
    check(a1.face == 1 && !a1.blocks.empty() && a1.blocks[0].kind == Block::Kind::Ask && a1.blocks[0].text == "Approve the copy?",
          "a cat's menu: its face, then its ask");
    bool open_first = false;
    for (const Block& b : a1.blocks)
        if (b.kind == Block::Kind::List) open_first = b.items[0].label == "Open" && b.items[0].arg == "https://claude.ai/code/session_abc123" && b.items[1].label == "Talk";
    check(open_first, "Open goes to its session; Talk after it");
    check(ui::menu_for(f, v::Thing::Cat, "agent:nobody").title.empty(), "a cat that has gone has no menu");

    // the hover line
    const ui::Tip t1 = ui::tip_for(f, v::Hit{v::Thing::Cat, "agent:a1", {}});
    check(t1.name == h.cat("agent:a1")->name && t1.small == "Needs you" && t1.says == "Approve the copy?", "hovering a cat: its name, its mood, its ask");
    check(ui::tip_for(f, v::Hit{v::Thing::Stairs, "stairs", {}}).name == "Upstairs", "hovering the stair on the ground floor says Upstairs");
    const ui::Tip litter = ui::tip_for(f, v::Hit{v::Thing::Litter, "brain", {}});
    check(litter.name == "The litter box" && litter.says == "Nothing to sort.", "hovering the litter box says what waits in it");
    const ui::Tip bath = ui::tip_for(f, v::Hit{v::Thing::Room, "bath", {}});
    check(bath.name == "Ensuite" && bath.small == "closed" && bath.need.empty(), "a closed room is named closed, with no badge");
    const ui::Tip queen_tip = ui::tip_for(f, v::Hit{v::Thing::Queen, "hall", {}});
    check(queen_tip.name == "Duchesse" && queen_tip.small == "queen" && queen_tip.says == "Said aloud", "hovering the queen: her name, queen, and her line");

    // placeMenu
    using catio::draw::Pt;
    using catio::draw::Rect;
    const Rect panel{1000, 20, 260, 240};
    const Pt right = ui::place_menu(stage, v::Thing::Room, Rect{300, 300, 200, 150}, Pt{248, 300}, panel, 60);
    check(right.x == 512 && right.y == 300, "a room's menu opens on its right, level with its top");
    const Pt left = ui::place_menu(stage, v::Thing::Cat, Rect{1100, 500, 20, 20}, Pt{248, 200}, panel, 60);
    check(left.x == 1100 - 248 - 12, "with no room on the right, it opens on the left");
    const Pt under = ui::place_menu(stage, v::Thing::Room, Rect{700, 100, 200, 150}, Pt{248, 300}, panel, 60);
    const bool clear = under.x + 248 <= panel.x - 12 || under.x >= panel.x + panel.w + 12 || under.y >= panel.y + panel.h + 12 || under.y + 300 <= panel.y - 12;
    check(clear, "never under the map panel");
    const v::Stage phone{390, 844, 1};
    const Pt corner = ui::place_menu(phone, v::Thing::Room, Rect{20, 200, 360, 200}, Pt{248, 300}, Rect{300, 770, 60, 60}, 60);
    check(corner.x == 390 - 248 - 12 && corner.y == 200, "on a phone a room that fills the screen gets it in its corner");
    const Pt hud = ui::place_menu(stage, v::Thing::House, Rect{20, 20, 230, 42}, Pt{248, 400}, panel, 130);
    check(hud.x == 20 && hud.y == 138, "the House menu opens under the whole header, sign and all");

    // drawn, with no window and no pack art: the fonts are the committed Nunito, and the House menu answers
    SDL_Surface* s = SDL_CreateSurface(1280, 800, SDL_PIXELFORMAT_RGBA32);
    SDL_Renderer* r = s ? SDL_CreateSoftwareRenderer(s) : nullptr;
    catio::draw::Canvas canvas{r};
    catio::art::Art none(std::filesystem::temp_directory_path() / "catio-tests-no-art");
    none.scan();
    ui::Ui face;
    check(face.fonts(std::filesystem::path(CATIO_SOURCE_DIR) / "assets", none, 1), "the committed body font opens, with no pack art at all");
    const catio::draw::Ctx c{&canvas, &none, 2, 1};
    face.draw(c, f);
    ui::Action a = Action::None;
    std::string arg;
    const bool brand = face.press(f, 40, 40, &a, &arg);
    check(brand && a == Action::OpenHouse && face.menu_kind() == v::Thing::House, "pressing the brand opens the House menu");
    // every item, pressed once, a frame drawn between presses as the app draws one
    std::set<std::string> pressed;
    std::set<Action> seen;
    auto reopen = [&] {
        face.draw(c, f);
        if (face.menu_kind() != v::Thing::House) face.press(f, 40, 40, &a, &arg), face.draw(c, f);
    };
    for (float y = 60; y < 800; y += 4) {
        reopen();
        const std::string id(face.under(f, 60, y));
        if (id.rfind("menu:item:", 0) != 0 || !pressed.insert(id).second) continue;
        face.press(f, 60, y, &a, &arg);
        seen.insert(a);
    }
    check(pressed.size() == 8 && seen.count(Action::StillCats) && seen.count(Action::CheckNow), "all eight of the page's items are there and answer a press, Still cats among them");
    check(!seen.count(Action::OpenRules) && !seen.count(Action::OpenBrain) && !seen.count(Action::Sound) && !face.can(Action::OpenRules) && !face.cannot(Action::OpenRules).empty(),
          "what is not built yet does nothing, and says why");
    reopen();
    check(face.escape() && face.menu_kind() == v::Thing::None && !face.escape(), "Escape closes the menu, and then there is nothing to close");
    SDL_DestroyRenderer(r);
    SDL_DestroySurface(s);
}

int main(int argc, char** argv) {
    if (argc < 3) {
        std::fprintf(stderr, "catio_tests <generated/manor.json> <test/fixtures>\n");
        return 2;
    }
    the_plan(argv[1]);
    the_house(argv[2]);
    the_draw_list(argv[2]);
    the_interface(argv[2]);
    std::printf("\n%d passed, %d failed\n", pass, fail);
    return fail ? 1 : 0;
}
