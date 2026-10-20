// app.cpp -- the window, the loop, the camera, and the one place a press becomes a write.
//
// The page's pointer and keyboard handling, ported: drag to pan (any button), the wheel or a pinch to
// zoom, + / - / 0 and Shift+arrows, arrows between rooms, Page Up and Page Down between floors, M for
// the map, Escape back. Hover names a thing only when the pointer really moved; a click opens its menu;
// a double click on a room looks in. On a phone (a narrow stage) the café opens zoomed into the room
// that needs her most, and a quick sideways swipe in a room goes to the room next door.
//
// It draws the way catio_look does -- the floor into one world-sized target, scaled to the screen once
// -- with the meadow tiled under it to the stage's edges, the lit room's brackets and the outline round
// the cat under the pointer, then the interface.

#include "catio/app.h"

#include <algorithm>
#include <atomic>
#include <cctype>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <map>
#include <memory>
#include <optional>
#include <set>
#include <thread>
#include <sstream>
#include <string>
#include <vector>

#include <nlohmann/json.hpp>

#include "catio/manor.h"
#include "internal.h"

namespace catio {
namespace {

using ui::Action;
using view::Thing;

std::string slurp(const std::filesystem::path& p) {
    std::ifstream in(p, std::ios::binary);
    std::stringstream s;
    s << in.rdbuf();
    return s.str();
}

// SDL's files reach inside a phone's package (an APK's assets), where std::filesystem sees nothing
bool readable(const std::filesystem::path& p) {
    SDL_IOStream* io = p.empty() ? nullptr : SDL_IOFromFile(to_utf8(p).c_str(), "rb");
    if (io) SDL_CloseIO(io);
    return io != nullptr;
}
std::string read_shipped(const std::filesystem::path& p) {
    size_t n = 0;
    void* data = SDL_LoadFile(to_utf8(p).c_str(), &n);
    std::string out = data ? std::string(static_cast<const char*>(data), n) : std::string();
    SDL_free(data);
    return out;
}
// the first of these that is there: a file, or a folder holding `probe`
std::filesystem::path first_of(std::initializer_list<std::filesystem::path> ps, const char* probe = nullptr) {
    for (const auto& p : ps) if (!p.empty() && readable(probe ? p / probe : p)) return p;
    return {};
}

double clock_s() { return double(SDL_GetTicksNS()) / 1e9; }
std::int64_t wall_ms() {
    SDL_Time t = 0;
    SDL_GetCurrentTime(&t);
    return std::int64_t(t / 1000000);
}

// One thing that happened, from the window or from a --do step: the same path for both.
struct In {
    enum Kind { Move, Down, Up, Wheel, Key, Text, PinchBegin, Pinch, PinchEnd, Resize, Quit } kind = Move;
    float x = 0, y = 0, dy = 0, scale = 1;
    bool touch = false, shift = false;
    bool primary = true;   // the left button (or a finger): only it clicks, as the page's click; any button drags
    std::string key;
    double at = 0;
};

constexpr manor::Dir kArrows[] = {manor::Dir::Left, manor::Dir::Right, manor::Dir::Up, manor::Dir::Down};

// HH:MM, as the page's clock() puts it, in local time: SDL's, so it builds on Windows too
std::string clock_of(std::int64_t ms) {
    SDL_DateTime dt{};
    if (!SDL_TimeToDateTime(SDL_Time(ms) * 1000000, &dt, true)) return "";
    char buf[8];
    std::snprintf(buf, sizeof buf, "%02d:%02d", dt.hour, dt.minute);
    return buf;
}

// What each ticket was for.
enum class Ask { Login, Docs, Agents, Quizzes, Art, Write };
struct Asked {
    Ask what = Ask::Docs;
    art::Id art = art::Id::Count;
    std::string label;
    std::shared_ptr<std::shared_ptr<art::Fetched>> ready;   // a piece of art, decoded and kept on the net's thread
};

}  // namespace

struct App::Impl {
    // what it was started with
    std::filesystem::path data, home, art_dir, manor_json, assets, shot, prefs;
    std::string origin;            // her gateway; empty, a folder of documents
    bool own_cache = false;        // the art is in the app's own cache (not a folder she named with --art)
    int shot_w = 1280, shot_h = 800, shot_css = 1;
    bool shot_touch = false;
    std::string steps;

    // the window, or the surface a shot is drawn on
    SDL_Window* window = nullptr;
    SDL_Renderer* r = nullptr;
    SDL_Surface* surface = nullptr;
    SDL_Texture* world = nullptr;
    std::uint64_t world_key = 0;   // what the world target holds: 0, nothing yet (or the GPU lost it)
    SDL_Cursor* paw = nullptr;
    SDL_Cursor* point = nullptr;
    bool pointing = false;

    House house;
    std::unique_ptr<art::Art> art;
    draw::Canvas canvas{};
    ui::Ui ui;

    view::Stage stage;
    view::Cam cam;
    view::Scene scene;
    double now = 0, start = 0;
    bool still = false, coarse = false, quit = false;
    bool still_given = false;      // --still: for this run, not written to the prefs
    std::atomic<bool> away{false}; // in the background: a phone ends an app that draws there
    std::vector<In> pending;       // what happened and isn't handled yet: one press a frame
    std::string live = "On this computer", status;

    // the gateway
    std::unique_ptr<net::Net> net;
    std::map<std::uint32_t, Asked> asked;
    Phase phase = Phase::Running;
    ui::SignIn form;
    double last_read = -1e9;       // when the 30-second clock last struck
    int reads_out = 0;             // documents, cats and homework still on their way
    bool read_once = false;
    bool read_again = false;       // a read was asked for while one was out
    std::string net_trouble, art_trouble, said, toast;
    double said_until = 0;
    bool said_bad = false;         // what was said is an error (the sign), not news (the toast)
    bool read_failed = false;      // a read in this batch failed: its trouble stands until a whole batch is clean
    bool got_docs = false, got_agents = false;   // the house needs both before it is drawn as hers
    float wheel = 0;               // a trackpad's fractions of a notch, added up, within one gesture
    double wheel_at = -1;
    bool vsync = false;            // the display paces the frames; without it the loop does
    std::int64_t live_at = 0;
    std::set<art::Id> fetching;
    std::set<art::Id> unkept;      // fetched but not written to the cache (full or read-only): not asked for again
    std::set<art::Id> failed;      // refused or broken: not asked for again until Check now, while the rest come
    std::string cache_trouble;

    // the pointer
    std::optional<draw::Pt> pointer;   // where it last really moved
    bool pressed = false, on_ui = false, dragging = false, on_map = false;
    draw::Pt press_at, last_at;
    double press_t = 0;
    double last_click_t = -1;
    std::string last_click_room;
    bool scrolling = false;            // a finger dragging a menu or a card: its lift is not a press
    std::string press_on;              // what of the interface it went down on: let go elsewhere, it is no press
    bool pinching = false;             // two fingers: the first finger's mouse is not a drag, a swipe or a click
    float pinch = 1;
    float map_off_x = 0, map_off_y = 0;   // a minimap drag: from the finger's spot to the view's centre, as grabbed
    std::map<SDL_FingerID, draw::Pt> fingers;   // where each finger is, for the point a pinch zooms about

    float k() const { return float(std::max(1, stage.css)); }
    int u_ui() const { return stage.u(); }

    ui::Frame frame() const {
        ui::Frame f;
        f.house = &house;
        f.scene = &scene;
        f.cam = &cam;
        f.stage = stage;
        f.now = now;
        f.clock_ms = wall_ms();
        f.coarse = coarse;
        f.still = still;
        f.live = !origin.empty() ? (live_at && net_trouble.empty() ? "Live through your gateway \u00b7 " + clock_of(live_at) : "Not live") : live;
        f.status = status;
        f.toast = toast;
        f.gateway = net != nullptr;
        return f;
    }

    // ---- the house, from a folder until the network code lands ----

    // The scene points into the house's cats: whatever changes the house builds it again at once, before another
    // event in the same batch picks a cat out of it.
    void rescene() {
        scene = view::build(house, cam.floor);
        // a cat that started meowing has walked to the line: the hover line names what is under the pointer now,
        // or nothing, as anything that slides under a still pointer
        if (ui.tipped().what != Thing::None && pointer) ui.tip(frame(), pick(pointer->x, pointer->y), false);
    }

    bool read_house() {
        const std::string db = slurp(data / "db.json"), agents = slurp(data / "agents.json");
        if (db.empty()) { std::fprintf(stderr, "catio_app: no db.json in %s\n", to_utf8(data).c_str()); return false; }
        house.docs(db);
        house.agents(agents.empty() ? R"({"agents": []})" : agents);
        if (const std::string q = slurp(data / "quizzes.json"); !q.empty()) house.quizzes(q);
        rescene();
        return true;
    }

    // The sign under the brand says only what is wrong (with the pack's cross); progress and what went right are
    // the toast at the foot of the screen, as the page's toast and stage message are.
    void say_status() {
        std::vector<std::string> wrong, told;
        if (now < said_until && !said.empty()) (said_bad ? wrong : told).push_back(said);
        if (!net_trouble.empty()) wrong.push_back(net_trouble);
        else if (phase == Phase::FirstRead) told.push_back("Waking the cats\u2026");
        if (phase == Phase::Setup) wrong.push_back("This caf\u00e9 has no rooms yet: set it up in a browser for now, at your gateway's address.");
        if (!art_trouble.empty()) wrong.push_back(art_trouble);
        else if (art && art->have() < art->total()) {
            const std::string n = std::to_string(art->have()) + " of " + std::to_string(art->total());
            if (!fetching.empty()) told.push_back("Fetching the caf\u00e9's art\u2026 (" + n + ")");
            else if (origin.empty()) wrong.push_back("The caf\u00e9's art isn't all here (" + n + "): it comes from your gateway once you sign in.");
            else if (const auto miss = art->missing(); read_once && std::any_of(miss.begin(), miss.end(), [&](const art::File* m) {
                         return !failed.count(m->id) && !unkept.count(m->id);
                     }))
                wrong.push_back("The caf\u00e9's art isn't all here yet (" + n + "): the rest is asked for again with the next read.");
        }
        if (!cache_trouble.empty()) wrong.push_back(cache_trouble);
        if (origin.empty() && data == from_utf8(CATIO_SOURCE_DIR) / "test" / "fixtures")
            wrong.push_back("Example cats, not yours: give the app your gateway (--gateway) to see your caf\u00e9.");
        status.clear(), toast.clear();
        for (const auto& w : wrong) status += (status.empty() ? "" : " ") + w;
        for (const auto& t : told) toast += (toast.empty() ? "" : " ") + t;
    }
    void say(std::string what, bool bad, double secs) { said = std::move(what), said_bad = bad, said_until = now + secs; }

    // ---- the gateway ----

    void ask(Ask what, net::Job job, art::Id id = art::Id::Count, std::string label = {},
             std::shared_ptr<std::shared_ptr<art::Fetched>> ready = {}) {
        if (!net) return;
        asked[net->send(std::move(job))] = Asked{what, id, std::move(label), std::move(ready)};
        if (what == Ask::Docs || what == Ask::Agents || what == Ask::Quizzes) ++reads_out;
    }
    // the documents, the cats and the homework, together, as the page reads them
    void read_all() {
        last_read = now;
        if (!net) return;
        if (reads_out) { read_again = true; return; }   // after a write: read again as soon as this read is back
        read_again = false;
        read_failed = false;
        ask(Ask::Docs, [](net::Gateway& g) { return g.docs(); });
        ask(Ask::Agents, [](net::Gateway& g) { return g.tool("list_agents", "{}"); });
        ask(Ask::Quizzes, [](net::Gateway& g) { return g.tool("quizzes", "{}"); });
    }
    // what the cache lacks, the house and the meadow first: a few at a time, each one that lands asking for the next,
    // so a read or her press never waits behind the whole download
    void fetch_art() {
        if (!net || !art) return;
        for (const art::File* file : art->missing()) {
            if (fetching.size() >= 4) break;
            if (fetching.count(file->id) || unkept.count(file->id) || failed.count(file->id)) continue;
            fetching.insert(file->id);
            const std::string path(file->path);
            const art::Id id = file->id;
            // fetched and decoded on the net's thread; written to the cache when the frame loop adopts it
            auto ready = std::make_shared<std::shared_ptr<art::Fetched>>();
            ask(Ask::Art, [path, id, ready](net::Gateway& g) {
                net::Reply r = g.art(path);
                if (r.ok()) *ready = art::prepare(id, std::move(r.body)), r.body = {};
                return r;
            }, id, path, ready);
        }
    }
    void sign_in() {
        if (form.busy) return;
        if (!form.ask_origin && !net) { form.ask_origin = true, form.field = 0, form.problem = "Fill in your gateway's address."; return; }
        if ((form.ask_origin && net::bare(form.origin).empty()) || form.user.empty() || form.password.empty()) {
            form.problem = form.ask_origin && net::bare(form.origin).empty() ? "Fill in your gateway's address." : form.user.empty() ? "Fill in your handle." : "Fill in your password.";
            form.field = form.ask_origin && net::bare(form.origin).empty() ? 0 : form.user.empty() ? 1 : 2;
            return;
        }
        if (form.ask_origin) {
            const std::string o = net::bare(form.origin);
            if (!net::safe_origin(o)) { form.problem = "Your gateway's address starts with https://."; return; }
            if (o != origin || !net) origin = o, net = std::make_unique<net::Net>(origin, home / "cookie");
        }
        form.busy = true;
        form.problem.clear();
        const std::string user = form.user, password = form.password;
        ask(Ask::Login, [user, password](net::Gateway& g) { return g.login(user, password); });
    }
    // The art an account's sign-in fetched, and everything drawn from it. The packs' licences are personal, so the
    // next person to sign in on this device gets what the gateway serves them, not what it served her. (Not a folder
    // she named with --art: that is hers to keep.)
    void forget_art() {
        if (!own_cache || !art) return;
        ui.forget_art();      // first: an open font holds its file, which Windows then won't delete
        draw::forget_tints();
        forget_cursors();
        art->forget_all();
        fetching.clear(), unkept.clear(), failed.clear(), cache_trouble.clear();
    }
    // whose art the cache holds: the gateway and the handle that fetched it
    std::filesystem::path owner_file() const { return home / "art-owner"; }
    std::string owner_now() const {
        std::string user = net::bare(form.user);   // as registry.js's checkPassword reads it: trimmed, lower case
        for (char& ch : user) ch = char(std::tolower(static_cast<unsigned char>(ch)));
        return origin + "\n" + user + "\n";
    }

    // Back to the sign-in: she signed out (`leaving`), or the cookie ran out. Nothing of the session stays: its queued
    // work, its cookie, its house. Signing out forgets the art too; a cookie that ran out keeps it, since the one to
    // sign in next is most likely her, and a sign-in as anyone else forgets it then (heard()'s Login).
    void signed_out(std::string why, bool leaving = false) {
        if (net) net->drop_waiting(), net->forget_cookie();
        house.clear();
        rescene();
        got_docs = got_agents = read_once = false;
        live_at = 0;
        net_trouble.clear(), art_trouble.clear();
        failed.clear();   // what failed is asked for again after the next sign-in, as the sign will say
        if (leaving) {
            forget_art();
            std::error_code ec;
            std::filesystem::remove(owner_file(), ec);
        }
        // a press held through it is over: its release lands on the sign-in, and nothing of it is a drag later
        pressed = dragging = scrolling = on_ui = on_map = pinching = false;
        phase = Phase::SignIn;
        form.busy = false;
        form.password.clear();
        form.field = form.ask_origin && form.origin.empty() ? 0 : form.user.empty() ? 1 : 2;
        form.problem = std::move(why);
        ui.close_menu();
        ui.close_card();
        ui.online(false);
        reads_out = 0;
        asked.clear();     // what comes back for them now has nowhere to go
        fetching.clear();  // so the art they were fetching is asked for again after the next sign-in
    }
    void heard(const Asked& a, net::Reply& r) {
        const bool read = a.what == Ask::Docs || a.what == Ask::Agents || a.what == Ask::Quizzes;
        if (net::signed_out(r) && a.what != Ask::Login) { signed_out("Signed out: sign in again."); return; }
        if (read) --reads_out;
        if (r.err.code == "unreachable") {
            switch (a.what) {
                case Ask::Login: form.busy = false, form.problem = "Can't reach " + origin + ": " + r.err.message; return;
                case Ask::Write: say("Your gateway couldn't be reached, so that wasn't done: try again.", true, 6); return;
                case Ask::Art: fetching.erase(a.art); break;   // asked for again with the next read
                default: read_failed = true; break;
            }
            net_trouble = "Can't reach your gateway (" + r.err.message + "). Trying again in half a minute.";   // the clock reads again
            if (read) settle_reads();
            return;
        }
        switch (a.what) {
            case Ask::Login:
                form.busy = false;
                if (!r.ok()) {   // as the gateway's page comes back: the handle kept, the password to type again
                    form.problem = r.err.message;
                    form.password.clear();
                    form.field = 2;
                    return;
                }
                form.password.clear();
                form.problem.clear();
                if (slurp(owner_file()) != owner_now()) {   // another account's art, or nobody's: not this one's to see
                    forget_art();
                    std::ofstream(owner_file(), std::ios::binary) << owner_now();   // read back as bytes: no \r\n
                }
                phase = Phase::FirstRead;
                save_prefs();   // the address that worked
                read_all();
                return;
            case Ask::Docs:
            case Ask::Agents:
            case Ask::Quizzes:
                if (!r.ok()) {
                    // an older gateway has no homework tool: nothing is wrong, there is just no homework
                    if (a.what == Ask::Quizzes && r.err.code == "not_found") { settle_reads(); return; }
                    read_failed = true;
                    net_trouble = "Your gateway didn't answer (" + r.err.code + "): " + r.err.message;
                } else if (a.what == Ask::Docs ? house.docs(r.body) : a.what == Ask::Agents ? house.agents(r.body) : house.quizzes(r.body)) {
                    rescene();
                    if (a.what == Ask::Docs) got_docs = true;
                    if (a.what == Ask::Agents) got_agents = true, live_at = wall_ms();
                } else {   // a 200 that isn't the café's answer (a portal's page): the house keeps what it had
                    read_failed = true;
                    net_trouble = "Your gateway's answer wasn't the caf\u00e9's: something may be standing in front of it.";
                }
                settle_reads();
                return;
            case Ask::Art:
                fetching.erase(a.art);
                if (!r.ok()) {
                    // a moment's trouble (busy, a 5xx) is asked again with the next read; a piece that isn't there waits
                    // for Check now: the packs' art is served to the café's first owner alone, once move-in.py has run
                    if (r.err.code != "busy" && r.err.code != "unavailable") failed.insert(a.art);
                    art_trouble = r.err.code == "not_found"
                        ? "Your gateway has no " + a.label + ": it serves the packs' art to the caf\u00e9's first owner alone, once move-in.py has uploaded it. Check now tries again."
                        : "The caf\u00e9's art couldn't all come (" + r.err.code + "). Check now tries again.";
                    fetch_art();   // the rest still comes
                    return;
                }
                if (!art->adopt(a.art, a.ready ? *a.ready : nullptr)) {
                    if (art->trouble() != "cache_unwritable") {
                        failed.insert(a.art);
                        art_trouble = "A piece of the art came back broken (" + a.label + ", " + std::string(art->trouble()) + "). Check now tries again.";
                    } else {   // drawn now if it could be decoded, but not kept
                        unkept.insert(a.art);
                        cache_trouble = "The app can't keep its art in " + to_utf8(art_dir) + " (full, or not writable): it is fetched again next time.";
                    }
                }
                fetch_art();
                if (a.art == art::Id::SproutFont) ui.fonts(assets, *art, stage.css);
                if (a.art == art::Id::UiCursor || a.art == art::Id::UiCursorPoint) make_cursors();
                return;
            case Ask::Write:
                if (!r.ok()) { say("Your gateway didn't take it (" + r.err.code + "): " + r.err.message, true, 6); return; }
                if (!a.label.empty()) say(a.label, false, 4);
                last_read = -1e9;   // see the change at once
                return;
        }
    }

    // Once the whole batch is back: its trouble stands if any of it failed, and the house is hers once its documents
    // and its cats have come (the homework can fail without keeping her out: an older gateway has no `quizzes`).
    // Whether it is still waiting to be set up is asked again every time, so setting it up in a browser shows here.
    void settle_reads() {
        if (reads_out) return;
        if (read_again) { read_all(); return; }
        if (!read_failed) net_trouble.clear();
        if (!got_docs || !got_agents || phase == Phase::SignIn) return;
        const bool first = phase == Phase::FirstRead;
        phase = house.never_set_up() ? Phase::Setup : Phase::Running;
        if (first) {
            read_once = true;
            ui.online(true);
            fetch_art();
        }
    }

    // ---- prefs: the map folded or open, still cats ----

    void load_prefs() {
        if (prefs.empty()) return;
        try {
            const auto j = nlohmann::json::parse(slurp(prefs));
            if (j.contains("minimap")) ui.set_map_open(j["minimap"] == "open");
            still = still || j.value("still", false);   // --still stays still
            if (form.ask_origin && j.contains("gateway") && j["gateway"].is_string()) form.origin = j["gateway"].get<std::string>();
        } catch (...) {}
    }
    void save_prefs() {
        if (prefs.empty() || !shot.empty()) return;
        // what this run doesn't set stays: a run with --gateway <url> keeps the address the sign-in screen saved
        nlohmann::json j = nlohmann::json::parse(slurp(prefs), nullptr, false);
        if (!j.is_object()) j = nlohmann::json::object();
        if (ui.map_known()) j["minimap"] = ui.map_open() ? "open" : "folded";   // not a phone's default before its first frame
        if (!still_given) j["still"] = still;
        if (form.ask_origin && !origin.empty()) j["gateway"] = origin;
        std::ofstream(prefs) << j.dump();
    }

    // ---- the camera ----

    // Every camera move goes through here. What slides under a still pointer isn't named until she moves.
    void place(view::Cam c) {
        c = view::clamp(c, stage);
        c.floor = cam.floor;
        c.focus = cam.focus;
        cam = c;
        ui.tip(frame(), {}, false);
    }
    void fit_to(manor::Box b) { place(view::fit(b, stage)); }
    // go(): into a room or back out to the whole house, changing floor first when the room is on the other
    void go(const std::string& room) {
        ui.close_menu();
        if (!room.empty() && manor::level_of(room) != cam.floor) set_floor(manor::level_of(room));
        cam.focus = room;
        fit_to(room.empty() ? manor::world() : view::padded(room));
    }
    // after she moves the camera herself: the room filling the view is the one she's in
    void settle() { cam.focus = view::room_in_view(cam, stage); }
    void set_floor(manor::Level f) {
        if (f == cam.floor) return;
        ui.close_menu();
        ui.tip(frame(), {}, false);
        cam.floor = f;
        if (!cam.focus.empty() && manor::level_of(cam.focus) != f) cam.focus.clear();
        rescene();
    }
    // the room that needs her most, for a phone's first view (her fix to "the house is tiny")
    // -- the upset cat first, upstairs or down (go() changes floor)
    std::string urgent_room() const {
        const auto need = ui::urgent_first(house.needing());   // the page's urgentFirst: upset, then meowing, then the rest
        return need.empty() ? "" : std::string(stands_in(*need.front()));
    }

    // ---- the frame ----

    void resize(int w, int h, float content_scale) {
        stage.w = w, stage.h = h;
        const int was = stage.css;
        stage.css = draw::css_for(content_scale);
        ui.fonts(assets, *art, stage.css);
        if (stage.css != was) forget_cursors(), make_cursors();   // the paw is one CSS pixel an art pixel too
        place(cam);
    }

    void draw() {
        say_status();
        if (phase == Phase::SignIn) {
            SDL_SetRenderTarget(r, nullptr);
            draw::Ctx c{&canvas, art.get(), u_ui(), stage.css};
            ui.draw_sign_in(c, frame(), form);
            return;
        }
        const double t = still ? 0 : now;
        auto blits = view::world(scene, cam.floor, t);

        // what the pointer is on, and whose menu is open, are outlined round their own shapes (.hot and .lit); a
        // filing cabinet or the litter box is the piece of furniture it stands over (outline()'s node.piece)
        const std::string hot = view::who_of(ui.tipped().what, ui.tipped().key), lit = view::who_of(ui.menu_kind(), ui.menu_key());
        auto is_outlined = [&](const view::Blit& b) { return !b.who.empty() && (b.who == hot || b.who == lit); };

        // a closed room under the pointer, or with its menu open, is lightened to 18%
        auto fill_of = [&](const view::Blit& b) {
            const bool lit = !b.room.empty() && ((ui.tipped().what == Thing::Room && ui.tipped().key == b.room) ||
                                                 (ui.menu_kind() == Thing::Room && ui.menu_key() == b.room));
            draw::Colour col = b.colour;
            if (lit) col.a = 46;
            return col;
        };
        // The world target is drawn again only when what is in it changed -- a cat's frame, the house, the floor, an
        // outline, a piece of art arriving -- not at the display's rate: a phone's battery is the reason.
        std::uint64_t key = 1469598103934665603ull;   // FNV-1a over everything drawn into it
        auto mix = [&](const void* p, size_t n) {
            for (size_t i = 0; i < n; ++i) key = (key ^ static_cast<const unsigned char*>(p)[i]) * 1099511628211ull;
        };
        for (const auto& b : blits) {
            mix(&b.dst, sizeof b.dst);
            if (b.fill) { const draw::Colour col = fill_of(b); mix(&col, sizeof col); continue; }
            const bool out = is_outlined(b);
            mix(&b.sheet, sizeof b.sheet), mix(&b.src, sizeof b.src), mix(&b.coat, sizeof b.coat), mix(&out, sizeof out);
        }
        const int have = art->have();
        mix(&have, sizeof have);
        if (key != world_key && world) {
            world_key = key;
            draw::Ctx wc{&canvas, art.get(), 2, 1};
            SDL_SetRenderTarget(r, world);
            SDL_SetRenderDrawColor(r, 0x8F, 0xBF, 0x4F, 255);
            SDL_RenderClear(r);
            for (const auto& b : blits) {
                if (b.fill) { draw::fill(wc, b.dst, fill_of(b)); continue; }
                if (is_outlined(b))
                    for (auto [dx, dy] : {std::pair{2.f, 0.f}, {-2.f, 0.f}, {0.f, 2.f}, {0.f, -2.f}})
                        draw::cell(wc, b.sheet, b.src, draw::Rect{b.dst.x + dx, b.dst.y + dy, b.dst.w, b.dst.h}, draw::kOutline);
                draw::cell(wc, b.sheet, b.src, b.dst, b.coat);
            }
            SDL_SetRenderTarget(r, nullptr);
        }

        // the stage: the lawn, the meadow tiled to follow the camera, the world over it
        SDL_SetRenderDrawColor(r, 0x8F, 0xBF, 0x4F, 255);
        SDL_RenderClear(r);
        draw::Ctx c{&canvas, art.get(), u_ui(), stage.css};
        const float tw = 112.f * cam.u, th = 32.f * cam.u;
        if (art->texture(art::Id::Meadow)) {
            const float x0 = std::fmod(cam.tx, tw) - (cam.tx > 0 ? tw : 0), y0 = std::fmod(cam.ty, th) - (cam.ty > 0 ? th : 0);
            for (float y = y0; y < stage.h; y += th)
                for (float x = x0; x < stage.w; x += tw) draw::cell(c, art::Id::Meadow, {0, 0, 112, 32}, {x, y, tw, th});
        }
        if (cam.floor == manor::Level::Upper) draw::fill(c, {0, 0, float(stage.w), float(stage.h)}, {0x16, 0x22, 0x14, 128});
        const draw::Rect wr = view::world_rect();
        const SDL_FRect dst{cam.tx, cam.ty, wr.w * cam.u / 2.f, wr.h * cam.u / 2.f};
        SDL_RenderTexture(r, world, nullptr, &dst);

        // the lit room: the pack's brackets, one size on screen at any zoom; the stair's at one pixel a pixel
        auto brackets = [&](const draw::Rect& box, float s) {
            const draw::Panel& b = draw::kBrackets;
            draw::nine(c, b.tex, {}, {b.l, b.r, b.t, b.b}, {b.l * s, b.r * s, b.t * s, b.b * s}, box, false);
        };
        auto lit_room = [&](const std::string& key) {
            const manor::Geom* g = manor::of(key);
            if (!g || g->level != cam.floor || key == cam.focus) return;
            const draw::Rect box = view::screen_box(cam, g->box);
            if (house.open(key)) draw::fill(c, box, {0xFF, 0xFA, 0xE1, 31});   // a closed room keeps its shade, lightened
            brackets(box, float(u_ui()));
        };
        if (ui.tipped().what == Thing::Room) lit_room(ui.tipped().key);
        if (ui.menu_kind() == Thing::Room && !(ui.tipped().what == Thing::Room && ui.tipped().key == ui.menu_key())) lit_room(ui.menu_key());
        if (ui.tipped().what == Thing::Stairs) {
            const manor::Box s = manor::stairs();
            const draw::Rect box = view::screen_box(cam, s);
            draw::fill(c, box, {0xFF, 0xFA, 0xE1, 36});
            brackets(box, k());
        }

        ui.draw(c, frame());
    }

    // ---- input ----

    view::Hit pick(float x, float y) const { return view::pick(scene, cam, stage, x, y, coarse); }

    void handle(App& app, const In& in);

    // the world target: the plan's world, doubled (never a number copied out of it)
    bool make_world() {
        if (world) SDL_DestroyTexture(world);
        const draw::Rect wr = view::world_rect();
        world = SDL_CreateTexture(r, SDL_PIXELFORMAT_RGBA32, SDL_TEXTUREACCESS_TARGET, int(wr.w), int(wr.h));
        if (world) SDL_SetTextureScaleMode(world, SDL_SCALEMODE_NEAREST);
        world_key = 0;
        return world != nullptr;
    }
    // The GPU was reset (a driver update on Windows, a lost context on Android): every texture is gone. Each is
    // made again from what is kept -- the art's surfaces, the fonts -- as it is next drawn.
    void lost_device() {
        if (art) art->forget_gpu();
        draw::forget_tints();
        ui.forget_words();
        make_world();
    }
    // A phone's going to the background is told in a watch, as it happens: from the queue it would come after the
    // next frame had already been drawn, which iOS ends the app for.
    static bool SDLCALL lifecycle(void* self, SDL_Event* e) {
        if (e->type == SDL_EVENT_WILL_ENTER_BACKGROUND) static_cast<Impl*>(self)->away = true;
        if (e->type == SDL_EVENT_DID_ENTER_FOREGROUND) static_cast<Impl*>(self)->away = false;
        return true;
    }

    void cursor(bool on_something) {
        if (!window || on_something == pointing) return;
        pointing = on_something;
        if (point && paw) SDL_SetCursor(on_something ? point : paw);
    }
    // the paw, and the paw that points (32 x 32 at one CSS pixel each), once both are in the cache
    void make_cursors() {
        if (!window || paw) return;
        const art::Texture* t = art->texture(art::Id::UiCursor);
        const art::Texture* p = art->texture(art::Id::UiCursorPoint);
        if (!t || !t->surface || !p || !p->surface) return;
        const int s = stage.css;
        SDL_Surface* a = SDL_ScaleSurface(t->surface, 32 * s, 32 * s, SDL_SCALEMODE_NEAREST);
        SDL_Surface* b = SDL_ScaleSurface(p->surface, 32 * s, 32 * s, SDL_SCALEMODE_NEAREST);
        if (a) paw = SDL_CreateColorCursor(a, 9 * s, 5 * s), SDL_DestroySurface(a);
        if (b) point = SDL_CreateColorCursor(b, 9 * s, 3 * s), SDL_DestroySurface(b);
        if (paw) SDL_SetCursor(pointing && point ? point : paw);
    }
    void forget_cursors() {
        if (!window) return;
        SDL_SetCursor(SDL_GetDefaultCursor());
        if (paw) SDL_DestroyCursor(paw), paw = nullptr;
        if (point) SDL_DestroyCursor(point), point = nullptr;
    }
};

App::App() : impl_(new Impl) {}
App::~App() {
    // everything drawn with the renderer -- the world, the art, the tinted sheets, the fonts' words in the Ui -- goes
    // while the renderer still stands; then the renderer, the window and SDL itself
    Impl& I = *impl_;
    if (I.window) SDL_RemoveEventWatch(Impl::lifecycle, &I);
    if (I.world) SDL_DestroyTexture(I.world);
    I.art.reset();
    draw::forget_tints();
    SDL_Renderer* r = I.r;
    SDL_Surface* surface = I.surface;
    SDL_Window* window = I.window;
    SDL_Cursor* cursors[] = {I.paw, I.point};
    delete impl_;   // the Ui and its fonts, and the net, which finishes a sign-out's /logout
    if (r) SDL_DestroyRenderer(r);
    if (surface) SDL_DestroySurface(surface);
    for (SDL_Cursor* c : cursors) if (c) SDL_DestroyCursor(c);
    if (window) SDL_DestroyWindow(window);
    SDL_Quit();
}

bool App::start(int argc, char** argv) {
    Impl& I = *impl_;
    const std::filesystem::path src = from_utf8(CATIO_SOURCE_DIR);
    const char* base_c = SDL_GetBasePath();
    const std::filesystem::path base = base_c ? from_utf8(base_c) : std::filesystem::path();
    std::string gateway;
    bool gateway_given = false;
    for (int i = 1; i < argc; ++i) {
        const std::string a = argv[i];
        auto next = [&]() -> std::string { return i + 1 < argc ? argv[++i] : ""; };
        auto path = [&] { return from_utf8(next()); };   // SDL's argv is UTF-8 on every platform
        if (a == "--data") I.data = path();
        else if (a == "--gateway") gateway = next(), gateway_given = true;
        else if (a == "--home") I.home = path();
        else if (a == "--art") I.art_dir = path();
        else if (a == "--manor") I.manor_json = path();
        else if (a == "--assets") I.assets = path();
        else if (a == "--shot") I.shot = path();
        else if (a == "--size") { const std::string v = next(); std::sscanf(v.c_str(), "%dx%d", &I.shot_w, &I.shot_h); }
        else if (a == "--css") I.shot_css = std::max(1, std::atoi(next().c_str()));
        else if (a == "--touch") I.shot_touch = true;
        else if (a == "--still") I.still = I.still_given = true;
        else if (a == "--do") I.steps = next();
        else { std::fprintf(stderr, "catio_app: what is %s? See include/catio/app.h.\n", a.c_str()); return false; }
    }
    if (I.manor_json.empty()) I.manor_json = first_of({base / "manor.json", src / "generated" / "manor.json"});
    if (I.assets.empty()) I.assets = first_of({base / "assets", src / "assets"}, "Nunito-Bold.ttf");
#ifdef CATIO_GATEWAY_ORIGIN
    if (!gateway_given && I.data.empty()) gateway = CATIO_GATEWAY_ORIGIN, gateway_given = true;   // her build
#endif
#if defined(SDL_PLATFORM_ANDROID) || defined(SDL_PLATFORM_IOS)
    gateway_given = true;   // a phone has no folder of documents: its gateway, or the sign-in asks for the address
#endif
    if (!manor::load_text(read_shipped(I.manor_json))) { std::fprintf(stderr, "catio_app: no floor plan at %s\n", to_utf8(I.manor_json).c_str()); return false; }

    // where her cookie, the prefs and the art's cache live: the app's own private folder, or the one she names
    if (I.home.empty()) {
        char* pref = SDL_GetPrefPath("KittyChat", "Cafe");
        if (pref) I.home = from_utf8(pref), SDL_free(pref);
    }
    if (gateway_given && I.home.empty()) {   // never a cookie written wherever it was started from
        std::fprintf(stderr, "catio_app: no private folder for the cookie (%s): give one with --home.\n", SDL_GetError());
        return false;
    }
    // the cache holds what a sign-in fetched, and is a gateway's alone: a folder of documents draws only the art
    // it is given with --art, never the licensed packs a past sign-in left there
    if (I.art_dir.empty() && gateway_given && !I.home.empty()) I.art_dir = I.home / "cache", I.own_cache = true;
    if (I.shot.empty() && !I.home.empty()) I.prefs = I.home / "prefs.json";

    if (gateway_given) {
        // the gateway: signed in already, or the sign-in screen first
        I.form.ask_origin = net::bare(gateway).empty() || gateway == "ask";   // "/" or spaces are no address
        I.load_prefs();
        I.origin = net::bare(I.form.ask_origin ? I.form.origin : gateway);
        if (!I.origin.empty()) I.net = std::make_unique<net::Net>(I.origin, I.home / "cookie");
        I.phase = I.net && I.net->has_cookie() ? Phase::FirstRead : Phase::SignIn;
        I.form.field = I.form.ask_origin && I.origin.empty() ? 0 : 1;
    } else {
        if (I.data.empty()) I.data = src / "test" / "fixtures";
        if (!I.read_house()) return false;
        I.load_prefs();
    }

    I.art = std::make_unique<art::Art>(I.art_dir);
    I.art->scan();

    if (!I.shot.empty()) {
        // a frame with no window: a plain surface and the software renderer
        if (!SDL_Init(0)) return false;
        I.surface = SDL_CreateSurface(I.shot_w, I.shot_h, SDL_PIXELFORMAT_RGBA32);
        I.r = I.surface ? SDL_CreateSoftwareRenderer(I.surface) : nullptr;
        I.coarse = I.shot_touch;
        if (!I.r) { std::fprintf(stderr, "catio_app: no renderer: %s\n", SDL_GetError()); return false; }
        I.stage.css = I.shot_css;
    } else {
        if (!SDL_Init(SDL_INIT_VIDEO | SDL_INIT_EVENTS)) { std::fprintf(stderr, "catio_app: %s\n", SDL_GetError()); return false; }
        I.window = SDL_CreateWindow("KittyChat Café", 1280, 800, SDL_WINDOW_RESIZABLE | SDL_WINDOW_HIGH_PIXEL_DENSITY);
        I.r = I.window ? SDL_CreateRenderer(I.window, nullptr) : nullptr;
        if (!I.r) { std::fprintf(stderr, "catio_app: no window: %s\n", SDL_GetError()); return false; }
        I.vsync = SDL_SetRenderVSync(I.r, 1);
        SDL_AddEventWatch(Impl::lifecycle, &I);
    }
    I.canvas.r = I.r;
    if (!I.make_world()) { std::fprintf(stderr, "catio_app: no world target: %s\n", SDL_GetError()); return false; }

    int w = I.shot_w, h = I.shot_h;
    float scale = float(I.shot_css);
    if (I.window) SDL_GetRenderOutputSize(I.r, &w, &h), scale = SDL_GetWindowDisplayScale(I.window);
    I.resize(w, h, scale);
    if (!I.ui.fonts(I.assets, *I.art, I.stage.css)) { std::fprintf(stderr, "catio_app: no fonts in %s\n", to_utf8(I.assets).c_str()); return false; }

    I.make_cursors();

    // the first view: the whole manor; on a phone, the room that needs her most
    I.cam.floor = manor::Level::Ground;
    I.rescene();
    const std::string urgent = I.stage.narrow() ? I.urgent_room() : "";
    if (!urgent.empty()) I.go(urgent);
    else I.go("");
    I.start = clock_s();
    if (I.phase == Phase::FirstRead) I.read_all();
    I.say_status();
    return true;
}

void App::act(ui::Action what, std::string_view arg_v) {
    Impl& I = *impl_;
    const std::string arg(arg_v);
    if (!I.ui.can(what)) return;   // drawn disabled; nothing to do
    switch (what) {
        case Action::LookIn: I.go(arg); break;
        case Action::WholeHouse: I.go(""); break;
        case Action::ZoomIn:
        case Action::ZoomOut:
            I.ui.close_menu();
            I.place(view::zoom_by(I.cam, what == Action::ZoomIn ? 1 : -1, I.stage.w / 2.f, I.stage.h / 2.f, I.stage));
            I.settle();
            break;
        case Action::ToFloor: I.set_floor(arg == "upper" ? manor::Level::Upper : manor::Level::Ground); break;
        case Action::FoldMap: I.save_prefs(); break;
        case Action::MapAt: {
            int x = 0, y = 0;
            if (std::sscanf(arg.c_str(), "%d %d", &x, &y) == 2) {
                I.ui.close_menu();     // the minimap's pointerdown hides it, as every camera move does
                view::Cam c = I.cam;   // centreOn
                c.tx = std::round(I.stage.w / 2.f - x * float(c.u));
                c.ty = std::round(I.stage.h / 2.f - y * float(c.u));
                I.place(c);
                I.settle();
            }
            break;
        }
        case Action::StillCats: I.still = !I.still; I.save_prefs(); break;
        case Action::OpenCat: I.ui.open(ui::Card::Cat, arg); break;
        case Action::OpenLink:
            // A cat's link is what its agent reported, and an agents' key is the one a leak would be: only a web address
            // is handed to the system, never a file:, smb: or an app's own scheme.
            if (!ui::web_link(arg)) { I.say("That link isn't a web address, so the app won't open it.", true, 6); break; }
            if (I.window) SDL_OpenURL(arg.c_str());
            else std::printf("open %s\n", arg.c_str());
            break;
        case Action::SignOut:
            // the gateway ends the cookie and the file goes, on the net's own thread; the sign-in comes back here at once
            if (!I.net) break;
            I.signed_out("", true);   // the queue emptied of the leaving account's work, the cookie and the art gone, now
            I.net->send([](net::Gateway& g) { g.sign_out(); return net::Reply{}; }, true);   // then /logout, first in line
            break;
        case Action::CheckNow:
            I.art_trouble.clear();
            I.failed.clear(), I.unkept.clear(), I.cache_trouble.clear();
            refresh(true);
            break;
        case Action::Field: I.form.field = std::atoi(arg.c_str()); break;
        case Action::ComeIn: I.sign_in(); break;
        // the writes: each one on her press, through her gateway
        case Action::OpenRoom: {
            if (!I.net) break;
            const std::string doc = "rooms/" + arg;
            I.ask(Ask::Write, [doc](net::Gateway& g) { return g.patch(doc, R"({"closed":false})"); }, art::Id::Count,
                  I.house.room(arg).name + " is open.");
            break;
        }
        default: break;   // the rest arrive with their cards
    }
}

void App::refresh(bool now) {
    Impl& I = *impl_;
    if (!I.net) {   // a folder of documents: read it again when asked (and on a phone's sign-in screen, nothing)
        if (now && !I.data.empty()) I.read_house();
        return;
    }
    if (I.phase == Phase::SignIn) return;
    if (now || I.now - I.last_read >= 30) {
        I.read_all();
        if (I.read_once && I.fetching.empty()) I.fetch_art();   // what failed waits for Check now
    }
}

void App::pump_net() {
    Impl& I = *impl_;
    if (!I.net) return;
    const Phase was = I.phase;
    std::uint32_t t = 0;
    net::Reply r;
    // the art comes decoded from the net's thread; making its textures is the draw's, a few a frame
    int art = 0;
    while (art < 4 && I.net && I.net->take(&t, &r)) {
        auto it = I.asked.find(t);
        if (it == I.asked.end()) continue;   // asked before she was signed out: nowhere to go now
        const Asked a = it->second;
        I.asked.erase(it);
        if (a.what == Ask::Art) ++art;
        I.heard(a, r);
    }
    // the house has arrived: on a phone, open on the room that needs her most
    if (was == Phase::FirstRead && I.phase == Phase::Running && I.stage.narrow()) {
        const std::string urgent = I.urgent_room();
        if (!urgent.empty()) I.go(urgent);
    }
}

void App::events() {
    Impl& I = *impl_;
    SDL_Event e;
    while (SDL_PollEvent(&e)) {
        SDL_ConvertEventToRenderCoordinates(I.r, &e);
        In in;
        in.at = clock_s();
        switch (e.type) {
            case SDL_EVENT_QUIT: in.kind = In::Quit; break;
            case SDL_EVENT_WILL_ENTER_BACKGROUND: I.away = true; continue;
            case SDL_EVENT_RENDER_TARGETS_RESET: I.world_key = 0; continue;   // the world target's pixels are gone
            case SDL_EVENT_RENDER_DEVICE_RESET: I.lost_device(); continue;     // and every other texture with them
            case SDL_EVENT_DID_ENTER_FOREGROUND: I.away = false, I.pinching = false, I.fingers.clear(); refresh(true); continue;
            case SDL_EVENT_WINDOW_PIXEL_SIZE_CHANGED:
            case SDL_EVENT_WINDOW_DISPLAY_SCALE_CHANGED: in.kind = In::Resize; break;
            case SDL_EVENT_MOUSE_MOTION: in.kind = In::Move, in.x = e.motion.x, in.y = e.motion.y, in.touch = e.motion.which == SDL_TOUCH_MOUSEID; break;
            case SDL_EVENT_MOUSE_BUTTON_DOWN:
            case SDL_EVENT_MOUSE_BUTTON_UP:
                in.kind = e.type == SDL_EVENT_MOUSE_BUTTON_DOWN ? In::Down : In::Up;
                in.x = e.button.x, in.y = e.button.y, in.touch = e.button.which == SDL_TOUCH_MOUSEID;
                in.primary = e.button.button == SDL_BUTTON_LEFT;
                break;
            case SDL_EVENT_WINDOW_MOUSE_LEAVE:   // 5: the pointer left the window: nothing is under it (pointerleave)
                I.pointer.reset();
                I.ui.hover(I.frame(), -1, -1);
                I.ui.tip(I.frame(), {}, false);
                continue;
            case SDL_EVENT_MOUSE_WHEEL: in.kind = In::Wheel, in.x = e.wheel.mouse_x, in.y = e.wheel.mouse_y, in.dy = e.wheel.y; break;
            case SDL_EVENT_TEXT_INPUT: in.kind = In::Text, in.key = e.text.text ? e.text.text : ""; break;
            case SDL_EVENT_FINGER_DOWN:
            case SDL_EVENT_FINGER_MOTION:   // fingers on the screen itself: a trackpad's are not where the pointer is
                if (SDL_GetTouchDeviceType(e.tfinger.touchID) == SDL_TOUCH_DEVICE_DIRECT) I.fingers[e.tfinger.fingerID] = {e.tfinger.x, e.tfinger.y};
                continue;
            case SDL_EVENT_FINGER_UP:
            case SDL_EVENT_FINGER_CANCELED:
                I.fingers.erase(e.tfinger.fingerID);
                if (I.fingers.empty()) I.pinching = false, I.pinch = 1;   // with no PINCH_END (a cancelled gesture) too
                continue;
            case SDL_EVENT_PINCH_BEGIN: in.kind = In::PinchBegin, in.touch = true; break;
            case SDL_EVENT_PINCH_END: in.kind = In::PinchEnd, in.touch = true; break;
            case SDL_EVENT_PINCH_UPDATE: {
                // it zooms about the point between the fingers
                in.kind = In::Pinch, in.scale = e.pinch.scale, in.touch = true;
                const draw::Pt at = I.pointer.value_or(draw::Pt{I.stage.w / 2.f, I.stage.h / 2.f});
                in.x = at.x, in.y = at.y;
                if (!I.fingers.empty()) {
                    in.x = in.y = 0;
                    for (const auto& [id, p] : I.fingers) in.x += p.x, in.y += p.y;
                    in.x /= float(I.fingers.size()), in.y /= float(I.fingers.size());
                }
                break;
            }
            case SDL_EVENT_KEY_DOWN: {
                in.kind = In::Key;
                in.shift = (e.key.mod & SDL_KMOD_SHIFT) != 0;
                if (e.key.mod & (SDL_KMOD_CTRL | SDL_KMOD_ALT | SDL_KMOD_GUI)) {   // the page leaves these to the browser
                    if (e.key.key != SDLK_V || (e.key.mod & SDL_KMOD_ALT)) continue;
                    in.key = "paste";
                    break;
                }
                switch (e.key.key) {
                    case SDLK_ESCAPE: in.key = "escape"; break;
                    case SDLK_PAGEUP: in.key = "pageup"; break;
                    case SDLK_PAGEDOWN: in.key = "pagedown"; break;
                    case SDLK_EQUALS: case SDLK_PLUS: case SDLK_KP_PLUS: in.key = "plus"; break;
                    case SDLK_MINUS: case SDLK_KP_MINUS: in.key = "minus"; break;
                    case SDLK_0: case SDLK_KP_0: in.key = "0"; break;
                    case SDLK_M: in.key = "m"; break;
                    case SDLK_LEFT: in.key = "left"; break;
                    case SDLK_RIGHT: in.key = "right"; break;
                    case SDLK_UP: in.key = "up"; break;
                    case SDLK_DOWN: in.key = "down"; break;
                    case SDLK_TAB: in.key = "tab"; break;
                    case SDLK_RETURN: case SDLK_KP_ENTER: in.key = "enter"; break;
                    case SDLK_BACKSPACE: in.key = "backspace"; break;
                    default: continue;
                }
                break;
            }
            default: continue;
        }
        I.pending.push_back(in);
    }
    // One press a frame: a press can open a menu or close one, and a menu's buttons are only where they are once it
    // is drawn, so what came after a press waits for the next frame rather than landing on the last frame's buttons.
    size_t used = 0;
    while (used < I.pending.size()) {
        const In in = I.pending[used++];
        if (in.kind == In::Quit) { I.quit = true; continue; }
        if (in.kind == In::Resize) {
            int w = 0, h = 0;
            SDL_GetRenderOutputSize(I.r, &w, &h);
            I.resize(w, h, SDL_GetWindowDisplayScale(I.window));
            continue;
        }
        I.handle(*this, in);
        if (in.kind == In::Up) break;
    }
    I.pending.erase(I.pending.begin(), I.pending.begin() + std::ptrdiff_t(used));
}

// The page's pointer and keys, for the window and for a shot's steps alike.
void App::Impl::handle(App& app, const In& in) {
    if (in.kind == In::Move || in.kind == In::Down) coarse = in.touch;   // before the frame that carries it
    const ui::Frame f = frame();
    if (phase == Phase::SignIn) {   // a form: its fields, Tab between them, Enter to come in
        std::string* field = form.field == 0 ? &form.origin : form.field == 1 ? &form.user : &form.password;
        switch (in.kind) {
            case In::Move: ui.hover(f, in.x, in.y); cursor(!ui.under(f, in.x, in.y).empty()); return;
            case In::Down: press_on = std::string(ui.under(f, in.x, in.y)); return;
            case In::Up: {
                ui::Action a;
                std::string arg;
                if (!in.primary || ui.under(f, in.x, in.y) != press_on) return;   // another button, or slid off it
                if (ui.press(f, in.x, in.y, &a, &arg) && a != Action::None) app.act(a, arg);
                return;
            }
            case In::Text:
                if (!form.busy && field->size() + in.key.size() <= 1024) *field += in.key;
                return;
            case In::Key:
                if (form.busy) return;
                if (in.key == "enter") sign_in();
                else if (in.key == "paste") {   // her password manager's, or the address copied from a browser
                    char* t = SDL_GetClipboardText();
                    std::string text = t ? t : "";
                    SDL_free(t);
                    std::erase_if(text, [](char ch) { return ch == '\n' || ch == '\r'; });
                    if (field->size() + text.size() <= 1024) *field += text;
                }
                else if (in.key == "backspace") draw::pop_char(*field);
                else if (in.key == "tab") {
                    const int first = form.ask_origin ? 0 : 1;
                    form.field = in.shift ? (form.field <= first ? 2 : form.field - 1) : (form.field >= 2 ? first : form.field + 1);
                }
                return;
            default: return;
        }
    }
    // while two fingers pinch, the first one's mouse is theirs: no drag, no swipe and no click when they lift
    if (pinching && in.touch && (in.kind == In::Move || in.kind == In::Down || in.kind == In::Up)) return;
    switch (in.kind) {
        case In::Move: {
            if (pressed) {
                const float dx = in.x - last_at.x, dy = in.y - last_at.y;
                if (in.touch && on_ui && !on_map && (scrolling || std::hypot(in.x - press_at.x, in.y - press_at.y) > 4 * k()) &&
                    ui.scroll(f, press_at.x, press_at.y, -dy)) {
                    // a finger dragging a menu taller than the screen, or a card, scrolls it
                    if (!scrolling) ui.hold(f, in.x, in.y, false);
                    scrolling = true;
                } else if (on_map) {   // dragging on the minimap pans the view with it, once it is a drag and not a tap
                    std::string arg;
                    if ((dragging || std::hypot(in.x - press_at.x, in.y - press_at.y) >= 3 * k()) && ui.map_drag(f, in.x, in.y, &arg)) {
                        int mx = 0, my = 0;
                        std::sscanf(arg.c_str(), "%d %d", &mx, &my);
                        app.act(Action::MapAt, std::to_string(int(std::lround(mx + map_off_x))) + " " + std::to_string(int(std::lround(my + map_off_y))));
                        dragging = true;
                    }
                } else if (!on_ui && (dragging || std::hypot(in.x - press_at.x, in.y - press_at.y) > 4 * k())) {
                    if (!dragging) ui.close_menu(), ui.tip(f, {}, false);
                    dragging = true;
                    place(view::pan_by(cam, dx, dy, stage));
                }
                last_at = {in.x, in.y};
                return;
            }
            pointer = draw::Pt{in.x, in.y};
            if (ui.over(f, in.x, in.y)) {
                ui.hover(f, in.x, in.y);
                ui.tip(f, {}, true);
                cursor(true);
                return;
            }
            ui.hover(f, -1, -1);
            const view::Hit h = pick(in.x, in.y);
            ui.tip(f, h, true);
            cursor(h.what != Thing::None && !(h.what == Thing::Room && h.key == cam.focus));
            return;
        }
        case In::Down: {
            pressed = true;
            dragging = scrolling = false;
            press_at = last_at = {in.x, in.y};
            press_t = in.at;
            on_ui = ui.over(f, in.x, in.y);
            on_map = false;
            press_on = std::string(ui.under(f, in.x, in.y));
            if (on_ui) {
                ui.hold(f, in.x, in.y, true);
                on_map = ui.under(f, in.x, in.y) == "map:mm";   // a drag on the minimap pans the view with it
                map_off_x = map_off_y = 0;
                if (std::string arg; on_map && ui.map_drag(f, in.x, in.y, &arg)) {
                    // grabbed inside the view's frame, it holds the view where it was grabbed (MM.drag.off)
                    int mx = 0, my = 0;
                    std::sscanf(arg.c_str(), "%d %d", &mx, &my);
                    const draw::Rect v = view::visible(cam, stage);
                    if (mx >= v.x && mx <= v.x + v.w && my >= v.y && my <= v.y + v.h) map_off_x = v.x + v.w / 2 - mx, map_off_y = v.y + v.h / 2 - my;
                }
            }
            return;
        }
        case In::Up: {
            if (!pressed) return;
            pressed = false;
            ui.hold(f, in.x, in.y, false);
            if (scrolling) { scrolling = on_ui = false; return; }                     // it scrolled; it wasn't a press
            if (dragging && on_map) { dragging = on_map = on_ui = false; return; }   // the minimap drag is done
            if (!in.primary && !dragging) { on_ui = false; return; }                // a right or middle click: no click
            if (dragging) {
                dragging = false;
                // a quick sideways swipe inside a room, on a phone: the room next door (her fix)
                const float dx = in.x - press_at.x, dy = in.y - press_at.y;
                if (stage.narrow() && !cam.focus.empty() && std::fabs(dx) > 60 * k() && std::fabs(dx) > 2 * std::fabs(dy) && in.at - press_t < 0.35) {
                    const auto next = manor::next_room(cam.focus, dx < 0 ? manor::Dir::Right : manor::Dir::Left);
                    if (!next.empty()) { go(std::string(next)); return; }
                }
                settle();
                return;
            }
            if (on_ui || ui.over(f, in.x, in.y)) {
                ui::Action a;
                std::string arg;
                // as a browser's click: on what it went down on, never on another button it slid onto
                if (ui.under(f, in.x, in.y) == press_on && ui.press(f, in.x, in.y, &a, &arg) && a != Action::None) app.act(a, arg);
                on_ui = false;
                return;
            }
            // a click on the house
            const view::Hit h = pick(in.x, in.y);
            const bool twice = h.what == Thing::Room && h.key == last_click_room && in.at - last_click_t < 0.4;
            last_click_t = in.at, last_click_room = h.what == Thing::Room ? h.key : "";
            switch (h.what) {
                case Thing::Room:
                    if (twice) { go(h.key); return; }   // a double click looks in
                    ui.toggle(f, h);
                    return;
                case Thing::Cat: case Thing::Queen: case Thing::Pile: ui.toggle(f, h); return;
                case Thing::Stairs: set_floor(cam.floor == manor::Level::Upper ? manor::Level::Ground : manor::Level::Upper); return;
                case Thing::Cabinet: case Thing::Litter: {
                    // their cards are still to come: the room's menu, which has them, instead
                    const manor::Geom* g = manor::of(h.key);
                    if (!g) return;
                    view::Hit room{Thing::Room, h.key, view::screen_box(cam, g->box)};
                    ui.toggle(f, room);
                    return;
                }
                default: ui.close_menu(); return;
            }
        }
        case In::Wheel: {
            // over a card or a menu the wheel is theirs: it scrolls one taller than the screen
            if (ui.scroll(f, in.x, in.y, -in.dy * 48 * k()) || ui.card() != ui::Card::None || ui.under(f, in.x, in.y).rfind("menu:", 0) == 0) {
                wheel = 0;
                return;
            }
            // a pause, or the other way, starts a new gesture: no leftover from the last one zooms this one
            if (in.at - wheel_at > 0.5 || (wheel != 0 && (wheel > 0) != (in.dy > 0))) wheel = 0;
            wheel_at = in.at;
            wheel += in.dy;   // a trackpad sends fractions of a notch, a flick several at once, a sideways scroll nothing
            const int steps = int(wheel);
            if (!steps) return;
            wheel -= float(steps);
            ui.close_menu();
            // over the minimap it zooms about the spot on the map under the pointer, as the page's does
            draw::Pt at{in.x, in.y};
            if (std::string arg; ui.under(f, in.x, in.y) == "map:mm" && ui.map_drag(f, in.x, in.y, &arg)) {
                int mx = 0, my = 0;
                std::sscanf(arg.c_str(), "%d %d", &mx, &my);
                at = {std::clamp(cam.tx + mx * float(cam.u), 0.f, float(stage.w)), std::clamp(cam.ty + my * float(cam.u), 0.f, float(stage.h))};
            }
            place(view::zoom_by(cam, steps, at.x, at.y, stage));
            settle();
            return;
        }
        case In::PinchBegin:
            // what the first finger started is dropped: a pinch is neither a drag nor a press (and under a card,
            // nothing at all: the card is modal)
            pinching = true;
            pinch = 1;
            if (pressed) ui.hold(f, press_at.x, press_at.y, false);
            pressed = dragging = scrolling = on_ui = on_map = false;
            ui.close_menu();
            return;
        case In::PinchEnd:
            pinching = false;
            pinch = 1;
            return;
        case In::Pinch: {
            if (ui.card() != ui::Card::None) return;
            pinch *= in.scale;
            if (pinch > 1.25f || pinch < 0.8f) {
                place(view::zoom_by(cam, pinch > 1 ? 1 : -1, in.x, in.y, stage));
                pinch = 1;
                settle();
            }
            return;
        }
        case In::Key: {
            const std::string& key = in.key;
            if (key == "escape") { if (!ui.escape()) go(""); return; }
            if (ui.card() != ui::Card::None) return;
            if (key == "pageup") { set_floor(manor::Level::Upper); return; }
            if (key == "pagedown") { set_floor(manor::Level::Ground); return; }
            if (key == "plus") { app.act(Action::ZoomIn, ""); return; }
            if (key == "minus") { app.act(Action::ZoomOut, ""); return; }
            if (key == "0") { go(""); return; }
            if (key == "m") { ui.set_map_open(!ui.map_open()); save_prefs(); return; }
            const char* names[] = {"left", "right", "up", "down"};
            for (int i = 0; i < 4; ++i) {
                if (key != names[i]) continue;
                if (in.shift) {   // Shift and an arrow moves the view
                    const float d = 140 * k();
                    const float mv[4][2] = {{d, 0}, {-d, 0}, {0, d}, {0, -d}};
                    ui.close_menu();
                    place(view::pan_by(cam, mv[i][0], mv[i][1], stage));
                    settle();
                    return;
                }
                // arrows move to the room next door: into it, in a room she has gone into; else its menu
                std::string from = !cam.focus.empty() ? cam.focus : ui.menu_kind() == Thing::Room ? ui.menu_key() : view::room_in_view(cam, stage);
                if (from.empty()) from = cam.floor == manor::Level::Upper ? "brain" : "hall";
                const auto to = manor::next_room(from, kArrows[i]);
                if (to.empty()) return;
                if (!cam.focus.empty()) { go(std::string(to)); return; }
                const manor::Geom* g = manor::of(to);
                ui.close_menu();
                ui.toggle(f, view::Hit{Thing::Room, std::string(to), view::screen_box(cam, g->box)});
                return;
            }
            return;
        }
        default: return;
    }
}

int App::run() {
    Impl& I = *impl_;
    if (!I.shot.empty()) {
        // the steps, a frame after each, then the frame she looks at; the network answered before each frame
        auto drain = [&] {
            for (int i = 0; i < 3000; ++i) {
                pump_net();
                if (!I.net || I.net->outstanding() == 0) break;
                std::this_thread::sleep_for(std::chrono::milliseconds(5));
            }
            pump_net();
        };
        I.now = 0;
        drain();
        I.draw();
        std::stringstream steps(I.steps);
        std::string step;
        while (std::getline(steps, step, ';')) {
            std::stringstream w(step);
            std::string verb;
            w >> verb;
            if (verb.empty()) continue;
            const float k = I.k();
            In in;
            in.touch = I.shot_touch;
            in.at = I.now;
            auto xy = [&](In& e) { w >> e.x >> e.y; e.x *= k, e.y *= k; };
            if (verb == "move") in.kind = In::Move, xy(in), I.handle(*this, in);
            else if (verb == "down") in.kind = In::Down, xy(in), I.handle(*this, in);
            else if (verb == "up") in.kind = In::Up, xy(in), I.handle(*this, in);
            else if (verb == "click") {
                In m = in; m.kind = In::Move; xy(m);
                if (!I.shot_touch) I.handle(*this, m), I.draw();
                In d = m; d.kind = In::Down; I.handle(*this, d);
                In u = m; u.kind = In::Up; I.handle(*this, u);
            } else if (verb == "drag") {
                In a = in; a.kind = In::Down; xy(a);
                In b = in; b.kind = In::Move; xy(b);
                I.handle(*this, a);
                for (int s = 1; s <= 4; ++s) {
                    In m = b;
                    m.x = a.x + (b.x - a.x) * s / 4, m.y = a.y + (b.y - a.y) * s / 4;
                    I.handle(*this, m);
                }
                In u = b; u.kind = In::Up; u.at = I.now + 0.5; I.handle(*this, u);
            } else if (verb == "wheel") in.kind = In::Wheel, xy(in), w >> in.dy, I.handle(*this, in);
            else if (verb == "key") {
                std::string name;
                w >> name;
                in.kind = In::Key;
                if (name.rfind("shift+", 0) == 0) in.shift = true, name = name.substr(6);
                in.key = name;
                I.handle(*this, in);
            } else if (verb == "wait") { double s = 0; w >> s; I.now += s; }
            else if (verb == "choose") {   // press the item that says this, wherever placeMenu put it
                std::string label;
                std::getline(w, label);
                if (!label.empty() && label.front() == ' ') label.erase(0, 1);
                const auto at = I.ui.find(label);
                if (!at) { std::fprintf(stderr, "catio_app: nothing says \"%s\"\n", label.c_str()); return 2; }
                In m = in;
                m.kind = In::Move, m.x = at->x, m.y = at->y;
                if (!I.shot_touch) I.handle(*this, m), I.draw();
                In d = m; d.kind = In::Down; I.handle(*this, d);
                In u = m; u.kind = In::Up; I.handle(*this, u);
            }
            else if (verb == "right") {   // a right click on what says this: "right Sign out"
                std::string label;
                std::getline(w, label);
                if (!label.empty() && label.front() == ' ') label.erase(0, 1);
                const auto at = I.ui.find(label);
                if (!at) { std::fprintf(stderr, "catio_app: nothing says \"%s\"\n", label.c_str()); return 2; }
                In d = in;
                d.kind = In::Down, d.x = at->x, d.y = at->y, d.primary = false;
                I.handle(*this, d);
                In u = d; u.kind = In::Up; I.handle(*this, u);
            }
            else if (verb == "slide") {   // down on what says one thing, up on what says another: "slide Check now > Sign out"
                std::string rest;
                std::getline(w, rest);
                const auto cut = rest.find(" > ");
                auto trim = [](std::string t) { while (!t.empty() && t.front() == ' ') t.erase(0, 1); return t; };
                const std::string from = trim(rest.substr(0, cut)), to = cut == std::string::npos ? "" : trim(rest.substr(cut + 3));
                const auto a = I.ui.find(from), b = I.ui.find(to);
                if (!a || !b) { std::fprintf(stderr, "catio_app: nothing says \"%s\" or \"%s\"\n", from.c_str(), to.c_str()); return 2; }
                In d = in; d.kind = In::Down, d.x = a->x, d.y = a->y; I.handle(*this, d);
                for (int s = 1; s <= 4; ++s) {
                    In m = in;
                    m.kind = In::Move, m.x = a->x + (b->x - a->x) * s / 4, m.y = a->y + (b->y - a->y) * s / 4;
                    I.handle(*this, m);
                }
                In u = in; u.kind = In::Up, u.x = b->x, u.y = b->y; I.handle(*this, u);
            }
            else if (verb == "type") {
                std::string text;
                std::getline(w, text);
                if (!text.empty() && text.front() == ' ') text.erase(0, 1);
                in.kind = In::Text, in.key = text;
                I.handle(*this, in);
            }
            else { std::fprintf(stderr, "catio_app: what step is %s?\n", verb.c_str()); return 2; }
            I.now += 0.05;
            refresh(false);
            drain();
            I.draw();
        }
        drain();
        I.draw();
        SDL_RenderPresent(I.r);
        if (!SDL_SavePNG(I.surface, to_utf8(I.shot).c_str())) { std::fprintf(stderr, "catio_app: %s\n", SDL_GetError()); return 1; }
        std::printf("%s: %dx%d at css %d\n", to_utf8(I.shot).c_str(), I.stage.w, I.stage.h, I.stage.css);
        // what the frame says, for a test to read
        std::printf("sign: %s\ntoast: %s\nform: %s\n", I.status.c_str(), I.toast.c_str(), I.form.problem.c_str());
        return 0;
    }
    while (!I.quit) {
        // the sign-in form takes typing; the house does not
        if (I.phase == Phase::SignIn && !SDL_TextInputActive(I.window)) SDL_StartTextInput(I.window);
        else if (I.phase != Phase::SignIn && SDL_TextInputActive(I.window)) SDL_StopTextInput(I.window);
        // with the cats stilled nothing moves on its own: wait for something to happen (or the net, or the clock)
        if (I.still && I.phase != Phase::SignIn && !(I.net && I.net->outstanding())) SDL_WaitEventTimeout(nullptr, 250);
        const double began = clock_s();
        events();
        pump_net();
        if (I.away) { SDL_WaitEventTimeout(nullptr, 500); continue; }   // nothing drawn until she is back
        I.now = clock_s() - I.start;
        refresh(false);
        I.draw();
        SDL_RenderPresent(I.r);
        if (!I.vsync) {   // no display pacing: about sixty frames a second, not as many as the core can draw
            const double left = 1.0 / 60 - (clock_s() - began);
            if (left > 0) SDL_DelayNS(Uint64(left * 1e9));
        }
    }
    return 0;
}

}  // namespace catio
