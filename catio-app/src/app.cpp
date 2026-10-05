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

#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <optional>
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
    enum Kind { Move, Down, Up, Wheel, Key, Pinch, Resize, Quit } kind = Move;
    float x = 0, y = 0, dy = 0, scale = 1;
    bool touch = false, shift = false;
    std::string key;
    double at = 0;
};

constexpr manor::Dir kArrows[] = {manor::Dir::Left, manor::Dir::Right, manor::Dir::Up, manor::Dir::Down};

}  // namespace

struct App::Impl {
    // what it was started with
    std::filesystem::path data, art_dir, manor_json, assets, shot, prefs;
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
        f.live = live;
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
        if (art && art->have() < art->total())
            wrong.push_back("The café's art isn't all here (" + std::to_string(art->have()) + " of " + std::to_string(art->total()) +
                            "): the app fetches it from your gateway once its network code is in.");
        if (data == std::filesystem::path(CATIO_SOURCE_DIR) / "test" / "fixtures")
            wrong.push_back("Example cats, not yours: the app reads your café once its network code is in.");
        status.clear();
        for (const auto& w : wrong) status += (status.empty() ? "" : " ") + w;
    }

    // ---- prefs: the map folded or open, still cats ----

    void load_prefs() {
        if (prefs.empty()) return;
        try {
            const auto j = nlohmann::json::parse(slurp(prefs));
            if (j.contains("minimap")) ui.set_map_open(j["minimap"] == "open");
            still = j.value("still", false);
        } catch (...) {}
    }
    void save_prefs() {
        if (prefs.empty() || !shot.empty()) return;
        nlohmann::json j{{"minimap", ui.map_open() ? "open" : "folded"}, {"still", still}};
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
            if (b.fill) { draw::fill(wc, b.dst, b.colour); continue; }
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
            draw::fill(c, box, {0xFF, 0xFA, 0xE1, 31});
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
    for (int i = 1; i < argc; ++i) {
        const std::string a = argv[i];
        auto next = [&]() -> std::string { return i + 1 < argc ? argv[++i] : ""; };
        if (a == "--data") I.data = next();
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
    if (I.data.empty()) I.data = src / "test" / "fixtures";
    if (!manor::load(I.manor_json)) { std::fprintf(stderr, "catio_app: no floor plan at %s\n", I.manor_json.string().c_str()); return false; }
    if (!I.read_house()) return false;

    // the art's cache: the app's own private folder, or the one she names
    if (I.art_dir.empty()) {
        char* pref = SDL_GetPrefPath("KittyChat", "Cafe");
        if (pref) {
            I.art_dir = std::filesystem::path(pref) / "cache";
            if (I.shot.empty()) I.prefs = std::filesystem::path(pref) / "prefs.json";
            SDL_free(pref);
        }
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
        I.load_prefs();
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
    I.say_status();
    I.start = clock_s();
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
        case Action::CheckNow: refresh(true); break;
        default: break;   // the rest arrive with their cards, and the writes with the network code
    }
}

void App::refresh(bool now) {
    (void)now;
    impl_->read_house();   // the folder again; the gateway's list_agents, once the network code is in
}

void App::pump_net() {}

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
        // the steps, a frame after each, then the frame she looks at
        I.now = 0;
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
            else { std::fprintf(stderr, "catio_app: what step is %s?\n", verb.c_str()); return 2; }
            I.now += 0.05;
            I.draw();
        }
        I.draw();
        SDL_RenderPresent(I.r);
        if (!SDL_SavePNG(I.surface, I.shot.string().c_str())) { std::fprintf(stderr, "catio_app: %s\n", SDL_GetError()); return 1; }
        std::printf("%s: %dx%d at css %d\n", I.shot.string().c_str(), I.stage.w, I.stage.h, I.stage.css);
        return 0;
    }
    while (!I.quit) {
        events();
        pump_net();
        I.now = clock_s() - I.start;
        I.draw();
        SDL_RenderPresent(I.r);
    }
    return 0;
}

}  // namespace catio
