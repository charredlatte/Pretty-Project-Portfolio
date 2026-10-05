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

#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <ctime>
#include <fstream>
#include <map>
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

std::filesystem::path first_of(std::initializer_list<std::filesystem::path> ps) {
    std::error_code ec;
    for (const auto& p : ps) if (!p.empty() && std::filesystem::exists(p, ec)) return p;
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
    enum Kind { Move, Down, Up, Wheel, Key, Text, Pinch, Resize, Quit } kind = Move;
    float x = 0, y = 0, dy = 0, scale = 1;
    bool touch = false, shift = false;
    std::string key;
    double at = 0;
};

constexpr manor::Dir kArrows[] = {manor::Dir::Left, manor::Dir::Right, manor::Dir::Up, manor::Dir::Down};

// HH:MM, as the page's clock() puts it
std::string clock_of(std::int64_t ms) {
    const std::time_t t = std::time_t(ms / 1000);
    std::tm tm{};
    localtime_r(&t, &tm);
    char buf[8];
    std::strftime(buf, sizeof buf, "%H:%M", &tm);
    return buf;
}

// One UTF-8 character off the end of what she has typed.
void pop_char(std::string& s) {
    while (!s.empty() && (static_cast<unsigned char>(s.back()) & 0xC0) == 0x80) s.pop_back();
    if (!s.empty()) s.pop_back();
}

// What each ticket was for.
enum class Ask { Login, Docs, Agents, Quizzes, Art, Write };
struct Asked {
    Ask what = Ask::Docs;
    art::Id art = art::Id::Count;
    std::string label;
};

}  // namespace

struct App::Impl {
    // what it was started with
    std::filesystem::path data, home, art_dir, manor_json, assets, shot, prefs;
    std::string origin;            // her gateway; empty, a folder of documents
    int shot_w = 1280, shot_h = 800, shot_css = 1;
    bool shot_touch = false;
    std::string steps;

    // the window, or the surface a shot is drawn on
    SDL_Window* window = nullptr;
    SDL_Renderer* r = nullptr;
    SDL_Surface* surface = nullptr;
    SDL_Texture* world = nullptr;
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
    std::string live = "On this computer", status;

    // the gateway
    std::unique_ptr<net::Net> net;
    std::map<std::uint32_t, Asked> asked;
    Phase phase = Phase::Running;
    ui::SignIn form;
    double last_read = -1e9;       // when the 30-second clock last struck
    int reads_out = 0;             // documents, cats and homework still on their way
    bool read_once = false;
    std::string net_trouble, art_trouble, said;
    double said_until = 0;
    std::int64_t live_at = 0;
    std::set<art::Id> fetching;

    // the pointer
    std::optional<draw::Pt> pointer;   // where it last really moved
    bool pressed = false, on_ui = false, dragging = false, on_map = false;
    draw::Pt press_at, last_at;
    double press_t = 0;
    double last_click_t = -1;
    std::string last_click_room;
    float pinch = 1;

    float k() const { return float(std::max(1, stage.css)); }
    int u_ui() const { return stage.css * (stage.narrow() ? 1 : 2); }

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
        return f;
    }

    // ---- the house, from a folder until the network code lands ----

    bool read_house() {
        const std::string db = slurp(data / "db.json"), agents = slurp(data / "agents.json");
        if (db.empty()) { std::fprintf(stderr, "catio_app: no db.json in %s\n", data.string().c_str()); return false; }
        house.docs(db);
        house.agents(agents.empty() ? "[]" : agents);
        if (const std::string q = slurp(data / "quizzes.json"); !q.empty()) house.quizzes(q);
        return true;
    }

    void say_status() {
        std::vector<std::string> wrong;
        if (now < said_until && !said.empty()) wrong.push_back(said);
        if (!net_trouble.empty()) wrong.push_back(net_trouble);
        if (phase == Phase::FirstRead) wrong.push_back("Waking the cats\u2026");
        if (phase == Phase::Setup) wrong.push_back("This caf\u00e9 has no rooms yet: set it up in a browser for now, at your gateway's address.");
        if (!art_trouble.empty()) wrong.push_back(art_trouble);
        else if (art && art->have() < art->total())
            wrong.push_back(!fetching.empty()
                ? "Fetching the caf\u00e9's art\u2026 (" + std::to_string(art->have()) + " of " + std::to_string(art->total()) + ")"
                : "The caf\u00e9's art isn't all here (" + std::to_string(art->have()) + " of " + std::to_string(art->total()) + "): it comes from your gateway once you sign in.");
        if (origin.empty() && data == std::filesystem::path(CATIO_SOURCE_DIR) / "test" / "fixtures")
            wrong.push_back("Example cats, not yours: give the app your gateway (--gateway) to see your caf\u00e9.");
        status.clear();
        for (const auto& w : wrong) status += (status.empty() ? "" : " ") + w;
    }

    // ---- the gateway ----

    void ask(Ask what, net::Job job, art::Id id = art::Id::Count, std::string label = {}) {
        asked[net->send(std::move(job))] = Asked{what, id, std::move(label)};
        if (what == Ask::Docs || what == Ask::Agents || what == Ask::Quizzes) ++reads_out;
    }
    // the documents, the cats and the homework, together, as the page reads them
    void read_all() {
        if (!net || reads_out) return;
        last_read = now;
        ask(Ask::Docs, [](net::Gateway& g) { return g.docs(); });
        ask(Ask::Agents, [](net::Gateway& g) { return g.tool("list_agents", "{}"); });
        ask(Ask::Quizzes, [](net::Gateway& g) { return g.tool("quizzes", "{}"); });
    }
    // what the cache lacks, the house and the meadow first
    void fetch_art() {
        if (!net || !art) return;
        for (const art::File* file : art->missing()) {
            if (fetching.count(file->id)) continue;
            fetching.insert(file->id);
            const std::string path(file->path);
            ask(Ask::Art, [path](net::Gateway& g) { return g.art(path); }, file->id, path);
        }
    }
    void sign_in() {
        if (form.busy || form.user.empty() || form.password.empty()) return;
        if (form.ask_origin) {
            std::string o = form.origin;
            while (!o.empty() && (o.back() == '/' || o.back() == ' ')) o.pop_back();
            if (o.rfind("https://", 0) != 0) { form.problem = "Your gateway's address starts with https://."; return; }
            if (o != origin || !net) origin = o, net = std::make_unique<net::Net>(origin, home / "cookie");
        }
        form.busy = true;
        form.problem.clear();
        const std::string user = form.user, password = form.password;
        ask(Ask::Login, [user, password](net::Gateway& g) { return g.login(user, password); });
    }
    void signed_out(std::string why) {
        phase = Phase::SignIn;
        form.busy = false;
        form.password.clear();
        form.field = form.ask_origin && form.origin.empty() ? 0 : form.user.empty() ? 1 : 2;
        form.problem = std::move(why);
        ui.close_menu();
        ui.close_card();
        ui.online(false);
        reads_out = 0;
        asked.clear();   // what comes back for them now has nowhere to go
    }
    void heard(const Asked& a, net::Reply& r) {
        if (net::signed_out(r) && a.what != Ask::Login) { signed_out("Signed out: sign in again."); return; }
        if (r.err.code == "unreachable") {
            net_trouble = "Can't reach your gateway (" + r.err.message + "). Trying again in half a minute.";
            if (a.what == Ask::Login) form.busy = false, form.problem = "Can't reach " + origin + ": " + r.err.message;
            if (a.what == Ask::Art) fetching.erase(a.art);
            if (a.what == Ask::Docs || a.what == Ask::Agents || a.what == Ask::Quizzes) --reads_out;
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
                phase = Phase::FirstRead;
                save_prefs();   // the address that worked
                read_all();
                return;
            case Ask::Docs:
            case Ask::Agents:
            case Ask::Quizzes:
                --reads_out;
                if (!r.ok()) { net_trouble = "Your gateway didn't answer (" + r.err.code + "): " + r.err.message; return; }
                net_trouble.clear();
                if (a.what == Ask::Docs) house.docs(r.body);
                else if (a.what == Ask::Agents) house.agents(r.body), live_at = wall_ms();
                else house.quizzes(r.body);
                if (!reads_out && phase == Phase::FirstRead) {
                    phase = house.never_set_up() ? Phase::Setup : Phase::Running;
                    read_once = true;
                    ui.online(true);
                    fetch_art();
                }
                return;
            case Ask::Art:
                fetching.erase(a.art);
                if (!r.ok()) {
                    // the packs' licences are personal: a guest's café is drawn plainly, and says why
                    art_trouble = r.err.code == "not_found"
                        ? "Your gateway has no art for this caf\u00e9 (" + a.label + "): the packs' art is its first owner's alone."
                        : "The caf\u00e9's art couldn't all come (" + r.err.code + "). Check now tries again.";
                    return;
                }
                if (!art->store(a.art, r.body)) { art_trouble = "A piece of the art came back broken (" + std::string(art->trouble()) + ")."; return; }
                if (a.art == art::Id::SproutFont) ui.fonts(assets, *art, stage.css);
                return;
            case Ask::Write:
                if (!r.ok()) { said = "Your gateway didn't take it (" + r.err.code + "): " + r.err.message, said_until = now + 6; return; }
                if (!a.label.empty()) said = a.label, said_until = now + 4;
                last_read = -1e9;   // see the change at once
                return;
        }
    }

    // ---- prefs: the map folded or open, still cats ----

    void load_prefs() {
        if (prefs.empty()) return;
        try {
            const auto j = nlohmann::json::parse(slurp(prefs));
            if (j.contains("minimap")) ui.set_map_open(j["minimap"] == "open");
            still = j.value("still", false);
            if (form.ask_origin && j.contains("gateway") && j["gateway"].is_string()) form.origin = j["gateway"].get<std::string>();
        } catch (...) {}
    }
    void save_prefs() {
        if (prefs.empty() || !shot.empty()) return;
        nlohmann::json j{{"minimap", ui.map_open() ? "open" : "folded"}, {"still", still}};
        if (form.ask_origin && !origin.empty()) j["gateway"] = origin;
        std::ofstream(prefs) << j.dump();
    }

    // ---- the camera ----

    void place(view::Cam c) {
        c = view::clamp(c, stage);
        c.floor = cam.floor;
        c.focus = cam.focus;
        cam = c;
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
    }
    // the room that needs her most, for a phone's first view (her fix to "the house is tiny")
    std::string urgent_room() const {
        const auto need = house.needing();
        for (const Cat* c : need) if (manor::level_of(c->mood == Mood::Meow ? "hall" : c->room) == manor::Level::Ground)
            return c->mood == Mood::Meow ? "hall" : c->room;
        return need.empty() ? "" : need.front()->room;
    }

    // ---- the frame ----

    void resize(int w, int h, float content_scale) {
        stage.w = w, stage.h = h;
        stage.css = draw::css_for(content_scale);
        ui.fonts(assets, *art, stage.css);
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
        scene = view::build(house, cam.floor);
        const double t = still ? 0 : now;
        auto blits = view::world(scene, cam.floor, t);

        // what the pointer is on, or whose menu is open, is outlined round its own shape
        std::optional<view::Blit> outlined;
        auto spot_of = [&](Thing what, const std::string& key) -> std::optional<view::Spot> {
            if (what == Thing::Cat) for (const auto& s : scene.cats) if (s.cat && s.cat->id == key) return s;
            if (what == Thing::Queen && scene.queen) return *scene.queen;
            if (what == Thing::Pile)
                for (const auto& p : scene.piles)
                    if (p.room == key) return view::Spot{p.cats[0], p.cats[0]->mood, p.cats[0]->coat, p.at, p.room};
            return std::nullopt;
        };
        if (auto s = spot_of(ui.tipped().what, ui.tipped().key)) outlined = view::blit_of(*s, t);
        else if (auto m = spot_of(ui.menu_kind(), ui.menu_key())) outlined = view::blit_of(*m, t);

        draw::Ctx wc{&canvas, art.get(), 2, 1};
        SDL_SetRenderTarget(r, world);
        SDL_SetRenderDrawColor(r, 0x8F, 0xBF, 0x4F, 255);
        SDL_RenderClear(r);
        for (const auto& b : blits) {
            if (b.fill) {
                // a closed room under the pointer, or with its menu open, is lightened to 18%
                const bool lit = !b.room.empty() && ((ui.tipped().what == Thing::Room && ui.tipped().key == b.room) ||
                                                     (ui.menu_kind() == Thing::Room && ui.menu_key() == b.room));
                draw::Colour col = b.colour;
                if (lit) col.a = 46;
                draw::fill(wc, b.dst, col);
                continue;
            }
            if (outlined && b.z == outlined->z && b.sheet == outlined->sheet && b.dst.x == outlined->dst.x && b.dst.y == outlined->dst.y)
                for (auto [dx, dy] : {std::pair{2.f, 0.f}, {-2.f, 0.f}, {0.f, 2.f}, {0.f, -2.f}})
                    draw::cell(wc, b.sheet, b.src, draw::Rect{b.dst.x + dx, b.dst.y + dy, b.dst.w, b.dst.h}, draw::kOutline);
            draw::cell(wc, b.sheet, b.src, b.dst, b.coat);
        }
        SDL_SetRenderTarget(r, nullptr);

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
        auto lit_room = [&](const std::string& key) {
            const manor::Geom* g = manor::of(key);
            if (!g || g->level != cam.floor || key == cam.focus) return;
            const draw::Rect box{g->box.x * float(cam.u) + cam.tx, g->box.y * float(cam.u) + cam.ty, g->box.w * float(cam.u), g->box.h * float(cam.u)};
            if (house.open(key)) draw::fill(c, box, {0xFF, 0xFA, 0xE1, 31});   // a closed room keeps its shade, lightened
            const float U = float(u_ui());
            draw::nine(c, art::Id::UiCorners, {}, {8, 8, 9, 9}, {8 * U, 8 * U, 9 * U, 9 * U}, box, false);
        };
        if (ui.tipped().what == Thing::Room) lit_room(ui.tipped().key);
        if (ui.menu_kind() == Thing::Room && ui.menu_key() != ui.tipped().key) lit_room(ui.menu_key());
        if (ui.tipped().what == Thing::Stairs) {
            const manor::Box s = manor::stairs();
            const draw::Rect box{s.x * float(cam.u) + cam.tx, s.y * float(cam.u) + cam.ty, s.w * float(cam.u), s.h * float(cam.u)};
            draw::fill(c, box, {0xFF, 0xFA, 0xE1, 36});
            draw::nine(c, art::Id::UiCorners, {}, {8, 8, 9, 9}, {8 * k(), 8 * k(), 9 * k(), 9 * k()}, box, false);
        }

        ui.draw(c, frame());
    }

    // ---- input ----

    view::Hit pick(float x, float y) const { return view::pick(scene, cam, stage, x, y, coarse); }

    void handle(App& app, const In& in);

    void cursor(bool on_something) {
        if (!window || on_something == pointing) return;
        pointing = on_something;
        if (point && paw) SDL_SetCursor(on_something ? point : paw);
    }
};

App::App() : impl_(new Impl) {}
App::~App() {
    Impl& I = *impl_;
    if (I.world) SDL_DestroyTexture(I.world);
    I.art.reset();   // its textures belong to the renderer
    if (I.r) SDL_DestroyRenderer(I.r);
    if (I.surface) SDL_DestroySurface(I.surface);
    if (I.paw) SDL_DestroyCursor(I.paw);
    if (I.point) SDL_DestroyCursor(I.point);
    if (I.window) SDL_DestroyWindow(I.window);
    SDL_Quit();
    delete impl_;
}

bool App::start(int argc, char** argv) {
    Impl& I = *impl_;
    const std::filesystem::path src = CATIO_SOURCE_DIR;
    const char* base_c = SDL_GetBasePath();
    const std::filesystem::path base = base_c ? base_c : "";
    std::string gateway;
    bool gateway_given = false;
    for (int i = 1; i < argc; ++i) {
        const std::string a = argv[i];
        auto next = [&]() -> std::string { return i + 1 < argc ? argv[++i] : ""; };
        if (a == "--data") I.data = next();
        else if (a == "--gateway") gateway = next(), gateway_given = true;
        else if (a == "--home") I.home = next();
        else if (a == "--art") I.art_dir = next();
        else if (a == "--manor") I.manor_json = next();
        else if (a == "--assets") I.assets = next();
        else if (a == "--shot") I.shot = next();
        else if (a == "--size") { const std::string v = next(); std::sscanf(v.c_str(), "%dx%d", &I.shot_w, &I.shot_h); }
        else if (a == "--css") I.shot_css = std::max(1, std::atoi(next().c_str()));
        else if (a == "--touch") I.shot_touch = true;
        else if (a == "--still") I.still = true;
        else if (a == "--do") I.steps = next();
        else { std::fprintf(stderr, "catio_app: what is %s? See include/catio/app.h.\n", a.c_str()); return false; }
    }
    if (I.manor_json.empty()) I.manor_json = first_of({base / "manor.json", src / "generated" / "manor.json"});
    if (I.assets.empty()) I.assets = first_of({base / "assets", src / "assets"});
#ifdef CATIO_GATEWAY_ORIGIN
    if (!gateway_given && I.data.empty()) gateway = CATIO_GATEWAY_ORIGIN, gateway_given = true;   // her build
#endif
    if (!manor::load(I.manor_json)) { std::fprintf(stderr, "catio_app: no floor plan at %s\n", I.manor_json.string().c_str()); return false; }

    // where her cookie, the prefs and the art's cache live: the app's own private folder, or the one she names
    if (I.home.empty()) {
        char* pref = SDL_GetPrefPath("KittyChat", "Cafe");
        if (pref) I.home = pref, SDL_free(pref);
    }
    if (I.art_dir.empty() && !I.home.empty()) I.art_dir = I.home / "cache";
    if (I.shot.empty() && !I.home.empty()) I.prefs = I.home / "prefs.json";

    if (gateway_given) {
        // the gateway: signed in already, or the sign-in screen first
        I.form.ask_origin = gateway.empty() || gateway == "ask";
        I.load_prefs();
        I.origin = I.form.ask_origin ? I.form.origin : gateway;
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
        SDL_SetRenderVSync(I.r, 1);
    }
    I.canvas.r = I.r;
    I.world = SDL_CreateTexture(I.r, SDL_PIXELFORMAT_RGBA32, SDL_TEXTUREACCESS_TARGET, 1920, 1152);
    if (!I.world) { std::fprintf(stderr, "catio_app: no world target: %s\n", SDL_GetError()); return false; }
    SDL_SetTextureScaleMode(I.world, SDL_SCALEMODE_NEAREST);

    int w = I.shot_w, h = I.shot_h;
    float scale = float(I.shot_css);
    if (I.window) SDL_GetRenderOutputSize(I.r, &w, &h), scale = SDL_GetWindowDisplayScale(I.window);
    I.resize(w, h, scale);
    if (!I.ui.fonts(I.assets, *I.art, I.stage.css)) { std::fprintf(stderr, "catio_app: no fonts in %s\n", I.assets.string().c_str()); return false; }

    // the paw, and the paw that points (32 x 32 at one CSS pixel each)
    if (I.window)
        if (const art::Texture* t = I.art->texture(art::Id::UiCursor); t && t->surface) {
            const art::Texture* p = I.art->texture(art::Id::UiCursorPoint);
            const int s = I.stage.css;
            SDL_Surface* a = SDL_ScaleSurface(t->surface, 32 * s, 32 * s, SDL_SCALEMODE_NEAREST);
            SDL_Surface* b = p && p->surface ? SDL_ScaleSurface(p->surface, 32 * s, 32 * s, SDL_SCALEMODE_NEAREST) : nullptr;
            if (a) I.paw = SDL_CreateColorCursor(a, 9 * s, 5 * s), SDL_DestroySurface(a);
            if (b) I.point = SDL_CreateColorCursor(b, 9 * s, 3 * s), SDL_DestroySurface(b);
            if (I.paw) SDL_SetCursor(I.paw);
        }

    // the first view: the whole manor; on a phone, the room that needs her most
    I.cam.floor = manor::Level::Ground;
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
            I.cam = view::zoom_by(I.cam, what == Action::ZoomIn ? 1 : -1, I.stage.w / 2.f, I.stage.h / 2.f, I.stage);
            I.settle();
            break;
        case Action::ToFloor: I.set_floor(arg == "upper" ? manor::Level::Upper : manor::Level::Ground); break;
        case Action::FoldMap: I.save_prefs(); break;
        case Action::MapAt: {
            int x = 0, y = 0;
            if (std::sscanf(arg.c_str(), "%d %d", &x, &y) == 2) {
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
            if (I.window) SDL_OpenURL(arg.c_str());
            else std::printf("open %s\n", arg.c_str());
            break;
        case Action::CheckNow:
            I.art_trouble.clear();
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
    if (!I.net) {   // a folder of documents: read it again when asked
        if (now) I.read_house();
        return;
    }
    if (I.phase == Phase::SignIn) return;
    if (now || I.now - I.last_read >= 30) {
        I.read_all();
        if (I.read_once && I.fetching.empty() && I.art_trouble.empty()) I.fetch_art();
    }
}

void App::pump_net() {
    Impl& I = *impl_;
    if (!I.net) return;
    const Phase was = I.phase;
    std::uint32_t t = 0;
    net::Reply r;
    while (I.net && I.net->take(&t, &r)) {
        auto it = I.asked.find(t);
        if (it == I.asked.end()) continue;   // asked before she was signed out: nowhere to go now
        const Asked a = it->second;
        I.asked.erase(it);
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
    std::vector<In> ins;
    SDL_Event e;
    while (SDL_PollEvent(&e)) {
        SDL_ConvertEventToRenderCoordinates(I.r, &e);
        In in;
        in.at = clock_s();
        switch (e.type) {
            case SDL_EVENT_QUIT: in.kind = In::Quit; break;
            case SDL_EVENT_WINDOW_PIXEL_SIZE_CHANGED:
            case SDL_EVENT_WINDOW_DISPLAY_SCALE_CHANGED: in.kind = In::Resize; break;
            case SDL_EVENT_MOUSE_MOTION: in.kind = In::Move, in.x = e.motion.x, in.y = e.motion.y, in.touch = e.motion.which == SDL_TOUCH_MOUSEID; break;
            case SDL_EVENT_MOUSE_BUTTON_DOWN: in.kind = In::Down, in.x = e.button.x, in.y = e.button.y, in.touch = e.button.which == SDL_TOUCH_MOUSEID; break;
            case SDL_EVENT_MOUSE_BUTTON_UP: in.kind = In::Up, in.x = e.button.x, in.y = e.button.y, in.touch = e.button.which == SDL_TOUCH_MOUSEID; break;
            case SDL_EVENT_MOUSE_WHEEL: in.kind = In::Wheel, in.x = e.wheel.mouse_x, in.y = e.wheel.mouse_y, in.dy = e.wheel.y; break;
            case SDL_EVENT_TEXT_INPUT: in.kind = In::Text, in.key = e.text.text ? e.text.text : ""; break;
            case SDL_EVENT_PINCH_UPDATE: in.kind = In::Pinch, in.scale = e.pinch.scale, in.touch = true; break;
            case SDL_EVENT_KEY_DOWN: {
                in.kind = In::Key;
                in.shift = (e.key.mod & SDL_KMOD_SHIFT) != 0;
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
        ins.push_back(in);
    }
    for (const In& in : ins) {
        if (in.kind == In::Quit) { I.quit = true; continue; }
        if (in.kind == In::Resize) {
            int w = 0, h = 0;
            SDL_GetRenderOutputSize(I.r, &w, &h);
            I.resize(w, h, SDL_GetWindowDisplayScale(I.window));
            continue;
        }
        I.handle(*this, in);
    }
}

// The page's pointer and keys, for the window and for a shot's steps alike.
void App::Impl::handle(App& app, const In& in) {
    const ui::Frame f = frame();
    if (phase == Phase::SignIn) {   // a form: its fields, Tab between them, Enter to come in
        std::string* field = form.field == 0 ? &form.origin : form.field == 1 ? &form.user : &form.password;
        switch (in.kind) {
            case In::Move: ui.hover(f, in.x, in.y); cursor(!ui.under(f, in.x, in.y).empty()); return;
            case In::Up: {
                ui::Action a;
                std::string arg;
                if (ui.press(f, in.x, in.y, &a, &arg) && a != Action::None) app.act(a, arg);
                return;
            }
            case In::Text:
                if (!form.busy && field->size() + in.key.size() <= 1024) *field += in.key;
                return;
            case In::Key:
                if (form.busy) return;
                if (in.key == "enter") sign_in();
                else if (in.key == "backspace") pop_char(*field);
                else if (in.key == "tab") {
                    const int first = form.ask_origin ? 0 : 1;
                    form.field = in.shift ? (form.field <= first ? 2 : form.field - 1) : (form.field >= 2 ? first : form.field + 1);
                }
                return;
            default: return;
        }
    }
    switch (in.kind) {
        case In::Move: {
            coarse = in.touch;
            if (pressed) {
                const float dx = in.x - last_at.x, dy = in.y - last_at.y;
                if (on_map) {   // dragging on the minimap pans the view with it
                    std::string arg;
                    if (ui.map_drag(f, in.x, in.y, &arg)) app.act(Action::MapAt, arg), dragging = true;
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
            coarse = in.touch;
            pressed = true;
            dragging = false;
            press_at = last_at = {in.x, in.y};
            press_t = in.at;
            on_ui = ui.over(f, in.x, in.y);
            on_map = false;
            if (on_ui) {
                ui.hold(f, in.x, in.y, true);
                on_map = ui.under(f, in.x, in.y) == "map:mm";   // a drag on the minimap pans the view with it
            }
            return;
        }
        case In::Up: {
            if (!pressed) return;
            pressed = false;
            ui.hold(f, in.x, in.y, false);
            if (dragging && on_map) { dragging = on_map = on_ui = false; return; }   // the minimap drag is done
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
                if (ui.press(f, in.x, in.y, &a, &arg) && a != Action::None) app.act(a, arg);
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
                    view::Hit room{Thing::Room, h.key, {g->box.x * float(cam.u) + cam.tx, g->box.y * float(cam.u) + cam.ty, g->box.w * float(cam.u), g->box.h * float(cam.u)}};
                    ui.toggle(f, room);
                    return;
                }
                default: ui.close_menu(); return;
            }
        }
        case In::Wheel: {
            if (ui.over(f, in.x, in.y) && ui.card() != ui::Card::None) return;
            ui.close_menu();
            cam = view::zoom_by(cam, in.dy > 0 ? 1 : -1, in.x, in.y, stage);
            settle();
            return;
        }
        case In::Pinch: {
            pinch *= in.scale;
            if (pinch > 1.25f || pinch < 0.8f) {
                ui.close_menu();
                const draw::Pt at = pointer.value_or(draw::Pt{stage.w / 2.f, stage.h / 2.f});
                cam = view::zoom_by(cam, pinch > 1 ? 1 : -1, at.x, at.y, stage);
                pinch = 1;
                settle();
            }
            return;
        }
        case In::Key: {
            const std::string& key = in.key;
            if (key == "escape") { if (!ui.escape() && !cam.focus.empty()) go(""); return; }
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
                ui.toggle(f, view::Hit{Thing::Room, std::string(to), {g->box.x * float(cam.u) + cam.tx, g->box.y * float(cam.u) + cam.ty, g->box.w * float(cam.u), g->box.h * float(cam.u)}});
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
        if (!SDL_SavePNG(I.surface, I.shot.string().c_str())) { std::fprintf(stderr, "catio_app: %s\n", SDL_GetError()); return 1; }
        std::printf("%s: %dx%d at css %d\n", I.shot.string().c_str(), I.stage.w, I.stage.h, I.stage.css);
        return 0;
    }
    while (!I.quit) {
        // the sign-in form takes typing; the house does not
        if (I.phase == Phase::SignIn && !SDL_TextInputActive(I.window)) SDL_StartTextInput(I.window);
        else if (I.phase != Phase::SignIn && SDL_TextInputActive(I.window)) SDL_StopTextInput(I.window);
        events();
        pump_net();
        I.now = clock_s() - I.start;
        refresh(false);
        I.draw();
        SDL_RenderPresent(I.r);
    }
    return 0;
}

}  // namespace catio
