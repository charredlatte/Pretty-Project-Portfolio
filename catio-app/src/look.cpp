// catio_look -- render a floor, or one room, to a PNG: no window, no GPU.
//
//   catio_look <catio dir> <manor.json> <fixtures dir> <out.png> [ground | upper | <room key>]
//
// What CLAUDE.md's "look first" asks of the page, for the app: draw it, open the picture, hold it against
// what she asked for. The <catio dir> is where art/ lives -- the page's own folder, whose art/licensed/
// is read back from the artifact and never committed.
//
// It draws the way the page does: everything into one world-sized target (the page's #world, the art
// doubled, 1920 x 1152), and for a room, that target cropped and scaled up once by a whole number.

#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>

#include "catio/art.h"
#include "catio/draw.h"
#include "catio/house.h"
#include "catio/manor.h"
#include "catio/view.h"
#include "internal.h"

namespace {

std::string slurp(const std::string& path) {
    std::ifstream in(path);
    std::stringstream s;
    s << in.rdbuf();
    return s.str();
}

int fail(const char* what) {
    std::fprintf(stderr, "catio_look: %s: %s\n", what, SDL_GetError());
    return 1;
}

}  // namespace

int main(int argc, char** argv) {
    using namespace catio;
    if (argc < 5) {
        std::fprintf(stderr, "catio_look <catio dir> <manor.json> <fixtures dir> <out.png> [ground|upper|<room>]\n");
        return 2;
    }
    const std::string what = argc > 5 ? argv[5] : "ground";

    if (!manor::load(argv[2])) { std::fprintf(stderr, "catio_look: no floor plan at %s\n", argv[2]); return 1; }
    House house;
    house.docs(slurp(std::string(argv[3]) + "/db.json"));
    house.agents(slurp(std::string(argv[3]) + "/agents.json"));

    art::Art art(argv[1]);
    art.scan();
    std::printf("art: %d of %d files in %s\n", art.have(), art.total(), argv[1]);
    if (!art.missing().empty()) {
        std::printf("  missing, so not drawn:");
        for (const auto* f : art.missing()) std::printf(" %.*s", int(f->path.size()), f->path.data());
        std::printf("\n");
    }

    // a room key draws its floor, then crops to it
    const manor::Geom* room = (what == "ground" || what == "upper") ? nullptr : manor::of(what);
    if (!room && what != "ground" && what != "upper") { std::fprintf(stderr, "catio_look: no room %s\n", what.c_str()); return 2; }
    const manor::Level floor = room ? room->level : what == "upper" ? manor::Level::Upper : manor::Level::Ground;

    const view::Scene scene = view::build(house, floor);
    const auto blits = view::world(scene, floor, 0);
    std::printf("scene: %zu cats, %zu piles, %s; %zu things to draw\n", scene.cats.size(), scene.piles.size(),
                scene.queen ? "the queen" : "no queen", blits.size());

    // the world target: the page's #world, over the stage's own green
    const draw::Rect all = view::world_rect();
    SDL_Surface* world = SDL_CreateSurface(int(all.w), int(all.h), SDL_PIXELFORMAT_RGBA32);
    SDL_Renderer* r = world ? SDL_CreateSoftwareRenderer(world) : nullptr;
    if (!r) return fail("renderer");
    SDL_SetRenderDrawColor(r, 0x8F, 0xBF, 0x4F, 255);   // .stage { background: #8FBF4F }
    SDL_RenderClear(r);

    draw::Canvas canvas{r};
    const draw::Ctx ctx{&canvas, &art, 2};
    for (const auto& b : blits) {
        if (b.fill) draw::fill(ctx, b.dst, b.colour);
        else draw::cell(ctx, b.sheet, b.src, b.dst, b.coat);
    }
    SDL_RenderPresent(r);

    SDL_Surface* out = world;
    if (room) {
        // padded(): the room and six art pixels round it, scaled up once by a whole number
        const int p = 6;
        const SDL_Rect src{(room->box.x - p) * 2, (room->box.y - p) * 2, (room->box.w + 2 * p) * 2, (room->box.h + 2 * p) * 2};
        const int k = std::max(1, 1200 / src.w);
        out = SDL_CreateSurface(src.w * k, src.h * k, SDL_PIXELFORMAT_RGBA32);
        if (!out) return fail("crop");
        const SDL_Rect dst{0, 0, out->w, out->h};
        SDL_BlitSurfaceScaled(world, &src, out, &dst, SDL_SCALEMODE_NEAREST);
    }
    if (!SDL_SavePNG(out, argv[4])) return fail("save");
    std::printf("wrote %s (%d x %d)\n", argv[4], out->w, out->h);

    if (out != world) SDL_DestroySurface(out);
    SDL_DestroyRenderer(r);
    SDL_DestroySurface(world);
    return 0;
}
