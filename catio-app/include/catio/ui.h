// ui.h — what is drawn over the house, and what a tap on it does.
//
// It holds the words she reads (apart from the mood labels, which belong with the rank in house.h).
//
// THE RULES THIS MODULE KEEPS, all of them hers.
//
//   No signs on the map. No room names, badges or stair signs on the art. A room is named on hover;
//   the other floor's tab carries its badge; the brand carries the house's.
//
//   Nothing on the cats. No letters, counts, faces, bubbles, pile numbers, crowns, and no "z Z" over a
//   sleeping cat. Hovering one says what it needs: its name and mood, then its ask or its waiting
//   files. A new fact about a cat goes in its hover line, its menu or its card, never on the sprite.
//
//   Two things on screen and nothing else: the brand (top left, which is the House button) and the map
//   panel (top right; bottom right on a phone).
//
//   Every menu has the same shape, as short as it can be: the name with a badge when cats need her and
//   one line under it; then what matters now; then the actions as a list, the first the default, the
//   pack's triangle beside the one under the pointer. A new action is a list item, and only if it earns
//   its place. A card puts what she came for first and folds the rest under Manage.
//
//   Hover names a thing; a click opens its menu beside it, pinned until a click elsewhere or Escape.
//   A tap does the same. Hover means the pointer really moved onto the thing: when the camera moves or
//   a card closes, the room that slides under a still pointer is not named until she moves.
//
// THE PHONE, which is why this app exists at all. Her UI audit, measured at 390x844:
// "On a phone, the house is tiny, has no room names, and cats can't be tapped" — the house fills about
// an eighth of the screen, cats are 6-12px, the smallest rooms 38x44, buttons 32px and the sound switch
// 22px. Her fixes, taken as the starting point and not a backlog: open zoomed into the most urgent
// room, swipe left and right through the NEXT map, fit the camera to the manor rather than the whole
// grounds, and no target under 44px.
//
// DRAFT: declarations only. Nothing here is implemented yet.

#ifndef CATIO_UI_H
#define CATIO_UI_H

#include <string>
#include <string_view>
#include <vector>

#include "catio/draw.h"
#include "catio/house.h"
#include "catio/view.h"

namespace catio::ui {

/// The audit's minimum, in device pixels. Every target on a coarse pointer is grown to it.
inline constexpr float kTouch = 44.0f;

/// What a press asks the app to do. app.h's act() is the only place one becomes a write.
enum class Action {
    None,
    // looking
    LookIn, WholeHouse, ZoomIn, ZoomOut, ToFloor, Swipe,
    // opening
    OpenCat, OpenQueen, OpenPile, OpenCabinet, OpenBrain, OpenRules, OpenMaps, OpenEditRooms,
    OpenSetup, OpenCredits, OpenLink,
    // doing: each one is a write, on her press and never otherwise
    Say, HandIn, AddFiles, Rename, Move, OpenRoom, CloseRoom, Pause, Resume, WrapUp, StopQueen,
    KeepNote, PinNote, FetchArtAgain, SignOut
};

struct Item {
    std::string label;
    Action action = Action::None;
    std::string arg;
    bool primary = false;    ///< the default, first in the list
    bool enabled = true;     ///< a disabled item carries cannot() under it, rather than vanishing
};

struct Menu {
    view::Thing kind = view::Thing::None;
    std::string key;
    std::string title;       ///< the name, with a badge when cats need her
    std::string line;        ///< the one line under it
    std::vector<std::string> now;   ///< what matters now: up to three cats, a queen's note, an ask
    std::vector<Item> items;
    draw::Rect at;           ///< beside its anchor, and clear of the map panel
};

/// The cards. Each puts what she came for first and folds the rest.
enum class Card {
    None, Cat, Queen, QueenSettings, Pile, Adopt, Cabinet, Brain, Rules, Maps, EditRooms, Setup, Credits
};

struct Frame {
    const House* house = nullptr;
    const view::Scene* scene = nullptr;
    const view::Cam* cam = nullptr;
    view::Stage stage;
    double now = 0;
    bool coarse = false;     ///< a touch screen: every target grows to kTouch, and there is no hover
    bool narrow = false;     ///< a phone: the map panel sits bottom right and starts folded
};

class Ui {
public:
    Ui();
    ~Ui();

    /// Hover names a thing in one line. Ignored on a coarse pointer, and only when it really moved.
    void tip(view::Hit h, bool moved);
    /// A click or tap opens its menu beside it, pinned. Keyboard focus opens one only when the focus is
    /// visible, and a click never closes a menu the keyboard opened.
    void toggle(view::Hit h);
    void close_menu();
    void open(Card c, std::string key = {});
    void close_card();
    Card card() const;

    void draw(const draw::Ctx& c, const Frame& f);

    /// A press. False when nothing was pressed.
    bool press(const Frame& f, float x, float y, Action* what, std::string* arg);
    /// A phone swipe: the room next door, following manor::next_room.
    bool swipe(const Frame& f, float dx, std::string* to_room);

    /// Why an action is not here. On the gateway's address the page has an honesty mode for the things
    /// only claude.ai can do; this app is in that mode always, so the table is small and fixed:
    /// no list of her claude.ai sessions, no posting into one that does not report to the gateway, no
    /// starting or archiving one, no LLM file sorter (a dropped file goes to the brain's tray). Those
    /// items are drawn, disabled, with this sentence under them — never hidden, and never pretended.
    std::string_view cannot(Action a) const;

    /// SC_siosio's licence requires his credit, word for word, and says it must not be intentionally
    /// hidden. The page keeps it at the foot of the House menu, because a phone has no room for it
    /// anywhere else. This app has no footer at all, so Credits is a House-menu item from the first
    /// frame: a condition of use, not polish. The words are catio/art/CREDITS.md.
    std::string_view credits() const;

private:
    struct Impl;
    Impl* impl_;
};

}  // namespace catio::ui

#endif  // CATIO_UI_H
