// app.h — the loop, who owns what, and the one place a press becomes a write.
//
// Nothing includes this header but main.cpp.
//
// The order of a frame: pump the window's events, drain the net's replies, build the scene from the
// house, settle the walks, draw (meadow, the floor's art, rugs, wall pieces, then floor pieces and cats
// interleaved by their bottom edge, then the upper floor lifted), then the interface over it.
//
// WRITES HAPPEN ON HER PRESS AND NEVER OTHERWISE. act() is the only function that sends one, so there
// is one place to read to know everything this app can change.
//
// Implemented in src/app.cpp: the window, the loop, the camera (drag, wheel, pinch, keys), the hover
// line, the menus, the map panel and the Cat card. Until the network code lands, the house is read
// from a folder (--data, the test's invented cats by default) and the status sign says so.
//
//   catio_app [--data <dir>] [--art <dir>] [--manor <file>] [--assets <dir>]
//             [--shot <out.png> [--size WxH] [--css N] [--touch] [--still] [--do "<steps>"]]
//
// --shot draws frames into a plain surface with no window and no GPU, and saves the last one: the
// app's own "look first". --do plays steps before it, one frame after each, `;` between them, in CSS
// pixels: move X Y, click X Y, down X Y, up X Y, drag X1 Y1 X2 Y2, wheel X Y DY, key NAME (escape,
// pageup, pagedown, plus, minus, 0, m, left, right, up, down, shift+left...), wait SECONDS.

#ifndef CATIO_APP_H
#define CATIO_APP_H

#include <string_view>

#include "catio/art.h"
#include "catio/draw.h"
#include "catio/house.h"
#include "catio/net.h"
#include "catio/ui.h"
#include "catio/view.h"

namespace catio {

enum class Phase {
    SignIn,     ///< her handle and password; drawn in the bundled font, since no pack art exists yet
    FirstRead,  ///< GET /api/db and list_agents, together
    Art,        ///< fetching what the cache lacks: "Fetching the café's art… (n of m)"
    Running,
    Setup       ///< a café with no rooms at all: the wizard, before the house
};

class App {
public:
    App();
    ~App();

    /// Read the arguments, open the floor plan, the house, the art and the fonts, and the window (or
    /// the surface, with --shot). False, having said why, when any of them will not open.
    bool start(int argc, char** argv);
    /// The loop, until she closes the window; or, with --shot, the steps and one saved frame.
    int run();

private:
    void events();
    /// Drain the net: documents, cats, art bytes, tool replies. Nothing in a frame ever blocks on it.
    void pump_net();
    /// The 30-second clock, as the page polls: list_agents, and the documents with it. `now` jumps the
    /// clock after a write, and on coming back to the foreground.
    void refresh(bool now);
    /// THE ONLY PLACE A WRITE HAPPENS.
    void act(ui::Action what, std::string_view arg);

    Phase phase_ = Phase::Running;

    struct Impl;
    Impl* impl_;
};

}  // namespace catio

#endif  // CATIO_APP_H
