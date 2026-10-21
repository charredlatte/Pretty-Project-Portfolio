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
// line, the menus, the map panel and the Cat card; and, given a gateway, signing in, the first read,
// fetching the art the cache lacks, reading again every 30 seconds, and the writes (Open this room).
// Given a folder instead (--data; the test's invented cats by default), it draws that, and writes nothing.
//
//   catio_app [--gateway <origin> | --gateway ask | --data <dir>] [--home <dir>] [--art <dir>]
//             [--manor <file>] [--assets <dir>]
//             [--shot <out.png> [--size WxH] [--css N] [--touch] [--still] [--do "<steps>"]]
//
// --home is where it keeps her cookie, its prefs and the art's cache (the platform's private app folder
// by default); --art reads the art from another folder instead, such as the page's catio/.
//
// --shot draws frames into a plain surface with no window and no GPU, and saves the last one: the
// app's own "look first". --do plays steps before it, one frame after each, `;` between them, in CSS
// pixels: move X Y, click X Y, down X Y, up X Y, drag X1 Y1 X2 Y2, wheel X Y DY, key NAME (escape,
// pageup, pagedown, plus, minus, 0, m, left, right, up, down, shift+left, tab, enter, backspace...),
// type TEXT, wait SECONDS, choose LABEL (press the item or button that says it, wherever it was drawn),
// slide LABEL > LABEL (down on one, up on the other), right LABEL (a right click on it). After each step it waits for the network to answer,
// so a shot is the same every time.

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
    FirstRead,  ///< GET /api/db, list_agents and quizzes, together; the art is fetched after, as it is missing
    Running,
    Setup       ///< a café with no rooms at all: the wizard is still to come, so the sign says to set it up in a browser
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

    struct Impl;
    Impl* impl_;
};

}  // namespace catio

#endif  // CATIO_APP_H
