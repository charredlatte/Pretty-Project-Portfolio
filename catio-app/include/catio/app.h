// app.h — the loop, who owns what, and the one place a press becomes a write.
//
// Nothing includes this header.
//
// The order of a frame: pump the window's events, drain the net's replies, build the scene from the
// house, settle the walks, draw (meadow, the floor's art, rugs, wall pieces, then floor pieces and cats
// interleaved by their bottom edge, then the upper floor lifted), then the interface over it.
//
// WRITES HAPPEN ON HER PRESS AND NEVER OTHERWISE. act() is the only function that sends one, so there
// is one place to read to know everything this app can change.
//
// DRAFT: declarations only. Nothing here is implemented yet.

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

    /// The gateway's origin comes from the build, or from her on the sign-in screen when it was not
    /// baked in. Returns false when the window or the generated floor plan will not open.
    bool start(int argc, char** argv);
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

    Phase phase_ = Phase::SignIn;

    struct Impl;
    Impl* impl_;
};

}  // namespace catio

#endif  // CATIO_APP_H
